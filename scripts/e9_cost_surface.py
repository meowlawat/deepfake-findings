#!/usr/bin/env python3
"""E9: does the decision-risk null survive the whole plausible cost space, or
only the one triple we happened to assume?

The paper reports that attenuation degrades calibration quality but does not
reliably move decisions. That claim was evaluated at a single assumed cost
triple, which is exactly the kind of result a reviewer should distrust: with
one configuration there is no way to tell a robust null from a lucky one.

This sweeps the cost space instead. For every (c_FN, c_FP, c_R) on a grid we
recompute Chow's thresholds, apply the frozen calibrators, and record decision
risk and DRD per arm. The reported quantity is the *fraction of the plausible
cost space* in which the null arms' decision risk separates from clean, which
is a statement about robustness rather than about one point.

Calibrators are fitted on the clean arm of the calibration half and frozen,
exactly as in the original analysis, so the only thing that varies here is the
cost model. Grid cells with an empty review band (c_R/c_FN + c_R/c_FP >= 1)
are infeasible by construction and are recorded as skipped rather than
silently dropped.
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

from deepfake_interference import metrics as M


def load_scores(results_dir: str, detector: str):
    arms = defaultdict(dict)
    y = {}
    for f in glob.glob(f"{results_dir}/chunk_*.json"):
        for r in json.loads(Path(f).read_text())["records"]:
            if r["detector"] != detector:
                continue
            arms[r["arm"]][r["idx"]] = r["v"]
            y[r["idx"]] = r["y"]
    return arms, y


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/large/validation/effnet")
    ap.add_argument("--detector", default="effnet")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results/e9_cost_surface.json")
    args = ap.parse_args()

    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression

    arms, y = load_scores(args.results, args.detector)
    idx = sorted(set(arms["clean"]) & set(y))
    rng = np.random.default_rng(args.seed)
    perm = rng.permutation(len(idx))
    half = len(idx) // 2
    cal_idx = [idx[i] for i in perm[:half]]
    ev_idx = [idx[i] for i in perm[half:]]

    v_cal = np.array([arms["clean"][i] for i in cal_idx])
    y_cal = np.array([y[i] for i in cal_idx])

    platt = LogisticRegression().fit(v_cal.reshape(-1, 1), y_cal)
    iso = IsotonicRegression(out_of_bounds="clip").fit(v_cal, y_cal)

    y_ev = np.array([y[i] for i in ev_idx])
    probs = {}
    for arm in arms:
        v = np.array([arms[arm][i] for i in ev_idx])
        probs[arm] = {
            "platt": platt.predict_proba(v.reshape(-1, 1))[:, 1],
            "isotonic": np.clip(iso.predict(v), 1e-6, 1 - 1e-6),
        }

    # Cost grid. c_R is fixed at 1 and the other two are expressed relative to
    # it, which is the only ratio the thresholds depend on.
    c_fn_grid = [2, 5, 10, 20, 50, 100, 200, 500]
    c_fp_grid = [2, 5, 10, 20, 50, 100, 200, 500]

    cells, skipped = [], 0
    for c_fn in c_fn_grid:
        for c_fp in c_fp_grid:
            try:
                lo, hi = M.chow_thresholds(c_fn, c_fp, 1.0)
            except ValueError:
                skipped += 1
                continue
            row = {"c_fn": c_fn, "c_fp": c_fp, "c_r": 1.0,
                   "tau_lo": lo, "tau_hi": hi, "drd": {}}
            for cal in ("platt", "isotonic"):
                row["drd"][cal] = {
                    arm: float(M.decision_risk_deviation(
                        y_ev, probs[arm][cal], lo, hi, c_fn, c_fp, 1.0))
                    for arm in sorted(probs)
                }
            cells.append(row)

    # Robustness summary: in what fraction of feasible cells does a null arm's
    # DRD exceed clean's by more than a threshold that matters?
    summary = {}
    for cal in ("platt", "isotonic"):
        for arm in sorted(probs):
            if arm == "clean":
                continue
            diffs = [c["drd"][cal][arm] - c["drd"][cal]["clean"] for c in cells]
            diffs = np.array(diffs)
            summary[f"{cal}/{arm}"] = {
                "median_drd_minus_clean": float(np.median(diffs)),
                "frac_cells_worse": float(np.mean(diffs > 0)),
                "frac_cells_worse_by_0.01": float(np.mean(diffs > 0.01)),
                "max_drd_minus_clean": float(diffs.max()),
                "min_drd_minus_clean": float(diffs.min()),
            }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({
        "detector": args.detector, "n_calibration": len(cal_idx), "n_eval": len(ev_idx),
        "c_fn_grid": c_fn_grid, "c_fp_grid": c_fp_grid,
        "n_cells_feasible": len(cells), "n_cells_skipped_empty_band": skipped,
        "summary": summary, "cells": cells,
    }, indent=1))

    print(f"feasible cells: {len(cells)}  skipped (empty band): {skipped}")
    print(f"n_cal={len(cal_idx)} n_eval={len(ev_idx)}")
    for k, v in summary.items():
        print(f"  {k:28s} median={v['median_drd_minus_clean']:+.4f} "
              f"worse in {v['frac_cells_worse']*100:.0f}% of cells "
              f"(>0.01 in {v['frac_cells_worse_by_0.01']*100:.0f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
