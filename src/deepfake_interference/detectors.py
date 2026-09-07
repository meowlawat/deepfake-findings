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
    """Lazy-loaded wrapper around one HF image-classification model.

    `device`: "cpu", "cuda", or None to auto-select CUDA when available.
    `fp16`: half precision on CUDA only - roughly halves memory and speeds up
    the large-input models (EfficientNet-B6 processes at 528x528, which
    dominates cost). Never enabled on CPU, where fp16 is slower, not faster.
    """

    def __init__(self, model_id: str, device: str | None = None, fp16: bool = True):
        self.model_id = model_id
        self._model = None
        self._processor = None
        self._fake_idx = None
        self._real_idx = None
        self._device = device
        self._fp16 = fp16

    def _load(self):
        if self._model is not None:
            return
        import torch
        from transformers import AutoImageProcessor, AutoModelForImageClassification

        if self._device is None:
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._use_fp16 = bool(self._fp16 and self._device == "cuda")

        self._processor = AutoImageProcessor.from_pretrained(self.model_id)
        self._model = AutoModelForImageClassification.from_pretrained(self.model_id)
        self._model.eval()
        self._model.to(self._device)
        if self._use_fp16:
            self._model.half()
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
        return self.score_batch([image])[0]

    def default_batch_size(self) -> int:
        """32 on CUDA, 1 on CPU - and the CPU case is not laziness.

        Measured on this project's models: batching EfficientNet-B6 on CPU
        makes it nearly 3x SLOWER per image (340 -> 951 ms/img at bs=32),
        because its processor works at 528x528 and a 32-image batch of those
        tensors thrashes cache with no parallelism to win back. On GPU the
        relationship inverts and batching is the difference between a run
        that finishes and one that doesn't. So the default follows the
        device rather than being a fixed constant someone tuned once.
        """
        self._load()
        return 32 if self._device == "cuda" else 1

    def score_batch(self, images: list[np.ndarray], batch_size: int | None = None) -> list[DetectorResult]:
        """Batched inference; see default_batch_size for why the default is
        device-dependent."""
        self._load()
        if batch_size is None:
            batch_size = self.default_batch_size()
        out: list[DetectorResult] = []
        for start in range(0, len(images), batch_size):
            chunk = [Image.fromarray(img) for img in images[start:start + batch_size]]
            inputs = self._processor(images=chunk, return_tensors="pt")
            inputs = {k: v.to(self._device) for k, v in inputs.items()}
            if self._use_fp16:
                inputs = {k: (v.half() if v.is_floating_point() else v) for k, v in inputs.items()}
            with self._torch.no_grad():
                logits = self._model(**inputs).logits.float().cpu().numpy()
            for row in logits:
                lf, lr = float(row[self._fake_idx]), float(row[self._real_idx])
                out.append(DetectorResult(v=lf - lr, logit_fake=lf, logit_real=lr))
        return out


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
