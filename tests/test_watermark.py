import numpy as np
import pytest

from deepfake_interference import watermark


def _sample_image(seed=0):
    rng = np.random.default_rng(seed)
    return (rng.random((256, 256, 3)) * 255).astype(np.uint8)


def test_dwtdctsvd_roundtrip_clean_channel():
    image = _sample_image()
    bits = list(np.random.default_rng(1).integers(0, 2, watermark.PAYLOAD_BITS))
    watermarked, psnr, ssim, ber = watermark.embed_and_measure(image, bits, "dwtDctSvd")
    assert watermarked.shape == image.shape
    assert psnr > 0
    assert 0 <= ssim <= 1
    assert ber < 0.1  # near-zero on an untransformed channel; docs/02 S2's p_0 anchor


def test_rivagan_roundtrip_produces_high_psnr():
    """RivaGan (learned) is expected to be far less perceptible than
    DwtDctSvd at the same payload length - docs/03 S1's strength-axis claim,
    checked at the imperceptibility level (T5), not the interference level.
    """
    image = _sample_image(2)
    bits = list(np.random.default_rng(3).integers(0, 2, watermark.PAYLOAD_BITS))
    watermarked, psnr, ssim, ber = watermark.embed_and_measure(image, bits, "rivaGan")
    assert watermarked.shape == image.shape
    assert psnr > 30  # learned scheme should be well above hand-crafted on a natural-ish image


def test_payload_length_mismatch_rejected():
    image = _sample_image()
    with pytest.raises(ValueError):
        watermark.embed(image, [1, 0, 1], "dwtDctSvd")
