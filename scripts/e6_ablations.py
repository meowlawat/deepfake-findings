#!/usr/bin/env python3
"""E6 ablations - docs/03 S2.

Three ablations, each isolating one design choice the method doc argues for:

1. `z_P` (the binomial LLR) vs raw BER as the provenance feature. docs/02 S2
   claims the LLR is the right quantity and raw BER discards information;
   this measures whether that matters in practice or is only theoretically tidy.
2. Raw logit vs softmax probability for V. docs/02 S1 uses the raw logit on
   the grounds that softmax confidence is unreliable under perturbation/OOD.
3. A nonlinear fuser (gradient boosting) as a control - docs/04 R4. The
   objection "your fusion is just logistic regression over three terms" is
   answered by showing a black-box fuser does not fix the calibration gap
   either, rather than by arguing about it.

Usage:
    python scripts/e6_ablations.py --config config.yaml --detector effnet
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import yaml
from sklearn.ensemble import GradientBoostingClassifier

from deepfake_interference import data as data_mod
from deepfake_interference import fusion
from deepfake_interference import metrics
from deepfake_interference.pipeline import build_fusion_dataset


def _report(y, probs, w, cfg, label) -> dict:
    cost = cfg["cost_model"]
    tau_lo, tau_hi = metrics.chow_thresholds(cost["c_fn"], cost["c_fp"], cost["c_r"])
    return {
        "variant": label,
        "auc": metrics.auc(y, probs),
        "ece": metrics.expected_calibration_error(y, probs, n_bins=cfg["fusion"]["n_bins_ece"]),
        "delta_ece_w": metrics.calibration_gap_by_watermark(y, probs, w, n_bins=cfg["fusion"]["n_bins_ece"]),
        "aurc": metrics.area_under_risk_coverage(y, probs),
        "drd": metrics.decision_risk_deviation(y, probs, tau_lo, tau_hi, cost["c_fn"], cost["c_fp"], cost["c_r"]),
    }


def ablation_zp_vs_ber(cal, test, cfg) -> list[dict]:
    """Swap z_P for raw BER in F3's design matrix. Implemented by handing the
    fusion model a FusionInputs whose z_p column literally holds BER, so the
    only thing that differs is the provenance feature's parameterisation.
    """
    out = []
    model = fusion.fit("F3", cal)
    out.append(_report(test.y, model.predict_proba(test), test.w, cfg, "F3 with z_P (LLR)"))

    cal_ber = fusion.FusionInputs(v=cal.v, z_p=cal.b, w=cal.w, b=cal.b, y=cal.y)
    test_ber = fusion.FusionInputs(v=test.v, z_p=test.b, w=test.w, b=test.b, y=test.y)
    model_ber = fusion.fit("F3", cal_ber)
    out.append(_report(test_ber.y, model_ber.predict_proba(test_ber), test_ber.w, cfg, "F3 with raw BER"))
    return out


def ablation_logit_vs_softmax(cal, test, cfg) -> list[dict]:
    """docs/02 S1 uses the raw logit for V, on the grounds that softmax
    confidence is unreliable under perturbation/OOD. V here is
    logit_fake - logit_real, so the corresponding softmax probability is
    exactly sigmoid(V) - a monotone squashing. That means AUC is invariant by
    construction (ranking is unchanged) and only the calibration-sensitive
    metrics can move. Reporting AUC alongside makes that invariance visible
    rather than looking like a null result: if ECE/DRD shift while AUC does
    not, the squashing is doing exactly what docs/02 S1 says it does.
    """
    def squash(d):
        return fusion.FusionInputs(
            v=1.0 / (1.0 + np.exp(-d.v)), z_p=d.z_p, w=d.w, b=d.b, y=d.y)

    model = fusion.fit("F3", cal)
    out = [_report(test.y, model.predict_proba(test), test.w, cfg, "F3 with raw logit V")]

    cal_s, test_s = squash(cal), squash(test)
    model_s = fusion.fit("F3", cal_s)
    out.append(_report(test_s.y, model_s.predict_proba(test_s), test_s.w, cfg,
                        "F3 with softmax-prob V"))
    return out


def ablation_nonlinear_fuser(cal, test, cfg) -> list[dict]:
    """docs/04 R4's control: does a black-box fuser close the calibration gap?"""
    def design(d):
        z = np.where(d.w == 1, np.nan_to_num(d.z_p), 0.0)
        b = np.where(d.w == 1, np.nan_to_num(d.b), 0.0)
        return np.column_stack([d.v, z, d.w.astype(float), d.w * d.v, b * d.v])

    clf = GradientBoostingClassifier(random_state=0)
    clf.fit(design(cal), cal.y)
    probs = clf.predict_proba(design(test))[:, 1]
    return [_report(test.y, probs, test.w, cfg, "gradient boosting (nonlinear control)")]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--detector", default="effnet", choices=["vit", "effnet"])
    parser.add_argument("--limit", type=int, default=None, help="cap items (stratified) for a smoke run")
    parser.add_argument("--out", default="results/e6_ablations.json")
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

    cal, p0_cal, _ = build_fusion_dataset(splits.calibration, cfg, args.detector, seed=41)
    test, _, _ = build_fusion_dataset(splits.test, cfg, args.detector, seed=42)
    print(f"p_0 (calibration): {p0_cal}")

    rows = []
    rows += ablation_zp_vs_ber(cal, test, cfg)
    rows += ablation_logit_vs_softmax(cal, test, cfg)
    rows += ablation_nonlinear_fuser(cal, test, cfg)

    for r in rows:
        print(f"  {r['variant']:38s} AUC={r['auc']:.3f} ECE={r['ece']:.4f} "
              f"dECE_W={r['delta_ece_w']:+.4f} DRD={r['drd']:.4f}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"detector": args.detector, "rows": rows}, indent=2))
    print(f"Results written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
