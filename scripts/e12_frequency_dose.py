#!/usr/bin/env python3
"""E12: is the detector's attenuation actually a function of frequency?

E7/E11 leave an inferential gap the manuscript currently papers over. We
observed two conditions -- a high-frequency-dominated control that attenuates,
and low-frequency-dominated arms (watermark, spectrum-matched control) that do
not -- and the manuscript calls the result "high-frequency sensitivity". Two
points do not establish a frequency response. The same data are equally
consistent with sensitivity to some property correlated with our particular
high-pass noise.

This measures the dose-response directly. We build payload-free perturbations
confined to a single radial frequency band -- low, mid, or high -- each
binary-searched to the same per-image PSNR as the watermark, and fit the same
evidence-transfer slope. Everything except the band is held fixed.

  H_freq: slope decreases monotonically as the perturbation's band rises.

A monotone decrease turns "high-frequency sensitivity" from an inference into
a measurement. A flat or non-monotone profile falsifies it, and the manuscript
must then retreat to the purely descriptive statement that two specific
controls differ.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np

BANDS = {"low": (0.0, 1 / 3), "mid": (1 / 3, 2 / 3), "high": (2 / 3, 1.01)}


def band_noise(shape, lo, hi, rng):
    """White noise projected onto one radial frequency band, per channel."""
    h, w, c = shape
    yy, xx = np.ogrid[:h, :w]
    r = np.sqrt((yy - h // 2) ** 2 + (xx - w // 2) ** 2)
    rmax = r.max()
    mask = ((r >= lo * rmax) & (r < hi * rmax)).astype(np.float32)
    out = np.empty(shape, dtype=np.float32)
    for ch in range(c):
        F = np.fft.fftshift(np.fft.fft2(rng.standard_normal((h, w))))
        out[:, :, ch] = np.real(np.fft.ifft2(np.fft.ifftshift(F * mask)))
    rms = np.sqrt(np.mean(out ** 2))
    return out / (rms + 1e-12)


def match_psnr(image, base, target_psnr, iters=20):
    from deepfake_interference.metrics import psnr as PSNR
    lo, hi, best = 0.0, 255.0, None
    for i in range(iters):
        mid = (lo + hi) / 2
        cand = np.clip(image.astype(np.float32) + mid * base, 0, 255).astype(np.uint8)
        p = PSNR(image, cand)
        if best is None or abs(p - target_psnr) < abs(best[1] - target_psnr):
            best = (cand, p)
        if abs(p - target_psnr) <= 0.5:
            break
        if p > target_psnr:
            lo = mid
        else:
            hi = mid
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="data/corpus/test")
    ap.add_argument("--offset", type=int, default=8000,
                    help="disjoint from E7 (1000), E8 (4000) and E10 (6000)")
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--image-size", type=int, default=256)
    ap.add_argument("--scheme", default="dwtDctSvd")
    ap.add_argument("--payload-bits", type=int, default=32)
    ap.add_argument("--detector", default="effnet")
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results/e12_frequency_dose.json")
    args = ap.parse_args()

    import cv2
    import yaml
    from deepfake_interference import watermark as W
    from deepfake_interference.detectors import Detector

    cfg = yaml.safe_load(Path("config.yaml").read_text())
    det = Detector(cfg["detectors"][args.detector])
    det._load()

    paths = []
    per = args.n // 2
    for label, sub in ((0, "real"), (1, "fake")):
        paths += [(p, label) for p in
                  sorted((Path(args.corpus) / sub).glob("*.png"))[args.offset: args.offset + per]]

    arms = {k: [] for k in ["clean", "watermark"] + list(BANDS)}
    labels, quality, t0 = [], [], time.time()

    for i, (p, label) in enumerate(paths):
        bgr = cv2.imread(str(p))
        if bgr is None:
            continue
        if bgr.shape[0] != args.image_size:
            bgr = cv2.resize(bgr, (args.image_size,) * 2, interpolation=cv2.INTER_AREA)
        img = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        rng = np.random.default_rng(args.seed + i)

        bits = list(rng.integers(0, 2, args.payload_bits))
        r = W.embed(img, bits, args.scheme)
        arms["clean"].append(img)
        arms["watermark"].append(r.watermarked)
        q = {"wm_psnr": r.psnr}
        for band, (lo, hi) in BANDS.items():
            base = band_noise(img.shape, lo, hi, rng)
            cand, p_ach = match_psnr(img, base, r.psnr)
            arms[band].append(cand)
            q[f"{band}_psnr"] = float(p_ach)
        quality.append(q)
        labels.append(label)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(paths)}  {(i+1)/(time.time()-t0):.2f} img/s", flush=True)

    print("scoring...", flush=True)
    scores = {k: np.array([x.v for x in det.score_batch(v)]) for k, v in arms.items()}

    rng = np.random.default_rng(args.seed)
    clean = scores["clean"]
    n = len(clean)
    report = {"n": n, "detector": args.detector, "scheme": args.scheme,
              "offset": args.offset, "n_boot": args.n_boot,
              "psnr_mean": {k: float(np.mean([q[f"{k}_psnr"] for q in quality]))
                            for k in BANDS},
              "wm_psnr_mean": float(np.mean([q["wm_psnr"] for q in quality])),
              "arms": {}}

    for arm in ["watermark"] + list(BANDS):
        v = scores[arm]
        pt = float(np.polyfit(clean, v, 1)[0])
        bs = np.empty(args.n_boot)
        for b in range(args.n_boot):
            s = rng.integers(0, n, n)
            bs[b] = np.polyfit(clean[s], v[s], 1)[0]
        report["arms"][arm] = {"slope": pt,
                               "ci": [float(np.percentile(bs, 2.5)),
                                      float(np.percentile(bs, 97.5))]}

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=1))

    print(f"\nn={n}  detector={args.detector}  watermark PSNR={report['wm_psnr_mean']:.2f}")
    for arm, v in report["arms"].items():
        extra = f"  (PSNR {report['psnr_mean'][arm]:.2f})" if arm in BANDS else ""
        print(f"  {arm:10s} b={v['slope']:.4f} [{v['ci'][0]:.4f},{v['ci'][1]:.4f}]{extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
