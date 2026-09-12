#!/usr/bin/env python3
"""Screen candidate detectors against E0's floor - docs/03 E0, docs/04 R14.

Why this exists: E1's null currently rests on a single functioning detector,
because the other candidate came in at chance. A null measured on one model
is weak evidence - it cannot distinguish "watermarking does not interfere"
from "this particular checkpoint happens not to respond". Widening the pool
of detectors that clear the floor is the cheapest available way to
strengthen (or overturn) the negative result.

Each candidate costs one forward pass per image, so screening is far cheaper
than the full interference run and can be done first.

Usage:
    python scripts/screen_detectors.py --limit 300
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import yaml

from deepfake_interference import data as data_mod
from deepfake_interference import metrics
from deepfake_interference.detectors import Detector

CANDIDATES = [
    "Wvolf/ViT_Deepfake_Detection",
    "Skullly/DeepFake-EN-B6",
    "dima806/deepfake_vs_real_image_detection",
    "prithivMLmods/Deep-Fake-Detector-v2-Model",
    "Hemg/Deepfake-Detection",
    "DaMsTaR/Detecto-DeepFake_Image_Detector",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--out", default="results/detector_screen.json")
    parser.add_argument("--models", nargs="*", default=CANDIDATES)
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text())
    items = data_mod.discover(Path(cfg["dataset"]["root"]))
    if args.limit:
        by_label: dict[int, list] = {}
        for it in items:
            by_label.setdefault(it.label, []).append(it)
        per_class = max(1, args.limit // max(1, len(by_label)))
        items = [it for g in by_label.values() for it in g[:per_class]]

    images = [(data_mod.load_image(it, size=cfg["dataset"]["image_size"]), it.label) for it in items]
    floor = cfg["detectors"]["floor_auc"]
    suspicion = cfg["detectors"]["leakage_suspicion_auc"]

    rows = []
    for model_id in args.models:
        try:
            det = Detector(model_id)
            v = np.array([det.score(img).v for img, _ in images])
            y = np.array([label for _, label in images])
            auc = metrics.auc(y, v)
            if np.isnan(auc):
                status = "NaN (single-class subset?)"
            elif auc < floor:
                status = f"FAIL (< {floor})"
            elif auc >= suspicion:
                status = f"PASS but SUSPECT LEAKAGE (>= {suspicion})"
            else:
                status = "PASS"
            rows.append({"model_id": model_id, "auc": None if np.isnan(auc) else float(auc),
                          "n": len(y), "status": status})
            print(f"  {model_id:48s} AUC={auc:.4f}  {status}", flush=True)
        except Exception as e:
            rows.append({"model_id": model_id, "auc": None, "n": len(images),
                          "status": f"LOAD FAILED: {type(e).__name__}"})
            print(f"  {model_id:48s} LOAD FAILED: {e}", flush=True)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(rows, indent=2))

    passing = [r for r in rows if r["status"].startswith("PASS")]
    print(f"\n{len(passing)}/{len(rows)} candidates clear the {floor} floor.")
    print("A null measured on one detector is weak; on several independent")
    print("backbones that each clear the floor, it is a much harder result to")
    print("dismiss as checkpoint-specific.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
