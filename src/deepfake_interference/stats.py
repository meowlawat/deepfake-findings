"""Sample-level bootstrap for CIs - docs/03 S4.

Named "sample-level", not "identity-level", deliberately: docs/03 S1 records
that identity metadata doesn't exist for the v1 dataset, so this is a weaker
guarantee than the identity-clustered bootstrap the deferred FF++ extension
would use. Every caller that reports a CI from this module should say so.
"""
from __future__ import annotations

from typing import Callable

import numpy as np


def bootstrap_ci(values_by_arg: dict[str, np.ndarray], statistic: Callable[..., float],
                  n_boot: int = 2000, ci: float = 0.95, seed: int = 0) -> tuple[float, float, float]:
    """Percentile bootstrap. `values_by_arg` maps each argument name `statistic`
    expects to an array of equal length N; each bootstrap draw resamples the
    N row-indices once and applies that same resampling to every array, so
    paired quantities (e.g. y_true and y_prob) stay aligned.

    Returns (point_estimate, lo, hi).
    """
    rng = np.random.default_rng(seed)
    names = list(values_by_arg.keys())
    n = len(values_by_arg[names[0]])
    for name, arr in values_by_arg.items():
        if len(arr) != n:
            raise ValueError(f"length mismatch: {name} has {len(arr)}, expected {n}")

    point = statistic(**values_by_arg)
    boot_stats = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        resampled = {name: np.asarray(arr)[idx] for name, arr in values_by_arg.items()}
        boot_stats[i] = statistic(**resampled)

    alpha = (1 - ci) / 2
    lo, hi = np.nanquantile(boot_stats, [alpha, 1 - alpha])
    return float(point), float(lo), float(hi)
