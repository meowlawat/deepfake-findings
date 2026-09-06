#!/usr/bin/env python3
"""E1 - the go/no-go gate (docs/03 S2). Computes Delta_mu, Delta_sigma,
Delta_AUC, and the headline Delta_AUC_net for every (scheme x detector x
class) cell, including the S=null control arm, and decides whether the
paper's premise holds well enough to keep building on it.

Usage:
    python scripts/e1_interference.py --config config.yaml [--limit N]

Requires config.yaml's dataset.root to point at a real, unzipped dataset
(docs/03 S0). Exits nonzero and prints the gate's verdict either way, so a
failed gate is loud, not a silently-ignored log line.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import yaml

from deepfake_interference import data as data_mod
from deepfake_interference import detectors as det_mod
from deepfake_interference import metrics
from deepfake_interference import null_perturbation as np_ctrl
from deepfake_interference import watermark as wm_mod

NET_GATE_THRESHOLD = 0.02  # |Delta_AUC_net| below this counts as "no signal" - docs/03 E1


def build_records(items, cfg, limit=None, seed=0):
    """One pass: for each image, produce V under W=0 (clean), each watermark
    scheme, and the null-perturbation control, from BOTH detectors. Returns a
    list of dict rows - simple and inspectable, deliberately not a DataFrame
    dependency at this stage.
    """
    if limit:
        items = items[:limit]

    detectors = {name: det_mod.Detector(model_id) for name, model_id in cfg["detectors"].items()
                 if name in ("vit", "effnet")}
    schemes = cfg["watermark"]["schemes"]
    payload_bits = cfg["watermark"]["payload_bits"]
    rng = np.random.default_rng(seed)

    records = []
    for item in items:
        image = data_mod.load_image(item, size=cfg["dataset"]["image_size"])

        clean_scores = {name: det.score(image).v for name, det in detectors.items()}
        for name, v in clean_scores.items():
            records.append({"arm": "clean", "y": item.label, "detector": name, "v": v})

        for scheme in schemes:
            bits = list(rng.integers(0, 2, payload_bits))
            result = wm_mod.embed(image, bits, scheme)
            for name, det in detectors.items():
                v = det.score(result.watermarked).v
                records.append({"arm": scheme, "y": item.label, "detector": name, "v": v})

            # null arm, PSNR-matched to THIS scheme's PSNR on THIS image - docs/02 S3.1
            null_result = np_ctrl.match_to_target(
                image, target_psnr=result.psnr, rng=rng,
                tolerance_db=cfg["watermark"]["null_tolerance_db"],
            )
            for name, det in detectors.items():
                v = det.score(null_result.perturbed).v
                records.append({"arm": f"null[{scheme}]", "y": item.label, "detector": name, "v": v})

    return records


def compute_interference_table(records: list[dict], schemes: list[str], detector_names: list[str]) -> list[dict]:
    rows = []
    for detector in detector_names:
        clean = [r for r in records if r["detector"] == detector and r["arm"] == "clean"]
        y_clean = np.array([r["y"] for r in clean])
        v_clean = np.array([r["v"] for r in clean])

        for scheme in schemes:
            wm = [r for r in records if r["detector"] == detector and r["arm"] == scheme]
            null = [r for r in records if r["detector"] == detector and r["arm"] == f"null[{scheme}]"]
            y_wm, v_wm = np.array([r["y"] for r in wm]), np.array([r["v"] for r in wm])
            y_null, v_null = np.array([r["y"] for r in null]), np.array([r["v"] for r in null])

            d_auc_scheme = metrics.delta_auc(y_wm, v_wm, y_clean, v_clean)
            d_auc_null = metrics.delta_auc(y_null, v_null, y_clean, v_clean)
            d_auc_net = metrics.delta_auc_net(d_auc_scheme, d_auc_null)

            rows.append({
                "detector": detector,
                "scheme": scheme,
                "delta_mu": metrics.delta_mu(v_wm, v_clean),
                "delta_sigma": metrics.delta_sigma(v_wm, v_clean),
                "delta_auc": d_auc_scheme,
                "delta_auc_null": d_auc_null,
                "delta_auc_net": d_auc_net,
                "n_clean": len(clean),
                "n_scheme": len(wm),
            })
    return rows


def gate_verdict(rows: list[dict]) -> tuple[bool, str]:
    """docs/03 E1: if Delta_AUC_net is ~0 everywhere, stop and re-scope before
    building E2-E6 on a premise that didn't hold.
    """
    net_values = [r["delta_auc_net"] for r in rows if not np.isnan(r["delta_auc_net"])]
    if not net_values:
        return False, "no valid Delta_AUC_net values computed - check detector floor (E0) first"
    max_abs_net = max(abs(v) for v in net_values)
    if max_abs_net < NET_GATE_THRESHOLD:
        return False, (
            f"max |Delta_AUC_net| = {max_abs_net:.4f} < {NET_GATE_THRESHOLD} across all cells - "
            f"no scheme shows structured interference beyond the null control. "
            f"Re-scope per docs/04 R1's fallback framing before proceeding to E2."
        )
    return True, f"max |Delta_AUC_net| = {max_abs_net:.4f} >= {NET_GATE_THRESHOLD} - gate PASSES, proceed to E2/E3"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--limit", type=int, default=None, help="cap items per class for a fast dry run")
    parser.add_argument("--out", default="results/e1_interference.json")
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text())
    items = data_mod.discover(Path(cfg["dataset"]["root"]))
    print(f"Loaded {len(items)} items from {cfg['dataset']['root']}")

    t0 = time.time()
    records = build_records(items, cfg, limit=args.limit)
    print(f"Built {len(records)} score records in {time.time() - t0:.1f}s")

    detector_names = [n for n in cfg["detectors"] if n in ("vit", "effnet")]
    rows = compute_interference_table(records, cfg["watermark"]["schemes"], detector_names)

    passed, message = gate_verdict(rows)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"rows": rows, "gate_passed": passed, "gate_message": message}, indent=2))

    print()
    print("=== E1 interference table (T1) ===")
    for r in rows:
        print(f"  {r['detector']:8s} {r['scheme']:12s} "
              f"dAUC={r['delta_auc']:+.4f} dAUC_null={r['delta_auc_null']:+.4f} "
              f"dAUC_net={r['delta_auc_net']:+.4f}")
    print()
    print(f"GATE: {'PASS' if passed else 'FAIL'} - {message}")
    print(f"Results written to {args.out}")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
