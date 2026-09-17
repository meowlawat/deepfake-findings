"""Shared dataset-building pipeline for E2-E6 (docs/03). Factored out of the
first draft of scripts/e2_e3_fusion.py, which built this inline - E4/E5/E6
need the identical construction (embed, extract, score, compute z_P from a
scheme-specific p_0), and duplicating it per script is exactly how earlier
bugs got introduced (see docs/05-code.md's three design corrections). One
implementation, imported everywhere.
"""
from __future__ import annotations

from typing import Callable

import numpy as np

from . import data as data_mod
from . import detectors as det_mod
from . import fusion
from . import metrics
from . import watermark as wm_mod


def build_fusion_dataset(items, cfg: dict, detector_name: str, seed: int = 0,
                          transform: Callable[[np.ndarray], np.ndarray] | None = None,
                          detector=None,
                          ) -> tuple[fusion.FusionInputs, dict[str, float]]:
    """One row per (item, arm) with arm in {clean, each scheme in
    cfg['watermark']['schemes']}. If `transform` is given, it is applied to
    the watermarked image AFTER embedding and BEFORE detector scoring and BER
    measurement - this is E4's hook (docs/03), and BER measured this way is
    genuinely post-transform, not the clean-channel estimate.

    p_0 (docs/02 S2) is always estimated from THIS call's own watermarked
    rows - i.e. under whatever `transform` is active - which is deliberate:
    docs/02 S2's "pooled p_0" resolution means p_0 reflects the channel
    actually being scored, not a clean-channel oracle smuggled into a
    transformed evaluation.

    `detector`: inject a pre-built object exposing `.score(image) -> result
    with .v`, instead of constructing `detectors.Detector(cfg[...])` (which
    needs network access to load an HF model). Lets tests exercise this
    function's actual embed/extract/BER/z_P wiring with a DummyDetector,
    rather than only testing it indirectly through a live pipeline run.

    Returns `(fusion_inputs, p0_by_scheme, row_meta)`. `row_meta` carries
    `item_id` (index into `items`) and `arm` (scheme name, or None for the
    clean row) for every row, explicitly - not left for a caller to
    reconstruct from row order and a modulus, which is exactly the kind of
    positional arithmetic that produced a bug earlier in this codebase
    (docs/05-code.md). E5's rho-sweep groups rows back by item using this.
    """
    det = detector if detector is not None else det_mod.Detector(cfg["detectors"][detector_name])
    schemes = cfg["watermark"]["schemes"]
    payload_bits = cfg["watermark"]["payload_bits"]
    rng = np.random.default_rng(seed)

    v_list, w_list, b_list, y_list, scheme_list, item_id_list = [], [], [], [], [], []

    for item_id, item in enumerate(items):
        image = data_mod.load_image(item, size=cfg["dataset"]["image_size"])

        v_clean = det.score(image).v
        v_list.append(v_clean); w_list.append(0); b_list.append(np.nan); y_list.append(item.label)
        scheme_list.append(None); item_id_list.append(item_id)

        for scheme in schemes:
            bits = list(rng.integers(0, 2, payload_bits))
            result = wm_mod.embed(image, bits, scheme)
            watermarked = result.watermarked if transform is None else transform(result.watermarked)

            recovered = wm_mod.extract(watermarked, scheme, n_bits=len(bits))
            ber = metrics.bit_error_rate(bits, recovered)

            v_wm = det.score(watermarked).v
            v_list.append(v_wm); w_list.append(1); b_list.append(ber); y_list.append(item.label)
            scheme_list.append(scheme); item_id_list.append(item_id)

    b_arr = np.array(b_list, dtype=float)
    scheme_arr = np.array(scheme_list, dtype=object)
    p0_by_scheme = {s: fusion.estimate_p0(b_arr[scheme_arr == s]) for s in schemes}

    z_p_list = []
    for w, b, scheme in zip(w_list, b_list, scheme_list):
        if w == 0:
            z_p_list.append(np.nan)
        else:
            k_e = b * payload_bits
            z_p_list.append(fusion.log_likelihood_ratio(k_e, payload_bits, p0_by_scheme[scheme]))

    inputs = fusion.FusionInputs(
        v=np.array(v_list), z_p=np.array(z_p_list, dtype=float),
        w=np.array(w_list), b=b_arr, y=np.array(y_list),
    )
    row_meta = {"item_id": np.array(item_id_list), "arm": scheme_arr}
    return inputs, p0_by_scheme, row_meta


def select_rho_mixture(inputs: fusion.FusionInputs, row_meta: dict, scheme: str,
                        rho: float, seed: int = 0) -> fusion.FusionInputs:
    """docs/03 E5: realistic mixed regime. For each item, keep EITHER its
    clean row OR its `scheme` row - never both, matching deployment, where a
    given piece of media is watermarked or it isn't - choosing watermarked
    with probability `rho`. Uses `row_meta['item_id']`/`['arm']` rather than
    positional row arithmetic.
    """
    rng = np.random.default_rng(seed)
    item_ids = row_meta["item_id"]
    arm = row_meta["arm"]
    unique_items = np.unique(item_ids)
    is_watermarked_item = rng.random(len(unique_items)) < rho

    keep_mask = np.zeros(len(item_ids), dtype=bool)
    for idx, item_id in enumerate(unique_items):
        item_rows = item_ids == item_id
        if is_watermarked_item[idx]:
            keep_mask |= item_rows & (arm == scheme)
        else:
            keep_mask |= item_rows & (arm == None)  # noqa: E711 - arm holds None, not NaN

    return fusion.FusionInputs(
        v=inputs.v[keep_mask], z_p=inputs.z_p[keep_mask],
        w=inputs.w[keep_mask], b=inputs.b[keep_mask], y=inputs.y[keep_mask],
    )
