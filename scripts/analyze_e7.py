#!/usr/bin/env python3
"""Analyse E7: does the watermark survive comparison against a control matched
on spectrum, not merely on PSNR?

Reports, per detector and per scheme, the evidence-transfer slope for the
watermark arm, the PSNR-matched control, and the spectrum-matched control,
with paired image-level bootstrap intervals on each slope and on the two
contrasts that matter:

    wm - null[]     the original comparison (PSNR-matched control)
    wm - spec[]     the strengthened comparison (spectrum-matched control)

Also verifies that the controls are matched in fact and not merely in
intention, by reporting the realised PSNR/SSIM of each arm. A control that
missed its target is not a control, and this is the check that would catch it.

Bootstrap resamples IMAGES, so every arm of an image moves together and the
paired structure is preserved; contrasts are computed inside each resample
rather than from independently resampled marginals.
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


def load(results_dir: str):
    arms = defaultdict(lambda: defaultdict(dict))   # det -> arm -> idx -> v
    y, quality = {}, []
    for f in sorted(glob.glob(f"{results_dir}/chunk_*.json")):
        d = json.loads(Path(f).read_text())
        for r in d["records"]:
            arms[r["detector"]][r["arm"]][r["idx"]] = r["v"]
            y[r["idx"]] = r["y"]
        quality += d.get("quality", [])
    return arms, y, quality


def slope(x, v):
    return float(np.polyfit(x, v, 1)[0])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/e7_control_hierarchy/test")
    ap.add_argument("--schemes", nargs="+", default=["dwtDctSvd", "rivaGan"])
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results/e7_analysis.json")
    args = ap.parse_args()

    arms_by_det, y, quality = load(args.results)
    if not arms_by_det:
        print(f"no results under {args.results}")
        return 1

    rng = np.random.default_rng(args.seed)
    report = {"n_boot": args.n_boot, "detectors": {}, "control_quality": {}}

    # --- did the controls actually match? ---
    for scheme in args.schemes:
        w_p = [q[scheme]["wm_psnr"] for q in quality if scheme in q]
        n_p = [q[scheme]["null_psnr"] for q in quality if scheme in q]
        s_p = [q[scheme]["spec_psnr"] for q in quality if scheme in q]
        w_s = [q[scheme]["wm_ssim"] for q in quality if scheme in q]
        n_s = [q[scheme]["null_ssim"] for q in quality if scheme in q]
        s_s = [q[scheme]["spec_ssim"] for q in quality if scheme in q]
        report["control_quality"][scheme] = {
            "n": len(w_p),
            "psnr_mean": {"wm": float(np.mean(w_p)), "null": float(np.mean(n_p)),
                          "spec": float(np.mean(s_p))},
            "psnr_abs_err_vs_wm": {"null": float(np.mean(np.abs(np.array(n_p) - w_p))),
                                   "spec": float(np.mean(np.abs(np.array(s_p) - w_p)))},
            "ssim_mean": {"wm": float(np.mean(w_s)), "null": float(np.mean(n_s)),
                          "spec": float(np.mean(s_s))},
        }

    for det, arms in sorted(arms_by_det.items()):
        common = set(arms["clean"])
        for a in arms:
            common &= set(arms[a])
        idx = sorted(common)
        clean = np.array([arms["clean"][i] for i in idx])
        entry = {"n": len(idx), "schemes": {}}

        for scheme in args.schemes:
            names = {"wm": scheme, "null": f"null[{scheme}]", "spec": f"spec[{scheme}]"}
            if not all(n in arms for n in names.values()):
                continue
            v = {k: np.array([arms[n][i] for i in idx]) for k, n in names.items()}
            point = {k: slope(clean, vv) for k, vv in v.items()}

            boots = {k: np.empty(args.n_boot) for k in names}
            d_null = np.empty(args.n_boot)
            d_spec = np.empty(args.n_boot)
            n = len(idx)
            for b in range(args.n_boot):
                sel = rng.integers(0, n, n)        # resample images, arms move together
                c = clean[sel]
                s_ = {k: slope(c, vv[sel]) for k, vv in v.items()}
                for k in names:
                    boots[k][b] = s_[k]
                d_null[b] = s_["wm"] - s_["null"]
                d_spec[b] = s_["wm"] - s_["spec"]

            def ci(a):
                return [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]

            entry["schemes"][scheme] = {
                "slope": {k: {"point": point[k], "ci": ci(boots[k])} for k in names},
                "wm_minus_null": {"point": point["wm"] - point["null"], "ci": ci(d_null),
                                  "excludes_zero": bool(ci(d_null)[0] > 0 or ci(d_null)[1] < 0)},
                "wm_minus_spec": {"point": point["wm"] - point["spec"], "ci": ci(d_spec),
                                  "excludes_zero": bool(ci(d_spec)[0] > 0 or ci(d_spec)[1] < 0)},
            }
        report["detectors"][det] = entry

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=1))

    print("=== control quality (are the controls actually matched?) ===")
    for scheme, q in report["control_quality"].items():
        print(f"{scheme} n={q['n']}  PSNR wm={q['psnr_mean']['wm']:.2f} "
              f"null={q['psnr_mean']['null']:.2f} spec={q['psnr_mean']['spec']:.2f}  "
              f"|err| null={q['psnr_abs_err_vs_wm']['null']:.3f} "
              f"spec={q['psnr_abs_err_vs_wm']['spec']:.3f}  "
              f"SSIM wm={q['ssim_mean']['wm']:.4f} null={q['ssim_mean']['null']:.4f} "
              f"spec={q['ssim_mean']['spec']:.4f}")
    print()
    for det, e in report["detectors"].items():
        print(f"=== {det}  n={e['n']} ===")
        for scheme, r in e["schemes"].items():
            s = r["slope"]
            print(f"  {scheme}")
            for k in ("wm", "null", "spec"):
                print(f"    {k:5s} b={s[k]['point']:.4f} [{s[k]['ci'][0]:.4f},{s[k]['ci'][1]:.4f}]")
            for cname, key in (("wm-null", "wm_minus_null"), ("wm-spec", "wm_minus_spec")):
                c = r[key]
                flag = "EXCLUDES 0" if c["excludes_zero"] else "includes 0"
                print(f"    {cname:8s} {c['point']:+.4f} [{c['ci'][0]:+.4f},{c['ci'][1]:+.4f}]  {flag}")
    print(f"\nwritten to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
