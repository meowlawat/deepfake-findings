#!/usr/bin/env python3
"""E2/E3 - does interference propagate into fusion, and does the correction
work (docs/03 S2)? Fits F0-F5 on a calibration split, evaluates on test,
reports ECE/Delta-ECE_W/AURC/selective risk/DRD per model, and beta_4 with a
bootstrap CI.

Builds its own scored dataset via pipeline.build_fusion_dataset rather than
reusing E1's records: E1 only needed V, while fusion needs per-item BER too
(for z_P), and E1's null-perturbation arm is a diagnostic that fusion never
sees - deployment presents media that is watermarked or isn't, never a
payload-free control. Cost is the same order as E1's pass, not larger.

Usage:
    python scripts/e2_e3_fusion.py --config config.yaml
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
from deepfake_interference import stats
from deepfake_interference.pipeline import build_fusion_dataset


def evaluate_model(name: str, model: fusion.FusionModel, test: fusion.FusionInputs, cfg: dict) -> dict:
    probs = model.predict_proba(test)
    y = test.y

    ece = metrics.expected_calibration_error(y, probs, n_bins=cfg["fusion"]["n_bins_ece"])
    brier = metrics.brier_score(y, probs)
    d_ece_w = metrics.calibration_gap_by_watermark(y, probs, test.w, n_bins=cfg["fusion"]["n_bins_ece"])
    auc = metrics.auc(y, probs)
    aurc = metrics.area_under_risk_coverage(y, probs)

    cost = cfg["cost_model"]
    tau_lo, tau_hi = metrics.chow_thresholds(cost["c_fn"], cost["c_fp"], cost["c_r"])
    drd = metrics.decision_risk_deviation(y, probs, tau_lo, tau_hi, cost["c_fn"], cost["c_fp"], cost["c_r"])

    beta4 = fusion.interference_coefficient(model)
    beta4_ci = None
    if beta4 is not None:
        def _beta4_stat(v, z_p, w, b, y):
            data = fusion.FusionInputs(v=v, z_p=z_p, w=w, b=b, y=y)
            m = fusion.fit(name, data)
            return fusion.interference_coefficient(m)

        point, lo, hi = stats.bootstrap_ci(
            {"v": test.v, "z_p": test.z_p, "w": test.w, "b": test.b, "y": test.y},
            _beta4_stat, n_boot=cfg["fusion"]["n_bootstrap"], ci=cfg["fusion"]["bootstrap_ci"],
            seed=cfg["fusion"]["bootstrap_seed"],
        )
        beta4_ci = {"point": point, "lo": lo, "hi": hi}

    # reliability curve per W group, for F1 (the money figure). Split, never
    # pooled - docs/02 S6.
    reliability = {}
    for group in (0, 1):
        mask = test.w == group
        if mask.sum() >= 10:
            conf, acc = metrics.reliability_curve(y[mask], probs[mask], n_bins=10)
            reliability[str(group)] = {"confidence": conf, "accuracy": acc, "n": int(mask.sum())}

    return {
        "model": name, "auc": auc, "ece": ece, "brier": brier,
        "delta_ece_w": d_ece_w, "aurc": aurc, "drd": drd,
        "tau_lo": tau_lo, "tau_hi": tau_hi,
        "beta4": beta4, "beta4_ci": beta4_ci,
        "coefficients": model.coef_by_name,
        "reliability": reliability,
        "selective_risk": {
            str(c): metrics.selective_risk_at_coverage(y, probs, c) for c in (0.8, 0.9, 0.95)
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--detector", default="effnet", choices=["vit", "effnet"],
                         help="which detector's V to fuse (run twice for both)")
    parser.add_argument("--limit", type=int, default=None, help="cap items (stratified) for a smoke run")
    parser.add_argument("--out", default="results/e2_e3_fusion.json")
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text())
    items = data_mod.discover(Path(cfg["dataset"]["root"]))
    if args.limit:
        by_label = {}
        for it in items:
            by_label.setdefault(it.label, []).append(it)
        per_class = max(1, args.limit // max(1, len(by_label)))
        items = [it for g in by_label.values() for it in g[:per_class]]

    splits = data_mod.stratified_split(items, cfg["dataset"]["calibration_fraction"], cfg["dataset"]["split_seed"])
    print(f"calibration={len(splits.calibration)} test={len(splits.test)}")

    cal_data, p0_cal, _ = build_fusion_dataset(splits.calibration, cfg, args.detector, seed=1)
    test_data, p0_test, _ = build_fusion_dataset(splits.test, cfg, args.detector, seed=2)
    print(f"p_0 estimated on calibration split: {p0_cal}")

    results = []
    for model_name in cfg["fusion"]["models"]:
        model = fusion.fit(model_name, cal_data)
        result = evaluate_model(model_name, model, test_data, cfg)
        results.append(result)
        beta4_str = f"beta4={result['beta4']:+.4f}" if result["beta4"] is not None else "beta4=n/a"
        print(f"  {model_name}: AUC={result['auc']:.3f} ECE={result['ece']:.4f} "
              f"dECE_W={result['delta_ece_w']:+.4f} AURC={result['aurc']:.4f} "
              f"DRD={result['drd']:.4f} {beta4_str}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"detector": args.detector, "p0_calibration": p0_cal, "results": results}, indent=2))
    print(f"Results written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
