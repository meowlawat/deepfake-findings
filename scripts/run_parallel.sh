#!/usr/bin/env bash
# Launch K data-parallel shards of e1_large.py across available cores.
#
# Why sharding rather than one process with more workers: a single process
# alternates between parallel embedding and SERIAL detection, so during
# detection (the majority of CPU-seconds on this box) the embed workers sit
# idle. K independent processes each pinned to one torch thread keep every
# core busy on a different chunk. Resume-by-existence makes the shards
# compose safely - each writes disjoint chunk ids, and a killed shard just
# leaves its chunks for a later run.
#
# Usage: bash scripts/run_parallel.sh <split> <num_shards> [detector...]
set -u
SPLIT="${1:-validation}"
K="${2:-4}"
shift 2 || true
DETECTORS="${*:-effnet}"

mkdir -p results/large logs
echo "launching $K shards on split=$SPLIT detectors=$DETECTORS"

for i in $(seq 0 $((K-1))); do
  OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 nohup python3 scripts/e1_large.py \
    --splits "$SPLIT" \
    --local-dir data/corpus \
    --chunk-size 100 \
    --workers 0 \
    --torch-threads 1 \
    --detectors $DETECTORS \
    --shard "$i" --num-shards "$K" \
    --out-dir results/large \
    > "logs/shard_${SPLIT}_${i}.log" 2>&1 &
  echo "  shard $i -> logs/shard_${SPLIT}_${i}.log (pid $!)"
done

echo "watch: tail -f logs/shard_${SPLIT}_0.log"
echo "count: ls results/large/${SPLIT}/ | wc -l"
