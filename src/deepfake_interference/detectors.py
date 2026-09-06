"""Passive detector harness - docs/03 S0/S1. Two verified pretrained models,
used zero-shot (no fine-tuning), returning the raw logit V - docs/02 S1: raw
logit, not softmax probability, because softmax confidence is known to be
unreliable exactly under the perturbation/OOD regime this study operates in.

Detector A: Wvolf/ViT_Deepfake_Detection (ViT). id2label {0: Real, 1: Fake}.
Detector B: Skullly/DeepFake-EN-B6 (EfficientNet-B6, genuinely different
    backbone family from A). id2label {0: f, 1: r} - note the REVERSED index
    order relative to A. Never hardcode an index; resolve it from id2label
    every time, per model.

Both verified this session to load via transformers.AutoModelForImageClassification
and to produce sane two-class logits (see docs/03 S0). Both carry an
unresolved training-data leakage risk (docs/04 R14) - the mitigation lives in
fusion.py / the analysis scripts (within-model deltas, not absolute accuracy
claims), not in this module.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

DETECTOR_MODEL_IDS = {
    "vit": "Wvolf/ViT_Deepfake_Detection",
    "effnet": "Skullly/DeepFake-EN-B6",
}


@dataclass
class DetectorResult:
    v: float  # raw logit(fake) - logit(real), docs/02 S1/S3
    logit_fake: float
    logit_real: float


class Detector:
    """Lazy-loaded wrapper around one HF image-classification model."""

    def __init__(self, model_id: str):
        self.model_id = model_id
        self._model = None
        self._processor = None
        self._fake_idx = None
        self._real_idx = None

    def _load(self):
        if self._model is not None:
            return
        import torch
        from transformers import AutoImageProcessor, AutoModelForImageClassification

        self._processor = AutoImageProcessor.from_pretrained(self.model_id)
        self._model = AutoModelForImageClassification.from_pretrained(self.model_id)
        self._model.eval()
        id2label = {int(k): v.lower() for k, v in self._model.config.id2label.items()}
        fake_candidates = [i for i, name in id2label.items() if "fake" in name or name == "f"]
        real_candidates = [i for i, name in id2label.items() if "real" in name or name == "r"]
        if len(fake_candidates) != 1 or len(real_candidates) != 1:
            raise ValueError(
                f"{self.model_id}: could not unambiguously resolve fake/real "
                f"indices from id2label={id2label}"
            )
        self._fake_idx, self._real_idx = fake_candidates[0], real_candidates[0]
        self._torch = torch

    def score(self, image: np.ndarray) -> DetectorResult:
        """image: H,W,3 uint8 RGB."""
        self._load()
        pil_image = Image.fromarray(image)
        inputs = self._processor(images=pil_image, return_tensors="pt")
        with self._torch.no_grad():
            logits = self._model(**inputs).logits[0].numpy()
        logit_fake = float(logits[self._fake_idx])
        logit_real = float(logits[self._real_idx])
        return DetectorResult(v=logit_fake - logit_real, logit_fake=logit_fake, logit_real=logit_real)

    def score_batch(self, images: list[np.ndarray]) -> list[DetectorResult]:
        return [self.score(img) for img in images]


class DummyDetector:
    """Deterministic, dependency-free stand-in used only in tests/smoke runs
    where no network or model download is available. Never used for anything
    that ends up as a number in the paper.
    """

    def __init__(self, seed: int = 0, fake_bias: float = 1.0):
        self._rng = np.random.default_rng(seed)
        self._fake_bias = fake_bias

    def score(self, image: np.ndarray, is_fake_hint: bool = False) -> DetectorResult:
        base = self._fake_bias if is_fake_hint else -self._fake_bias
        v = base + float(self._rng.standard_normal())
        return DetectorResult(v=v, logit_fake=v / 2, logit_real=-v / 2)
