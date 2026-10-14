#!/usr/bin/env python3
"""E10: is the attenuation caused by input resolution?

The paper observes attenuation on EfficientNet-B6 (processing at 528x528) and
not on a ResNet-18 probe (processing at 224x224), and currently says the cause
is unresolved, naming training augmentation and input resolution as untested
possibilities. Resolution is the one we can test cleanly, because it can be
varied while holding everything else fixed.

The mechanism, if it is resolution, is concrete. Corpus images are 256x256.
A detector processing at 224 DOWNSAMPLES them, and downsampling averages
neighbouring pixels, which suppresses exactly the fine-grained perturbation
the control arm adds before the network ever sees it. A detector processing at
528 UPSAMPLES, preserving that perturbation. So:

    H_resolution: the null arm's slope falls (more attenuation) as input
                  resolution rises above the corpus resolution.

This holds architecture, backbone weights, training data, head type and
training split constant and varies ONLY the input resolution at which features
are extracted, for both the probe fit and the scoring. A ResNet-18 is fully
convolutional with global pooling, so it accepts all three sizes natively and
no architectural change is needed to sweep them.

A confirmed prediction supports resolution as the mechanism. A flat sweep
rules resolution out and leaves the mechanism unresolved, which we would
report as such.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np

BACKBONE = "microsoft/resnet-18"


def build(device):
    from transformers import AutoImageProcessor, AutoModel
    proc = AutoImageProcessor.from_pretrained(BACKBONE)
    model = AutoModel.from_pretrained(BACKBONE)
    model.eval().to(device)
    return model, proc


def feats(model, proc, imgs, res, device, batch=32):
    """Pooled features at an explicit input resolution."""
    import torch
    from PIL import Image
    out = []
    with torch.no_grad():
        for s in range(0, len(imgs), batch):
            chunk = [Image.fromarray(im).resize((res, res), Image.BILINEAR)
                     for im in imgs[s:s + batch]]
            inp = proc(images=chunk, return_tensors="pt",
                       do_resize=False, do_center_crop=False)
            inp = {k: v.to(device) for k, v in inp.items()}
            p = model(**inp).pooler_output
            out.append(p.reshape(p.shape[0], -1).cpu().numpy())
    return np.concatenate(out)


def load_images(root: Path, offset: int, n: int, size: int):
    import cv2
    imgs, labels = [], []
    per = n // 2
    for label, sub in ((0, "real"), (1, "fake")):
        for p in sorted((root / sub).glob("*.png"))[offset: offset + per]:
            bgr = cv2.imread(str(p))
            if bgr is None:
                continue
            if bgr.shape[0] != size:
                bgr = cv2.resize(bgr, (size, size), interpolation=cv2.INTER_AREA)
            imgs.append(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            labels.append(label)
    return imgs, np.array(labels)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="data/corpus")
    ap.add_argument("--resolutions", nargs="+", type=int, default=[224, 320, 448])
    ap.add_argument("--n-train", type=int, default=1200)
    ap.add_argument("--n-eval", type=int, default=600)
    ap.add_argument("--eval-offset", type=int, default=6000,
                    help="disjoint from every other analysis on the test split")
    ap.add_argument("--scheme", default="dwtDctSvd")
    ap.add_argument("--payload-bits", type=int, default=32)
    ap.add_argument("--image-size", type=int, default=256)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results/e10_resolution_ablation.json")
    args = ap.parse_args()

    import torch
    from sklearn.linear_model import LogisticRegression
    from deepfake_interference import null_perturbation as NP
    from deepfake_interference import watermark as W

    torch.set_num_threads(4)
    device = "cpu"
    model, proc = build(device)

    print("loading train images...", flush=True)
    tr_imgs, tr_y = load_images(Path(args.corpus) / "train", 0, args.n_train, args.image_size)
    print("loading eval images...", flush=True)
    ev_imgs, ev_y = load_images(Path(args.corpus) / "test", args.eval_offset,
                                args.n_eval, args.image_size)
    print(f"train={len(tr_imgs)} eval={len(ev_imgs)}", flush=True)

    # Build the three eval arms ONCE; every resolution sees identical pixels,
    # so a difference across resolutions cannot come from a difference in arms.
    print("building arms...", flush=True)
    t0 = time.time()
    arms = {"clean": ev_imgs, args.scheme: [], f"null[{args.scheme}]": []}
    for i, im in enumerate(ev_imgs):
        rng = np.random.default_rng(args.seed + i)
        bits = list(rng.integers(0, 2, args.payload_bits))
        res = W.embed(im, bits, args.scheme)
        arms[args.scheme].append(res.watermarked)
        arms[f"null[{args.scheme}]"].append(
            NP.match_to_target(im, target_psnr=res.psnr, rng=rng, tolerance_db=0.5).perturbed)
        if (i + 1) % 100 == 0:
            print(f"  arms {i+1}/{len(ev_imgs)}  {(i+1)/(time.time()-t0):.2f} img/s", flush=True)

    rng = np.random.default_rng(args.seed)
    report = {"backbone": BACKBONE, "scheme": args.scheme,
              "n_train": len(tr_imgs), "n_eval": len(ev_imgs),
              "n_boot": args.n_boot, "resolutions": {}}

    for res_px in args.resolutions:
        print(f"\n=== resolution {res_px} ===", flush=True)
        t = time.time()
        Xtr = feats(model, proc, tr_imgs, res_px, device)
        clf = LogisticRegression(max_iter=2000, C=1.0).fit(Xtr, tr_y)
        print(f"  fit on {Xtr.shape} in {time.time()-t:.0f}s", flush=True)

        scores = {}
        for arm, imgs in arms.items():
            X = feats(model, proc, imgs, res_px, device)
            scores[arm] = X @ clf.coef_[0] + clf.intercept_[0]

        from sklearn.metrics import roc_auc_score
        clean = scores["clean"]
        entry = {"baseline_auc": float(roc_auc_score(ev_y, clean)), "arms": {}}

        for arm in (args.scheme, f"null[{args.scheme}]"):
            v = scores[arm]
            point = float(np.polyfit(clean, v, 1)[0])
            bs = np.empty(args.n_boot)
            n = len(clean)
            for b in range(args.n_boot):
                sel = rng.integers(0, n, n)
                bs[b] = np.polyfit(clean[sel], v[sel], 1)[0]
            entry["arms"][arm] = {
                "slope": point,
                "ci": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                "auc": float(roc_auc_score(ev_y, v)),
            }
        # the contrast the hypothesis is about
        wm, nl = entry["arms"][args.scheme]["slope"], entry["arms"][f"null[{args.scheme}]"]["slope"]
        entry["null_minus_wm"] = nl - wm
        report["resolutions"][str(res_px)] = entry
        print(f"  baseline AUC {entry['baseline_auc']:.4f}  "
              f"wm b={wm:.4f}  null b={nl:.4f}  null-wm={nl-wm:+.4f}", flush=True)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=1))
    print(f"\nwritten to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
