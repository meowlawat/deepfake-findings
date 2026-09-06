import numpy as np
import pytest

from deepfake_interference import metrics


def test_bit_error_rate():
    sent = [1, 0, 1, 1, 0]
    recovered = [1, 1, 1, 0, 0]
    assert metrics.bit_error_rate(sent, recovered) == pytest.approx(2 / 5)


def test_bit_error_rate_length_mismatch():
    with pytest.raises(ValueError):
        metrics.bit_error_rate([1, 0], [1, 0, 1])


def test_auc_perfect_and_chance():
    y = [0, 0, 1, 1]
    perfect = metrics.auc(y, [0.1, 0.2, 0.8, 0.9])
    assert perfect == pytest.approx(1.0)
    single_class = metrics.auc([0, 0, 0], [0.1, 0.2, 0.3])
    assert np.isnan(single_class)


def test_delta_auc_net_matches_manual_subtraction():
    rng = np.random.default_rng(0)
    y = np.array([0] * 50 + [1] * 50)
    v_clean = rng.standard_normal(100) + y * 2  # decent separation
    v_wm = v_clean - 0.5  # uniform shift, same as null would produce
    v_null = v_clean - 0.5  # identical shift -> net should be ~0

    d_scheme = metrics.delta_auc(y, v_wm, y, v_clean)
    d_null = metrics.delta_auc(y, v_null, y, v_clean)
    net = metrics.delta_auc_net(d_scheme, d_null)
    assert net == pytest.approx(0.0, abs=1e-9)


def test_chow_thresholds_matches_source_design_band():
    # docs/02 S5: 0.35/0.65 implies c_fn == c_fp and c_r = 0.35 * c_fn
    tau_lo, tau_hi = metrics.chow_thresholds(c_fn=1.0, c_fp=1.0, c_r=0.35)
    assert tau_lo == pytest.approx(0.35)
    assert tau_hi == pytest.approx(0.65)


def test_chow_thresholds_wider_band_example():
    # docs/02 S5's plausible cost example
    tau_lo, tau_hi = metrics.chow_thresholds(c_fn=100, c_fp=20, c_r=1)
    assert tau_lo == pytest.approx(0.01)
    assert tau_hi == pytest.approx(0.95)


def test_chow_thresholds_rejects_empty_band():
    with pytest.raises(ValueError):
        metrics.chow_thresholds(c_fn=1.0, c_fp=1.0, c_r=0.6)


def test_ece_perfect_calibration_is_zero():
    rng = np.random.default_rng(1)
    y_prob = rng.uniform(0, 1, 5000)
    y_true = (rng.uniform(0, 1, 5000) < y_prob).astype(int)
    ece = metrics.expected_calibration_error(y_true, y_prob, n_bins=20)
    assert ece < 0.05  # not exactly 0 due to finite sampling


def test_calibration_gap_by_watermark_zero_when_identical():
    rng = np.random.default_rng(2)
    y_prob = rng.uniform(0, 1, 400)
    y_true = (rng.uniform(0, 1, 400) < y_prob).astype(int)
    w = np.array([0, 1] * 200)
    gap = metrics.calibration_gap_by_watermark(y_true, y_prob, w)
    assert abs(gap) < 0.1  # same distribution both groups -> small gap


def test_selective_risk_decreases_or_equal_as_coverage_drops():
    rng = np.random.default_rng(3)
    y = (rng.uniform(0, 1, 1000) < 0.5).astype(int)
    y_prob = np.clip(y + rng.normal(0, 0.4, 1000), 0, 1)
    risk_full = metrics.selective_risk_at_coverage(y, y_prob, 1.0)
    risk_partial = metrics.selective_risk_at_coverage(y, y_prob, 0.5)
    assert risk_partial <= risk_full + 1e-9
