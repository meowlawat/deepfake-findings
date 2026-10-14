"""Transform suite T - docs/03 S1, reduced to 3 classes for v1.

Each function takes and returns an H,W,3 uint8 RGB image, so they compose
freely with watermark.py and detectors.py without format juggling.
"""
from __future__ import annotations

import cv2
import numpy as np


def jpeg_compress(image: np.ndarray, quality: int) -> np.ndarray:
    """JPEG re-encode at `quality` (1-100). docs/03: q in {90, 70, 50}."""
    bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    ok, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("JPEG encode failed")
    decoded = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    return cv2.cvtColor(decoded, cv2.COLOR_BGR2RGB)


def resize_roundtrip(image: np.ndarray, scale: float) -> np.ndarray:
    """Downscale by `scale` then upscale back to the original size, so output
    shape matches input shape and downstream code never branches on it.
    docs/03: scale in {0.75, 0.5}.
    """
    h, w = image.shape[:2]
    small = cv2.resize(image, (max(1, int(w * scale)), max(1, int(h * scale))),
                        interpolation=cv2.INTER_AREA)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)


def brightness_contrast(image: np.ndarray, delta_pct: float) -> np.ndarray:
    """Brightness and contrast shift of +/- delta_pct percent, applied
    identically (both scale by the same factor around mid-gray). docs/03:
    +/-20%, called out because transform-domain marks reportedly fail here.
    """
    factor = 1.0 + delta_pct / 100.0
    shifted = (image.astype(np.float32) - 127.5) * factor + 127.5
    shifted = shifted + (127.5 * (factor - 1.0))  # brightness component
    return np.clip(shifted, 0, 255).astype(np.uint8)


TRANSFORM_GRID: dict[str, list[dict]] = {
    "jpeg": [{"quality": q} for q in (90, 70, 50)],
    "resize": [{"scale": s} for s in (0.75, 0.5)],
    "brightness_contrast": [{"delta_pct": d} for d in (20, -20)],
}


def apply(name: str, image: np.ndarray, **kwargs) -> np.ndarray:
    return {
        "jpeg": jpeg_compress,
        "resize": resize_roundtrip,
        "brightness_contrast": brightness_contrast,
    }[name](image, **kwargs)
