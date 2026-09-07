#!/usr/bin/env python3
"""Blocker 1: does the attenuation asymmetry replicate on a second detector?

The whole confirmatory result rests on an evidence-transfer regression
`v_arm = a + b*v_clean` fitted per arm. On EfficientNet-B6 the null
(payload-free, PSNR-matched) arm attenuates hard (b ~ 0.84) while the
watermarked arm barely does (b ~ 0.97-0.99), and the paper's claim was that
random perturbation destroys detector evidence in a way watermarking does not.

That claim is only a property of *detection* if it survives a detector with
different architecture and disclosed provenance. `own` (frozen ImageNet
ResNet-18 + logistic head fitted on the train split, see
scripts/train_own_detector.py) is that detector. This script fits the same
regression on both and reports the difference with bootstrap CIs, so the
comparison is a measurement rather than an assertion either way.

Both detectors must have been run over the SAME arms on the same split;
`--split validation` is where both exist. Only overlapping image indices are
used, so the two fits are on identical images, not merely the same corpus.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np


def load(split_dir: Path):
    """-> {detector: {arm: {idx: v}}}"""
    out = defaultdict(lambda: defaultdict(dict))
    for chunk in sorted(split_dir.glob("chunk_*.json")):
        for r in json.loads(chunk.read_text())["records"]:
            out[r["detector"]][r["arm"]][r["idx"]] = r["v"]
    return out


def fit(v_clean, v_arm):
    slope, intercept = np.polyfit(v_clean, v_arm, 1)
    return float(slope), float(intercept)


def boot_slope(v_clean, v_arm, n_boot, rng):
    n = len(v_clean)
    slopes = np.empty(n_boot)
    for b in range(n_boot):
        sel = rng.integers(0, n, n)
        slopes[b] = np.polyfit(v_clean[sel], v_arm[sel], 1)[0]
    return float(np.percentile(slopes, 2.5)), float(np.percentile(slopes, 97.5))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/large")
    ap.add_argument("--split", default="validation")
    ap.add_argument("--n-boot", type=int, default=800)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results/replication_check.json")
    args = ap.parse_args()

    root = Path(args.results) / args.split
    per_det = {}
    for det_dir in sorted(root.iterdir()):
        if det_dir.name.endswith("-cleanonly"):
            continue          # clean arm only: no arms to regress against
        for det, arms in load(det_dir).items():
            per_det[det] = arms

    if len(per_det) < 2:
        print(f"need >=2 detectors with full arms under {root}; found {list(per_det)}")
        return 1

    # Restrict every detector to the images ALL of them scored. Without this
    # the comparison is confounded: effnet covers 20k validation images and the
    # own-detector run 8k, so a difference in slope could be a difference in
    # sample. The intersection makes the two fits identical in their inputs.
    shared = None
    for arms in per_det.values():
        ids = set(arms["clean"])
        for a in arms:
            ids &= set(arms[a])
        shared = ids if shared is None else (shared & ids)
    shared = sorted(shared)

    rng = np.random.default_rng(args.seed)
    report = {"split": args.split, "n_boot": args.n_boot,
              "n_shared_images": len(shared), "detectors": {}}

    for det, arms in sorted(per_det.items()):
        idx = shared
        clean = np.array([arms["clean"][i] for i in idx])
        entry = {"n": len(idx), "arms": {}}
        for scheme in ("dwtDctSvd", "rivaGan"):
            if scheme not in arms:
                continue
            row = {}
            for arm in (scheme, f"null[{scheme}]"):
                v = np.array([arms[arm][i] for i in idx])
                s, a0 = fit(clean, v)
                lo, hi = boot_slope(clean, v, args.n_boot, rng)
                row[arm] = {"slope": s, "intercept": a0, "ci": [lo, hi]}
            # The asymmetry the paper claims: null attenuates, watermark does not.
            # Positive here means "watermark attenuates MORE than the null",
            # i.e. the claimed effect with its sign reversed.
            row["null_minus_wm"] = row[f"null[{scheme}]"]["slope"] - row[scheme]["slope"]
            entry["arms"][scheme] = row
        report["detectors"][det] = entry

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2))

    for det, e in report["detectors"].items():
        print(f"\n{det}  n={e['n']}")
        for scheme, row in e["arms"].items():
            w, nl = row[scheme], row[f"null[{scheme}]"]
            print(f"  {scheme:10s} wm b={w['slope']:.4f}[{w['ci'][0]:.4f},{w['ci'][1]:.4f}]   "
                  f"null b={nl['slope']:.4f}[{nl['ci'][0]:.4f},{nl['ci'][1]:.4f}]   "
                  f"null-minus-wm={row['null_minus_wm']:+.4f}")
    print(f"\nwritten to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
