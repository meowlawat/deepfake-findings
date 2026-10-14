#!/usr/bin/env python3
"""E8: where does the payload actually fail? Four manipulation families by a
coverage grid, both schemes.

The previous manipulation result tested one mechanism (Poisson-blended splice)
at six coverage levels and concluded the payload survives at face-replacement
scale. The obvious objection is that one mechanism cannot separate "robust
watermarks survive localised editing" from "this particular splice happens not
to disturb the carrier". Four families on deliberately different axes answer
it:

  splice       foreign content blended in
  inpaint      region reconstructed from surrounding context
  copy_move    the image's own content relocated over the region
  local_regen  fine structure destroyed in place (blur + requantisation)

The first three leave the carrier's local statistics broadly intact; the
fourth attacks the high-frequency detail a transform-domain payload rides on.
If survival holds across all four, the result is about coverage rather than
about one mechanism. If local_regen breaks it, that localises the failure to
carrier destruction and is a more useful finding than the original.

No detector is involved: BER is measured by extraction alone, so this runs at
a fraction of the cost of the scoring experiments.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np

FAMILIES = ("splice", "inpaint", "copy_move", "local_regen")
# BER at or below this is treated as a readable payload: with L=32 bits, a
# decoder tolerating 25% bit error still recovers the identifier under any
# reasonable ECC, whereas 0.5 is chance.
READABLE_BER = 0.25


def apply_family(name, host, donor, area, rng):
    from deepfake_interference import manipulation as M
    if name == "splice":
        return M.splice_region(host, donor, area_fraction=area, rng=rng)
    if name == "inpaint":
        return M.inpaint_region(host, area_fraction=area, rng=rng)
    if name == "copy_move":
        return M.copy_move_region(host, area_fraction=area, rng=rng)
    if name == "local_regen":
        return M.local_regenerate_region(host, area_fraction=area, rng=rng)
    raise ValueError(name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="data/corpus/test/real")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--offset", type=int, default=4000,
                    help="index offset so these images are disjoint from every other analysis")
    ap.add_argument("--image-size", type=int, default=256)
    ap.add_argument("--payload-bits", type=int, default=32)
    ap.add_argument("--schemes", nargs="+", default=["dwtDctSvd", "rivaGan"])
    ap.add_argument("--coverage", nargs="+", type=float,
                    default=[0.05, 0.10, 0.25, 0.50, 0.75, 1.00])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results/e8_manipulation_grid.json")
    args = ap.parse_args()

    import cv2
    from deepfake_interference import watermark as W

    paths = sorted(Path(args.corpus).glob("*.png"))[args.offset: args.offset + args.n]
    if len(paths) < args.n:
        print(f"WARNING: only {len(paths)} images available at offset {args.offset}")

    def load(p):
        bgr = cv2.imread(str(p))
        if bgr.shape[0] != args.image_size:
            bgr = cv2.resize(bgr, (args.image_size,) * 2, interpolation=cv2.INTER_AREA)
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    rows, t0 = [], time.time()
    for i, p in enumerate(paths):
        host = load(p)
        donor = load(paths[(i + 1) % len(paths)])      # a different real image
        rng = np.random.default_rng(args.seed + i)
        for scheme in args.schemes:
            bits = list(rng.integers(0, 2, args.payload_bits))
            res = W.embed(host, bits, scheme)

            # baseline: unmanipulated recovery, so every row is read against
            # this scheme's own clean-channel error rate rather than against 0.
            base = W.extract(res.watermarked, scheme, n_bits=args.payload_bits)
            base_ber = float(np.mean(np.asarray(base) != np.asarray(bits)))

            for fam in FAMILIES:
                for area in args.coverage:
                    m = apply_family(fam, res.watermarked, donor, area,
                                     np.random.default_rng(args.seed + i))
                    got = W.extract(m.manipulated, scheme, n_bits=args.payload_bits)
                    ber = float(np.mean(np.asarray(got) != np.asarray(bits)))
                    rows.append({
                        "idx": i, "file": p.name, "scheme": scheme, "family": fam,
                        "target_area": area, "actual_area": m.area_fraction,
                        "ber": ber, "baseline_ber": base_ber,
                        "readable": bool(ber <= READABLE_BER),
                    })
        if (i + 1) % 20 == 0:
            print(f"{i+1}/{len(paths)} images  {(i+1)/(time.time()-t0):.2f} img/s", flush=True)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({
        "n_images": len(paths), "offset": args.offset, "corpus": args.corpus,
        "coverage": args.coverage, "families": list(FAMILIES),
        "readable_ber_threshold": READABLE_BER, "seed": args.seed,
        "rows": rows,
    }, indent=1))
    print(f"wrote {len(rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
