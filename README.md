# Interference-Aware Fusion of Provenance and Passive Evidence for Deepfake Detection

Working repository. Current state: **design stage** — no experiments have been
run. Nothing in `docs/` is an empirical claim yet.

**Scope: v1 fast-track, 10-day deadline.** Hardware is one RTX 3050 (6GB) plus
Kaggle's free-tier T4 as overflow. This forces no gated datasets (FaceForensics++
/ Celeb-DF access requests alone can eat the whole budget), zero training
(pretrained watermark embedders and detectors, used as shipped — this is an
inference-only workload, which is exactly why 6GB is enough), and a narrower
scheme/detector/transform matrix than a journal-scale study would run. The full
matrix is kept in `docs/03-experiment-plan.md` §6 as a named extension, not
discarded — v1 is a real, honestly-scoped, submittable result on its own; the
extension is what a revision or follow-up widens toward. See `docs/04-open-risks.md`
R5–R10 for what this narrowing costs and how it's disclosed in the paper.

## What this project is

The starting material (`docs/00-source-material.md`) described a conventional
hybrid pipeline: embed a DWT-SVD watermark, extract it later to get a provenance
score `P`, run a ViT detector to get an anomaly score `V`, fuse the two with
logistic regression, threshold at 0.35/0.65 with an "inconclusive" band.

That framing is not publishable as-is; the space is populated (see
`docs/01-positioning.md`). The project has been re-aimed at the one thing the
original design got wrong in an interesting way:

> **The two evidence sources are not independent.** The watermark is embedded in
> the same media the passive detector inspects, and published work shows
> watermark signals overlap with the forgery signals detectors rely on. A fused
> posterior built on the independence assumption is therefore miscalibrated on
> exactly the watermarked media the system is designed for — and a risk-derived
> abstention band is only valid on a calibrated posterior.

Contribution, in one sentence: *quantify watermark–detector interference in a
fusion setting, show it breaks posterior calibration and hence invalidates
risk-derived decision thresholds, and give an interference-aware fusion rule
that restores both.*

## Layout

| Path | Contents |
| --- | --- |
| `docs/00-source-material.md` | Verbatim content of the two source PDFs, preserved |
| `docs/01-positioning.md` | Related work map, occupancy analysis, gap statement, citation-verification ledger |
| `docs/02-method.md` | Formal method: LLR provenance score, interference model, fusion, Chow abstention |
| `docs/03-experiment-plan.md` | Datasets, schemes, detectors, attack suite, metrics, table/figure inventory |
| `docs/04-open-risks.md` | Unverified claims, threats to the contribution, what must be read before citing |
| `paper/main.tex` | Paper scaffold matching the plan |
| `paper/refs.bib` | Bibliography — **verified entries only** |

## Rules of this repository

1. No citation enters `paper/refs.bib` until it appears as VERIFIED in the ledger
   in `docs/01-positioning.md`.
2. No number enters the paper until it is produced by code in this repository.
3. Claims about prior work state what was read: abstract, or full paper.
