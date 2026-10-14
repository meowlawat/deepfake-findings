# Viva / presentation prep — Spectral Confounding in Watermark–Detector Interference

Sourced entirely from `paper/main.tex`, `docs/manuscript_audit.md`, and the result files
in `results/`, as they exist at commit `7361970` on `main`. Every number below was
either independently reproduced by running `scripts/audit_manuscript.py` and `pytest`
in this session, or read directly from `paper/main.tex` / a `results/*.json` file and
is cited by path. Anything not supported this way is labeled `[UNVERIFIED]` rather than
asserted. This document does not introduce new claims, numbers, or interpretations
beyond what the manuscript and artifacts already state.

**Paper:** "Spectral Confounding in Watermark–Detector Interference: PSNR-Matched
Controls Are Not Sufficient" — Hardik (IIT Patna; VIPS-TC), Yuv Jindal (VIPS-TC).

---

## 1. The research question, in one sentence

Does embedding a provenance watermark measurably interfere with a passive
synthetic-image detector inspecting the same pixels, once the control used to test
that claim is actually adequate? (`paper/main.tex` abstract, `README.md` "Research
question")

The paper's answer is not "no" — it is "the obvious control (PSNR-matching) is not
adequate, and once you fix that, the answer depends on which detector you ask."

## 2. Why a control is needed at all

A detector trained on clean images responds to *any* imperceptible perturbation, not
just a watermark. Without a control, a measured score change after watermarking could
be generic perturbation sensitivity, not something specific to the watermark. This is
the reason the paper's entire structure exists (`paper/main.tex` abstract, opening
sentence).

## 3. Why PSNR-matching is not sufficient — the central finding

The natural control is a payload-free perturbation matched per image to the
watermark's PSNR. On this control, initial results on 20,000 held-out images looked
decisive: PSNR-matched noise attenuated EfficientNet-B6's evidence (slope
0.83–0.85) while watermarking did not (slope 0.97–0.99) (`paper/main.tex` abstract).

That conclusion does not survive measuring *where* the perturbation's energy sits in
frequency. PSNR fixes only total distortion energy, not its spectral distribution.
Measured residual power fractions (low/mid/high radial frequency bands):

| Arm | Low | Mid | High | Source |
| --- | --- | --- | --- | --- |
| DWT-DCT-SVD watermark | 0.825 | 0.071 | 0.104 | `results/e11_spectral_profile.json` |
| DWT-DCT-SVD PSNR-matched null | 0.143 | 0.396 | 0.461 | same |
| RivaGAN watermark | 0.967 | 0.024 | 0.008 | same |
| RivaGAN PSNR-matched null | ~0.15 | ~0.39 | ~0.46 | same |

Both watermarks concentrate 83–97% of residual power in the lowest band; their
PSNR-matched controls put ~46% in the *highest* band. The control is spectrally
**inverted** relative to the thing it is supposed to stand in for (`paper/main.tex`,
§"What a PSNR-matched control actually matches").

## 4. The spectrum-matched control

Built to carry the watermark's own per-image power spectrum while remaining
payload-free:

1. Take the watermark residual `r = x̃ − x`.
2. Compute its 2-D Fourier transform.
3. Keep the magnitude (the power spectrum); replace the phase with random phase.
4. Inverse-transform, then scale to match the watermark's PSNR.

Validated two ways, both in `results/e11_spectral_profile.json`:

- **Payload-free:** recovered BER ≈ 0.51–0.52 (chance is 0.5; the real watermark's BER
  is near 0).
- **Spectrally matched:** DWT spectrum-control bands are 0.824 / 0.073 / 0.103 — within
  0.005 of the watermark's own 0.825 / 0.071 / 0.104 in every band.

This is explicitly a **second-order** control: it matches magnitude/energy spectrum,
not phase structure or higher-order statistics. The paper states this itself as a
residual limitation (`paper/main.tex`, Limitations: "Removed: the control matched only
energy").

## 5. The main result — detector-dependent, not universal

Independently reproduced in this session via `scripts/audit_manuscript.py` (26/26
checks passed) against `results/e7_full_panel_analysis.json`:

| Detector | Scheme | wm − PSNR-null | wm − spectrum-null |
| --- | --- | --- | --- |
| EfficientNet-B6 | DWT-DCT-SVD | +0.126 [+0.105, +0.146] | +0.006 [−0.009, +0.021] |
| EfficientNet-B6 | RivaGAN | +0.137 [+0.116, +0.159] | +0.014 [0, +0.027] |
| ResNet-18 (own probe) | DWT-DCT-SVD | −0.005 (incl. 0) | +0.012 (incl. 0) |
| ResNet-18 (own probe) | RivaGAN | −0.011 (incl. 0) | +0.029 (excl. 0) |
| ConvNeXt-Base (own probe) | DWT-DCT-SVD | +0.037 (excl. 0) | +0.039 (excl. 0) |
| ConvNeXt-Base (own probe) | RivaGAN | −0.044 (excl. 0) | +0.033 (excl. 0) |
| ViT-B/16 (own probe) | DWT-DCT-SVD | −0.153 (excl. 0) | −0.027 (excl. 0) |
| ViT-B/16 (own probe) | RivaGAN | −0.239 (excl. 0) | −0.013 (incl. 0) |

Reading each row:

- **EfficientNet-B6:** the gap that looked large and reliable under PSNR-matching
  (+0.126, +0.137) collapses to near-zero under spectrum-matching, both intervals now
  including or nearly including zero. The cleanest case for "it was a control
  artifact."
- **ResNet-18:** mostly inconclusive against the PSNR-null; one small, reliable
  residual gap remains against the spectrum-null for RivaGAN.
- **ConvNeXt-Base:** a small, reliable, same-signed gap survives spectrum-matching for
  *both* schemes. This is the clearest evidence that spectrum-matching does not
  universally close the effect.
- **ViT-B/16:** the ordering **reverses** before spectrum-matching is even applied —
  the watermark attenuates evidence *more* than the PSNR-null, the opposite of
  EfficientNet-B6. Spectrum-matching shrinks but does not fully close this for
  DWT-DCT-SVD.

**The defensible conclusion, in the paper's own words:** "an adequate control makes
the effect go away" does not hold as a general statement — it does on EfficientNet-B6,
does not on ConvNeXt-Base, and produces a sign-reversed effect on ViT-B/16 that
spectrum-matching only partially closes (`paper/main.tex`, Discussion).

## 6. What the paper does *not* claim

- Does **not** claim watermark–detector interference is universally absent.
- Does **not** claim to have identified *why* the effect fractures by architecture.
  Two hypotheses are named (ConvNeXt's large-kernel depthwise convolutions responding
  to local phase structure the control doesn't preserve; ViT's patch tokenization and
  attention responding differently to payload structure) and explicitly labeled
  untested — no kernel ablation, no attention-map analysis was run
  (`paper/main.tex`, "Architecture, not just control quality, determines what a fixed
  comparison finds").
- Does **not** claim the spectrum-matched control is a perfect stand-in for the
  watermark — it is a stronger, second-order control, not an exhaustive one.
- Does **not** claim this generalizes beyond whole-image StyleGAN-vs-real synthesis to
  face-swap or reenactment deepfakes.

## 7. Supporting experiments

### Watermark schemes and setup
Two schemes spanning hand-crafted/learned: **DWT-DCT-SVD** (transform-domain) and
**RivaGAN** (learned encoder/decoder), both 32-bit payload, via the
`invisible-watermark` package (`README.md` "Watermarks").

### Detector panel
EfficientNet-B6 is the only **fine-tuned, task-specific** detector in the panel, used
zero-shot, training data undisclosed. ResNet-18, ConvNeXt-Base, and ViT-B/16 are own
probes: frozen ImageNet backbones + a logistic regression head trained on this
project's own split, disclosed provenance. This is a real confound the paper states
explicitly: architecture and training regime are **not independently varied** between
EfficientNet-B6 and the other three — only among the three probes themselves
(`paper/main.tex`, Limitations: "Remains: the strong detector's provenance").

Baseline AUCs (`results/e0_own_panel_floor.json`, floor = 0.80 per `config.yaml`):
ResNet-18 0.858, ConvNeXt-Base 0.987, ViT-B/16 0.973. EfficientNet-B6: 0.895
(`results/detector_screen.json`).

### Public checkpoint screening
Six public HF checkpoints screened for the 0.80 AUC floor (`results/detector_screen.json`,
read directly in this session):

| Checkpoint | AUC | Status |
| --- | --- | --- |
| `Skullly/DeepFake-EN-B6` | 0.895 | PASS |
| `Wvolf/ViT_Deepfake_Detection` | 0.536 | FAIL |
| `dima806/deepfake_vs_real_image_detection` | 0.530 | FAIL |
| `prithivMLmods/Deep-Fake-Detector-v2-Model` | 0.530 | FAIL |
| `Hemg/Deepfake-Detection` | 0.458 | FAIL |
| `DaMsTaR/Detecto-DeepFake_Image_Detector` | 0.536 | FAIL |

`Wvolf/ViT_Deepfake_Detection`'s model card advertises 98.70% accuracy; it scores
AUC 0.5365 (chance) on this evaluation distribution — `paper/main.tex` line 213 and
368, `docs/06-results.md`. The point: advertised performance does not automatically
transfer to a different evaluation distribution; this is not a claim that the
checkpoint is generally poor.

### Frequency dose-response (EfficientNet-B6 only)
Band-limited payload-free perturbations at matched PSNR, evidence-transfer slope:

| Band | Slope | Source |
| --- | --- | --- |
| Low | 0.9075 | `results/e12_frequency_dose.json` |
| Mid | 0.8683 | same |
| High | 0.8092 | same |

Attenuation grows monotonically with frequency on this detector — but the watermark
itself (low-frequency-dominated) attenuates *less* than even the low-band control, so
frequency band alone does not fully explain the watermark's own behavior
(`paper/main.tex`, §"A frequency dose-response, and what it does not explain").

### Resolution ablation
Input resolution (224→448) tested and **excluded** as the explanation for
EfficientNet-B6's asymmetry over the tested range (`paper/main.tex`, §"Mechanism:
resolution is tested and excluded"). `results/e10_resolution_ablation.json` exists and
is git-tracked; its individual cell values were **not** independently re-verified
number-by-number in the audit this document draws from
(`docs/manuscript_audit.md`) — flagged, not silently treated as checked.

### Localized manipulation / payload survival
9,600 measurements (200 images × 6 coverage levels × 4 manipulation families × 2
schemes). At ≤25% coverage: 100% readable across all 8 scheme/family combinations,
mean BER 0.00418 (`results/e8_manipulation_grid.json`, independently reproduced in
this session via `scripts/audit_manuscript.py`). Does not establish survival for face
swaps or any manipulation family not tested.

### Calibration — a secondary, non-confirmatory analysis
Platt and isotonic calibration **disagree** (`paper/main.tex`, §"Calibration under
attenuation"):

| Arm | Platt ECE | Isotonic ECE | slope vs. clean |
| --- | --- | --- | --- |
| clean | 0.1273 | 0.0094 | 1.000 |
| DWT-DCT-SVD | 0.1228 | 0.0154 | 0.968 |
| RivaGAN | 0.1353 | 0.0290 | 0.990 |
| null [DWT] | 0.0958 | 0.0492 | 0.834 |
| null [RivaGAN] | 0.1009 | 0.0456 | 0.850 |

Under isotonic, attenuation degrades ECE 4–5× relative to clean; under Platt the null
arms appear to *improve* — because Platt's clean-arm baseline is already badly
misspecified (ECE 0.1273, 13× isotonic's), so shrinkage partially cancels that
misspecification rather than reflecting a real calibration gain. The paper reports the
disagreement rather than picking the calibrator that supports a conclusion.

A single assumed cost triple looked like a null; this did not survive an 8×8 cost-grid
sweep (63 feasible cells). Under isotonic, the RivaGAN **watermark** arm (not a
control) has the largest effect: worse decision risk than clean in 100% of feasible
cells, median +0.0610. Null arms are worse in 83–98% of cells. This is explicitly
stated as a decision-level, post-hoc, non-independent, non-confirmatory observation —
**not** evidence of watermark-specific interference in the sense the main
control-hierarchy test is (`paper/main.tex`, §"Calibration under attenuation", closing
paragraph).

### The fusion comparison was not run
The planned fusion comparison (combining provenance evidence with detector evidence)
is explicitly reported as **not estimable**: the provenance feature (BER-derived) is
effectively constant across the localized-manipulation coverage range tested, so a
coefficient on a non-varying feature is undefined, not weak. No confirmatory fusion
result is reported or implied (`paper/main.tex`, §"The fusion comparison is not
estimable"). A separate *exploratory* 400-image transform analysis was run to
characterize an interaction term's behavior only — point estimates, no bootstrap
intervals, not offered as a fusion result.

## 8. Limitations, in the paper's own framing

The manuscript distinguishes limitations it removed by experiment from those that
remain (`paper/main.tex`, §Limitations) — this structure is worth using directly
rather than flattening into a generic list:

**Removed by experiment:**
- The control matching only energy — addressed by the spectrum-matched control, though
  that control is still second-order (phase/higher-order structure not matched).
- Relying on one assumed cost triple — replaced by the 63-cell sweep, though costs are
  still assumed, not elicited from a real deployment.

**Reduced, not eliminated:**
- The mechanism was fully unresolved — resolution is now tested and excluded, but
  architecture, training data, and augmentation remain untested confounds.
- A two-detector panel — widened to four across three architecture families, enough to
  show the effect is architecture-dependent, not enough to say which population of
  detectors shows which pattern or why. **New limitation introduced by this widening:**
  the mechanism behind the fracture itself is unresolved.

**Remain, not fixable by further analysis on this data:**
- EfficientNet-B6's training provenance is undisclosed; contamination with the
  evaluation set cannot be excluded. Mitigated, not resolved, by within-model,
  within-image deltas.
- The resize-to-0.5× exploratory cell (β₄ outlier) has no confidence interval — flagged
  and unclaimed, not rerun.
- The corpus is whole-image GAN synthesis, not face-swap/reenactment manipulation, and
  has no identity metadata, so bootstrap intervals are image-level, not
  identity-clustered.

## 9. Likely viva questions and grounded answers

**Q: What is the paper's main contribution?**
A methodological one: demonstrating that a PSNR-matched control can be spectrally
inverted relative to the perturbation it's meant to control for, and that this
confound alone can produce an apparent watermark-interference effect. The
spectrum-matched control and the four-detector panel are what make that demonstration
and its limits concrete.

**Q: Does the paper prove watermarks don't interfere with detectors?**
No. It shows the apparent effect is detector-dependent once the control is adequate —
closes on EfficientNet-B6, partially remains on ConvNeXt-Base, reverses sign on
ViT-B/16 before spectrum-matching.

**Q: Why not just use PSNR matching — what's wrong with it specifically?**
PSNR constrains total distortion energy only, not where that energy sits in frequency.
The paper measured the actual residual spectra and found the PSNR-matched controls
were nearly spectrally inverted relative to the watermarks (46% high-band energy in
the control vs. 83–97% low-band in the watermark).

**Q: Is the spectrum-matched control perfect?**
No — it's explicitly a second-order control (magnitude-spectrum matched, phase
randomized). It doesn't constrain higher-order statistics or phase structure. The
paper states this as a residual limitation, not a solved problem.

**Q: Why does ConvNeXt behave differently from EfficientNet?**
Unknown, and the paper says so. Named as an untested hypothesis: ConvNeXt's
large-kernel depthwise convolutions may respond to local phase structure the
radially-averaged spectral match doesn't preserve. No kernel ablation was run.

**Q: Why does ViT reverse the sign?**
Also unknown. Named hypothesis: patch tokenization and attention may respond to
payload structure differently from generic noise. No attention-map or patch-level
analysis was run to test this.

**Q: Can you trust EfficientNet-B6's result given it's the "cleanest" case?**
With a caveat: it's the only fine-tuned, task-specific, undisclosed-provenance
detector in the panel. Architecture and training regime are confounded between it and
the three probes. The paper mitigates contamination risk with within-model,
within-image deltas but does not claim to have resolved the provenance question.

**Q: What would make this result stronger?**
Per the paper's own limitations: a kernel-size ablation and an attention-map analysis
to actually test the two named architecture hypotheses; a wider public-checkpoint
population (five of six screened checkpoints failed the floor, so the three added
probes are self-trained rather than independently sourced); an experiment that holds
architecture fixed while varying training regime or vice versa.

## 10. Five-sentence summary

1. The paper tests whether apparent watermark–detector interference is genuinely
   watermark-specific or an artifact of using an inadequate control.
2. A PSNR-matched, payload-free control looked decisive on EfficientNet-B6, but its
   residual spectrum is nearly inverted relative to the watermark's — PSNR matches
   energy, not frequency structure.
3. A stronger, payload-free, spectrum-matched control (same per-image power spectrum,
   randomized phase) closes the gap on EfficientNet-B6, from +0.126/+0.137 to
   +0.006/+0.014.
4. That closure does not generalize: ConvNeXt-Base retains a small, reliable gap under
   both schemes, and ViT-B/16 reverses the sign of the effect before spectrum-matching
   is even applied.
5. The defensible conclusion is that PSNR-only controls can be spectrally confounded,
   and once corrected, the apparent effect is detector-dependent rather than
   universally present or absent — the underlying mechanism is named as an open
   question, not resolved.

---

*This document was generated from the manuscript and result artifacts in this
repository and cross-checked against `scripts/audit_manuscript.py`'s 26 passing checks
in the same session it was written. It supersedes any viva-prep content generated in a
separate, disposable environment not reflected in this repository's git history.*
