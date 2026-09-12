"""Provenance likelihood ratio and fusion models F0-F5 - docs/02 SS2, S4.

This module is the paper's contribution. Everything upstream (watermark.py,
detectors.py, transforms.py) produces the raw ingredients; this is where
z_P is computed and where beta_4 - the interference coefficient - either
turns out to matter or doesn't (docs/03 E1's go/no-go gate happens on
Delta_AUC_net in metrics.py, before fusion is even fit; this module is E2/E3).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.linear_model import LogisticRegression


def estimate_p0(clean_bers: np.ndarray) -> float:
    """p_0: a scheme's residual bit-error rate under an authentic (untransformed)
    channel, estimated on held-out clean data - docs/02 S2, 'not assumed'.
    """
    return float(np.clip(np.mean(clean_bers), 1e-6, 0.5 - 1e-6))


def log_likelihood_ratio(k_e: np.ndarray | int, L: int, p0: float) -> np.ndarray:
    """z_P = L*log(2) + k_e*log(p0) + (L - k_e)*log(1 - p0) - docs/02 eq. in S2.

    k_e: observed bit-error count(s) out of L. Vectorised over k_e.
    """
    k_e = np.asarray(k_e, dtype=float)
    return L * np.log(2) + k_e * np.log(p0) + (L - k_e) * np.log(1 - p0)


@dataclass
class FusionInputs:
    """One row per media item. z_p is NaN (not zero - docs/02 S2 last line)
    when w == 0; callers must not silently coerce it.
    """
    v: np.ndarray          # raw detector logit
    z_p: np.ndarray        # provenance LLR, NaN where w == 0
    w: np.ndarray          # 0/1. In v1, ground truth from the embedding
                            # pipeline (we know exactly which images were
                            # embedded) - NOT the output of crypto_binding's
                            # verify step, whose own reliability is measured
                            # separately (crypto_binding.verification_reliability_rate)
                            # rather than trusted as W's source. See that
                            # module's docstring for why this changed from
                            # docs/02 S2.1's original "W observed via
                            # verification" framing once hash-stability was
                            # measured rather than assumed.
    b: np.ndarray          # raw BER, NaN where w == 0 (for F4's degradation term)
    y: np.ndarray          # ground truth, 1 = manipulated


def _design_matrix(data: FusionInputs, model: str) -> np.ndarray:
    """Builds the feature matrix for F0-F5. z_p := 0 when w == 0 happens HERE,
    at the fusion boundary, and only for the models that need it (F1+) - never
    upstream, so 'missing vs zero' (docs/02 S2) stays a real distinction until
    the last possible moment.
    """
    n = len(data.v)
    z_p_filled = np.where(data.w == 1, data.z_p, 0.0)
    b_filled = np.where(data.w == 1, data.b, 0.0)

    columns = {"v": data.v}
    if model in ("F1", "F2", "F3", "F4", "F5"):
        columns["z_p"] = z_p_filled
    if model in ("F2", "F3", "F4", "F5"):
        columns["w"] = data.w.astype(float)
    if model in ("F3", "F4", "F5"):
        columns["w_times_v"] = data.w.astype(float) * data.v
    if model in ("F4", "F5"):
        columns["b_times_v"] = b_filled * data.v

    return np.column_stack([columns[k] for k in columns]), list(columns.keys())


@dataclass
class FusionModel:
    name: str
    clf: LogisticRegression
    feature_names: list[str]
    coef_by_name: dict[str, float] = field(default_factory=dict)

    def predict_proba(self, data: FusionInputs) -> np.ndarray:
        X, _ = _design_matrix(data, self.name)
        return self.clf.predict_proba(X)[:, 1]


def fit(model_name: str, data: FusionInputs) -> FusionModel:
    """Fit one of F0-F5 (docs/02 S4 table) by ordinary logistic regression.

    Deliberately plain: interpretability is the point (docs/04 R4/R7) - the
    interference coefficient (w_times_v's weight, i.e. beta_4) must be
    readable off `coef_by_name`, not buried inside a black-box fuser. E6
    separately fits a nonlinear control model to show that swapping the
    fuser doesn't fix miscalibration - that's a different code path, not this
    one, because conflating them would hide exactly what's being tested.
    """
    if model_name not in ("F0", "F1", "F2", "F3", "F4", "F5"):
        raise ValueError(f"unknown fusion model {model_name}")
    X, feature_names = _design_matrix(data, model_name)
    clf = LogisticRegression()
    clf.fit(X, data.y)
    coef_by_name = {"intercept": float(clf.intercept_[0])}
    coef_by_name.update({name: float(c) for name, c in zip(feature_names, clf.coef_[0])})
    return FusionModel(name=model_name, clf=clf, feature_names=feature_names, coef_by_name=coef_by_name)


def interference_coefficient(model: FusionModel) -> float | None:
    """beta_4, the empirical claim of the paper - docs/02 S4: 'a significant
    beta_4 IS the measurement of interference in the fusion.' None if this
    model doesn't have the term (F0/F1/F2).
    """
    return model.coef_by_name.get("w_times_v")
