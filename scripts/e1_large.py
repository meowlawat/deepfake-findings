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
    """Stream the HF corpus rather than materialising 4GB of PNGs on disk."""
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


def run_split(split: str, cfg, args, detectors) -> int:
    schemes = cfg["watermark"]["schemes"]
    payload_bits = cfg["watermark"]["payload_bits"]
    tol_db = cfg["watermark"]["null_tolerance_db"]
    image_size = cfg["dataset"]["image_size"]
    arms = ["clean"] + [s for s in schemes] + [f"null[{s}]" for s in schemes]

    out_dir = Path(args.out_dir) / split
    out_dir.mkdir(parents=True, exist_ok=True)

    done_chunks = {int(p.stem.split("_")[-1]) for p in out_dir.glob("chunk_*.json")}
    if done_chunks:
        print(f"[{split}] resuming; {len(done_chunks)} chunk(s) already on disk", flush=True)

    stream = iter_hf_split(split, args.limit, image_size)
    chunk, chunk_id, n_written = [], 0, 0
    t0 = time.time()

    pool = ProcessPoolExecutor(max_workers=args.workers)
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

            if chunk_id in done_chunks:
                chunk_id += 1
                continue

            jobs = [(idx, img, label, schemes, payload_bits, args.seed + idx, tol_db)
                    for idx, img, label in chunk]
            embedded = list(pool.map(_embed_one, jobs, chunksize=4))
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
    parser.add_argument("--out-dir", default="results/large")
    args = parser.parse_args()

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

    print(f"workers={args.workers} chunk_size={args.chunk_size} splits={args.splits}", flush=True)

    total = 0
    for split in args.splits:
        total += run_split(split, cfg, args, detectors)
    print(f"done: {total} images scored across {len(args.splits)} split(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
