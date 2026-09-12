"""Watermark embed/extract harness - docs/03 S1 scheme table.

Wraps `invisible-watermark`'s DwtDctSvd (hand-crafted, weak arm) and RivaGan
(learned encoder/decoder, strong arm; ONNX weights ship inside the pip
package, verified this session - no separate download, no training). Both
loaded lazily so importing this module doesn't require onnxruntime unless
RivaGan is actually used.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from .metrics import bit_error_rate, psnr, ssim

Scheme = Literal["dwtDctSvd", "rivaGan"]

_MODELS_LOADED = {"rivaGan": False}


def _ensure_model_loaded(method: Scheme) -> None:
    if method == "rivaGan" and not _MODELS_LOADED["rivaGan"]:
        from imwatermark import WatermarkDecoder, WatermarkEncoder

        WatermarkEncoder.loadModel()
        WatermarkDecoder.loadModel()
        _MODELS_LOADED["rivaGan"] = True


# RivaGan is fixed at 32 payload bits by the shipped model; DwtDctSvd handles
# arbitrary lengths but we standardise on the same length for a fair
# comparison and so a single ProvenancePayload framing (docs/02 SS2.1) fits
# both schemes without a per-scheme special case leaking into the fusion code.
PAYLOAD_BITS = 32


@dataclass
class EmbedResult:
    watermarked: np.ndarray
    sent_bits: list[int]
    psnr: float
    ssim: float


def embed(image: np.ndarray, bits: list[int], method: Scheme) -> EmbedResult:
    """Embed `bits` (length PAYLOAD_BITS) into `image` (H,W,3 uint8, RGB)."""
    from imwatermark import WatermarkEncoder

    if len(bits) != PAYLOAD_BITS:
        raise ValueError(f"expected {PAYLOAD_BITS} bits, got {len(bits)}")
    _ensure_model_loaded(method)
    enc = WatermarkEncoder()
    enc.set_watermark("bits", list(bits))
    watermarked = enc.encode(image, method)
    return EmbedResult(
        watermarked=watermarked,
        sent_bits=list(bits),
        psnr=psnr(image, watermarked),
        ssim=ssim(image, watermarked),
    )


def extract(image: np.ndarray, method: Scheme, n_bits: int = PAYLOAD_BITS) -> list[int]:
    """Recover a bit list from a (possibly transformed) image."""
    from imwatermark import WatermarkDecoder

    _ensure_model_loaded(method)
    dec = WatermarkDecoder("bits", n_bits)
    recovered = dec.decode(image, method)
    return [int(b) for b in recovered]


def embed_and_measure(image: np.ndarray, bits: list[int], method: Scheme) -> tuple[np.ndarray, float, float, float]:
    """Convenience: embed, then immediately re-extract with no transform to get
    the scheme's clean BER on this image (used to estimate p_0, docs/02 SS2).

    Returns (watermarked_image, psnr, ssim, clean_ber).
    """
    result = embed(image, bits, method)
    recovered = extract(result.watermarked, method, n_bits=len(bits))
    ber = bit_error_rate(result.sent_bits, recovered)
    return result.watermarked, result.psnr, result.ssim, ber
