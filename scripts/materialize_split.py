#!/usr/bin/env python3
"""Materialise one HF split to local PNGs once, so parallel shards read from
disk instead of each re-streaming the same parquet files over the network.

Measured: four shards streaming the validation split independently produced
zero completed chunks in nine minutes with the dataset cache still empty --
the bottleneck was 4x redundant download, not compute.

PNG (lossless) is deliberate. This study measures the effect of imperceptible
perturbations, so re-encoding the corpus as JPEG would inject compression
artefacts into the very signal being measured.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
from datasets import load_dataset


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="validation")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--size", type=int, default=256)
    ap.add_argument("--out", default="data/corpus")
    args = ap.parse_args()

    root = Path(args.out) / args.split
    for sub in ("real", "fake"):
        (root / sub).mkdir(parents=True, exist_ok=True)

    ds = load_dataset("TheKernel01/140k-Real-and-Fake-Faces", split=args.split, streaming=True)
    names = {0: "real", 1: "fake"}
    n = 0
    for i, ex in enumerate(ds):
        if args.limit is not None and i >= args.limit:
            break
        path = root / names[int(ex["label"])] / f"{i:06d}.png"
        if not path.exists():
            img = np.array(ex["image"].convert("RGB"))
            if img.shape[0] != args.size or img.shape[1] != args.size:
                img = cv2.resize(img, (args.size, args.size), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        n += 1
        if n % 1000 == 0:
            print(f"  {n} images", flush=True)

    print(f"done: {n} images -> {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
