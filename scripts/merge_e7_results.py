#!/usr/bin/env python3
"""Merge two E7 result directories scored on the identical image slice.

e7_control_hierarchy.py's resumability marks a chunk "done" by filename alone
(docs/07): it has no notion of which detectors populated that chunk, so
pointing a second run with new detectors at the same --out-dir would see all
existing chunks already on disk and skip every one, writing nothing. So new
detectors are scored into their own directory (same --split/--offset/--limit,
hence the identical image population) and merged here rather than appended
in place.

Merging is keyed on image index, not on chunk filename. Two directories can
legitimately use different --chunk-size values (a resharded or restarted run
need not reproduce the original's chunk boundaries) and still cover the same
population -- requiring identical chunk_NNNNN.json boundaries would reject a
merge that is actually valid, so the real invariant checked here is "every
directory covers exactly the same set of image indices," and the output is
written as a single chunk covering all of them.
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path


def load_records(d: str):
    records, quality = [], None
    for f in sorted(glob.glob(f"{d}/chunk_*.json")):
        c = json.loads(Path(f).read_text())
        records += c["records"]
        if quality is None:
            quality = c.get("quality", [])  # identical across dirs for the same slice
    return records, quality


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", required=True,
                    help="two or more E7 output dirs scored on the same slice")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    per_dir = [load_records(d) for d in args.dirs]
    idx_sets = [{r["idx"] for r in records} for records, _ in per_dir]
    base = idx_sets[0]
    for d, idxs in zip(args.dirs, idx_sets):
        if idxs != base:
            missing = base - idxs
            extra = idxs - base
            raise SystemExit(
                f"{d} does not cover the same image indices as {args.dirs[0]} -- "
                f"missing {len(missing)}, extra {len(extra)} -- refusing to merge "
                f"results that were not scored on the same population")

    # detector collision check: merging two dirs that scored the SAME detector
    # would silently duplicate that detector's rows in every downstream mean/
    # bootstrap, so refuse rather than let it happen quietly.
    det_by_dir = []
    for d, (records, _) in zip(args.dirs, per_dir):
        dets = {r["detector"] for r in records}
        det_by_dir.append(dets)
    for i in range(len(det_by_dir)):
        for j in range(i + 1, len(det_by_dir)):
            overlap = det_by_dir[i] & det_by_dir[j]
            if overlap:
                raise SystemExit(
                    f"{args.dirs[i]} and {args.dirs[j]} both scored detector(s) "
                    f"{sorted(overlap)} -- refusing to merge duplicate detector rows")

    all_records = [r for records, _ in per_dir for r in records]
    all_quality = per_dir[0][1]  # identical across dirs (same images, same seeds)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "chunk_00000.json").write_text(
        json.dumps({"records": all_records, "quality": all_quality}))

    all_dets = sorted(set().union(*det_by_dir))
    print(f"merged {len(args.dirs)} directories, {len(base)} images, "
          f"detectors={all_dets} -> {out_dir}/chunk_00000.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
