"""Cross-check numeric claims in paper/main.tex against canonical result files.

Every check below was derived by hand in docs/manuscript_audit.md; this
script automates re-checking the same numbers so the audit doesn't go stale
silently. It does not invent a source for any value it can't find — a value
with no machine-readable backing is reported as MANUSCRIPT REPORTED ONLY,
not treated as a failure and not filled in.

Exit code is non-zero only if a value that DOES have a backing artifact no
longer matches it (a real regression), not for values that were always
manuscript-only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
TOL = 1e-3  # matches the paper's own reporting precision (3 decimals)


def load(name: str) -> dict:
    return json.loads((RESULTS / name).read_text())


def close(a: float, b: float, tol: float = TOL) -> bool:
    return abs(a - b) <= tol


def check_auc_floor() -> list[tuple[str, bool, str]]:
    d = load("e0_own_panel_floor.json")["detectors"]
    expected = {
        "own": 0.858,
        "own_convnext": 0.987,
        "own_vit": 0.973,
    }
    out = []
    for key, want in expected.items():
        got = d[key]["baseline_auc"]
        out.append((f"AUC[{key}]", close(got, want), f"want~{want} got={got:.4f}"))
    return out


def check_evidence_transfer() -> list[tuple[str, bool, str]]:
    d = load("e7_full_panel_analysis.json")["detectors"]
    # (detector key in results file, scheme key, expected wm-null, expected wm-spec)
    expected = [
        ("effnet", "dwtDctSvd", 0.126, 0.006),
        ("effnet", "rivaGan", 0.137, 0.014),
        ("own", "dwtDctSvd", -0.005, 0.012),
        ("own", "rivaGan", -0.011, 0.029),
        ("own_convnext", "dwtDctSvd", 0.037, 0.039),
        ("own_convnext", "rivaGan", -0.044, 0.033),
        ("own_vit", "dwtDctSvd", -0.153, -0.027),
        ("own_vit", "rivaGan", -0.239, -0.013),
    ]
    out = []
    for det, scheme, want_null, want_spec in expected:
        node = d[det]["schemes"][scheme]
        got_null = node["wm_minus_null"]["point"]
        got_spec = node["wm_minus_spec"]["point"]
        out.append((
            f"{det}/{scheme} wm-null",
            close(got_null, want_null),
            f"want~{want_null} got={got_null:.4f}",
        ))
        out.append((
            f"{det}/{scheme} wm-spec",
            close(got_spec, want_spec),
            f"want~{want_spec} got={got_spec:.4f}",
        ))
    return out


def check_e8_localized_manipulation() -> list[tuple[str, bool, str]]:
    d = load("e8_manipulation_grid.json")
    rows = d["rows"]
    assert len(rows) == 9600, f"expected 9600 rows, found {len(rows)}"
    sub = [r for r in rows if abs(r["target_area"] - 0.25) < 1e-9]
    all_readable = all(r["readable"] for r in sub)
    mean_ber = sum(r["ber"] for r in sub) / len(sub)
    out = [
        ("E8 row count == 9600", len(rows) == 9600, f"n={len(rows)}"),
        ("E8 all readable @25% coverage", all_readable, f"n={len(sub)}"),
        ("E8 mean BER @25% <= 0.006", mean_ber <= 0.006, f"mean_ber={mean_ber:.5f}"),
    ]
    return out


def check_confirmatory_scale() -> list[tuple[str, bool, str]]:
    d = load("large_summary.json")
    out = [
        (
            "large_summary n_records == 140000",
            d["n_records"] == 140000,
            f"n_records={d['n_records']}",
        ),
    ]
    return out


def check_frequency_dose() -> list[tuple[str, bool, str]]:
    d = load("e12_frequency_dose.json")["arms"]
    expected = {"low": 0.908, "mid": 0.868, "high": 0.809}
    out = []
    for band, want in expected.items():
        got = d[band]["slope"]
        out.append((f"E12 {band} slope", close(got, want, tol=2e-3), f"want~{want} got={got:.4f}"))
    return out


# Values referenced in the manuscript/spec with no located machine-readable
# artifact backing them, as of this audit. Listed explicitly so the script
# documents the gap rather than silently ignoring it.
MANUSCRIPT_REPORTED_ONLY = [
    "Total corpus size '22,000 images' (not found verbatim; see docs/manuscript_audit.md)",
    "E9 63-cell cost-risk grid individual cell values (artifact present, not value-checked here)",
    "E10 resolution ablation individual values (artifact present, not value-checked here)",
    "detector_screen.json individual per-model AUCs (artifact present, not value-checked here)",
]


def main() -> int:
    checks = (
        check_auc_floor()
        + check_evidence_transfer()
        + check_e8_localized_manipulation()
        + check_confirmatory_scale()
        + check_frequency_dose()
    )

    failed = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        status = "OK  " if ok else "FAIL"
        print(f"[{status}] {name}: {detail}")

    print()
    print("MANUSCRIPT REPORTED ONLY (no machine-readable artifact cross-checked here):")
    for item in MANUSCRIPT_REPORTED_ONLY:
        print(f"  - {item}")

    print()
    if failed:
        print(f"{len(failed)} check(s) FAILED against their backing artifact.")
        return 1
    print(f"All {len(checks)} artifact-backed checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
