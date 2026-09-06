import numpy as np
import pytest

from deepfake_interference import null_perturbation as np_ctrl
from deepfake_interference import watermark
from deepfake_interference.metrics import psnr


def _sample_image(seed=0):
    rng = np.random.default_rng(seed)
    return (rng.random((256, 256, 3)) * 255).astype(np.uint8)


def test_null_arm_matches_target_psnr_within_tolerance():
    """docs/02 S3.1 / docs/04 R11: the null arm's whole purpose is to be a
    fair PSNR/SSIM-matched control. If matching is loose, Delta_AUC_net is
    comparing arms at different perturbation strengths, which reopens the
    exact confound the arm exists to close.
    """
    image = _sample_image()
    bits = list(np.random.default_rng(1).integers(0, 2, watermark.PAYLOAD_BITS))
    result = watermark.embed(image, bits, "dwtDctSvd")

    rng = np.random.default_rng(5)
    null_result = np_ctrl.match_to_target(image, target_psnr=result.psnr, rng=rng, tolerance_db=0.5)
    assert null_result.perturbed.shape == image.shape
    assert abs(null_result.psnr - result.psnr) <= 1.0  # allow a little slack over the strict 0.5dB target


def test_null_arm_is_not_identical_to_watermarked_image():
    image = _sample_image()
    bits = list(np.random.default_rng(1).integers(0, 2, watermark.PAYLOAD_BITS))
    result = watermark.embed(image, bits, "dwtDctSvd")

    rng = np.random.default_rng(6)
    null_result = np_ctrl.match_to_target(image, target_psnr=result.psnr, rng=rng)
    assert not np.array_equal(null_result.perturbed, result.watermarked)
