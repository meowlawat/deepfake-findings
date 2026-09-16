# Detector Panel Expansion — H100 Execution Plan

Status: **not started**. This is the plan for the next phase, written before any
of it is run, so scope is fixed before compute is spent. Current paper
(`paper/main.tex`, commit `7ca7e89`) is unaffected until this plan is executed
and its results are folded in.

## Why this phase exists

The paper's central finding — that the reported watermark--detector
interference effect is a control-construction artifact, not a property of
watermarking — rests on one non-disclosed checkpoint (EfficientNet-B6) and one
disclosed linear probe (ResNet-18, frozen ImageNet features + logistic head).
A reviewer's strongest objection is panel breadth: two detectors, one of them
a toy probe, is not enough to claim the finding is a property of detection in
general rather than of one checkpoint.

This phase closes that gap by widening the disclosed-provenance panel from one
probe to three, while changing nothing else about the experiment.

## What this phase is NOT

Rejected scope (originally proposed, cut after review):

- **Diffusion models (SDXL/FLUX/Midjourney).** Different artifact spectrum
  from the StyleGAN corpus the spectral-inversion finding was measured on.
  Would require re-deriving the spectral-confounding result from scratch on a
  new generator family, not extending it. Separate paper.
- **Real generative inpainting (ControlNet/SDXL-Inpainting/InstructPix2Pix)
  at 100k+ images.** Introduces a new confound (edit-boundary destruction vs.
  watermark interference) with no control scheme yet designed for it, and is
  real GPU-hours even on a large cluster. Separate paper.
- **Latent-space watermarking (Tree-Ring, Stable Signature).** Embedded during
  sampling; there is no clean image to watermark after the fact, so the
  evidence-transfer regression design (`v_arm = a + b*v_clean`) does not
  transfer. Separate paper.
- **Fine-tuning full backbones end-to-end.** Breaks the disclosed-provenance
  methodology the paper already argues for (frozen generic features + linear
  head, weak-probe-as-existence-proof logic — see
  `scripts/train_own_detector.py` docstring) and reintroduces in-distribution
  overfitting risk. Not used even with GPUs available.

Each of the above needs its own control design and its own baseline
measurement before it can be trusted. Bundling them into this phase would
repeat the exact mistake the precision pass just corrected: claiming more than
the evidence, extended to claiming more than the design supports.

## What this phase IS

Two more frozen-backbone + linear-head detectors, trained the same way
`models/own_detector.json` (ResNet-18) already was, with the same disclosure
argument: pretraining contains no deepfake corpus, the head is fitted only on
the named train split, validation/test are never touched during fitting.

**Backbones (proposed, confirm before running):**
1. **ConvNeXt-Tiny** — modern CNN family, architecturally distinct from
   ResNet-18.
2. **DINOv2 ViT-S/14** — self-supervised transformer; provenance argument is
   if anything cleaner than plain ImageNet classification (curated web images,
   no labels at all, let alone deepfake labels).

Explicitly avoided: ConvNeXt-**Base**/ViT-**Large** or bigger — 5-8x the
per-image CPU cost of ResNet-18 for feature extraction alone at n_train=16,000,
risking the compute budget for no methodological gain the smaller variants
don't already provide.

**Held fixed (the point of the design — architecture is the only variable
that moves):**
- Corpus: existing StyleGAN real/fake corpus (`data/corpus/{train,test,validation}`).
- Watermark schemes: DWT-DCT-SVD, RivaGAN.
- Control: phase-randomized, spectrum-matched control
  (`null_perturbation.match_spectrum_and_psnr`), verified payload-free and
  matched exactly as for the existing panel.
- Confirmatory test split: n=800, same offset as the current E7 run, so new
  results are directly comparable to the existing table, not a new sample.

## Steps

1. **Generalize `scripts/train_own_detector.py`** to accept `--backbone`
   (HF model id) and `--out`, instead of hardcoding ResNet-18. No change to
   the frozen-features + logistic-head method itself.
2. **Train two new heads** on the existing train split (n_train=16,000,
   balanced, matching the ResNet-18 run) — one per backbone.
3. **E0 floor check** on each new detector (AUC > 0.80 bar, matching the
   existing gate) before anything downstream runs. A detector that lands at
   chance is reported as such, not discarded quietly — five of six screened
   public checkpoints already did this in the current paper, and that
   precedent holds here too.
4. **Re-run the E7 control-hierarchy contrast**
   (`scripts/e7_control_hierarchy.py` / `scripts/analyze_e7.py`) once per new
   detector that clears the floor, same n=800 confirmatory images, same
   bootstrap protocol (2,000 resamples over images).
5. **Fold results into the existing Table** (currently EffNet-B6 + ResNet-18
   probe) as additional rows, not a new table — same wm-null / wm-spec columns,
   same CI format.
6. **Update the panel-breadth limitation** in `paper/main.tex` from "one
   checkpoint, one toy probe" to the actual resulting count and composition,
   and update the abstract/conclusion only as far as the new data supports —
   same precision-pass discipline as the last commit, not a rewrite of the
   scientific story.
7. **Rebuild, re-run the numerical lock and stale-claim search**
   (grep the whole manuscript again, as in commit `7ca7e89`) before any push.

## Compute

This phase does **not** require the H100 cluster. `train_own_detector.py`
already ran ResNet-18's feature extraction (n_train=16,000) on this
CPU-only, 4-core, 15GB sandbox. ConvNeXt-Tiny and DINOv2 ViT-S/14 are heavier
per image but tractable on the same hardware within the backbone choices
above; a GPU would only shorten wall-clock time, not change what's
achievable.

If GPU access (the H100 cluster referenced by the user) becomes available and
connected to a session that can reach it, it should be used to shorten step 2
(feature extraction) — that is the only step with meaningful wall-clock cost —
not to expand scope beyond what is written above. Any scope change (more
backbones, fine-tuning, new generators, new watermark families) requires a new
version of this plan, reviewed the same way this one was, before it is run.

## Timeline (within the stated 3-6 week submission window)

- Week 1: script generalization, train both new heads, E0 floor check.
- Week 2: E7 re-run across panel, analysis, control-quality verification
  (BER/PSNR/SSIM checks, matching the existing arms).
- Week 3: paper integration — table, limitations section, figure update,
  numerical lock, stale-claim search, rebuild.
- Weeks 4-6: buffer for anything that fails the floor check or produces a
  result requiring a claim to be narrowed rather than widened, plus final
  review pass and submission prep.

## Explicit stop conditions

- A new backbone below the AUC floor is reported at chance, not retrained
  with a different split or head to force it over the bar.
- If the wm-null / wm-spec pattern does not replicate on a new backbone the
  way it did on EfficientNet-B6, that is reported as a boundary condition
  (as the paper already does for the ResNet-18 probe's reversed ordering),
  not smoothed over.
- No step here changes the corpus, watermark schemes, or control construction
  that the current spectral-inversion finding depends on. Any request to vary
  those belongs to a separate plan, not this one.
