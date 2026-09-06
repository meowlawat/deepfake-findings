"""Image-quality and detection metrics used across E0-E6 (docs/03).

Nothing here is novel; the point of collecting them in one module is that
every experiment script imports the same implementation, so a number in one
table and the same-named number in another are guaranteed comparable.
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_auc_score
from skimage.metrics import peak_signal_noise_ratio, structural_similarity


def psnr(a: np.ndarray, b: np.ndarray, data_range: int = 255) -> float:
    """Peak signal-to-noise ratio between two same-shape uint8-range images."""
    return float(peak_signal_noise_ratio(a, b, data_range=data_range))


def ssim(a: np.ndarray, b: np.ndarray, data_range: int = 255) -> float:
    """Structural similarity. Handles both grayscale and multichannel input."""
    channel_axis = -1 if a.ndim == 3 else None
    return float(structural_similarity(a, b, data_range=data_range, channel_axis=channel_axis))


def bit_error_rate(sent: np.ndarray, recovered: np.ndarray) -> float:
    """Fraction of mismatched bits between the embedded and extracted payload.

    Both arrays are 0/1 integer arrays of the same length L (docs/02 SS1-2).
    """
    sent = np.asarray(sent).astype(int)
    recovered = np.asarray(recovered).astype(int)
    if sent.shape != recovered.shape:
        raise ValueError(f"payload length mismatch: sent {sent.shape} vs recovered {recovered.shape}")
    return float(np.mean(sent != recovered))


def auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    """AUC of `scores` (higher = more likely class 1) against binary `y_true`.

    Returns NaN rather than raising when only one class is present in
    `y_true`, since that happens legitimately in small stratified subsets
    (e.g. a single (scheme, transform) cell) and callers need to be able to
    tell "no signal" apart from "couldn't compute" in a results table.
    """
    y_true = np.asarray(y_true)
    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(roc_auc_score(y_true, scores))


def delta_mu(v_watermarked: np.ndarray, v_clean: np.ndarray) -> float:
    """Location shift Delta_mu(s, y) - docs/02 SS3."""
    return float(np.mean(v_watermarked) - np.mean(v_clean))


def delta_sigma(v_watermarked: np.ndarray, v_clean: np.ndarray) -> float:
    """Scale ratio Delta_sigma(s, y) - docs/02 SS3."""
    sd_clean = np.std(v_clean, ddof=1)
    if sd_clean == 0:
        return float("nan")
    return float(np.std(v_watermarked, ddof=1) / sd_clean)


def delta_auc(y_watermarked: np.ndarray, v_watermarked: np.ndarray,
              y_clean: np.ndarray, v_clean: np.ndarray) -> float:
    """Delta_AUC(s) = AUC(V; W=1, S=s) - AUC(V; W=0) - docs/02 SS3."""
    return auc(y_watermarked, v_watermarked) - auc(y_clean, v_clean)


def delta_auc_net(delta_auc_scheme: float, delta_auc_null: float) -> float:
    """Delta_AUC_net = Delta_AUC(s) - Delta_AUC(nullset) - docs/02 SS3.1, docs/03 E1.

    This, not the raw Delta_AUC, is the E1 go/no-go quantity: a scheme's
    shift that the payload-free null arm reproduces is generic brittleness,
    not watermark-specific interference (docs/04 R11).
    """
    return delta_auc_scheme - delta_auc_null


def expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 15) -> float:
    """Equal-mass-bin ECE. Standard definition, e.g. Guo et al. 2017 (calibration)."""
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    order = np.argsort(y_prob)
    y_true, y_prob = y_true[order], y_prob[order]
    n = len(y_prob)
    bins = np.array_split(np.arange(n), n_bins)
    ece = 0.0
    for idx in bins:
        if len(idx) == 0:
            continue
        conf = y_prob[idx].mean()
        acc = y_true[idx].mean()
        ece += (len(idx) / n) * abs(acc - conf)
    return float(ece)


def brier_score(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    return float(np.mean((y_prob - y_true) ** 2))


def calibration_gap_by_watermark(y_true: np.ndarray, y_prob: np.ndarray, w: np.ndarray,
                                  n_bins: int = 15) -> float:
    """Delta-ECE_W = ECE(y_hat | W=1) - ECE(y_hat | W=0) - docs/02 SS6.

    The headline calibration-gap quantity for E2/E3.
    """
    w = np.asarray(w).astype(bool)
    ece_w1 = expected_calibration_error(y_true[w], y_prob[w], n_bins=n_bins)
    ece_w0 = expected_calibration_error(y_true[~w], y_prob[~w], n_bins=n_bins)
    return ece_w1 - ece_w0


def chow_thresholds(c_fn: float, c_fp: float, c_r: float) -> tuple[float, float]:
    """Chow's optimal reject-rule thresholds - docs/02 SS5.

        tau_lo = c_r / c_fn      (below: declare Authentic)
        tau_hi = 1 - c_r / c_fp  (above: declare Deepfake)

    Raises if the implied review band is empty (c_r/c_fn + c_r/c_fp >= 1),
    since a caller silently getting tau_lo >= tau_hi is worse than an error.
    """
    tau_lo = c_r / c_fn
    tau_hi = 1.0 - c_r / c_fp
    if tau_lo >= tau_hi:
        raise ValueError(
            f"empty review band: tau_lo={tau_lo:.4f} >= tau_hi={tau_hi:.4f}; "
            f"costs imply c_r/c_fn + c_r/c_fp >= 1"
        )
    return tau_lo, tau_hi


def decision_risk_deviation(y_true: np.ndarray, y_prob: np.ndarray,
                             tau_lo: float, tau_hi: float,
                             c_fn: float, c_fp: float, c_r: float) -> float:
    """DRD - docs/02 SS6: |realised risk under (tau_lo, tau_hi) - targeted risk|.

    "Targeted risk" is the expected cost Chow's rule was derived to achieve
    under a perfectly calibrated posterior: c_r everywhere the rule abstains,
    weighted by the coverage the rule actually achieves at that y_hat
    distribution, plus the residual error cost inside the accept/reject
    regions. We compute realised cost directly from labels and compare it to
    the risk a calibrated model would have incurred at the same coverage.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    accept_authentic = y_prob < tau_lo
    accept_deepfake = y_prob > tau_hi
    abstain = ~(accept_authentic | accept_deepfake)

    realised = 0.0
    n = len(y_true)
    realised += np.sum(y_true[accept_authentic] == 1) * c_fn  # missed deepfakes
    realised += np.sum(y_true[accept_deepfake] == 0) * c_fp   # false alarms
    realised += np.sum(abstain) * c_r
    realised /= n

    # Targeted risk: if y_hat were calibrated, expected cost at abstention is
    # exactly c_r * coverage_of_abstention, and expected cost in the decided
    # region is the calibrated posterior's own error rate times its cost -
    # i.e. E[y_hat * c_fn | accept_authentic] + E[(1-y_hat) * c_fp | accept_deepfake].
    targeted = 0.0
    if accept_authentic.any():
        targeted += np.sum(y_prob[accept_authentic] * c_fn)
    if accept_deepfake.any():
        targeted += np.sum((1 - y_prob[accept_deepfake]) * c_fp)
    targeted += np.sum(abstain) * c_r
    targeted /= n

    return float(abs(realised - targeted))


def selective_risk_at_coverage(y_true: np.ndarray, y_prob: np.ndarray,
                                target_coverage: float) -> float:
    """Risk (0/1 error rate) when abstaining on the least-confident
    (1 - target_coverage) fraction of samples, confidence = |y_hat - 0.5|.
    Used for risk-coverage curves (F2) and AAA-style selective prediction.
    """
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    confidence = np.abs(y_prob - 0.5)
    n_keep = int(np.ceil(target_coverage * len(y_prob)))
    if n_keep == 0:
        return float("nan")
    keep_idx = np.argsort(-confidence)[:n_keep]
    pred = (y_prob[keep_idx] > 0.5).astype(int)
    return float(np.mean(pred != y_true[keep_idx]))


def area_under_risk_coverage(y_true: np.ndarray, y_prob: np.ndarray,
                              n_points: int = 100) -> float:
    """AURC via trapezoidal integration of the risk-coverage curve."""
    coverages = np.linspace(1.0 / len(y_prob), 1.0, n_points)
    risks = [selective_risk_at_coverage(y_true, y_prob, c) for c in coverages]
    return float(np.trapz(risks, coverages))
