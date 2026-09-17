# Spectral Confounding in Watermark--Detector Interference

Code, data, and manuscript for **"Spectral Confounding in Watermark--Detector
Interference: PSNR-Matched Controls Are Not Sufficient"** (Hardik, IIT Patna
and VIPS-TC; Yuv Jindal, VIPS-TC).

**Status: Tier 1 (this manuscript) is empirically complete.** Every
quantitative claim in `paper/main.tex` that this audit could locate a source
for is backed by a real, git-tracked result file produced by the scripts in
this repository — see `docs/source_provenance.md` and
`docs/manuscript_audit.md` for the full per-claim trace, and
`scripts/audit_manuscript.py` to re-run the numeric cross-checks yourself.
This is stated explicitly because an earlier version of this README (written
before the E0-E12 experimental work) said "no experiment has been run on real
data yet" — that sentence is now false and has been removed; it described a
much earlier stage of this project.

## Research question

Does embedding a provenance watermark measurably interfere with a passive
synthetic-image detector inspecting the same pixels, once the control for
that comparison is adequate? "Adequate" turns out to be the hard part: a
control matched only on perturbation energy (PSNR) is not matched on where
that energy sits in frequency, and that gap alone can manufacture an
apparent interference effect.

## Scientific contribution

1. A payload-free control matched to a watermark's PSNR looked, on 20,000
   held-out images, like it settled the question: an EfficientNet-B6
   detector's evidence was attenuated under the control but not under
   watermarking. That conclusion does not survive measuring the control's
   own frequency spectrum: both tested watermarks concentrate 83-97% of
   their residual power in the lowest radial band; the PSNR-matched control
   puts 46% in the highest. It is spectrally inverted relative to the thing
   it stands in for.
2. A stronger control -- payload-free but phase-randomized to carry the
   watermark's own per-image power spectrum -- closes the gap on
   EfficientNet-B6 (wm-null +0.126 -> wm-spec +0.006, CI now includes zero).
3. That closure does **not** generalize. Scoring the identical 800-image
   slice through three more disclosed-provenance, frozen-backbone linear
   probes (ResNet-18, ConvNeXt-Base, ViT-B/16) shows the effect fractures by
   architecture: ConvNeXt-Base keeps a small, statistically reliable residual
   gap even against the spectrum-matched control; ViT-B/16 reverses which arm
   attenuates more before spectrum matching is even applied; ResNet-18 is
   mixed. Two mechanism hypotheses (kernel-size/local-phase sensitivity;
   attention-level payload disruption) are named and **explicitly labeled
   untested** -- no attention-map analysis or kernel ablation was run.

The corrected claim, stated in the manuscript's own words: *"whether the
effect survives an adequate control depends on the detector, and we can
report the pattern without yet explaining it."*

## Dataset

Source corpus: Hugging Face `TheKernel01/140k-Real-and-Fake-Faces` (mirror of
Kaggle `xhlulu/140k-real-and-fake-faces`; 140,000 images, 100k/20k/20k
train/val/test, `real`/`fake` labels, StyleGAN vs. real photographs, license
`cc`). This is whole-image synthesis, not face-swap/reenactment -- the
manuscript uses "synthetic-image detection" throughout for that reason and
states the substitution cost in its limitations.

Splits actually used, each with an artifact behind it (see
`docs/manuscript_audit.md` for the full trace):

| Split | n | Purpose |
| --- | --- | --- |
| Exploratory pilot | 150+150 | Early go/no-go gate (E0/E1) |
| Probe training | 16,000 | Training the three disclosed-provenance linear probes |
| Confirmatory validation | 20,000 | The paper's headline result, 5 arms |
| Second-detector replication | 8,000 | Subset of validation, cross-checks the confirmatory result on ResNet-18 |
| 4-detector panel (E7) | 800 | The evidence-transfer comparison across all four detectors, 7 arms each |
| Localized manipulation (E8) | 200 (x6 coverage x4 families x2 schemes = 9,600 measurements) | Does a robust watermark survive partial manipulation |

Note: a "22,000 total images, 50/50 StyleGAN/real" figure appears in some
external descriptions of this project but was **not** found anywhere in
`paper/main.tex` or the result artifacts during this audit. Treat the table
above as authoritative; see `docs/manuscript_audit.md` for the discrepancy
note.

## Watermarks

Two schemes spanning the hand-crafted/learned divide, both at a 32-bit
payload: **DWT-DCT-SVD** (transform-domain) and **RivaGAN** (learned
encoder/decoder), via the `invisible-watermark` package.

## Controls

- **PSNR-matched (the "original" control):** a payload-free perturbation
  matched per image to the watermark's PSNR. This is what most published
  interference comparisons use, and it's the one this paper shows is
  insufficient.
- **Spectrum-matched (the stronger control):** payload-free, phase-randomized
  to carry the watermark's own per-image residual power spectrum. Verified
  payload-free (recovered BER ~0.51-0.52, chance) and verified matched
  (PSNR within ~0.3 dB, SSIM closer to the watermark than the PSNR-matched
  control) -- see `src/deepfake_interference/null_perturbation.py` and
  `results/e7_full_panel_analysis.json.control_quality`.

## Detectors

| Detector | Provenance | Baseline AUC | Notes |
| --- | --- | --- | --- |
| EfficientNet-B6 | Fine-tuned, undisclosed training data (`Skullly/DeepFake-EN-B6`) | 0.895 (screened) | The only fine-tuned model in the panel -- architecture family and training regime are *not* independently varied between this and the other three, and the manuscript says so explicitly |
| ResNet-18 (own probe) | Frozen ImageNet backbone + own logistic head, disclosed training | 0.858 | `models/own_detector.json` |
| ConvNeXt-Base (own probe) | Frozen backbone + own logistic head, disclosed training | 0.987 | `models/own_detector_convnext-base.json` |
| ViT-B/16 (own probe) | Frozen backbone + own logistic head, disclosed training | 0.973 | `models/own_detector_vit-b16.json` |

Registered floor: AUC >= 0.80 (`config.yaml: floor_auc`). Five of six
initially screened public checkpoints operated at chance on this
distribution and were excluded (`results/detector_screen.json`).

## Statistical analysis

Evidence-transfer regression `v_s = a_s + b_s * v_clean` fit per (detector,
scheme, arm); paired bootstrap resampling at the **image** level (every arm
for a given image is resampled together, never independently) with 2,000
replicates; 95% percentile confidence intervals. See
`src/deepfake_interference/stats.py` and `scripts/e7_control_hierarchy.py` /
`scripts/analyze_e7.py` for the implementation, `tests/` for the pairing and
metric unit tests.

## Results provenance -- three different things, not one

- **Verified from raw artifact:** a number that appears in a committed,
  git-tracked result file produced by a script in this repo (e.g. every AUC
  and evidence-transfer delta above). See `docs/source_provenance.md`.
- **Independently re-executed in this audit session:** the unit/integration
  test suite (`pytest`, 38/38 passing after installing the packages
  `requirements.txt` already specifies) and `scripts/audit_manuscript.py`
  (26/26 automated numeric cross-checks against the result files, passing).
  This is real re-execution, not a claim taken on faith -- but it is
  code-level verification, not a full re-run of the 20,000-image pipeline
  against freshly downloaded data and freshly scored detectors.
- **Manuscript-reported only:** the one located discrepancy is the "22,000
  images" total-corpus figure -- not found as stated anywhere in this repo.
  Reported as a gap, not silently corrected or silently repeated.

Full breakdown: `docs/source_provenance.md`, `docs/manuscript_audit.md`,
`docs/research_integrity_report.md`.

## Reproduction procedure

```bash
pip install -e .
pip install -r requirements.txt
pytest -q                        # 38 tests, no GPU/network required, ~10s
python scripts/audit_manuscript.py   # cross-checks manuscript numbers against results/*.json
```

Re-running the experiments themselves against real data requires the
dataset (`config.yaml: dataset.root`, not vendored -- see
`scripts/fetch_dataset.py`) and, for the fine-tuned/public detectors,
network access to Hugging Face Hub. `scripts/run_all.sh` and the individual
`scripts/e*.py` files are the actual pipeline; `docs/05-code.md` documents
what's implemented and what's been run.

## Hardware requirements

Tier 1 (this manuscript) is inference-only and was run entirely on one RTX
3050 (6GB) laptop GPU plus Kaggle's free-tier T4 as overflow -- no training,
no server-class GPU. See `docs/hardware_requirements.md` for the measured
throughput numbers and the Tier 2 comparison.

## Paper 1 (Tier 1) status

**Submitted-manuscript-ready, not yet submitted.** 1267-line IEEEtran source
at `paper/main.tex`, compiled PDF committed at `paper/main.pdf` (same commit
as the current `.tex`, so no drift between source and compiled artifact as
of that commit -- this audit could not independently rebuild the PDF in its
sandbox, which lacks a LaTeX toolchain and admin rights to install one; see
`docs/research_integrity_report.md`). No DOI, no venue, no acceptance claim
anywhere in the manuscript or `CITATION.cff` -- none of those exist yet and
none are claimed.

## Paper 2 (Tier 2) status

**Not started.** A separate, later project: active adversarial watermark
removal via generative optimization. Discussed in a prior chat session but
never previously written to this repository. Planning documents only --
`docs/tier2_resource_plan.md`, and the "Rejected scope" section of
`docs/09-cli-handoff-context.md` -- no Tier 2 code exists, and none should be
written before Tier 1 is submitted. Tier 2 experimental failures must not
contaminate Tier 1's conclusions, and Tier 1's assumptions must not
automatically become Tier 2's.

## Limitations

Stated in full in `paper/main.tex`'s Discussion/Limitations and in
`docs/04-open-risks.md`. In short: whole-image GAN synthesis stands in for
"deepfake," not face-swap/reenactment; two public detector checkpoints carry
unresolved training-data-leakage risk (disclosed, not resolved); no
identity-level splitting is available for this corpus; the architecture-level
mechanism behind the ConvNeXt/ViT residual is genuinely unknown, not just
unstated; EfficientNet-B6 confounds architecture with training regime
relative to the three frozen probes.

## Citation

See `CITATION.cff`. No DOI or venue -- omitted, not invented.

## Repository layout

| Path | Contents |
| --- | --- |
| `paper/` | Manuscript source, bibliography, figures, compiled PDF |
| `src/deepfake_interference/` | Watermarking, crypto-binding, detectors, metrics, transforms, fusion, stats, pipeline |
| `scripts/` | The actual experiment pipeline, E0 through E12, plus aggregation/analysis/reporting scripts |
| `results/` | Raw and derived result JSON -- see `results/PROVENANCE.md` |
| `models/` | The three disclosed-provenance linear probes (frozen backbone + logistic head weights) |
| `tests/` | 38 tests, no GPU/network required |
| `docs/` | Design history (`00`-`04`), code/results logs (`05`, `06`), panel-expansion and preregistration plans (`07`), CLI handoff context (`09`), and this audit's output (`source_provenance.md`, `manuscript_audit.md`, `research_integrity_report.md`, `hardware_requirements.md`, `tier2_resource_plan.md`) |
| `config.yaml`, `e4e5_config.yaml` | Single source of truth for every constant a script uses -- no absolute personal paths |
| `.github/workflows/ci.yml` | Syntax check, tests, config validation, manuscript numeric audit -- no GPU/dataset dependency |
