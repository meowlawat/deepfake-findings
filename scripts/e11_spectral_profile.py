#!/usr/bin/env python3
"""E11: what, exactly, does a PSNR-matched control fail to match?

E7 found that the watermark/control asymmetry on EfficientNet-B6 disappears
once the control is matched on power spectrum rather than only on PSNR. That
result needs a mechanism, and the mechanism is measurable directly: compare
where in the frequency plane each perturbation puts its energy.

For every image we form three residuals against the same clean image --
watermark, PSNR-matched control, spectrum-matched control -- take the 2-D
power spectrum of each, and integrate it over three equal-width radial bands
(low, mid, high). Reporting the fraction of total residual power per band
makes the comparison scale-free, so it is unaffected by the fact that the arms
are matched on energy by construction.

If the PSNR-matched control turns out to sit in a different band from the
watermark it is nominally controlling for, then PSNR matching is not a
sufficient control for this class of experiment, and any conclusion drawn from
it may be a statement about spectrum rather than about watermarking.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np

BANDS = [(0.0, 1 / 3), (1 / 3, 2 / 3), (2 / 3, 1.01)]
BAND_NAMES = ["low", "mid", "high"]


def band_fractions(residual: np.ndarray) -> np.ndarray:
    """Fraction of residual power in each radial frequency band, averaged over
    colour channels. Normalised per image, so arms matched on total energy are
    still distinguishable by where that energy sits."""
    P = np.zeros(len(BANDS))
    for c in range(residual.shape[2]):
        F = np.fft.fftshift(np.abs(np.fft.fft2(residual[:, :, c])) ** 2)
        h, w = F.shape
        yy, xx = np.ogrid[:h, :w]
        r = np.sqrt((yy - h // 2) ** 2 + (xx - w // 2) ** 2)
        rmax = r.max()
        for b, (lo, hi) in enumerate(BANDS):
            mask = (r >= lo * rmax) & (r < hi * rmax)
            P[b] += F[mask].mean()
    return P / P.sum()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="data/corpus/test/real")
    ap.add_argument("--offset", type=int, default=1000)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--schemes", nargs="+", default=["dwtDctSvd", "rivaGan"])
    ap.add_argument("--payload-bits", type=int, default=32)
    ap.add_argument("--image-size", type=int, default=256)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results/e11_spectral_profile.json")
    args = ap.parse_args()

    import cv2
    from deepfake_interference import null_perturbation as NP
    from deepfake_interference import watermark as W

    paths = sorted(Path(args.corpus).glob("*.png"))[args.offset: args.offset + args.n]
    report = {"n": len(paths), "bands": BAND_NAMES, "offset": args.offset, "schemes": {}}

    for scheme in args.schemes:
        acc = {"watermark": [], "psnr_matched_control": [], "spectrum_matched_control": []}
        payload_ber = {"watermark": [], "psnr_matched_control": [],
                       "spectrum_matched_control": []}
        for i, p in enumerate(paths):
            bgr = cv2.imread(str(p))
            if bgr.shape[0] != args.image_size:
                bgr = cv2.resize(bgr, (args.image_size,) * 2, interpolation=cv2.INTER_AREA)
            img = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

            rng = np.random.default_rng(args.seed + i)
            bits = list(rng.integers(0, 2, args.payload_bits))
            r = W.embed(img, bits, scheme)
            f = img.astype(np.float32)

            arms = {
                "watermark": r.watermarked,
                "psnr_matched_control": NP.match_to_target(
                    img, target_psnr=r.psnr, rng=rng).perturbed,
                "spectrum_matched_control": NP.match_spectrum_and_psnr(
                    img, r.watermarked.astype(np.float32) - f, r.psnr, rng).perturbed,
            }
            for name, arm in arms.items():
                acc[name].append(band_fractions(arm.astype(np.float32) - f))
                got = W.extract(arm, scheme, n_bits=args.payload_bits)
                payload_ber[name].append(
                    float(np.mean(np.asarray(got) != np.asarray(bits))))

        report["schemes"][scheme] = {
            name: {
                "band_fraction_mean": np.mean(v, axis=0).tolist(),
                "band_fraction_sd": np.std(v, axis=0).tolist(),
                # BER ~0.5 confirms an arm is payload-free; this is what makes
                # the spectrum-matched arm a control and not a second watermark.
                "payload_ber_mean": float(np.mean(payload_ber[name])),
            }
            for name, v in acc.items()
        }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=1))

    for scheme, d in report["schemes"].items():
        print(f"\n{scheme}  (n={report['n']})  fraction of residual power")
        print(f"  {'arm':26s} {'low':>7s} {'mid':>7s} {'high':>7s}   payload BER")
        for name, v in d.items():
            m = v["band_fraction_mean"]
            print(f"  {name:26s} {m[0]:7.3f} {m[1]:7.3f} {m[2]:7.3f}   "
                  f"{v['payload_ber_mean']:.4f}")
    print(f"\nwritten to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
