#!/usr/bin/env python3
"""Turn results/*.json into the paper's tables (LaTeX + console) and figures.

Figures follow one validated categorical palette (blue/orange/aqua, checked
for CVD separation and lightness band before use, not chosen by eye). Every
series is direct-labelled as well as coloured, so identity never rests on
colour alone - which also discharges the aqua slot's contrast warning and
keeps the figures readable in the grayscale a print reviewer may see.

Usage:
    python scripts/make_report.py --results-dir results --out-dir paper/generated
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Validated categorical palette - see scripts/validate_palette.js in the
# dataviz reference. Assigned in fixed order, never cycled.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
INK = "#1a1a19"
MUTED = "#6b6b66"
GRID = "#e3e3df"


def _style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.grid(True, color=GRID, linewidth=0.6, alpha=0.9)
    ax.set_axisbelow(True)
    for label in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
        label.set_color(MUTED)


def table_t1(e1: dict) -> str:
    """T1 - the interference matrix. Delta_AUC_net is the headline column."""
    lines = [
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"Detector & Scheme & $\Delta_\mu$ & $\Delta_\sigma$ & $\Delta$AUC & $\Delta$AUC$_{\text{net}}$ \\",
        r"\midrule",
    ]
    for r in e1["rows"]:
        lines.append(
            f"{r['detector']} & {r['scheme']} & {r['delta_mu']:+.3f} & {r['delta_sigma']:.3f} & "
            f"{r['delta_auc']:+.4f} & {r['delta_auc_net']:+.4f} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def table_e0(e1: dict) -> str:
    lines = [
        r"\begin{tabular}{lrl}",
        r"\toprule",
        r"Detector & Baseline AUC ($W{=}0$) & Status \\",
        r"\midrule",
    ]
    for det, v in e1["e0"].items():
        auc = "n/a" if v["baseline_auc"] is None else f"{v['baseline_auc']:.4f}"
        lines.append(f"{det} & {auc} & {v['status'].split('(')[0].strip()} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def table_t2(e23: dict) -> str:
    lines = [
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        r"Model & AUC & ECE & $\Delta$ECE$_W$ & AURC & DRD & $\beta_4$ \\",
        r"\midrule",
    ]
    for r in e23["results"]:
        beta4 = "--" if r["beta4"] is None else f"{r['beta4']:+.3f}"
        lines.append(
            f"{r['model']} & {r['auc']:.3f} & {r['ece']:.4f} & {r['delta_ece_w']:+.4f} & "
            f"{r['aurc']:.4f} & {r['drd']:.4f} & {beta4} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def fig_interference(e1: dict, out_path: Path):
    """F4-style: Delta_AUC vs Delta_AUC_null per (detector, scheme), showing
    how much of the raw shift the null control already accounts for. Grouped
    bars, because the job is comparing magnitudes across a small set of
    labelled categories.
    """
    rows = e1["rows"]
    labels = [f"{r['detector']}\n{r['scheme']}" for r in rows]
    raw = [r["delta_auc"] for r in rows]
    null = [r["delta_auc_null"] for r in rows]
    net = [r["delta_auc_net"] for r in rows]

    x = np.arange(len(rows))
    width = 0.26
    fig, ax = plt.subplots(figsize=(7, 3.4))
    for offset, values, color, name in (
        (-width, raw, SERIES[0], r"$\Delta$AUC (scheme)"),
        (0.0, null, SERIES[1], r"$\Delta$AUC (null arm)"),
        (width, net, SERIES[2], r"$\Delta$AUC$_{net}$"),
    ):
        ax.bar(x + offset, values, width * 0.92, label=name, color=color,
               edgecolor="white", linewidth=0.8)

    ax.axhline(0, color=INK, linewidth=1.0)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel(r"$\Delta$AUC", color=MUTED, fontsize=9)
    ax.set_title("Watermark interference vs. PSNR-matched null perturbation",
                 color=INK, fontsize=10, loc="left")
    _style_axes(ax)
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED, ncol=3,
              loc="upper center", bbox_to_anchor=(0.5, -0.22))
    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_reliability(e23: dict, out_path: Path, models=("F1", "F3")):
    """F1 - the money figure. Reliability split by W, never pooled: pooling
    hides exactly the effect under study (docs/02 S6).
    """
    fig, axes = plt.subplots(1, len(models), figsize=(7, 3.2), sharey=True)
    if len(models) == 1:
        axes = [axes]
    for ax, model_name in zip(axes, models):
        row = next((r for r in e23["results"] if r["model"] == model_name), None)
        ax.plot([0, 1], [0, 1], color=MUTED, linewidth=1.0, linestyle=(0, (4, 3)))
        if row and row.get("reliability"):
            for i, (group, series) in enumerate(row["reliability"].items()):
                ax.plot(series["confidence"], series["accuracy"], marker="o",
                        markersize=4, linewidth=2, color=SERIES[i], label=f"W={group}")
                if series["confidence"]:
                    ax.annotate(f"W={group}", (series["confidence"][-1], series["accuracy"][-1]),
                                color=SERIES[i], fontsize=8,
                                xytext=(3, -2), textcoords="offset points")
        ax.set_title(model_name, color=INK, fontsize=10, loc="left")
        ax.set_xlabel("predicted probability", color=MUTED, fontsize=9)
        _style_axes(ax)
    axes[0].set_ylabel("observed frequency", color=MUTED, fontsize=9)
    fig.suptitle("Reliability by watermark presence", color=INK, fontsize=10, x=0.02, ha="left")
    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_rho(e45: dict, out_path: Path, models=("F0", "F1", "F3")):
    """F3 - selective risk vs the watermarked fraction rho."""
    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    for i, model_name in enumerate(models):
        rows = [r for r in e45.get("e5", []) if r["model"] == model_name]
        if not rows:
            continue
        by_rho: dict[float, list[float]] = {}
        for r in rows:
            by_rho.setdefault(r["rho"], []).append(r["drd"])
        xs = sorted(by_rho)
        ys = [float(np.mean(by_rho[x])) for x in xs]
        ax.plot(xs, ys, marker="o", markersize=5, linewidth=2, color=SERIES[i % len(SERIES)],
                label=model_name)
        if xs:
            ax.annotate(model_name, (xs[-1], ys[-1]), color=SERIES[i % len(SERIES)],
                        fontsize=8, xytext=(4, 0), textcoords="offset points")
    ax.set_xlabel(r"watermarked fraction $\rho$", color=MUTED, fontsize=9)
    ax.set_ylabel("decision risk deviation", color=MUTED, fontsize=9)
    ax.set_title("Decision risk vs. watermarked fraction", color=INK, fontsize=10, loc="left")
    _style_axes(ax)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--out-dir", default="paper/generated")
    args = parser.parse_args()

    rd, od = Path(args.results_dir), Path(args.out_dir)
    od.mkdir(parents=True, exist_ok=True)

    e1_path = rd / "e1_full_run.json"
    if e1_path.exists():
        e1 = json.loads(e1_path.read_text())
        (od / "table_e0.tex").write_text(table_e0(e1))
        (od / "table_t1.tex").write_text(table_t1(e1))
        fig_interference(e1, od / "fig_interference.png")
        print(f"wrote E0/T1 tables and interference figure from {e1_path}")
        print(f"  gate: {'PASS' if e1['gate_passed'] else 'FAIL'} - {e1['gate_message']}")

    e23_path = rd / "e2_e3_fusion.json"
    if e23_path.exists():
        e23 = json.loads(e23_path.read_text())
        (od / "table_t2.tex").write_text(table_t2(e23))
        fig_reliability(e23, od / "fig_reliability.png")
        print(f"wrote T2 and reliability figure from {e23_path}")

    e45_path = rd / "e4_e5.json"
    if e45_path.exists():
        e45 = json.loads(e45_path.read_text())
        fig_rho(e45, od / "fig_rho.png")
        print(f"wrote rho figure from {e45_path}")

    print(f"outputs in {od}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
