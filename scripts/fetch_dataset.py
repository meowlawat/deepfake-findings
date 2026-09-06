#!/usr/bin/env python3
"""Fetch a balanced subset of the v1 dataset without needing a Kaggle account.

`TheKernel01/140k-Real-and-Fake-Faces` on the Hugging Face Hub is a mirror of
the exact Kaggle dataset docs/03 S0 names (`xhlulu/140k-real-and-fake-faces`):
same 140k images, same real/fake labels, plus a `generator` field (Real vs
StyleGAN). License `cc`. Verified to exist and match this session by
inspecting its dataset card before use.

Streams the test split (which alone contains both classes) rather than
downloading all ~4GB, and writes a balanced subset to disk as
data/raw/{real,fake}/*.png, the layout data.py expects.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from datasets import load_dataset


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-per-class", type=int, default=150)
    parser.add_argument("--out", default="data/raw")
    parser.add_argument("--split", default="test")
    args = parser.parse_args()

    out_root = Path(args.out)
    (out_root / "real").mkdir(parents=True, exist_ok=True)
    (out_root / "fake").mkdir(parents=True, exist_ok=True)

    print(f"Streaming TheKernel01/140k-Real-and-Fake-Faces [{args.split}] ...")
    ds = load_dataset("TheKernel01/140k-Real-and-Fake-Faces", split=args.split, streaming=True)

    counts = {0: 0, 1: 0}
    names = {0: "real", 1: "fake"}
    for example in ds:
        label = example["label"]
        if counts[label] >= args.n_per_class:
            if all(c >= args.n_per_class for c in counts.values()):
                break
            continue
        img = example["image"].convert("RGB")
        out_path = out_root / names[label] / f"{names[label]}_{counts[label]:05d}.png"
        img.save(out_path)
        counts[label] += 1
        if sum(counts.values()) % 50 == 0:
            print(f"  ... real={counts[0]} fake={counts[1]}")

    print(f"Done: real={counts[0]} fake={counts[1]} written to {out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
