#!/usr/bin/env python3
"""Generate paper/figures/*.pdf from released results.

Every number plotted here is read from a committed results file (or, for the
BER-vs-area curve, from the table already reported in docs/06-results.md and
paper/main.tex Sec V-E) -- nothing here is a fabricated or illustrative value.
Regenerate after any change to the underlying results with:

    python scripts/make_paper_figures.py
"""
from __future__ import annotations

import json
import glob
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)


def _load_detector_arms(det_dir: Path) -> dict:
    out = defaultdict(lambda: defaultdict(dict))
    for f in glob.glob(str(det_dir / "chunk_*.json")):
        for r in json.loads(Path(f).read_text())["records"]:
            out[r["detector"]][r["arm"]][r["idx"]] = r["v"]
    return out


def fig_replication():
    """Evidence-transfer regression, both detectors, identical images -
    the central figure for Sec V-D (blocker-1 replication failure)."""
    effnet = _load_detector_arms(ROOT / "results/large/validation/effnet")["effnet"]
    own = _load_detector_arms(ROOT / "results/large/validation/own")["own"]

    shared = set(effnet["clean"])
    for arms in (effnet, own):
        for a in arms:
            shared &= set(arms[a])
    shared = sorted(shared)

    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2))
    for ax, (arms, title) in zip(
        axes, [(effnet, "EfficientNet-B6"), (own, "ResNet-18 probe")]
    ):
        clean = np.array([arms["clean"][i] for i in shared])
        wm = np.array([arms["dwtDctSvd"][i] for i in shared])
        null = np.array([arms["null[dwtDctSvd]"][i] for i in shared])

        ax.scatter(clean, null, s=6, alpha=0.35, color="#d62728", label="null (payload-free)")
        ax.scatter(clean, wm, s=6, alpha=0.35, color="#1f77b4", label="dwtDctSvd (watermark)")

        xs = np.linspace(clean.min(), clean.max(), 50)
        b_wm, a_wm = np.polyfit(clean, wm, 1)
        b_null, a_null = np.polyfit(clean, null, 1)
        ax.plot(xs, a_wm + b_wm * xs, color="#1f77b4", lw=2)
        ax.plot(xs, a_null + b_null * xs, color="#d62728", lw=2)
        ax.plot(xs, xs, color="gray", lw=1, ls="--", label="identity ($b=1$)")

        ax.set_title(f"{title}\n$b_{{wm}}={b_wm:.3f}$, $b_{{null}}={b_null:.3f}$", fontsize=10)
        ax.set_xlabel(r"$v_{\mathrm{clean}}$")
        ax.set_ylabel(r"$v_{\mathrm{arm}}$")

    axes[0].legend(fontsize=8, loc="upper left", framealpha=0.9)
    fig.suptitle(f"Evidence-transfer regression, DWT-DCT-SVD scheme, identical images (n={len(shared)})", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(OUT / "fig_replication.pdf")
    plt.close(fig)


def fig_ber_area():
    """BER vs. manipulated area - values as reported in docs/06-results.md
    and paper Sec V-E, produced by the manipulation-experiment sweep."""
    area = [10, 25, 40, 60, 80, 95]
    dwt = [0.0000, 0.0000, 0.0026, 0.0443, 0.1953, 0.2630]
    riva = [0.0052, 0.0104, 0.0156, 0.0521, 0.1224, 0.1615]

    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    ax.plot(area, dwt, marker="o", color="#1f77b4", label="DWT-DCT-SVD")
    ax.plot(area, riva, marker="s", color="#ff7f0e", label="RivaGAN")
    ax.axhline(0.5, color="gray", ls=":", lw=1, label="payload destroyed (BER=0.5)")
    ax.axvspan(10, 25, color="#d62728", alpha=0.08)
    ax.text(17.5, 0.35, "face-replacement\nscale", ha="center", fontsize=8, color="#d62728")
    ax.set_xlabel("Manipulated area (%)")
    ax.set_ylabel("Bit error rate")
    ax.set_ylim(-0.02, 0.55)
    ax.set_title("Watermark payload recovery vs. splice area")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_ber_area.pdf")
    plt.close(fig)


def fig_e4_beta4():
    """Beta4 point estimate per transform, from the real E4 run
    (results/e4_e5_test400.json), model F4."""
    d = json.loads((ROOT / "results/e4_e5_test400.json").read_text())
    rows = [r for r in d["e4"] if r["model"] == "F4"]
    labels = [r["transform"].replace("brightness_contrast", "bright").replace("(", "\n(") for r in rows]
    beta4 = [r["beta4"] for r in rows]
    colors = ["#d62728" if abs(b) > 0.15 else "#1f77b4" for b in beta4]

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.bar(range(len(rows)), beta4, color=colors)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels(labels, fontsize=7.5)
    ax.set_ylabel(r"$\beta_4$ (F4, point estimate, no CI)")
    ax.set_title("Interference coefficient by transform, n=400 (first look)")
    fig.tight_layout()
    fig.savefig(OUT / "fig_e4_beta4.pdf")
    plt.close(fig)


def fig_calibration():
    """ECE by arm, both calibrators - read directly from
    results/calibration_effect.json (same numbers as the table in Sec V-F)."""
    d = json.loads((ROOT / "results/calibration_effect.json").read_text())
    order = ["clean", "dwtDctSvd", "rivaGan", "null[dwtDctSvd]", "null[rivaGan]"]
    labels = ["clean", "DWT-DCT-\nSVD", "RivaGAN", "null\n[DWT]", "null\n[Riva]"]
    ece = {(r["arm"], r["calibrator"]): r["ece"] for r in d["rows"]}
    platt = [ece[(a, "platt")] for a in order]
    isotonic = [ece[(a, "isotonic")] for a in order]
    arms = labels

    x = np.arange(len(arms))
    w = 0.35
    fig, ax = plt.subplots(figsize=(5.4, 3.4))
    ax.bar(x - w / 2, platt, w, label="Platt", color="#ff7f0e")
    ax.bar(x + w / 2, isotonic, w, label="Isotonic", color="#2ca02c")
    ax.set_xticks(x)
    ax.set_xticklabels(arms, fontsize=8)
    ax.set_ylabel("Expected calibration error")
    ax.set_title("Calibration error by arm and calibrator")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_calibration.pdf")
    plt.close(fig)


def fig_rho_sweep():
    """AUC and DRD vs. rho, both schemes - from results/e4_e5_test400.json."""
    d = json.loads((ROOT / "results/e4_e5_test400.json").read_text())
    rows = [r for r in d["e5"] if r["model"] == "F4"]

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
    for scheme, color, marker in [("dwtDctSvd", "#1f77b4", "o"), ("rivaGan", "#ff7f0e", "s")]:
        sub = sorted([r for r in rows if r["scheme"] == scheme], key=lambda r: r["rho"])
        rho = [r["rho"] for r in sub]
        axes[0].plot(rho, [r["auc"] for r in sub], marker=marker, color=color, label=scheme)
        axes[1].plot(rho, [r["drd"] for r in sub], marker=marker, color=color, label=scheme)

    axes[0].set_title("AUC vs. $\\rho$", fontsize=10)
    axes[1].set_title("DRD vs. $\\rho$", fontsize=10)
    for ax in axes:
        ax.set_xlabel(r"$\rho$ (watermarked fraction)")
    axes[0].set_ylabel("AUC")
    axes[1].set_ylabel("Decision risk deviation")
    axes[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_rho_sweep.pdf")
    plt.close(fig)


if __name__ == "__main__":
    fig_replication()
    fig_ber_area()
    fig_e4_beta4()
    fig_calibration()
    fig_rho_sweep()
    print(f"figures written to {OUT}")
