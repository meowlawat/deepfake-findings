"""The missing manipulation step D - docs/02 S1, docs/04 (structural limit).

Everything up to this point watermarked images that were *already* real or
already synthetic, so the mark was applied after the fact and survived
equally on both classes. That makes the provenance channel carry no
information about the label by construction, and it is why the fusion half of
the framework was untestable.

Deployment has the opposite ordering:

    authentic image -> embed watermark -> MANIPULATION -> high BER signals tampering

This module supplies the manipulation. It is a region splice: an elliptical
face-sized region of a donor image is composited into the host with Poisson
blending (`cv2.seamlessClone`), which is what a face swap does geometrically
- replace the face region, blend the seam - without needing a generative
model, which the compute budget excludes.

What matters for the experiment is not photorealism but the *provenance
mechanics*, and those are faithful: the watermark survives outside the
spliced region and is destroyed inside it, so bit error rate rises with the
manipulated area exactly as it would under a real face swap. We state
plainly in the paper that this is a splice rather than a learned face swap,
and that the detector-facing realism is therefore limited; the claim it
supports is about how provenance evidence behaves under localised tampering,
not about detecting state-of-the-art face swaps.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class SpliceResult:
    manipulated: np.ndarray
    area_fraction: float          # fraction of the image the splice covers
    center: tuple[int, int]
    axes: tuple[int, int]


def splice_region(host: np.ndarray, donor: np.ndarray,
                   area_fraction: float = 0.18,
                   rng: np.random.Generator | None = None) -> SpliceResult:
    """Composite an elliptical region of `donor` into `host`.

    `area_fraction` is the target fraction of image area covered. Poisson
    blending removes the hard seam, so the result is not trivially detectable
    as a paste, and - importantly for provenance - the blend modifies pixels
    smoothly across the boundary rather than leaving an abrupt watermark
    discontinuity that a decoder could exploit as a tell.
    """
    rng = rng or np.random.default_rng(0)
    h, w = host.shape[:2]
    if donor.shape[:2] != (h, w):
        donor = cv2.resize(donor, (w, h), interpolation=cv2.INTER_AREA)

    # Ellipse axes chosen so pi*a*b / (h*w) == area_fraction, centred near the
    # middle where a face sits in this corpus, with mild jitter so the splice
    # is not at an identical location in every image.
    target = area_fraction * h * w
    ratio = 1.3                                  # taller than wide, face-like
    b = int(np.sqrt(target / (np.pi * ratio)))
    a = int(ratio * b)
    cx = int(w // 2 + rng.integers(-w // 20, w // 20 + 1))
    cy = int(h // 2 + rng.integers(-h // 20, h // 20 + 1))
    a = max(8, min(a, w // 2 - 2))
    b = max(8, min(b, h // 2 - 2))
    cx = int(np.clip(cx, a + 1, w - a - 1))
    cy = int(np.clip(cy, b + 1, h - b - 1))

    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.ellipse(mask, (cx, cy), (a, b), 0, 0, 360, 255, -1)

    blended = cv2.seamlessClone(
        cv2.cvtColor(donor, cv2.COLOR_RGB2BGR),
        cv2.cvtColor(host, cv2.COLOR_RGB2BGR),
        mask, (cx, cy), cv2.NORMAL_CLONE,
    )
    manipulated = cv2.cvtColor(blended, cv2.COLOR_BGR2RGB)
    return SpliceResult(
        manipulated=manipulated,
        area_fraction=float(mask.mean() / 255.0),
        center=(cx, cy), axes=(a, b),
    )


def inpaint_region(host: np.ndarray, area_fraction: float = 0.18,
                    rng: np.random.Generator | None = None) -> SpliceResult:
    """Alternative manipulation: remove a region and reconstruct it from its
    surroundings. Unlike the splice this introduces no foreign content, so it
    isolates "the watermark was destroyed locally" from "foreign pixels were
    introduced" - a useful second condition when attributing any effect.
    """
    rng = rng or np.random.default_rng(0)
    h, w = host.shape[:2]
    target = area_fraction * h * w
    ratio = 1.3
    b = max(8, min(int(np.sqrt(target / (np.pi * ratio))), h // 2 - 2))
    a = max(8, min(int(ratio * b), w // 2 - 2))
    cx = int(np.clip(w // 2 + rng.integers(-w // 20, w // 20 + 1), a + 1, w - a - 1))
    cy = int(np.clip(h // 2 + rng.integers(-h // 20, h // 20 + 1), b + 1, h - b - 1))

    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.ellipse(mask, (cx, cy), (a, b), 0, 0, 360, 255, -1)
    bgr = cv2.cvtColor(host, cv2.COLOR_RGB2BGR)
    filled = cv2.inpaint(bgr, mask, 3, cv2.INPAINT_TELEA)
    return SpliceResult(
        manipulated=cv2.cvtColor(filled, cv2.COLOR_BGR2RGB),
        area_fraction=float(mask.mean() / 255.0),
        center=(cx, cy), axes=(a, b),
    )
