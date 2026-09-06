#!/usr/bin/env bash
# Re-run the suite after the three correctness fixes:
#   - E1: null arm now subtracted from delta_mu/delta_sigma, not just delta_auc
#   - E1: raw per-image records persisted so CIs cost seconds, not a re-score
#   - E2/E3: beta_4's CI now bootstraps the calibration set it was fit on
# Ordered cheapest-informative first so a failure surfaces early.
set -u
mkdir -p results

stage () {
  local name="$1"; shift
  echo "=== [$(date -u +%H:%M:%S)] START $name ==="
  "$@" > "results/${name}.log" 2>&1
  echo "=== [$(date -u +%H:%M:%S)] END $name exit=$? ==="
}

stage e1_corrected  python3 scripts/e1_interference.py --config config.yaml --out results/e1_full_run.json
stage e1_bootstrap  python3 scripts/e1_bootstrap.py --records results/e1_full_run_records.json --out results/e1_bootstrap.json
stage e2e3_effnet   python3 scripts/e2_e3_fusion.py --detector effnet --out results/e2_e3_fusion.json
stage e6            python3 scripts/e6_ablations.py --detector effnet --out results/e6_ablations.json
stage e4e5          python3 scripts/e4_e5_transforms_rho.py --detector effnet --out results/e4_e5.json
stage report        python3 scripts/make_report.py --results-dir results --out-dir paper/generated

echo "=== ALL STAGES COMPLETE $(date -u +%H:%M:%S) ==="
