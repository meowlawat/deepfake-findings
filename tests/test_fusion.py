import numpy as np
import pytest

from deepfake_interference import fusion


def test_log_likelihood_ratio_monotone_decreasing_in_errors():
    L, p0 = 32, 0.02
    z_no_errors = fusion.log_likelihood_ratio(0, L, p0)
    z_some_errors = fusion.log_likelihood_ratio(5, L, p0)
    z_half_errors = fusion.log_likelihood_ratio(16, L, p0)
    assert z_no_errors > z_some_errors > z_half_errors
    # k_e = L/2 is a huge deviation from the H_P mean (p0*L << L/2) - it
    # should favor H0 strongly, not sit near zero. (An earlier version of
    # this test wrongly assumed near-zero here; the crossover point where
    # z_P == 0 is not at k_e = L/2 for small p0, it's much closer to k_e = 0.)
    assert z_half_errors < 0
    assert z_no_errors > 0


def test_log_likelihood_ratio_scales_with_payload_length():
    """docs/02 S2: a longer payload at the same BER should carry more
    evidence - this is exactly what raw BER discards and z_P restores.
    """
    p0 = 0.02
    ber = 0.1
    z_short = fusion.log_likelihood_ratio(int(ber * 32), 32, p0)
    z_long = fusion.log_likelihood_ratio(int(ber * 256), 256, p0)
    assert z_long > z_short


def _synthetic_inputs(n=2000, seed=0, true_beta4=0.0):
    """Generated FORWARD through the model F3 actually fits:
        logit P(Y=1) = beta0 + beta2*V + beta4*(W*V)
    i.e. V's log-odds slope is beta2 when W=0 and (beta2+beta4) when W=1.
    This is the only way to construct a synthetic-data test that checks
    "does fitting recover a known beta4" without smuggling in a different,
    confounded causal story (an earlier version of this generator built V as
    a function of Y and W with a location shift, which a location term
    (beta3, F2) absorbs - not the beta4 interaction F3 is meant to detect;
    that version's failure exposed the bug, not the fitting code).
    """
    rng = np.random.default_rng(seed)
    w = rng.integers(0, 2, n)
    v = rng.normal(0, 1, n)
    beta0, beta2 = -0.1, 1.4
    logits = beta0 + beta2 * v + true_beta4 * (w * v)
    p = 1 / (1 + np.exp(-logits))
    y = (rng.random(n) < p).astype(int)

    b = np.where(w == 1, np.clip(rng.normal(0.05, 0.03, n), 0, 0.5), np.nan)
    k_e = np.where(w == 1, (b * 32).round(), np.nan)
    z_p = np.where(w == 1, fusion.log_likelihood_ratio(np.nan_to_num(k_e), 32, 0.05) + y * 2.0, np.nan)
    return fusion.FusionInputs(v=v, z_p=z_p, w=w, b=b, y=y)


def test_f0_uses_only_v():
    data = _synthetic_inputs()
    model = fusion.fit("F0", data)
    assert set(model.feature_names) == {"v"}
    assert fusion.interference_coefficient(model) is None


def test_f3_recovers_injected_interference():
    """A true negative beta4 (V's slope on log-odds of Y is smaller under
    W=1) should be recovered as negative by the fit; a true zero beta4
    should be recovered near zero. Both directions checked so this isn't
    passing by an accident of sign convention.
    """
    data_negative = _synthetic_inputs(true_beta4=-1.2, n=6000, seed=1)
    model_negative = fusion.fit("F3", data_negative)
    beta4_negative = fusion.interference_coefficient(model_negative)
    assert beta4_negative is not None
    assert beta4_negative < -0.3

    data_null = _synthetic_inputs(true_beta4=0.0, n=6000, seed=2)
    model_null = fusion.fit("F3", data_null)
    beta4_null = fusion.interference_coefficient(model_null)
    assert abs(beta4_null) < 0.3


def test_f1_treats_missing_z_p_as_zero_not_error():
    data = _synthetic_inputs()
    model = fusion.fit("F1", data)  # should not raise on NaN z_p where w==0
    probs = model.predict_proba(data)
    assert np.all(np.isfinite(probs))
    assert np.all((probs >= 0) & (probs <= 1))
