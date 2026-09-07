#!/usr/bin/env python3
"""Aggregate e1_large.py's shards into E0/E1 results with bootstrap CIs.

Two things this does that the n=300 pipeline could not:

1. **Per-split reporting, as a leakage diagnostic.** If the third-party
   detectors were fine-tuned on this corpus it was almost certainly the
   train split, so a large train-vs-test gap in baseline AUC is direct
   evidence of contamination (docs/04 R14). At n=300 on one split that
   question was unanswerable; across all three splits it is measurable.
2. **CIs that actually constrain.** At n=300 the standard error on a single
   AUC (~0.03) exceeded every effect measured, so the null bounded nothing.
   The interval is what a negative result rests on, so it is reported for
   every cell rather than only the headline.

Usage:
    python scripts/aggregate_large.py --in-dir results/large --out results/large_summary.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np

from deepfake_interference import metrics


def load_records(in_dir: Path) -> list[dict]:
    records = []
    for split_dir in sorted(p for p in in_dir.iterdir() if p.is_dir()):
        for shard in sorted(split_dir.glob("chunk_*.json")):
            records.extend(json.loads(shard.read_text())["records"])
    return records


def _by(records, split, detector, arm):
    sel = [r for r in records if r["split"] == split and r["detector"] == detector and r["arm"] == arm]
    sel.sort(key=lambda r: r["idx"])
    return np.array([r["y"] for r in sel]), np.array([r["v"] for r in sel])


def e0_table(records, floor: float, suspicion: float) -> list[dict]:
    rows = []
    for split in sorted({r["split"] for r in records}):
        for detector in sorted({r["detector"] for r in records}):
            y, v = _by(records, split, detector, "clean")
            auc = metrics.auc(y, v)
            status = ("NaN" if np.isnan(auc) else
                      f"FAIL (<{floor})" if auc < floor else
                      f"PASS but SUSPECT LEAKAGE (>={suspicion})" if auc >= suspicion else "PASS")
            rows.append({"split": split, "detector": detector, "n": int(len(y)),
                          "baseline_auc": None if np.isnan(auc) else float(auc),
                          "status": status})
    return rows


def leakage_diagnostic(e0: list[dict]) -> list[dict]:
    """train-vs-test baseline AUC gap, per detector. This is the measurement
    that all-140k buys and a single subset cannot provide.
    """
    out = []
    for detector in sorted({r["detector"] for r in e0}):
        byspl = {r["split"]: r["baseline_auc"] for r in e0 if r["detector"] == detector}
        train, test = byspl.get("train"), byspl.get("test")
        if train is None or test is None:
            continue
        gap = train - test
        out.append({
            "detector": detector, "auc_train": train, "auc_test": test, "gap": gap,
            "reading": ("gap is large - consistent with the detector having seen the "
                         "train split during fine-tuning; treat absolute accuracies as "
                         "contaminated and rely on within-model deltas"
                         if gap > 0.05 else
                         "no substantial train/test gap - weak evidence AGAINST "
                         "train-split contamination, not proof of its absence"),
        })
    return out


def interference_table(records, n_boot: int, seed: int) -> list[dict]:
    rng = np.random.default_rng(seed)
    schemes = sorted({r["arm"] for r in records
                       if r["arm"] != "clean" and not r["arm"].startswith("null[")})
    rows = []
    for split in sorted({r["split"] for r in records}):
        for detector in sorted({r["detector"] for r in records}):
            y_c, v_c = _by(records, split, detector, "clean")
            for scheme in schemes:
                y_w, v_w = _by(records, split, detector, scheme)
                y_n, v_n = _by(records, split, detector, f"null[{scheme}]")
                n = min(len(y_c), len(y_w), len(y_n))
                if n == 0:
                    continue
                y_c2, v_c2, v_w2, v_n2 = y_c[:n], v_c[:n], v_w[:n], v_n[:n]

                def net(idx):
                    da = metrics.delta_auc(y_c2[idx], v_w2[idx], y_c2[idx], v_c2[idx])
                    dn = metrics.delta_auc(y_c2[idx], v_n2[idx], y_c2[idx], v_c2[idx])
                    dm = metrics.delta_mu(v_w2[idx], v_c2[idx]) - metrics.delta_mu(v_n2[idx], v_c2[idx])
                    return da - dn, dm

                base = np.arange(n)
                p_auc, p_mu = net(base)
                boots = np.array([net(rng.integers(0, n, n)) for _ in range(n_boot)])
                lo_a, hi_a = np.nanquantile(boots[:, 0], [0.025, 0.975])
                lo_m, hi_m = np.nanquantile(boots[:, 1], [0.025, 0.975])
                rows.append({
                    "split": split, "detector": detector, "scheme": scheme, "n": int(n),
                    "delta_auc_net": {"point": float(p_auc), "lo": float(lo_a), "hi": float(hi_a)},
                    "delta_mu_net": {"point": float(p_mu), "lo": float(lo_m), "hi": float(hi_m)},
                })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in-dir", default="results/large")
    parser.add_argument("--out", default="results/large_summary.json")
    parser.add_argument("--floor", type=float, default=0.80)
    parser.add_argument("--suspicion", type=float, default=0.97)
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    records = load_records(Path(args.in_dir))
    print(f"loaded {len(records)} records")

    e0 = e0_table(records, args.floor, args.suspicion)
    print("\n=== E0 baseline AUC by split ===")
    for r in e0:
        auc = "NaN" if r["baseline_auc"] is None else f"{r['baseline_auc']:.4f}"
        print(f"  {r['split']:11s} {r['detector']:9s} n={r['n']:6d}  AUC={auc}  {r['status']}")

    leak = leakage_diagnostic(e0)
    if leak:
        print("\n=== Leakage diagnostic (train - test baseline AUC) ===")
        for r in leak:
            print(f"  {r['detector']:9s} train={r['auc_train']:.4f} test={r['auc_test']:.4f} "
                  f"gap={r['gap']:+.4f}")
            print(f"    -> {r['reading']}")

    t1 = interference_table(records, args.n_boot, args.seed)
    print("\n=== E1 interference, net of null arm, with 95% CI ===")
    for r in t1:
        a, m = r["delta_auc_net"], r["delta_mu_net"]
        print(f"  {r['split']:11s} {r['detector']:9s} {r['scheme']:11s} n={r['n']:6d}  "
              f"dAUC_net={a['point']:+.4f} [{a['lo']:+.4f},{a['hi']:+.4f}]  "
              f"dMu_net={m['point']:+.4f} [{m['lo']:+.4f},{m['hi']:+.4f}]")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(
        {"e0": e0, "leakage": leak, "interference": t1, "n_records": len(records)}, indent=2))
    print(f"\nWritten to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
