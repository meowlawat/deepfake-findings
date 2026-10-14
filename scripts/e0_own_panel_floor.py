#!/usr/bin/env python3
"""E0 floor gate for the disclosed-provenance probe panel (docs/07 step 3).

A detector that cannot separate real from fake on this corpus tells us nothing
about whether watermarking perturbs its evidence, so every probe must clear the
floor before its slopes are fitted, not after. Five of six screened *public*
checkpoints failed exactly this gate (docs/04 R14), which is why the gate runs
first here too rather than being assumed away for probes we trained ourselves.

Two design choices make the resulting numbers comparable:

  - **The same images as the slopes.** Baseline AUC is measured on the clean
    arm of E7's evaluation slice (`test`, offset 1000, 800 balanced images),
    reusing E7's own `iter_split` rather than a re-implementation, so the
    population the gate is measured on is the population the regression is fit
    on. A probe that clears the floor on some other split has not been shown to
    clear it here.
  - **The same split for every probe.** ResNet-18, ConvNeXt-Base and ViT-B/16
    are scored on identical pixels, so a difference between them is a
    difference in the probe and not in the sample.

Reports AUC per probe against `detectors.floor_auc` from config. A probe below
the floor is reported as below the floor; it is not retrained, re-split or
re-headed until it passes.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import yaml


def _load_e7():
    """Import E7's module so the evaluation slice is literally the same code,
    not a copy that can drift from it."""
    path = Path(__file__).resolve().parent / "e7_control_hierarchy.py"
    spec = importlib.util.spec_from_file_location("e7_control_hierarchy", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--local-dir", default="data/corpus")
    ap.add_argument("--split", default="test")
    ap.add_argument("--offset", type=int, default=1000, help="must match E7's")
    ap.add_argument("--limit", type=int, default=800, help="must match E7's")
    ap.add_argument("--detectors", nargs="+",
                    default=["own", "own_convnext", "own_vit"])
    ap.add_argument("--out", default="results/e0_own_panel_floor.json")
    args = ap.parse_args()

    from sklearn.metrics import roc_auc_score
    from deepfake_interference.detectors import Detector, OwnDetector

    e7 = _load_e7()
    cfg = yaml.safe_load(Path(args.config).read_text())
    floor = float(cfg["detectors"].get("floor_auc", 0.80))
    image_size = cfg["dataset"]["image_size"]

    print(f"loading clean slice: {args.split} offset={args.offset} n={args.limit}",
          flush=True)
    images, labels = [], []
    for _, img, label, _ in e7.iter_split(Path(args.local_dir), args.split,
                                          args.offset, args.limit, image_size):
        images.append(img)
        labels.append(label)
    y = np.asarray(labels)
    print(f"  {len(images)} images, {int(y.sum())} fake / {int((1-y).sum())} real",
          flush=True)

    report = {"split": args.split, "offset": args.offset, "n": len(images),
              "floor_auc": floor, "detectors": {}}

    for name in args.detectors:
        spec = cfg["detectors"][name]
        det = (OwnDetector(spec[len("own:"):]) if spec.startswith("own:")
               else Detector(spec))
        t0 = time.time()
        v = np.array([r.v for r in det.score_batch(images)])
        auc = float(roc_auc_score(y, v))
        passed = auc >= floor
        report["detectors"][name] = {
            "model": spec, "baseline_auc": auc,
            "clears_floor": passed, "seconds": round(time.time() - t0, 1),
        }
        print(f"  {name:14s} AUC={auc:.4f}  "
              f"{'PASS' if passed else 'BELOW FLOOR'}  ({time.time()-t0:.0f}s)",
              flush=True)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=1))
    print(f"\nwritten to {args.out}")
    below = [n for n, d in report["detectors"].items() if not d["clears_floor"]]
    if below:
        print(f"BELOW FLOOR (reported, not silently dropped): {below}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
