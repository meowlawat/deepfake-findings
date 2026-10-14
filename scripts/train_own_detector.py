#!/usr/bin/env python3
"""Train a detector whose provenance is known by construction.

Every result so far rests on one third-party checkpoint with undisclosed
training data (docs/04 R14), and five of six public alternatives are at
chance. A reviewer cannot distinguish "attenuation is a property of
detectors" from "attenuation is a property of this checkpoint", and no
amount of further screening fixes that.

So we build these. A pretrained backbone is used as a *frozen* feature
extractor and a logistic head is fitted on the corpus's own train split.
Two properties follow that no public checkpoint offers here:

  - **Disclosed provenance.** The backbone's pretraining is public and
    contains no deepfake corpus; the head is fitted here, on a split we
    name, with code in this repository.
  - **No leakage into evaluation.** The head sees only `train`. Validation
    and test are untouched, so a baseline AUC on those splits is honest by
    construction rather than by a diagnostic that can only fail to detect
    contamination.

The head is deliberately linear. A linear probe on frozen generic features
is a weak detector, and that is the point: if attenuation appears across a
strong purpose-built CNN AND several architecturally distinct linear probes
over generic features, it is a property of the detection problem rather than
of one architecture. If it appears in only one, the paper says so.

Backbones registered below (see docs/07): microsoft/resnet-18 (existing
panel entry, "own"), facebook/convnext-base-224-22k-1k (modern CNN family),
google/vit-base-patch16-224-in21k (transformer family, CLS-token features --
see extract_features for why CLS rather than pooler_output is used for ViT).
Fine-tuning is deliberately never offered here: end-to-end backprop would let
a backbone memorize this corpus's pixel statistics, breaking the "generic
features" argument the disclosed panel depends on -- see docs/07's rejected
scope.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np


# name -> (HF model id, pooling strategy, human-readable provenance note)
BACKBONES = {
    "resnet18": (
        "microsoft/resnet-18", "pooler",
        "ImageNet-1k classification pretraining (ResNet-18), contains no deepfake corpus.",
    ),
    "convnext-base": (
        "facebook/convnext-base-224-22k-1k", "pooler",
        "ImageNet-21k->1k classification pretraining (ConvNeXt-Base), contains no deepfake corpus.",
    ),
    "vit-b16": (
        "google/vit-base-patch16-224-in21k", "cls",
        "ImageNet-21k pretraining, no classification fine-tuning (ViT-B/16), contains no deepfake corpus.",
    ),
}


def build_backbone(model_id: str, device: str):
    """Any of the registered backbones via the HF hub.

    torch.hub's download of resnet18-f37072fd.pth fails a hash check through
    this environment's outbound proxy (the bytes that arrive are not the
    bytes upstream signed), which is why every backbone here goes through
    the HF hub rather than torch.hub -- already proven to work in this
    sandbox. Same architecture, same provenance argument either way.
    """
    from transformers import AutoImageProcessor, AutoModel

    processor = AutoImageProcessor.from_pretrained(model_id)
    model = AutoModel.from_pretrained(model_id)
    model.eval().to(device)
    return model, processor


def pooled_features(out, pooling: str):
    """pooler: global-pool output HF already provides (ResNet/ConvNeXt --
    plain spatial average pooling, nothing separately trained). cls: the
    [CLS] token from the last hidden state, used for ViT instead of
    pooler_output because a ViT's HF pooler is a Dense+Tanh layer that is not
    reliably pretrained for every checkpoint on the hub; the CLS token itself
    is the representation actually trained by the backbone."""
    if pooling == "pooler":
        feat = out.pooler_output
    elif pooling == "cls":
        feat = out.last_hidden_state[:, 0]
    else:
        raise ValueError(f"unknown pooling strategy: {pooling}")
    return feat.reshape(feat.shape[0], -1)


def extract_features(paths, labels, model_id, pooling, device, batch_size=32, log_every=1000):
    import torch
    from PIL import Image

    model, processor = build_backbone(model_id, device)
    feats, t0 = [], time.time()
    with torch.no_grad():
        for start in range(0, len(paths), batch_size):
            imgs = [Image.open(p).convert("RGB") for p in paths[start:start + batch_size]]
            inputs = processor(images=imgs, return_tensors="pt")
            inputs = {k: v.to(device) for k, v in inputs.items()}
            out = model(**inputs)
            feats.append(pooled_features(out, pooling).cpu().numpy())
            done = start + len(imgs)
            if done % log_every < batch_size or done == len(paths):
                rate = done / max(1e-9, time.time() - t0)
                print(f"  {done}/{len(paths)}  {rate:.2f} img/s", flush=True)
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
    ap.add_argument("--backbone", choices=sorted(BACKBONES), default="resnet18")
    ap.add_argument("--corpus", default="data/corpus")
    ap.add_argument("--train-split", default="train")
    ap.add_argument("--limit", type=int, default=None, help="cap TRAIN images (balanced)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--device", default=None)
    ap.add_argument("--batch-size", type=int, default=None)
    ap.add_argument("--cache-dir", default="cache/features",
                    help="extracted features are cached here; a re-run with the "
                         "same backbone/split/n reuses them instead of "
                         "re-extracting. Pass '' to disable.")
    args = ap.parse_args()

    import torch
    from sklearn.linear_model import LogisticRegression

    model_id, pooling, provenance = BACKBONES[args.backbone]
    out_path = args.out or f"models/own_detector_{args.backbone}.json"

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    torch.set_num_threads(4)

    paths, labels = collect(Path(args.corpus) / args.train_split, args.limit)
    print(f"backbone={args.backbone} ({model_id})  pooling={pooling}  "
          f"training on {len(paths)} images from split '{args.train_split}' (device={device})")

    # Extraction is the expensive step and the head is cheap, so cache the
    # features: an interrupted or repeated run refits in seconds instead of
    # re-reading every image through the backbone.
    cache = (Path(args.cache_dir) /
             f"{args.backbone}_{args.train_split}_{len(paths)}.npz"
             if args.cache_dir else None)
    if cache and cache.exists():
        d = np.load(cache)
        X, y = d["X"], d["y"]
        print(f"features {X.shape} (loaded from {cache})")
    else:
        kw = {"batch_size": args.batch_size} if args.batch_size else {}
        X, y = extract_features(paths, labels, model_id, pooling, device, **kw)
        print(f"features {X.shape}")
        if cache:
            cache.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(cache, X=X, y=y)
            print(f"cached to {cache}")

    clf = LogisticRegression(max_iter=2000, C=1.0)
    clf.fit(X, y)
    train_auc = float(np.mean((clf.predict(X) == y)))
    print(f"train accuracy (in-sample, NOT a result): {train_auc:.4f}")

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps({
        "backbone_key": args.backbone,
        "backbone_id": model_id,
        "pooling": pooling,
        "backbone": f"{model_id}, frozen, {pooling} features",
        "head": f"sklearn LogisticRegression(C=1.0, max_iter=2000) on {X.shape[1]}-d features",
        "trained_on_split": args.train_split,
        "n_train": len(paths),
        "coef": clf.coef_[0].tolist(),
        "intercept": float(clf.intercept_[0]),
        "in_sample_accuracy": train_auc,
        "provenance_note": (
            f"{provenance} The head was fitted here on the named split only. "
            "Validation and test were never seen during fitting, so baseline AUC "
            "on those splits is honest by construction."),
    }, indent=2))
    print(f"written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
