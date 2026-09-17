"""The S = null-perturbation control arm - docs/02 SS3.1, docs/03 S1.

Without this, Delta_AUC < 0 is equally explained by H_interference (the
watermark's structure overlaps forgery cues) or H_brittle (a zero-shot
detector trained on clean images degrades under any imperceptible
perturbation, watermark or not). This generates payload-free noise matched to
a *target* watermark's PSNR/SSIM on each image, so the null arm is a fair
control, not a strawman at a different perturbation strength.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .metrics import psnr, ssim


@dataclass
class NullPerturbationResult:
    perturbed: np.ndarray
    psnr: float
    ssim: float
    noise_scale: float
    iterations: int


def _add_scaled_noise(image: np.ndarray, scale: float, rng: np.random.Generator) -> np.ndarray:
    """Additive noise with the same coarse spectral character as a DCT-domain
    watermark: mid-frequency-weighted, not pure white noise, so the null arm
    is not trivially distinguishable from the watermark arms on frequency
    content alone. Documented residual risk in docs/04 R11: this still isn't
    a spectral match, only a PSNR/SSIM match - see that risk for why.
    """
    noise = rng.standard_normal(image.shape).astype(np.float32)
    # crude low/high-frequency attenuation via a 3x3 box blur pass, cheap and
    # dependency-free (avoids pulling in FFT machinery for a control arm).
    if noise.ndim == 3:
        kernel = np.ones((3, 3), dtype=np.float32) / 9.0
        for c in range(noise.shape[2]):
            import cv2

            noise[:, :, c] = noise[:, :, c] - cv2.filter2D(noise[:, :, c], -1, kernel)
    perturbed = image.astype(np.float32) + scale * noise
    return np.clip(perturbed, 0, 255).astype(np.uint8)


def match_to_target(image: np.ndarray, target_psnr: float, rng: np.random.Generator,
                     tolerance_db: float = 0.5, max_iters: int = 20) -> NullPerturbationResult:
    """Binary-search the noise scale so the perturbed image's PSNR lands
    within `tolerance_db` of `target_psnr` (the corresponding watermark's
    measured PSNR on this same image). Reports the SSIM achieved as a
    secondary check - it is not separately optimised, per the residual-risk
    note above.
    """
    lo, hi = 0.0, 255.0
    best = None
    for i in range(max_iters):
        mid = (lo + hi) / 2
        candidate = _add_scaled_noise(image, mid, rng)
        p = psnr(image, candidate)
        if abs(p - target_psnr) <= tolerance_db:
            best = NullPerturbationResult(candidate, p, ssim(image, candidate), mid, i + 1)
            break
        # PSNR decreases as scale increases (monotonic for this noise model)
        if p > target_psnr:
            lo = mid
        else:
            hi = mid
    if best is None:
        candidate = _add_scaled_noise(image, mid, rng)
        best = NullPerturbationResult(candidate, psnr(image, candidate), ssim(image, candidate), mid, max_iters)
    return best


def _spectral_surrogate(residual: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """A payload-free field with the SAME power spectrum as `residual`.

    Phase randomisation: take the residual's 2-D Fourier transform, keep its
    magnitude exactly, replace its phase with uniform random phase (Hermitian-
    symmetrised so the inverse transform is real). The result has, per channel,
    the identical power spectrum to the watermark residual it was built from,
    but carries no payload and no spatial structure from the mark.

    This is the control that PSNR matching cannot be: PSNR fixes only the
    energy of the perturbation, so a mid-frequency transform-domain mark and
    broadband noise can share a PSNR while differing completely in where that
    energy sits. Matching the spectrum removes that degree of freedom.
    """
    out = np.empty(residual.shape, dtype=np.float32)
    for c in range(residual.shape[2]):
        F = np.fft.rfft2(residual[:, :, c].astype(np.float32))
        mag = np.abs(F)
        phase = rng.uniform(-np.pi, np.pi, size=F.shape)
        out[:, :, c] = np.fft.irfft2(mag * np.exp(1j * phase), s=residual.shape[:2])
    return out


def match_spectrum_and_psnr(image: np.ndarray, residual: np.ndarray, target_psnr: float,
                            rng: np.random.Generator, tolerance_db: float = 0.5,
                            max_iters: int = 20) -> NullPerturbationResult:
    """Payload-free perturbation matched to a watermark on BOTH per-image PSNR
    and per-image power spectrum.

    `residual` is the watermark's own residual (watermarked - clean) for this
    image, so the match is per image and per scheme, not to a global average.
    The surrogate's spectrum is fixed by construction; the scalar gain is then
    binary-searched to land PSNR within `tolerance_db`, exactly as the
    PSNR-only control does, so the two controls differ in spectrum matching
    and nothing else.
    """
    base = _spectral_surrogate(residual, rng)
    base = base / (np.sqrt(np.mean(base ** 2)) + 1e-12)   # unit RMS; gain set below
    lo, hi, best = 0.0, 255.0, None
    for i in range(max_iters):
        mid = (lo + hi) / 2
        cand = np.clip(image.astype(np.float32) + mid * base, 0, 255).astype(np.uint8)
        p = psnr(image, cand)
        if best is None or abs(p - target_psnr) < abs(best[1] - target_psnr):
            best = (cand, p, mid, i + 1)
        if abs(p - target_psnr) <= tolerance_db:
            break
        if p > target_psnr:      # too clean -> need more noise
            lo = mid
        else:
            hi = mid
    cand, p, scale, iters = best
    return NullPerturbationResult(perturbed=cand, psnr=p, ssim=ssim(image, cand),
                                  noise_scale=scale, iterations=iters)
