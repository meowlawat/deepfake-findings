#!/usr/bin/env python3
"""Train a detector whose provenance is known by construction.

Every result so far rests on one third-party checkpoint with undisclosed
training data (docs/04 R14), and five of six public alternatives are at
chance. A reviewer cannot distinguish "attenuation is a property of
detectors" from "attenuation is a property of this checkpoint", and no
amount of further screening fixes that.

So we build one. An ImageNet-pretrained ResNet-18 is used as a *frozen*
feature extractor and a logistic head is fitted on the corpus's own train
split. Two properties follow that no public checkpoint offers here:

  - **Disclosed provenance.** The backbone's pretraining (ImageNet
    classification) is public and contains no deepfake corpus; the head is
    fitted here, on a split we name, with code in this repository.
  - **No leakage into evaluation.** The head sees only `train`. Validation
    and test are untouched, so a baseline AUC on those splits is honest by
    construction rather than by a diagnostic that can only fail to detect
    contamination.

The head is deliberately linear. A linear probe on frozen generic features
is a weak detector, and that is the point: if attenuation appears in both a
strong purpose-built CNN and a weak linear probe over generic features, it is
a property of the detection problem rather than of one architecture. If it
appears in only one, the paper says so.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np


BACKBONE_ID = "microsoft/resnet-18"


def build_backbone(device: str):
    """ImageNet ResNet-18 via the HF hub rather than torch.hub.

    torch.hub's download of resnet18-f37072fd.pth fails a hash check through
    this environment's outbound proxy (the bytes that arrive are not the
    bytes upstream signed). The HF hub path is already proven to work here,
    and `microsoft/resnet-18` is the same ImageNet-pretrained architecture,
    so the provenance argument is unchanged: ImageNet classification
    pretraining, containing no deepfake corpus.
    """
    from transformers import AutoImageProcessor, AutoModel

    processor = AutoImageProcessor.from_pretrained(BACKBONE_ID)
    model = AutoModel.from_pretrained(BACKBONE_ID)
    model.eval().to(device)
    return model, processor


def extract_features(paths, labels, device, batch_size=64, log_every=2000):
    import torch
    from PIL import Image

    model, processor = build_backbone(device)
    feats, t0 = [], time.time()
    with torch.no_grad():
        for start in range(0, len(paths), batch_size):
            imgs = [Image.open(p).convert("RGB") for p in paths[start:start + batch_size]]
            inputs = processor(images=imgs, return_tensors="pt")
            inputs = {k: v.to(device) for k, v in inputs.items()}
            out = model(**inputs).pooler_output      # (B, 512, 1, 1)
            feats.append(out.reshape(out.shape[0], -1).cpu().numpy())
            done = start + len(imgs)
            if done % log_every < batch_size:
                print(f"  {done}/{len(paths)}  {done/max(1e-9,time.time()-t0):.1f} img/s", flush=True)
    return np.concatenate(feats), np.asarray(labels)


def collect(split_dir: Path, limit: int | None):
    paths, labels = [], []
    for label, sub in ((0, "real"), (1, "fake")):
        ps = sorted((split_dir / sub).glob("*.png"))
        if limit:
            ps = ps[: limit // 2]
        paths += ps
        labels += [label] * len(ps)
    return paths, labels


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="data/corpus")
    ap.add_argument("--train-split", default="train")
    ap.add_argument("--limit", type=int, default=None, help="cap TRAIN images (balanced)")
    ap.add_argument("--out", default="models/own_detector.json")
    ap.add_argument("--device", default=None)
    args = ap.parse_args()

    import torch
    from sklearn.linear_model import LogisticRegression

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    torch.set_num_threads(4)

    paths, labels = collect(Path(args.corpus) / args.train_split, args.limit)
    print(f"training on {len(paths)} images from split '{args.train_split}' (device={device})")
    X, y = extract_features(paths, labels, device)
    print(f"features {X.shape}")

    clf = LogisticRegression(max_iter=2000, C=1.0)
    clf.fit(X, y)
    train_auc = float(np.mean((clf.predict(X) == y)))
    print(f"train accuracy (in-sample, NOT a result): {train_auc:.4f}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({
        "backbone": BACKBONE_ID + " (ImageNet ResNet-18), frozen, pooler_output",
        "head": "sklearn LogisticRegression(C=1.0, max_iter=2000) on 512-d features",
        "trained_on_split": args.train_split,
        "n_train": len(paths),
        "coef": clf.coef_[0].tolist(),
        "intercept": float(clf.intercept_[0]),
        "in_sample_accuracy": train_auc,
        "provenance_note": (
            "Backbone pretraining is ImageNet classification, which contains no "
            "deepfake corpus. The head was fitted here on the named split only. "
            "Validation and test were never seen during fitting, so baseline AUC "
            "on those splits is honest by construction."),
    }, indent=2))
    print(f"written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
