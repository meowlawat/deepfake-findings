#!/usr/bin/env python3
"""Reproduce docs/03 S0's tooling verification in code, so 'verified this
session' is a runnable claim, not just a paragraph in a doc. Run this first,
on the actual machine that will run the rest of the pipeline (Kaggle or the
local 3050) - onnxruntime/torch availability and CPU/GPU behaviour can differ
from where this was drafted.

Exit code is nonzero if anything fails, so it can gate a CI step or a
Kaggle-notebook cell without a human reading the output.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np


def _photo_like_image(seed=0):
    import cv2

    rng = np.random.default_rng(seed)
    base = rng.random((256, 256, 3)).astype(np.float32)
    smooth = cv2.GaussianBlur(base, (31, 31), 0)
    smooth = (smooth - smooth.min()) / (smooth.max() - smooth.min()) * 255
    return smooth.astype(np.uint8)


def check_watermarking() -> bool:
    from deepfake_interference import watermark

    image = _photo_like_image()
    bits = list(np.random.default_rng(1).integers(0, 2, watermark.PAYLOAD_BITS))
    ok = True
    for scheme in ("dwtDctSvd", "rivaGan"):
        try:
            wm, psnr, ssim, ber = watermark.embed_and_measure(image, bits, scheme)
            print(f"  [{scheme}] PSNR={psnr:.1f}dB SSIM={ssim:.3f} clean-BER={ber:.3f}")
        except Exception as e:
            print(f"  [{scheme}] FAILED: {e}")
            ok = False
    return ok


def check_crypto_binding() -> bool:
    from deepfake_interference import crypto_binding as cb
    from deepfake_interference import watermark

    sk, pk = cb.generate_keypair()
    rng = np.random.default_rng(2)
    clean, watermarked, key_ids = [], [], []
    for i in range(8):
        image = _photo_like_image(seed=i + 10)
        bits = list(rng.integers(0, 2, watermark.PAYLOAD_BITS))
        result = watermark.embed(image, bits, "dwtDctSvd")
        clean.append(image)
        watermarked.append(result.watermarked)
        key_ids.append(i.to_bytes(4, "big"))
    rate = cb.verification_reliability_rate(clean, watermarked, sk, pk, key_ids, timestamp=int(time.time()))
    print(f"  crypto-binding false-negative rate on photo-like content: {rate:.3f}")
    if rate > 0.2:
        print("  WARNING: unexpectedly high - re-tune DEFAULT_HASH_SIZE before trusting this on real data")
    return True


def check_detectors() -> bool:
    from deepfake_interference.detectors import DETECTOR_MODEL_IDS, Detector

    image = _photo_like_image(seed=42)
    ok = True
    for name, model_id in DETECTOR_MODEL_IDS.items():
        try:
            det = Detector(model_id)
            result = det.score(image)
            print(f"  [{name}] {model_id} -> V={result.v:.3f} "
                  f"(logit_fake={result.logit_fake:.3f}, logit_real={result.logit_real:.3f})")
        except Exception as e:
            print(f"  [{name}] {model_id} FAILED: {e}")
            ok = False
    return ok


def check_dataset(root: str = "data/raw") -> bool:
    from deepfake_interference.data import discover

    try:
        items = discover(Path(root))
        print(f"  found {len(items)} images under {root}")
        return True
    except FileNotFoundError as e:
        print(f"  NOT FOUND (expected until the Kaggle dataset is placed locally): {e}")
        return False


def main() -> int:
    print("=== invisible-watermark (DwtDctSvd, RivaGan) ===")
    ok_wm = check_watermarking()
    print("=== Ed25519 provenance binding ===")
    ok_crypto = check_crypto_binding()
    print("=== HF detectors (ViT, EfficientNet-B6) ===")
    ok_det = check_detectors()
    print("=== dataset ===")
    ok_data = check_dataset()

    print()
    print("Summary:")
    print(f"  watermarking : {'OK' if ok_wm else 'FAIL'}")
    print(f"  crypto binding: {'OK' if ok_crypto else 'FAIL'}")
    print(f"  detectors    : {'OK' if ok_det else 'FAIL'}")
    print(f"  dataset      : {'OK' if ok_data else 'MISSING (place the Kaggle dataset under data/raw)'}")

    # Dataset absence doesn't fail the check here - it's expected in this
    # environment and is a local-machine step, not a code bug.
    return 0 if (ok_wm and ok_crypto and ok_det) else 1


if __name__ == "__main__":
    raise SystemExit(main())
