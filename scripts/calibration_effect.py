#!/usr/bin/env python3
"""Measure, rather than argue, that attenuation breaks calibration.

The paper's central claim is that shrinking a detector's log-odds evidence
changes the score-to-posterior mapping, so a threshold calibrated on
unperturbed media is wrong on perturbed media. Until now that was an
argument. This measures it.

Protocol (fixed before running; no arm-specific tuning):
  1. Split the scored images in half: CALIBRATION and EVAL, stratified, seeded.
  2. Fit a calibrator on the CALIBRATION half of the **clean** arm only.
     This is the deployment story: you calibrate on clean media, once.
  3. Apply that frozen calibrator to the EVAL half of every arm.
  4. Report ECE, Brier, reliability, and the realised risk under a Chow rule
     whose thresholds were derived from the clean calibration.

If attenuation is inert for decisions, ECE stays flat across arms. If the
paper's claim is right, ECE rises on the null (attenuated) arm while the
watermark arms stay closer to clean.

Both Platt (parametric, monotone in the logit) and isotonic (non-parametric)
are reported. Platt is the honest primary: it is the calibrator most
deployments actually use, and being monotone it CANNOT undo a monotone
attenuation by construction -- which is precisely why attenuation is
dangerous. Isotonic is shown as the generous comparison.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from deepfake_interference import metrics


def load_arms(shard_glob: str):
    recs = []
    for f in sorted(glob.glob(shard_glob)):
        recs.extend(json.loads(Path(f).read_text())["records"])
    by = defaultdict(dict)
    for r in recs:
        by[r["idx"]][r["arm"]] = (r["v"], r["y"])
    idx = sorted(k for k, d in by.items() if len(d) == 5)
    y = np.array([next(iter(by[i].values()))[1] for i in idx])
    arms = {a: np.array([by[i][a][0] for i in idx]) for a in by[idx[0]]}
    return arms, y


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shards", default="results/large/validation/effnet/chunk_*.json")
    ap.add_argument("--out", default="results/calibration_effect.json")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-bins", type=int, default=15)
    args = ap.parse_args()

    arms, y = load_arms(args.shards)
    n = len(y)
    rng = np.random.default_rng(args.seed)
    perm = rng.permutation(n)
    cal_idx, ev_idx = perm[: n // 2], perm[n // 2:]
    print(f"images={n}  calibration={len(cal_idx)}  eval={len(ev_idx)}")

    clean = arms["clean"]

    # Frozen calibrators, fit on CLEAN calibration half only.
    platt = LogisticRegression()
    platt.fit(clean[cal_idx].reshape(-1, 1), y[cal_idx])
    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(clean[cal_idx], y[cal_idx])

    cost = {"c_fn": 100, "c_fp": 20, "c_r": 1}
    tau_lo, tau_hi = metrics.chow_thresholds(**cost)

    rows = []
    for arm, v in arms.items():
        ve, ye = v[ev_idx], y[ev_idx]
        for name, p in (("platt", platt.predict_proba(ve.reshape(-1, 1))[:, 1]),
                         ("isotonic", iso.predict(ve))):
            p = np.clip(p, 1e-6, 1 - 1e-6)
            rows.append({
                "arm": arm, "calibrator": name,
                "ece": metrics.expected_calibration_error(ye, p, n_bins=args.n_bins),
                "brier": metrics.brier_score(ye, p),
                "auc": metrics.auc(ye, p),
                "drd": metrics.decision_risk_deviation(ye, p, tau_lo, tau_hi, **cost),
                "mean_prob": float(p.mean()),
                "n": int(len(ye)),
            })
        tr = metrics.evidence_transfer(clean[ev_idx], ve)
        rows[-1]["slope_vs_clean"] = tr["slope"]
        rows[-1]["intercept_vs_clean"] = tr["intercept"]

    print(f"\nFrozen calibrator fit on CLEAN only. Chow thresholds "
          f"tau=({tau_lo:.3f},{tau_hi:.3f}) from c_fn/c_fp/c_r={cost}\n")
    print(f"{'arm':18s} {'calib':9s} {'ECE':>8s} {'Brier':>8s} {'AUC':>7s} {'DRD':>8s}")
    for r in rows:
        print(f"{r['arm']:18s} {r['calibrator']:9s} {r['ece']:8.4f} {r['brier']:8.4f} "
              f"{r['auc']:7.4f} {r['drd']:8.4f}")

    base = {r["calibrator"]: r["ece"] for r in rows if r["arm"] == "clean"}
    print("\nECE degradation vs clean (same frozen calibrator):")
    for r in rows:
        if r["arm"] != "clean":
            print(f"  {r['arm']:18s} {r['calibrator']:9s} "
                  f"dECE={r['ece'] - base[r['calibrator']]:+.4f}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(
        {"rows": rows, "thresholds": [tau_lo, tau_hi], "cost": cost, "n_images": n}, indent=2))
    print(f"\nWritten to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
