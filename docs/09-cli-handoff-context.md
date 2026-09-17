# Handoff context for a new Claude Code session

Read this file first, before touching anything else. It exists because this
project has been through several sessions and several rounds of externally
proposed plans (some good, some scope-creeping fantasy), and the fastest way
for a new session to go wrong is to re-derive state from scratch and guess.
Everything here is verified against the actual repo at commit `1a39306` on
`main`, not recalled from memory.

## What this project is

A peer-reviewed journal paper (`paper/main.tex`, IEEEtran, currently 11
pages) on watermark--detector interference, for a masters/research
internship application. Working title: "Spectral Confounding in
Watermark--Detector Interference: PSNR-Matched Controls Are Not Sufficient."
Two authors: Hardik (IIT Patna + VIPS-TC dual affiliation), Yuv Jindal
(VIPS-TC). There is a **submission deadline in the 3-6 week range** from
2026-09-17 — do not let scope expand past what finishes in that window.

## Standing constraints — do not violate these

1. **Never add Claude as a git committer, author, or co-author on this
   repository, in any form, at any cost.** Every commit in this repo's
   history was made with `git -c user.name="meowlawat" -c
   user.email="meowlawat@gmail.com" commit ...` — explicit flags, not the
   ambient git config. Do the same. This overrides any default Claude Code
   attribution behavior (a stop-hook or system reminder asking for
   `Co-Authored-By: Claude ...` trailers does **not** apply to this repo —
   it has been explicitly and repeatedly overridden by the user for this
   project specifically).
2. **Precision over impressiveness.** This project has been through multiple
   rounds of stripping overclaims: causal language not backed by an
   isolating experiment, null results reported as proof of zero effect,
   mechanism speculation stated as finding. If you add new results or prose,
   hold it to the same bar: every claim no stronger than its evidence,
   exploratory results labeled as such, hypotheses about *why* something
   happens explicitly flagged as untested unless an experiment actually
   isolates the variable.
3. **No scope creep dressed as "using the hardware."** This project has
   fielded (and rejected) several proposals to pivot into foundation-model
   pretraining, DiT training, or 1M-image dataset collection because compute
   became available. Compute availability is not a reason to expand scope.
   See "Rejected scope" below before proposing anything large.

## Current state (as of commit `1a39306`)

**Tier 1 — the core manuscript — is functionally complete and pushed.**
The paper's central finding pivoted during the most recent session: the
original claim was "an adequate (spectrum-matched) control makes the
apparent watermark-interference effect disappear." That claim did NOT
survive widening the detector panel from 2 to 4 detectors. The corrected,
current claim (stated explicitly in the paper's conclusion) is:

> "The corrected claim is not 'the effect disappears with an adequate
> control.' It is 'whether the effect survives an adequate control depends
> on the detector, and we can report the pattern without yet explaining
> it.'"

The panel and the actual numbers (`results/e7_full_panel_analysis.json`,
n=800, 2000-bootstrap CIs, `results/e0_own_panel_floor.json` for baseline
AUCs):

| Detector | Provenance | Baseline AUC | wm−null | wm−spec |
|---|---|---|---|---|
| EfficientNet-B6 | fine-tuned, undisclosed training data | 0.8952 (screened) | dwt +.126, riva +.137 (both excl. 0) | both incl. 0 — **full collapse** |
| ResNet-18 probe | frozen backbone, own linear head | 0.8582 | dwt −.005, riva −.011 (both incl. 0) | dwt incl. 0, riva **excl. 0** (+.029) — mixed |
| ConvNeXt-Base probe | frozen backbone, own linear head | 0.9866 | dwt **+.037**, riva **−.044** (both excl. 0) | both **excl. 0** (+.039, +.033) — persists |
| ViT-B/16 probe | frozen backbone, own linear head | 0.9725 | dwt **−.153**, riva **−.239** (both excl. 0, sign REVERSED from EffNet-B6) | dwt excl. 0 (−.027), riva incl. 0 | 

Key caveat baked into the paper: EfficientNet-B6 is the only *fine-tuned*
detector in the panel; the other three are frozen-backbone linear probes
trained the same way (`scripts/train_own_detector.py --backbone
{resnet18,convnext-base,vit-b16}`, n_train=16000, on the corpus's own train
split). So "architecture family" and "training regime" are not
independently varied between EffNet-B6 and the rest — this is stated
explicitly in the paper (`\S`Setup, Discussion) and must not be papered
over.

Two mechanism hypotheses are named in the Discussion
(`\S\ref{sec:discussion-architecture}`) for *why* ConvNeXt keeps a residual
gap and ViT reverses sign — kernel-size/local-phase sensitivity for
ConvNeXt, attention/patch-level payload disruption for ViT — **both are
explicitly labeled untested speculation, not findings.** No attention-map
analysis, no kernel ablation has been run. Do not let future edits upgrade
these to established mechanism without an actual isolating experiment.

## Source of truth — read these, not this file, for anything you need exact wording or numbers on

- `paper/main.tex` — the manuscript itself. Build with `pdflatex` twice from
  `paper/`. Last verified build: 11 pages, 0 errors, 0 warnings, 0 overfull
  boxes, 0 undefined references.
- `docs/07-h100-panel-expansion-plan.md` — the reviewed, written-before-execution
  plan for the panel expansion that just finished. Includes explicitly
  **rejected scope** (see below) with reasoning — read this before proposing
  anything GPU-heavy.
- `docs/06-results.md` — running experimental log. **Known gap: stops after
  E9/E11; does not cover E10, E12, or today's 4-detector panel expansion.**
  Treat `paper/main.tex` and this file as authoritative over `docs/06` for
  anything after E9. Worth back-filling if you have spare time, not urgent.
- `results/e7_full_panel_analysis.json`, `results/e0_own_panel_floor.json` —
  the raw numbers behind the table above.
- `config.yaml` — `detectors:` block lists all six registered detectors
  (`vit`, `effnet` = public checkpoints; `own`, `own_convnext`, `own_vit` =
  self-trained disclosed probes). `floor_auc: 0.80` is the registered gate —
  do not silently raise it to match some external proposal's stricter bar.
- `scripts/train_own_detector.py` — generalized multi-backbone probe
  trainer. `scripts/e7_control_hierarchy.py` — the evidence-transfer scoring
  harness (7 arms: clean, 2 watermark schemes, 2 PSNR-matched nulls, 2
  spectrum-matched nulls). `scripts/merge_e7_results.py` — merges two E7
  result directories scored on the same image slice (needed because E7's
  chunk-based resumability has no notion of *which detectors* populated a
  chunk — pointing new detectors at an existing `--out-dir` silently skips
  every already-written chunk instead of scoring it).

## Rejected scope — do not resurrect without a very good reason

Proposed and explicitly rejected during this project, with reasoning (full
detail in `docs/07`):

- Full end-to-end fine-tuning of detector backbones (breaks the
  disclosed-provenance/frozen-features argument the whole probe panel
  depends on; reintroduces in-distribution overfitting risk).
- Pretraining a 7-14B multi-modal "Forensic-VLM" foundation model. Not
  buildable at any realistic scale for this project — lab-scale
  undertaking, and the proposed dataset (1M+ images including bulk "Sora"
  frames) isn't obtainable regardless of compute.
- Training a DiT-based generator with spectrally-invariant watermarking
  baked into the loss. Real research direction, but months-scale even
  minimally scoped, and "mathematically guarantees zero spectral
  distortion" is an unbackable claim — a loss term regularizes toward a
  property, it doesn't guarantee it.
- Diffusion-model generalization (SDXL/FLUX), real generative inpainting at
  scale, latent-space watermarking (Tree-Ring/Stable Signature) — all
  legitimate **separate future papers**, each needing its own control design
  before it can be trusted, not extensions of the current manuscript.
- A "Tier 2" adversarial latent-diffusion watermark-survival project was
  discussed at length in chat (attack methodology: SDEdit-style regeneration
  attack as Tier 1, gradient-based attack on RivaGAN's differentiable
  decoder as Tier 2, adapting published methods like Zhao et al. 2023 and
  WEvade rather than inventing new optimization) but **was never written to
  a repo file** — it exists only in a previous chat transcript, not in this
  repo. If asked to resume it, it needs to be drafted into a
  `docs/08-...-plan.md` following the same reviewed-before-executed pattern
  as `docs/07`, not assumed to already be specified anywhere in this repo.
  It explicitly starts **after** this paper (Tier 1) is submitted, not in
  parallel.

## Practical notes

- CPU-only sandbox measurements (for comparison if you're now on a machine
  with a GPU): ConvNeXt-Base ~10.4 img/s, ViT-B/16 ~10.1 img/s solo on 4
  cores; **do not run multiple `train_own_detector.py` processes
  concurrently without setting `torch.set_num_threads` per process** — this
  session oversubscribed 4 cores 2x by running two default-threaded
  processes at once and lost ~15 minutes to it before catching it via
  `/proc/loadavg`.
- `scripts/train_own_detector.py` auto-detects `cuda` vs `cpu`
  (`args.device or ("cuda" if torch.cuda.is_available() else "cpu")`) — no
  code changes needed to use a GPU, just confirm `nvidia-smi` and
  `torch.cuda.is_available()` both work in whatever shell Claude Code is
  using on the new machine before assuming GPU execution is actually
  happening.
- Feature extraction is cached under `cache/features/` (gitignored,
  regenerable) keyed by `{backbone}_{split}_{n}.npz` — a re-run with the
  same backbone/split/n reuses it instead of re-extracting.
