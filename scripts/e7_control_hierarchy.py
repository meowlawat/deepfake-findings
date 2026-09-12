#!/usr/bin/env python3
"""E7: the control hierarchy - is the watermark still distinguishable once the
control matches the watermark's spectrum, not merely its PSNR?

The paper's causal claim rests on one control: a payload-free perturbation
matched per image to the watermark's PSNR. Its documented weakness is that
PSNR fixes only perturbation *energy*, so a mid-frequency transform-domain
mark and broadband noise can share a PSNR while putting that energy in
completely different places. A reviewer can therefore say the comparison is
unfair to the watermark, and nothing in the previous experiments answers them.

This script adds a strictly stronger control and scores seven arms per image:

    clean
    <scheme>            the watermark
    null[<scheme>]      payload-free, PSNR-matched          (the old control)
    spec[<scheme>]      payload-free, PSNR- AND spectrum-matched   (new)

for each of the two schemes. spec[] is built by phase-randomising the
watermark's own per-image residual, so it carries the identical power spectrum
with no payload and no spatial structure from the mark.

The inference this licenses, either way, is sharper than before:

  - if the watermark still transfers evidence differently from spec[], the
    difference is not explained by energy or second-order spectral statistics,
    which is positive evidence for watermark-specific structure;
  - if the watermark becomes indistinguishable from spec[], the generic-
    perturbation explanation strengthens and the paper must say so.

Split: the held-out `test` split at an index offset past every image any
earlier analysis touched (exploratory n=300 used data/raw; E4/E5 used the
first 400 of `test`). --offset 1000 keeps this analysis disjoint from both.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import yaml


def iter_split(local_dir: Path, split: str, offset: int, limit: int, image_size: int):
    """Balanced, deterministic, offset past previously-touched indices."""
    import cv2
    root = Path(local_dir) / split
    per_class = limit // 2
    items = []
    for label, sub in ((0, "real"), (1, "fake")):
        ps = sorted((root / sub).glob("*.png"))[offset: offset + per_class]
        items += [(p, label) for p in ps]
    items.sort(key=lambda t: (t[0].name, t[1]))
    for i, (path, label) in enumerate(items):
        bgr = cv2.imread(str(path))
        if bgr is None:
            continue
        if bgr.shape[0] != image_size:
            bgr = cv2.resize(bgr, (image_size, image_size), interpolation=cv2.INTER_AREA)
        yield i, cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), label, path.name


def build_arms(image, schemes, payload_bits, seed, tol_db):
    """All seven arms for one image, plus the quality metrics that prove each
    control is actually matched (reported, not assumed)."""
    from deepfake_interference import null_perturbation as NP
    from deepfake_interference import watermark as W

    rng = np.random.default_rng(seed)
    arms = {"clean": image}
    meta = {}
    for scheme in schemes:
        bits = list(rng.integers(0, 2, payload_bits))
        res = W.embed(image, bits, scheme)
        arms[scheme] = res.watermarked
        resid = res.watermarked.astype(np.float32) - image.astype(np.float32)

        psnr_null = NP.match_to_target(image, target_psnr=res.psnr, rng=rng,
                                       tolerance_db=tol_db)
        arms[f"null[{scheme}]"] = psnr_null.perturbed

        spec_null = NP.match_spectrum_and_psnr(image, resid, target_psnr=res.psnr,
                                               rng=rng, tolerance_db=tol_db)
        arms[f"spec[{scheme}]"] = spec_null.perturbed

        meta[scheme] = {
            "wm_psnr": res.psnr, "wm_ssim": res.ssim,
            "null_psnr": psnr_null.psnr, "null_ssim": psnr_null.ssim,
            "spec_psnr": spec_null.psnr, "spec_ssim": spec_null.ssim,
            "spec_gain": spec_null.noise_scale,
        }
    return arms, meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--local-dir", default="data/corpus")
    ap.add_argument("--split", default="test")
    ap.add_argument("--offset", type=int, default=1000)
    ap.add_argument("--limit", type=int, default=2000)
    ap.add_argument("--chunk-size", type=int, default=100)
    ap.add_argument("--detectors", nargs="*", default=["effnet", "own"])
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--num-shards", type=int, default=1)
    ap.add_argument("--torch-threads", type=int, default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out-dir", default="results/e7_control_hierarchy")
    args = ap.parse_args()

    if args.torch_threads:
        import torch
        torch.set_num_threads(args.torch_threads)

    from deepfake_interference.detectors import Detector, OwnDetector

    cfg = yaml.safe_load(Path(args.config).read_text())
    schemes = cfg["watermark"]["schemes"]
    payload_bits = cfg["watermark"]["payload_bits"]
    tol_db = cfg["watermark"]["null_tolerance_db"]
    image_size = cfg["dataset"]["image_size"]

    detectors = {}
    for name in args.detectors:
        spec = cfg["detectors"][name]
        detectors[name] = (OwnDetector(spec[len("own:"):]) if spec.startswith("own:")
                           else Detector(spec))
        detectors[name]._load()

    arm_names = (["clean"]
                 + [s for s in schemes]
                 + [f"null[{s}]" for s in schemes]
                 + [f"spec[{s}]" for s in schemes])

    out_dir = Path(args.out_dir) / args.split
    out_dir.mkdir(parents=True, exist_ok=True)
    done = {int(p.stem.split("_")[-1]) for p in out_dir.glob("chunk_*.json")}

    stream = iter_split(Path(args.local_dir), args.split, args.offset, args.limit, image_size)
    chunk_id, n_done, t0 = 0, 0, time.time()
    print(f"arms={arm_names} detectors={list(detectors)} shard={args.shard}/{args.num_shards}",
          flush=True)

    while True:
        chunk = []
        for _ in range(args.chunk_size):
            try:
                chunk.append(next(stream))
            except StopIteration:
                break
        if not chunk:
            break
        if (chunk_id % args.num_shards) != args.shard or chunk_id in done:
            chunk_id += 1
            continue

        records, quality = [], []
        built = []
        for idx, img, label, fname in chunk:
            arms, meta = build_arms(img, schemes, payload_bits, args.seed + idx, tol_db)
            built.append((idx, label, fname, arms))
            quality.append({"idx": int(idx), "file": fname, **meta})

        for arm in arm_names:
            images = [a[arm] for _, _, _, a in built]
            for det_name, det in detectors.items():
                for (idx, label, fname, _), r in zip(built, det.score_batch(images)):
                    records.append({"arm": arm, "y": label, "detector": det_name,
                                    "v": r.v, "idx": int(idx), "file": fname})

        (out_dir / f"chunk_{chunk_id:05d}.json").write_text(
            json.dumps({"records": records, "quality": quality}))
        n_done += len(chunk)
        rate = n_done / max(1e-9, time.time() - t0)
        print(f"chunk {chunk_id:05d} images={n_done} {rate:.2f} img/s", flush=True)
        chunk_id += 1

    print(f"done: {n_done} images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
