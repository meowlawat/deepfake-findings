import time

import cv2
import numpy as np

from deepfake_interference import crypto_binding as cb
from deepfake_interference import watermark


def _white_noise_image(seed=0):
    """Adversarial content for a DCT/DWT-domain watermark: no spatial
    correlation for the transform to hide energy in, so embedding is far
    more visible (and far more disruptive to a pixel-block hash) than on a
    real photo. Used deliberately to demonstrate the limitation below, not
    as a stand-in for realistic content.
    """
    rng = np.random.default_rng(seed)
    return (rng.random((256, 256, 3)) * 255).astype(np.uint8)


def _photo_like_image(seed=0):
    """Smooth, spatially-correlated synthetic content - a much closer analog
    to a real photograph than i.i.d. noise, for testing purposes only (no
    real dataset is available in this environment; see docs/03 S0).
    """
    rng = np.random.default_rng(seed)
    base = rng.random((256, 256, 3)).astype(np.float32)
    smooth = cv2.GaussianBlur(base, (31, 31), 0)
    smooth = (smooth - smooth.min()) / (smooth.max() - smooth.min()) * 255
    return smooth.astype(np.uint8)


def test_perceptual_hash_stable_on_photo_like_content():
    """Positive case for docs/02 S2.1's binding, at the empirically-tuned
    hash_size (see crypto_binding.perceptual_hash's docstring for the
    measurement that set DEFAULT_HASH_SIZE=3): on smooth, photo-like
    content, both schemes' watermark should leave the hash unchanged.
    """
    image = _photo_like_image()
    bits = list(np.random.default_rng(1).integers(0, 2, watermark.PAYLOAD_BITS))
    for scheme in ("dwtDctSvd", "rivaGan"):
        result = watermark.embed(image, bits, scheme)
        h_before = cb.perceptual_hash(image)
        h_after = cb.perceptual_hash(result.watermarked)
        assert h_before == h_after, f"{scheme}: hash changed under its own watermark embedding"


def test_perceptual_hash_can_fail_on_adversarial_content():
    """Documented limitation, not a bug: this is NOT expected to pass, and
    asserting so is how the limitation stays visible instead of silently
    rotting if someone "fixes" the hash function later without noticing why
    it was set this way. i.i.d. noise is a worst case no real photo
    resembles; docs/04 should carry this as a stated risk, not a surprise
    discovered during the 10-day run.
    """
    image = _white_noise_image()
    bits = list(np.random.default_rng(1).integers(0, 2, watermark.PAYLOAD_BITS))
    result = watermark.embed(image, bits, "dwtDctSvd")
    h_before = cb.perceptual_hash(image)
    h_after = cb.perceptual_hash(result.watermarked)
    assert h_before != h_after  # documents the failure mode; do not "fix" this assertion


def test_verification_reliability_rate_on_photo_like_content():
    """The diagnostic that replaces "assume the hash is stable": measure the
    false-negative rate directly. On photo-like content this should be low;
    reported, not assumed, per docs/03 S0's tooling-verification discipline
    extended to this module.
    """
    sk, pk = cb.generate_keypair()
    rng = np.random.default_rng(3)
    clean_images, watermarked_images, key_ids = [], [], []
    for i in range(8):
        image = _photo_like_image(seed=i)
        bits = list(rng.integers(0, 2, watermark.PAYLOAD_BITS))
        result = watermark.embed(image, bits, "dwtDctSvd")
        clean_images.append(image)
        watermarked_images.append(result.watermarked)
        key_ids.append(i.to_bytes(4, "big"))

    rate = cb.verification_reliability_rate(
        clean_images, watermarked_images, sk, pk, key_ids, timestamp=int(time.time())
    )
    assert 0.0 <= rate <= 1.0
    assert rate < 0.5  # a weak sanity bound; the actual number is what gets reported, not asserted tight


def test_registry_verifies_correct_key_with_no_bit_errors():
    sk, pk = cb.generate_keypair()
    image = _photo_like_image()
    key_id = b"\x01\x02\x03\x04"
    entry = cb.sign_entry(sk, image, key_id, timestamp=int(time.time()))

    registry = cb.ProvenanceRegistry(pk, match_tolerance_bits=4)
    registry.register(entry)

    recovered_bits = cb.key_id_to_bits(key_id)  # perfect recovery
    w, matched = registry.resolve_and_verify(image, recovered_bits)
    assert w is True
    assert matched == key_id


def test_registry_tolerates_bounded_bit_errors():
    sk, pk = cb.generate_keypair()
    image = _photo_like_image()
    key_id = b"\x01\x02\x03\x04"
    entry = cb.sign_entry(sk, image, key_id, timestamp=int(time.time()))

    registry = cb.ProvenanceRegistry(pk, match_tolerance_bits=4)
    registry.register(entry)

    bits = cb.key_id_to_bits(key_id)
    bits[0] = 1 - bits[0]  # flip a single bit
    bits[5] = 1 - bits[5]
    w, matched = registry.resolve_and_verify(image, bits)
    assert w is True
    assert matched == key_id


def test_registry_rejects_wrong_image():
    sk, pk = cb.generate_keypair()
    image = _photo_like_image()
    other_image = _photo_like_image(seed=99)
    key_id = b"\xaa\xbb\xcc\xdd"
    entry = cb.sign_entry(sk, image, key_id, timestamp=int(time.time()))

    registry = cb.ProvenanceRegistry(pk, match_tolerance_bits=4)
    registry.register(entry)

    bits = cb.key_id_to_bits(key_id)
    w, matched = registry.resolve_and_verify(other_image, bits)
    # key-ID matches but the signature is bound to a different image's hash
    assert w is False


def test_registry_returns_w_false_with_no_key_within_tolerance():
    sk, pk = cb.generate_keypair()
    image = _photo_like_image()
    entry = cb.sign_entry(sk, image, b"\x00\x00\x00\x00", timestamp=int(time.time()))

    registry = cb.ProvenanceRegistry(pk, match_tolerance_bits=2)
    registry.register(entry)

    garbage_bits = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                     1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]  # far from 0x00000000
    w, matched = registry.resolve_and_verify(image, garbage_bits)
    assert matched is None
    assert w is False
