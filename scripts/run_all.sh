#!/usr/bin/env bash
# Run the v1 experiment suite in dependency order, logging each stage.
# E1 is a gate: if it fails, downstream experiments still run (their numbers
# are informative either way) but the gate's verdict is what decides how the
# paper is framed - see docs/03 E1 and docs/04 R1.
#
# Usage: bash scripts/run_all.sh [--limit N]
set -u

LIMIT_ARG=""
if [ "${1:-}" = "--limit" ]; then LIMIT_ARG="--limit $2"; fi

mkdir -p results
run () {
  local name="$1"; shift
  echo "=== [$(date -u +%H:%M:%S)] $name ==="
  "$@" 2>&1 | grep -vE "Loading weights|Warning: You are sending" | tee "results/${name}.log"
  echo "=== [$(date -u +%H:%M:%S)] $name exit=${PIPESTATUS[0]} ==="
}

run e1  python3 scripts/e1_interference.py --config config.yaml $LIMIT_ARG --out results/e1_full_run.json
run e2e3_effnet python3 scripts/e2_e3_fusion.py --detector effnet $LIMIT_ARG --out results/e2_e3_fusion.json
run e2e3_vit   python3 scripts/e2_e3_fusion.py --detector vit    $LIMIT_ARG --out results/e2_e3_fusion_vit.json
run e6  python3 scripts/e6_ablations.py --detector effnet $LIMIT_ARG --out results/e6_ablations.json
run e4e5 python3 scripts/e4_e5_transforms_rho.py --detector effnet $LIMIT_ARG --out results/e4_e5.json
run report python3 scripts/make_report.py --results-dir results --out-dir paper/generated

echo "=== all stages complete ==="
