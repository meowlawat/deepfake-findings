#!/usr/bin/env python3
"""Bootstrap CIs for E1's interference quantities - docs/03 S4.

E1 returned a null on the pre-registered gate. A null without confidence
intervals is not evidence of absence, especially at n=300 where the standard
error on a single AUC (~0.03) is larger than the net effects measured. This
script answers the question that actually matters for a negative result:
**what effect sizes can we rule out?**

Reads the raw per-image records persisted by e1_interference.py, so it costs
seconds rather than re-scoring every image.

Usage:
    python scripts/e1_bootstrap.py --records results/e1_full_run_records.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np

from deepfake_interference import metrics


def _arrays(records, detector, arm):
    sel = [r for r in records if r["detector"] == detector and r["arm"] == arm]
    return np.array([r["y"] for r in sel]), np.array([r["v"] for r in sel])


def bootstrap_net_quantities(records, detector, scheme, n_boot=2000, ci=0.95, seed=0):
    """Resample IMAGES (not rows) so the clean/scheme/null arms of one image
    move together - they are three measurements of the same source image, and
    resampling them independently would understate the correlation and give a
    falsely narrow interval.
    """
    y_clean, v_clean = _arrays(records, detector, "clean")
    y_wm, v_wm = _arrays(records, detector, scheme)
    y_null, v_null = _arrays(records, detector, f"null[{scheme}]")
    n = len(y_clean)
    if not (len(y_wm) == len(y_null) == n):
        raise ValueError("arm lengths differ; records file is malformed")

    rng = np.random.default_rng(seed)

    def _net(idx):
        d_auc = metrics.delta_auc(y_wm[idx], v_wm[idx], y_clean[idx], v_clean[idx])
        d_auc_null = metrics.delta_auc(y_null[idx], v_null[idx], y_clean[idx], v_clean[idx])
        d_mu = metrics.delta_mu(v_wm[idx], v_clean[idx])
        d_mu_null = metrics.delta_mu(v_null[idx], v_clean[idx])
        return d_auc - d_auc_null, d_mu - d_mu_null

    base_idx = np.arange(n)
    point_auc, point_mu = _net(base_idx)

    boots_auc, boots_mu = np.empty(n_boot), np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        boots_auc[i], boots_mu[i] = _net(idx)

    alpha = (1 - ci) / 2
    lo_a, hi_a = np.nanquantile(boots_auc, [alpha, 1 - alpha])
    lo_m, hi_m = np.nanquantile(boots_mu, [alpha, 1 - alpha])
    return {
        "detector": detector, "scheme": scheme, "n_images": int(n),
        "delta_auc_net": {"point": float(point_auc), "lo": float(lo_a), "hi": float(hi_a)},
        "delta_mu_net": {"point": float(point_mu), "lo": float(lo_m), "hi": float(hi_m)},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", default="results/e1_full_run_records.json")
    parser.add_argument("--out", default="results/e1_bootstrap.json")
    parser.add_argument("--n-boot", type=int, default=2000)
    args = parser.parse_args()

    records = json.loads(Path(args.records).read_text())
    detectors = sorted({r["detector"] for r in records})
    schemes = sorted({r["arm"] for r in records if r["arm"] not in ("clean",) and not r["arm"].startswith("null[")})

    rows = []
    for detector in detectors:
        for scheme in schemes:
            rows.append(bootstrap_net_quantities(records, detector, scheme, n_boot=args.n_boot))

    print(f"{'detector':9s} {'scheme':11s} {'dAUC_net [95% CI]':32s} {'dMu_net [95% CI]'}")
    for r in rows:
        a, m = r["delta_auc_net"], r["delta_mu_net"]
        print(f"{r['detector']:9s} {r['scheme']:11s} "
              f"{a['point']:+.4f} [{a['lo']:+.4f}, {a['hi']:+.4f}]      "
              f"{m['point']:+.4f} [{m['lo']:+.4f}, {m['hi']:+.4f}]")

    Path(args.out).write_text(json.dumps(rows, indent=2))
    print(f"\nWritten to {args.out}")
    print("Read these as: what effect sizes does the interval RULE OUT? A null")
    print("whose CI spans effects large enough to matter has not shown absence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
