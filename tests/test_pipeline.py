import numpy as np
import pytest

from deepfake_interference import data as data_mod
from deepfake_interference.detectors import DummyDetector
from deepfake_interference.pipeline import build_fusion_dataset, select_rho_mixture


def _write_tiny_dataset(tmp_path):
    import cv2

    root = tmp_path / "ds"
    (root / "real").mkdir(parents=True)
    (root / "fake").mkdir(parents=True)
    rng = np.random.default_rng(0)
    for label, sub in ((0, "real"), (1, "fake")):
        for i in range(3):
            base = rng.random((256, 256, 3)).astype(np.float32)
            smooth = cv2.GaussianBlur(base, (31, 31), 0)
            smooth = (smooth - smooth.min()) / (smooth.max() - smooth.min()) * 255
            cv2.imwrite(str(root / sub / f"{sub}_{i}.png"),
                        cv2.cvtColor(smooth.astype(np.uint8), cv2.COLOR_RGB2BGR))
    return root


def test_build_fusion_dataset_shapes_and_missingness(tmp_path):
    root = _write_tiny_dataset(tmp_path)
    items = data_mod.discover(root)
    cfg = {
        "dataset": {"image_size": 256},
        "watermark": {"schemes": ["dwtDctSvd", "rivaGan"], "payload_bits": 32},
        "detectors": {},
    }
    detector = DummyDetector(seed=0)
    fusion_inputs, p0, row_meta = build_fusion_dataset(items, cfg, detector_name="dummy", seed=1, detector=detector)

    n_items = len(items)
    n_schemes = 2
    expected_rows = n_items * (1 + n_schemes)  # 1 clean row + 1 per scheme, per item
    assert len(fusion_inputs.v) == expected_rows
    assert len(fusion_inputs.y) == expected_rows

    # every w==0 row must have z_p and b as NaN, not zero (docs/02 S2's
    # "missing, not zero" distinction) - this is the actual thing the fusion
    # design boundary depends on, so it's worth a direct assertion here.
    clean_mask = fusion_inputs.w == 0
    assert clean_mask.sum() == n_items
    assert np.all(np.isnan(fusion_inputs.z_p[clean_mask]))
    assert np.all(np.isnan(fusion_inputs.b[clean_mask]))

    wm_mask = fusion_inputs.w == 1
    assert np.all(np.isfinite(fusion_inputs.z_p[wm_mask]))
    assert np.all(np.isfinite(fusion_inputs.b[wm_mask]))

    assert set(p0.keys()) == {"dwtDctSvd", "rivaGan"}
    for scheme, p in p0.items():
        assert 0 < p < 0.5


def test_build_fusion_dataset_applies_transform_before_scoring(tmp_path):
    """The E4 hook: a transform should be visible in the recovered BER (worse
    channel -> more bit errors) - if it silently no-ops, E4's whole premise
    (robustness under attack) is untested even though the script "runs".
    """
    root = _write_tiny_dataset(tmp_path)
    items = data_mod.discover(root)
    cfg = {
        "dataset": {"image_size": 256},
        "watermark": {"schemes": ["dwtDctSvd"], "payload_bits": 32},
        "detectors": {},
    }
    detector = DummyDetector(seed=0)

    def destroy(image):
        # a transform severe enough to guarantee elevated BER, unlike a mild
        # JPEG pass which might not move BER much on a small tiny image
        return np.zeros_like(image)

    clean_inputs, _, _ = build_fusion_dataset(items, cfg, "dummy", seed=2, detector=detector)
    transformed_inputs, _, _ = build_fusion_dataset(items, cfg, "dummy", seed=2, detector=detector, transform=destroy)

    clean_wm_ber = clean_inputs.b[clean_inputs.w == 1]
    transformed_wm_ber = transformed_inputs.b[transformed_inputs.w == 1]
    assert transformed_wm_ber.mean() > clean_wm_ber.mean()


def test_select_rho_mixture_keeps_exactly_one_row_per_item(tmp_path):
    root = _write_tiny_dataset(tmp_path)
    items = data_mod.discover(root)
    cfg = {
        "dataset": {"image_size": 256},
        "watermark": {"schemes": ["dwtDctSvd"], "payload_bits": 32},
        "detectors": {},
    }
    detector = DummyDetector(seed=0)
    inputs, _, row_meta = build_fusion_dataset(items, cfg, "dummy", seed=3, detector=detector)

    mixed = select_rho_mixture(inputs, row_meta, scheme="dwtDctSvd", rho=0.5, seed=7)
    n_items = len(items)
    assert len(mixed.y) == n_items  # exactly one row per item, never both or neither
    # w should be a mix, not all-0 or all-1, at rho=0.5 with several items
    assert 0 < mixed.w.sum() < n_items


def test_select_rho_mixture_extremes():
    import numpy as np
    from deepfake_interference.fusion import FusionInputs

    inputs = FusionInputs(
        v=np.array([0.1, 0.2, 0.3, 0.4]),
        z_p=np.array([np.nan, 1.0, np.nan, 2.0]),
        w=np.array([0, 1, 0, 1]),
        b=np.array([np.nan, 0.1, np.nan, 0.2]),
        y=np.array([0, 0, 1, 1]),
    )
    row_meta = {"item_id": np.array([0, 0, 1, 1]), "arm": np.array([None, "s", None, "s"], dtype=object)}

    all_clean = select_rho_mixture(inputs, row_meta, scheme="s", rho=0.0, seed=0)
    assert np.all(all_clean.w == 0)

    all_wm = select_rho_mixture(inputs, row_meta, scheme="s", rho=1.0, seed=0)
    assert np.all(all_wm.w == 1)
