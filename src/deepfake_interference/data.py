"""Dataset loading and splits - docs/03 S1.

Expects a local directory with `real/` and `fake/` subfolders of images (the
shape both v1 dataset candidates unzip to). No identity metadata is assumed
to exist - docs/03 S1 states this is a real reduction in rigor relative to
the deferred FF++/Celeb-DF extension, and R14 in docs/04 is the reason every
downstream metric must be a within-model delta rather than an absolute claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


@dataclass
class DatasetItem:
    path: Path
    label: int  # 1 = fake/manipulated, 0 = real, matches Y in docs/02 S1


def discover(root: Path) -> list[DatasetItem]:
    root = Path(root)
    items = []
    for label, sub in ((0, "real"), (1, "fake")):
        d = root / sub
        if not d.exists():
            raise FileNotFoundError(
                f"expected {d} - dataset root must contain real/ and fake/ subfolders "
                f"(docs/03 S0 candidates: xhlulu/140k-real-and-fake-faces or "
                f"manjilkarki/deepfake-and-real-images, unzipped)"
            )
        for p in sorted(d.iterdir()):
            if p.suffix.lower() in IMAGE_EXTENSIONS:
                items.append(DatasetItem(path=p, label=label))
    if not items:
        raise ValueError(f"no images found under {root}")
    return items


@dataclass
class Splits:
    calibration: list[DatasetItem]
    test: list[DatasetItem]


def stratified_split(items: list[DatasetItem], calibration_fraction: float = 0.3,
                      seed: int = 0) -> Splits:
    """Sample-level stratified split, fixed seed - docs/03 S1/S4. Not
    identity-level (no identity metadata exists for this dataset); state that
    limitation wherever this function's output is used in results.
    """
    rng = np.random.default_rng(seed)
    by_label: dict[int, list[DatasetItem]] = {0: [], 1: []}
    for item in items:
        by_label[item.label].append(item)

    calibration, test = [], []
    for label, group in by_label.items():
        group = list(group)
        rng.shuffle(group)
        n_cal = int(round(len(group) * calibration_fraction))
        calibration.extend(group[:n_cal])
        test.extend(group[n_cal:])
    rng.shuffle(calibration)
    rng.shuffle(test)
    return Splits(calibration=calibration, test=test)


def load_image(item: DatasetItem, size: int = 256) -> np.ndarray:
    import cv2

    bgr = cv2.imread(str(item.path))
    if bgr is None:
        raise IOError(f"could not read {item.path}")
    bgr = cv2.resize(bgr, (size, size), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
