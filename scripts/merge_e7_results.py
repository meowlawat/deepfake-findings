#!/usr/bin/env python3
"""Merge two E7 result directories scored on the identical image slice.

e7_control_hierarchy.py's resumability marks a chunk "done" by filename alone
(docs/07): it has no notion of which detectors populated that chunk, so
pointing a second run with new detectors at the same --out-dir would see all
16 chunks already on disk and skip every one of them, writing nothing. So new
detectors are scored into their own directory (same --split/--offset/--limit,
hence identical image ordering and chunk boundaries) and merged here rather
than appended in place.

Verifies before merging, not after, that both directories actually cover the
same images: a merge across two different slices would silently produce a
"panel" whose rows were never scored on the same population, which is exactly
the comparability failure this whole panel expansion exists to avoid.
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path


def load_dir(d: str):
    chunks = {}
    for f in sorted(glob.glob(f"{d}/chunk_*.json")):
        idx = int(Path(f).stem.split("_")[-1])
        chunks[idx] = json.loads(Path(f).read_text())
    return chunks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", required=True,
                    help="two or more E7 output dirs scored on the same slice")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    per_dir = [load_dir(d) for d in args.dirs]
    chunk_ids = set(per_dir[0])
    for d, chunks in zip(args.dirs, per_dir):
        if set(chunks) != chunk_ids:
            raise SystemExit(f"chunk id mismatch: {args.dirs[0]} has {sorted(chunk_ids)}, "
                             f"{d} has {sorted(chunks)} -- not the same slice, refusing to merge")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    seen_idx_per_chunk = {}
    for cid in sorted(chunk_ids):
        merged_records, merged_quality = [], None
        for d, chunks in zip(args.dirs, per_dir):
            c = chunks[cid]
            # sanity: every directory must agree on which image indices this
            # chunk covers, or "same slice" is false despite matching chunk ids
            idxs = sorted({r["idx"] for r in c["records"]})
            seen_idx_per_chunk.setdefault(cid, idxs)
            if idxs != seen_idx_per_chunk[cid]:
                raise SystemExit(f"chunk {cid}: {d} covers different image indices "
                                 f"than the first directory -- refusing to merge")
            merged_records += c["records"]
            if merged_quality is None:
                merged_quality = c.get("quality", [])  # identical across dirs; keep once
        (out_dir / f"chunk_{cid:05d}.json").write_text(
            json.dumps({"records": merged_records, "quality": merged_quality}))

    n_detectors = len({r["detector"] for c in per_dir[0].values() for r in c["records"]})
    total_det = sum(len({r["detector"] for c in chunks.values() for r in c["records"]})
                    for chunks in per_dir)
    print(f"merged {len(chunk_ids)} chunks from {len(args.dirs)} directories "
          f"({total_det} detector-slices total) -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
