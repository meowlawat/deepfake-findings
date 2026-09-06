#!/usr/bin/env python3
"""E4 (robustness under the transform suite) and E5 (watermarked-fraction
sweep) - docs/03 S2.

E4: for each transform class, rebuild calibration+test under that transform,
refit F0-F5, and report the same metrics as E3. Each transform is its own
mini-experiment, which is what docs/02 S2's pooled-p_0 resolution implies:
p_0 reflects the channel actually being scored, not a clean-channel oracle
smuggled into a transformed evaluation.

E5: sweep rho, the fraction of media that carries a watermark at all. Uses
one already-built test set and selects one row per item (clean OR
watermarked) via pipeline.select_rho_mixture, so the sweep costs no extra
detector inference.

Usage:
    python scripts/e4_e5_transforms_rho.py --config config.yaml --detector effnet
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
from deepfake_interference import fusion
from deepfake_interference import metrics
from deepfake_interference import transforms as tf_mod
from deepfake_interference.pipeline import build_fusion_dataset, select_rho_mixture


def summarise(name: str, model: fusion.FusionModel, test: fusion.FusionInputs, cfg: dict) -> dict:
    probs = model.predict_proba(test)
    y = test.y
    cost = cfg["cost_model"]
    tau_lo, tau_hi = metrics.chow_thresholds(cost["c_fn"], cost["c_fp"], cost["c_r"])
    has_both_groups = (test.w == 1).any() and (test.w == 0).any()
    return {
        "model": name,
        "auc": metrics.auc(y, probs),
        "ece": metrics.expected_calibration_error(y, probs, n_bins=cfg["fusion"]["n_bins_ece"]),
        "delta_ece_w": metrics.calibration_gap_by_watermark(y, probs, test.w, n_bins=cfg["fusion"]["n_bins_ece"])
                        if has_both_groups else None,
        "aurc": metrics.area_under_risk_coverage(y, probs),
        "drd": metrics.decision_risk_deviation(y, probs, tau_lo, tau_hi, cost["c_fn"], cost["c_fp"], cost["c_r"]),
        "beta4": fusion.interference_coefficient(model),
        "n_test": int(len(y)),
    }


def run_e4(splits, cfg, detector_name) -> list[dict]:
    out = []
    for tname, grid in tf_mod.TRANSFORM_GRID.items():
        for params in grid:
            label = f"{tname}({','.join(f'{k}={v}' for k, v in params.items())})"
            transform = lambda img, _t=tname, _p=params: tf_mod.apply(_t, img, **_p)
            print(f"  [E4] {label} ...", flush=True)
            cal, _, _ = build_fusion_dataset(splits.calibration, cfg, detector_name, seed=11, transform=transform)
            test, p0, _ = build_fusion_dataset(splits.test, cfg, detector_name, seed=12, transform=transform)
            for model_name in cfg["fusion"]["models"]:
                model = fusion.fit(model_name, cal)
                row = summarise(model_name, model, test, cfg)
                row.update({"transform": label, "p0": p0})
                out.append(row)
                print(f"     {model_name}: AUC={row['auc']:.3f} ECE={row['ece']:.4f} DRD={row['drd']:.4f}")
    return out


def run_e5(splits, cfg, detector_name) -> list[dict]:
    """Fit once on the full calibration set, then evaluate on rho-mixtures of
    the test set. Fitting stays fixed across rho deliberately: rho is a
    property of the deployment stream, not something a deployed model gets to
    retrain against per-stream.
    """
    cal, _, _ = build_fusion_dataset(splits.calibration, cfg, detector_name, seed=21)
    test, _, row_meta = build_fusion_dataset(splits.test, cfg, detector_name, seed=22)

    out = []
    for scheme in cfg["watermark"]["schemes"]:
        for rho in cfg["rho_sweep"]:
            mixed = select_rho_mixture(test, row_meta, scheme=scheme, rho=rho, seed=33)
            for model_name in cfg["fusion"]["models"]:
                model = fusion.fit(model_name, cal)
                row = summarise(model_name, model, mixed, cfg)
                row.update({"scheme": scheme, "rho": rho})
                out.append(row)
            print(f"  [E5] scheme={scheme} rho={rho}: n={len(mixed.y)} "
                  f"watermarked={int(mixed.w.sum())}", flush=True)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--detector", default="effnet", choices=["vit", "effnet"])
    parser.add_argument("--skip-e4", action="store_true", help="E4 is the expensive half (one full rebuild per transform)")
    parser.add_argument("--out", default="results/e4_e5.json")
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text())
    items = data_mod.discover(Path(cfg["dataset"]["root"]))
    splits = data_mod.stratified_split(items, cfg["dataset"]["calibration_fraction"], cfg["dataset"]["split_seed"])
    print(f"calibration={len(splits.calibration)} test={len(splits.test)} detector={args.detector}")

    e4 = [] if args.skip_e4 else run_e4(splits, cfg, args.detector)
    e5 = run_e5(splits, cfg, args.detector)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"detector": args.detector, "e4": e4, "e5": e5}, indent=2))
    print(f"Results written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
