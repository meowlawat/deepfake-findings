"""Ed25519 provenance binding - docs/02 SS2.1, revised for real payload capacity.

Replaces the source design's AES-256 box. AES gives confidentiality; the
threat model needs unforgeability, which a symmetric cipher with a
verifier-shared key cannot provide.

**Design correction made while implementing this (not in docs/02 as
originally written):** docs/02 SS2.1 specifies `m = ID_key || sig`, embedding
the Ed25519 signature (512 bits) plus a key ID and timestamp directly in the
watermark payload. That does not fit: RivaGan, the learned scheme actually
verified this session, carries a fixed 32-bit payload; even DwtDctSvd is not
comfortably reliable at 600+ bits. The signature cannot travel in-band at
this payload capacity, for any scheme in v1's scope.

The fix used here is the pattern C2PA itself uses: the in-band payload is a
short **key-ID only** (fits in PAYLOAD_BITS, docs/03 unified both schemes to
32 bits for a fair comparison - see watermark.py). The Ed25519 signature over
(perceptual hash || key-ID || timestamp) lives in an out-of-band
`ProvenanceRegistry`, keyed by key-ID. Verification is: recover the payload,
find the closest registered key-ID (bit errors are expected - that's what z_P
already models), and check whether *that* entry's signature verifies against
the image currently being scored.

This keeps W's core property from docs/02 SS2.1 - it is a cryptographic
pass/fail with a ~2^-128 false-accept rate, not a continuous BER threshold -
while being something that actually fits in the payload. The one thing it
adds that docs/02 doesn't mention: a nearest-key-ID matching tolerance is
needed before verification can even be attempted. That tolerance is a
disclosed registry-lookup parameter, not the same thing as thresholding BER
to decide provenance validity, but it is not perfectly free of BER either -
say so in the paper rather than claiming clean identifiability.
"""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass

import numpy as np
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


DEFAULT_HASH_SIZE = 3  # see the empirical note below - chosen from measurement, not assumed

def perceptual_hash(image: np.ndarray, hash_size: int = DEFAULT_HASH_SIZE) -> bytes:
    """Average-hash over grayscale, downsampled before averaging.

    **Empirical correction made while testing this module.** The original
    design assumed this would be exactly stable under a watermark's own
    embedding, at hash_size=8. Measured directly: on a smooth, photo-like
    synthetic image, DwtDctSvd matched exactly at hash_size<=4, but RivaGan
    (despite a *higher* PSNR - 40dB vs 37dB) flipped 2/16 bits at
    hash_size=4 and only matched cleanly at hash_size<=3. PSNR does not
    predict perceptual-hash stability; the two properties are independent
    and RivaGan's more spatially-diffuse perturbation is the harder case.
    On adversarial content (i.i.d. random noise, not a real photo) even
    hash_size=4 fails outright for DwtDctSvd - see test_crypto_binding.py's
    dedicated adversarial-content test, kept as a documented limitation
    rather than something papered over.

    Because exact-match hashing feeds a SHA-256 signature (any single flipped
    bit changes the whole digest), this is a genuinely fragile primitive, not
    a robust one - a production system would use a fuzzy commitment / secure
    sketch to tolerate bit noise while still producing a stable signing key.
    v1 does not build that; instead, W in the actual interference/fusion
    experiments (fusion.py) is taken from *ground truth* - we know exactly
    which images were embedded, because we ran the embedding ourselves - and
    this module's verification path is evaluated separately as a measured
    reliability diagnostic (see `verification_reliability_rate`), never as
    the mechanism that sets W for E1-E6. That keeps docs/02 S2.1's
    identifiability argument (W independent of the BER used for z_P) intact
    without pretending this hash construction is more robust than measured.
    """
    import cv2

    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    small = cv2.resize(gray, (hash_size, hash_size), interpolation=cv2.INTER_AREA)
    avg = small.mean()
    bits = (small > avg).flatten()
    return np.packbits(bits).tobytes()


KEY_ID_BYTES = 4  # 32 bits - matches PAYLOAD_BITS in watermark.py exactly


@dataclass
class RegistryEntry:
    key_id: bytes
    signature: bytes  # Ed25519, 64 bytes
    timestamp: int


def key_id_to_bits(key_id: bytes) -> list[int]:
    return list(np.unpackbits(np.frombuffer(key_id, dtype=np.uint8)))


def bits_to_key_id(bits: list[int]) -> bytes:
    return np.packbits(np.array(bits, dtype=np.uint8)).tobytes()[:KEY_ID_BYTES]


def sign_entry(private_key: Ed25519PrivateKey, image: np.ndarray,
               key_id: bytes, timestamp: int) -> RegistryEntry:
    """sig = Ed25519_sign(sk, H(phash(x) || key_id || ts)) - the out-of-band record."""
    binding = perceptual_hash(image) + key_id + struct.pack(">Q", timestamp)
    digest = hashlib.sha256(binding).digest()
    signature = private_key.sign(digest)
    return RegistryEntry(key_id=key_id, signature=signature, timestamp=timestamp)


def verify_entry(public_key: Ed25519PublicKey, image: np.ndarray, entry: RegistryEntry) -> bool:
    binding = perceptual_hash(image) + entry.key_id + struct.pack(">Q", entry.timestamp)
    digest = hashlib.sha256(binding).digest()
    try:
        public_key.verify(entry.signature, digest)
        return True
    except InvalidSignature:
        return False


class ProvenanceRegistry:
    """Out-of-band signature store, keyed by key-ID. Recovers from noisy
    payloads by nearest-Hamming-distance match before attempting verification.
    """

    def __init__(self, public_key: Ed25519PublicKey, match_tolerance_bits: int = 4):
        self.public_key = public_key
        self.match_tolerance_bits = match_tolerance_bits
        self._entries: dict[bytes, RegistryEntry] = {}

    def register(self, entry: RegistryEntry) -> None:
        self._entries[entry.key_id] = entry

    def resolve_and_verify(self, image: np.ndarray, recovered_bits: list[int]) -> tuple[bool, bytes | None]:
        """W = 1 iff a registry entry is found within tolerance AND its
        signature verifies against `image` (docs/02 SS2.1, as corrected above).

        Returns (w, matched_key_id). matched_key_id is None if no candidate
        was within tolerance - that case is W=0 by construction, not a
        rejected verification.
        """
        recovered = np.array(recovered_bits, dtype=np.uint8)
        best_key, best_dist = None, None
        for key_id in self._entries:
            candidate_bits = np.array(key_id_to_bits(key_id), dtype=np.uint8)
            dist = int(np.sum(candidate_bits != recovered))
            if best_dist is None or dist < best_dist:
                best_key, best_dist = key_id, dist
        if best_key is None or best_dist > self.match_tolerance_bits:
            return False, None
        entry = self._entries[best_key]
        return verify_entry(self.public_key, image, entry), best_key


def generate_keypair() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    sk = Ed25519PrivateKey.generate()
    return sk, sk.public_key()


def verification_reliability_rate(clean_images: list[np.ndarray], watermarked_images: list[np.ndarray],
                                   private_key: Ed25519PrivateKey, public_key: Ed25519PublicKey,
                                   key_ids: list[bytes], timestamp: int) -> float:
    """Measured false-negative rate of the crypto binding: sign against the
    CLEAN image (as a real pipeline would, before embedding), then check
    whether verification still passes against the WATERMARKED image. This is
    the diagnostic docs/03's day 1-2 tooling checklist must run before the
    binding is trusted for anything beyond ground-truth-labelled experiments;
    it is a number to report, not an assumption to make (see the docstring
    on `perceptual_hash` for why hash_size was already tuned once by
    measurement and can still fail on some content).
    """
    if not (len(clean_images) == len(watermarked_images) == len(key_ids)):
        raise ValueError("clean_images, watermarked_images, and key_ids must be the same length")
    failures = 0
    for clean, watermarked, key_id in zip(clean_images, watermarked_images, key_ids):
        entry = sign_entry(private_key, clean, key_id, timestamp)
        if not verify_entry(public_key, watermarked, entry):
            failures += 1
    return failures / len(clean_images)
