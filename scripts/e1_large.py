#!/usr/bin/env python3
"""E1 at corpus scale - chunked, resumable, GPU-batched.

Why this exists separately from e1_interference.py: at n=300 that script's
straight-line loop is fine. At n=140,000 three things break it.

1. **Wall clock.** Kaggle sessions die at 12h. A run with no checkpointing
   loses everything at hour 12 having produced nothing. This one writes a
   shard per chunk and resumes from whatever already exists on disk.
2. **The bottleneck flips.** On CPU, detection dominates (EfficientNet-B6
   ~341 ms/img). On GPU it does not: watermark embedding is CPU-bound and
   stays there - dwtDctSvd ~214 ms + rivaGan ~169 ms + the null search
   ~46 ms per scheme. Left serial that is ~18h of CPU work for 140k images
   and the GPU idles through all of it. So embedding runs in a process pool
   while detection runs batched on the accelerator.
3. **Leakage becomes measurable.** Scoring every split (train/val/test)
   rather than a single subset turns docs/04 R14 from an unresolvable
   caveat into a diagnostic: if these third-party detectors were fine-tuned
   on this corpus it was almost certainly the train split, so a large
   train-vs-test gap in baseline AUC is direct evidence of contamination.
   Per-split results are recorded for exactly this comparison.

Usage:
    python scripts/e1_large.py --splits test val train --chunk-size 500
    python scripts/e1_large.py --resume            # picks up where it stopped
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import yaml


def _embed_one(payload):
    """Runs in a worker process: all CPU-bound watermark work for one image.

    Returns the watermarked and null-perturbed variants as raw arrays so the
    parent can batch them onto the GPU. Deliberately does no detector work -
    the accelerator lives in the parent.
    """
    import numpy as _np
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    from deepfake_interference import null_perturbation as NP
    from deepfake_interference import watermark as W

    idx, image, label, schemes, payload_bits, seed, tol_db = payload
    rng = _np.random.default_rng(seed)
    variants = {"clean": image}
    meta = {}
    for scheme in schemes:
        bits = list(rng.integers(0, 2, payload_bits))
        res = W.embed(image, bits, scheme)
        variants[scheme] = res.watermarked
        null = NP.match_to_target(image, target_psnr=res.psnr, rng=rng, tolerance_db=tol_db)
        variants[f"null[{scheme}]"] = null.perturbed
        meta[scheme] = {"psnr": res.psnr, "ssim": res.ssim, "null_psnr": null.psnr}
    return idx, label, variants, meta


def iter_hf_split(split: str, limit: int | None, image_size: int):
    """Stream the HF corpus directly.

    Only appropriate for a SINGLE process. Parallel shards must not each call
    this: measured, four shards streaming the same split independently
    produced zero completed chunks in nine minutes with the dataset cache
    still empty, because each was re-downloading the same parquet files.
    Use scripts/materialize_split.py once, then iter_local_split.
    """
    import cv2
    from datasets import load_dataset

    ds = load_dataset("TheKernel01/140k-Real-and-Fake-Faces", split=split, streaming=True)
    for i, ex in enumerate(ds):
        if limit is not None and i >= limit:
            break
        img = np.array(ex["image"].convert("RGB"))
        if img.shape[0] != image_size or img.shape[1] != image_size:
            img = cv2.resize(img, (image_size, image_size), interpolation=cv2.INTER_AREA)
        yield i, img, int(ex["label"])


def iter_local_split(local_dir: Path, split: str, limit: int | None, image_size: int):
    """Read a materialised split from disk. Ordering is deterministic (sorted
    by filename, interleaved across classes) so every shard agrees on which
    image carries which index, and so a resumed run reproduces the same
    chunk boundaries as the run it is continuing.
    """
    import cv2

    root = Path(local_dir) / split
    by_label = []
    for label, sub in ((0, "real"), (1, "fake")):
        by_label.append([(p, label) for p in sorted((root / sub).glob("*.png"))])

    ordered = []
    for pair in zip(*by_label):          # interleave so any prefix stays balanced
        ordered.extend(pair)
    for lst in by_label:                  # append any class remainder
        ordered.extend(lst[len(ordered) // 2:])

    for i, (path, label) in enumerate(ordered):
        if limit is not None and i >= limit:
            break
        bgr = cv2.imread(str(path))
        if bgr is None:
            continue
        if bgr.shape[0] != image_size or bgr.shape[1] != image_size:
            bgr = cv2.resize(bgr, (image_size, image_size), interpolation=cv2.INTER_AREA)
        yield i, cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), label


def run_split(split: str, cfg, args, detectors) -> int:
    schemes = cfg["watermark"]["schemes"]
    payload_bits = cfg["watermark"]["payload_bits"]
    tol_db = cfg["watermark"]["null_tolerance_db"]
    image_size = cfg["dataset"]["image_size"]
    arms = ["clean"] + [s for s in schemes] + [f"null[{s}]" for s in schemes]

    # Namespace shards by detector set. Without this, a later run adding a
    # second detector would find chunk_00001.json already on disk, skip it as
    # "done", and silently never score the new detector - resume turning into
    # data loss. The tag makes "done" mean "done FOR THIS detector set".
    det_tag = "+".join(sorted(detectors))
    out_dir = Path(args.out_dir) / split / det_tag
    out_dir.mkdir(parents=True, exist_ok=True)

    done_chunks = {int(p.stem.split("_")[-1]) for p in out_dir.glob("chunk_*.json")}
    if done_chunks:
        print(f"[{split}] resuming; {len(done_chunks)} chunk(s) already on disk", flush=True)

    stream = (iter_local_split(Path(args.local_dir), split, args.limit, image_size)
              if args.local_dir else iter_hf_split(split, args.limit, image_size))
    chunk, chunk_id, n_written = [], 0, 0
    t0 = time.time()

    # workers=0 means embed inline in this process. When shards ARE the
    # parallelism (scripts/run_parallel.sh), an inner pool per shard
    # oversubscribes the box: 4 shards x (1 main + 1 worker) = 8 processes on
    # 4 cores, measured at load average 8.5 and thrashing. Inline keeps it 1:1.
    pool = ProcessPoolExecutor(max_workers=args.workers) if args.workers > 0 else None
    try:
        while True:
            chunk = []
            for _ in range(args.chunk_size):
                try:
                    chunk.append(next(stream))
                except StopIteration:
                    break
            if not chunk:
                break

            # Data-parallel sharding: each process takes every Kth chunk.
            # Composes with resume-by-existence for free, since both are just
            # "skip this chunk_id". On a CPU box this is the difference
            # between one process leaving 3 cores idle during detection and
            # K processes saturating all of them.
            if (chunk_id % args.num_shards) != args.shard or chunk_id in done_chunks:
                chunk_id += 1
                continue

            jobs = [(idx, img, label, schemes, payload_bits, args.seed + idx, tol_db)
                    for idx, img, label in chunk]
            embedded = (list(pool.map(_embed_one, jobs, chunksize=4)) if pool
                         else [_embed_one(j) for j in jobs])
            embedded.sort(key=lambda r: r[0])

            records = []
            for arm in arms:
                images = [variants[arm] for _, _, variants, _ in embedded]
                labels = [label for _, label, _, _ in embedded]
                for det_name, det in detectors.items():
                    results = det.score_batch(images, batch_size=args.batch_size)
                    for (idx, label, _, _), r in zip(embedded, results):
                        records.append({"arm": arm, "y": label, "detector": det_name,
                                         "v": r.v, "idx": int(idx), "split": split})

            quality = [{"idx": int(idx), **{k: v for k, v in meta.items()}}
                        for idx, _, _, meta in embedded]
            (out_dir / f"chunk_{chunk_id:05d}.json").write_text(
                json.dumps({"records": records, "quality": quality}))

            n_written += len(chunk)
            rate = n_written / max(1e-9, time.time() - t0)
            print(f"[{split}] chunk {chunk_id:05d}  images={n_written}  "
                  f"{rate:.2f} img/s  ({len(records)} records)", flush=True)
            chunk_id += 1
    finally:
        if pool:
            pool.shutdown(wait=True)

    return n_written


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--splits", nargs="+", default=["test", "validation", "train"],
                         help="cheapest/cleanest first: test is held out, train is where "
                              "leakage would live")
    parser.add_argument("--limit", type=int, default=None, help="cap images PER SPLIT")
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=None, help="detector batch; device default if unset")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--detectors", nargs="*", default=None,
                         help="detector keys from config; default all that config lists")
    parser.add_argument("--shard", type=int, default=0, help="this process handles chunks where id %% num_shards == shard")
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--torch-threads", type=int, default=None,
                         help="set to 1 when running several shards in parallel, so they do not oversubscribe cores")
    parser.add_argument("--local-dir", default=None,
                         help="read a materialised split from disk (scripts/materialize_split.py). "
                              "Required when running parallel shards - see iter_hf_split docstring.")
    parser.add_argument("--out-dir", default="results/large")
    args = parser.parse_args()

    if args.torch_threads:
        import torch
        torch.set_num_threads(args.torch_threads)

    from deepfake_interference.detectors import Detector

    cfg = yaml.safe_load(Path(args.config).read_text())
    det_cfg = {k: v for k, v in cfg["detectors"].items() if isinstance(v, str)}
    if args.detectors:
        det_cfg = {k: v for k, v in det_cfg.items() if k in args.detectors}
    detectors = {name: Detector(model_id) for name, model_id in det_cfg.items()}

    for name, det in detectors.items():
        det._load()
        print(f"detector {name}: {det.model_id} on {det._device} "
              f"(batch default {det.default_batch_size()})", flush=True)

    print(f"workers={args.workers} chunk_size={args.chunk_size} splits={args.splits} "
          f"shard={args.shard}/{args.num_shards}", flush=True)

    total = 0
    for split in args.splits:
        total += run_split(split, cfg, args, detectors)
    print(f"done: {total} images scored across {len(args.splits)} split(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
