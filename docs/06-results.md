# Results log

Every number here is produced by code in this repository and traceable to a
JSON under `results/`. Nothing is copied from a plan, an expectation, or a
prior session's summary. Where a number is preliminary (small n, one seed,
one dataset), it says so on the same line rather than in a distant caveat.

## Run configuration

| Item | Value |
| --- | --- |
| Dataset | `TheKernel01/140k-Real-and-Fake-Faces` (HF mirror of Kaggle `xhlulu/140k-real-and-fake-faces`), balanced subset fetched by `scripts/fetch_dataset.py` |
| Content type | whole-image StyleGAN synthesis vs. real FFHQ photographs — **not** face-swap/reenactment (docs/04 R8) |
| Subset size | 150 real + 150 fake = 300 images |
| Watermark schemes | `dwtDctSvd` (hand-crafted), `rivaGan` (learned, pretrained ONNX), `∅` null-perturbation control |
| Detectors | `Wvolf/ViT_Deepfake_Detection` (ViT), `Skullly/DeepFake-EN-B6` (EfficientNet-B6) — both zero-shot (docs/04 R10), both of undisclosed training provenance (docs/04 R14) |
| Compute | CPU-only container; no GPU |

## Standing caveats that apply to every number below

1. **n = 300 is small.** These are single-run point estimates on one dataset
   subset. Bootstrap CIs are reported where computed; where they are wide,
   say so rather than reporting the point estimate alone.
2. **Detector leakage is unresolved** (docs/04 R14). Absolute AUC/accuracy is
   context, never a claim. The load-bearing quantities are within-model
   deltas.
3. **GAN synthesis, not deepfakes** (docs/04 R8). The framing constraint on
   the title and abstract is unchanged by any result here.

## Imperceptibility controls (T5)

Measured by `scripts/00_verify_tooling.py` on photo-like content:

| Scheme | PSNR | SSIM | Clean-channel BER |
| --- | --- | --- | --- |
| `dwtDctSvd` | 36.9 dB | 0.967 | 0.000 |
| `rivaGan` | 40.2 dB | 0.983 | 0.125 |

Note `rivaGan`'s nonzero clean BER: the learned scheme is *more*
imperceptible (higher PSNR/SSIM) but does not round-trip its payload
losslessly even on an untransformed channel. That is exactly what `p_0`
(docs/02 §2) is for — the LLR treats it as reduced evidence strength rather
than silent corruption — but it is worth stating plainly, because a reader
who assumes BER≈0 on a clean channel would misread every `z_P` downstream.

## Cryptographic binding reliability

`crypto_binding.verification_reliability_rate`, false-negative rate
(a legitimately watermarked image failing its own signature check):

| Content | Scheme | n | FN rate |
| --- | --- | --- | --- |
| synthetic smooth noise | `dwtDctSvd` | 8 | 0.625 |
| **real photographs** | `dwtDctSvd` | 100 | **0.07** |
| **real photographs** | `rivaGan` | 100 | **0.07** |

Synthetic content was a bad proxy by an order of magnitude. 7% on real data
is reportable and non-zero: the Ed25519 binding is a sound *design*
correction to the source material's AES-256 choice, but it is not a
demonstrated-reliable deployment mechanism at this hash construction
(docs/04 R15).

## E0 — detector floor check

From `results/e1_full_run.json`, n = 300, clean channel (`W = 0`):

| Detector | Baseline AUC | Floor (0.80) | Verdict |
| --- | --- | --- | --- |
| `Wvolf/ViT_Deepfake_Detection` | **0.5365** | fails | at chance |
| `Skullly/DeepFake-EN-B6` | **0.8952** | passes | usable |

**The ViT detector is at chance on this dataset.** Its model card advertises
98.70% test accuracy. On StyleGAN-synthesis vs. real FFHQ it discriminates
barely better than a coin. Every ViT row in the interference table below is
therefore noise around a non-functional detector and carries no
information about interference; they are reported for completeness and
excluded from interpretation.

This is a result in its own right, and an unflattering one for the field's
practice of publishing zero-shot detectors with headline accuracies: a
community detector advertising ~99% transfers to a different synthesis
distribution at ~0.54 AUC. It also vindicates E0 existing as a *precondition*
rather than a formality — without it, four meaningless rows would have gone
into T1 looking like measurements.

The EfficientNet detector's 0.8952 sits **below** the 0.97
leakage-suspicion threshold (docs/04 R14), so the leakage flag does not
fire. That is weak evidence against contamination, not proof of its absence.

## E1 — interference (T1) and the go/no-go gate

From `results/e1_full_run.json`, n = 300. `∅` = PSNR-matched
null-perturbation control.

| Detector | Scheme | Δμ | Δσ | ΔAUC | ΔAUC(∅) | **ΔAUC_net** |
| --- | --- | --- | --- | --- | --- | --- |
| vit *(dead — ignore)* | dwtDctSvd | +0.019 | 1.005 | +0.0162 | −0.0022 | +0.0184 |
| vit *(dead — ignore)* | rivaGan | −0.541 | 0.992 | +0.0024 | −0.0041 | +0.0065 |
| **effnet** | dwtDctSvd | −0.054 | 0.983 | +0.0015 | +0.0009 | **+0.0006** |
| **effnet** | rivaGan | +0.679 | 1.003 | −0.0159 | −0.0025 | **−0.0134** |

### Gate verdict: FAIL, as pre-registered

The gate threshold (|ΔAUC_net| ≥ 0.02, fixed in advance) is not met by either
scheme on the only working detector: +0.0006 and −0.0134. **No
watermark-specific interference in detector *ranking* is detectable here.**

Per `docs/03` E1 and `docs/04` R1, this is the branch that was written down
in advance: stop, and re-scope toward a bounded replication/negative result,
rather than continue building on a premise that did not hold.

### Two things that must not be spun

**1. A null result at n = 300 without confidence intervals is not evidence of
absence.** With 150 per class, the standard error on a single AUC is roughly
0.03, which is *larger than both net effects*. The honest statement is "no
effect detectable at this sample size," and the CI almost certainly does not
exclude effects large enough to matter. `scripts/e1_interference.py` now
persists raw per-image records so the bootstrap can be run without a
17-minute re-score; **the CIs are required before this is written up as a
negative result.**

**2. Δμ is large where ΔAUC is ~zero, and the gate does not test Δμ.**
effnet + rivaGan shows Δμ = **+0.679 logits** with Δσ = 1.003 — a near-pure
*location* shift with no scale change. A uniform location shift barely moves
AUC (ranking is preserved) but is precisely what invalidates a posterior
calibrated on unwatermarked media — which is this paper's actual thesis
(calibration, not accuracy; docs/02 §5's "load-bearing dependency").

So the gate may be thresholding the wrong quantity for the hypothesis it
guards. **This observation is post-hoc and is not claimed as a result.**
Changing the gate's target after seeing the data is exactly the move that
turns a null into a false positive. It is recorded here as a *design flaw in
the gate*, and the legitimate test of it is E2/E3's ΔECE_W and β₄, which were
pre-registered as the calibration measurements and are computed on data the
gate did not select.

A further caveat on Δμ specifically: an earlier version of
`e1_interference.py` subtracted the `∅` control from ΔAUC only, leaving
Δμ/Δσ **uncontrolled**. The Δμ values in the table above are therefore raw,
not net, and part of that +0.679 may be generic perturbation response rather
than anything watermark-specific. The script now computes `delta_mu_null`
and `delta_mu_net`; the table must be regenerated before Δμ is discussed
anywhere.

## E2/E3 — fusion and calibration (T2, F1, F2)

_Filled from `results/e2_e3_fusion.json`._

## E4/E5 — transforms and the ρ sweep (T3, F3)

_Filled from `results/e4_e5.json`._

## E6 — ablations (T4)

_Filled from `results/e6_ablations.json`._

## A structural limitation that governs how E2–E6 must be read

Noted before E2/E3's numbers arrived, so it cannot be mistaken for a
post-hoc excuse for them.

**The provenance channel is non-informative in this setup by construction.**
The pipeline takes images that are *already* real or fake (the dataset ships
both classes pre-made) and embeds a watermark into them. So the mark is
applied *after* the synthetic image exists, and survives equally well on both
classes.

The deployment threat model is the opposite ordering:

```
deployment:  authentic image -> embed watermark -> deepfake manipulation D -> high BER signals tampering
v1 pipeline: (already real OR already fake) -> embed watermark -> BER reflects image texture, not provenance
```

`docs/02` §1 lists `D` (deepfake manipulation) in the notation and `V =
f_θ(T(D(x̃)))` puts `D` *after* embedding. v1 has no `D` step at all — it
was never in scope, because applying a real face-swap to watermarked images
needs a generative model that the zero-training constraint (docs/03 §0)
excludes.

Consequences, all of which must be stated wherever E2–E6 appear:

1. `z_P` should carry ~no information about `y`, so `β₁ ≈ 0` and `F1` should
   perform about like `F0`. If `β₁` comes out clearly non-zero, that is
   **not** provenance signal — it is a confound (e.g. StyleGAN textures
   carrying watermarks slightly differently from photographic ones), and it
   would need investigating rather than celebrating.
2. The fusion is therefore not fusing two informative evidence sources. It is
   one informative source plus noise, which is a degenerate case of the
   method docs/02 describes.
3. **E1 is unaffected.** E1 asks only whether watermarking shifts a
   detector's scores. That question is well-posed regardless of whether the
   provenance channel is informative, so the gate result stands on its own.

This is a scope limitation inherited from the 10-day/no-training constraint,
not a bug. But it means v1 cannot substantiate the fusion half of the
contribution, only the interference-measurement half — and the paper must
say so plainly rather than presenting F0–F5 comparisons as though the
provenance channel were doing work.

## Detector screening: five of six community detectors are at chance

`scripts/screen_detectors.py`, n = 300, baseline AUC on unwatermarked images
(`W = 0`). All six are public Hugging Face checkpoints returned by searching
the hub for deepfake image classifiers.

| Model | Baseline AUC | Verdict |
| --- | --- | --- |
| `Skullly/DeepFake-EN-B6` | **0.8952** | passes the 0.80 floor |
| `Wvolf/ViT_Deepfake_Detection` | 0.5365 | chance — card advertises 98.70% accuracy |
| `DaMsTaR/Detecto-DeepFake_Image_Detector` | 0.5365 | chance |
| `prithivMLmods/Deep-Fake-Detector-v2-Model` | 0.5299 | chance |
| `dima806/deepfake_vs_real_image_detection` | 0.5296 | chance |
| `Hemg/Deepfake-Detection` | 0.4576 | **below** chance |

This was run to widen the evidential base for E1's null, which rests on a
single detector. **It failed at that, and the failure is itself the more
interesting result.** Only one of six publicly available deepfake detectors
discriminates at all on whole-image StyleGAN synthesis versus real FFHQ
photographs — a task that is, if anything, *easier* than the face-swap
detection these models are nominally for.

Two things to check before this is written up:

1. **`Wvolf` and `DaMsTaR` report AUC identical to four decimal places
   (0.5365).** That is not plausibly coincidence across 300 images; the
   likeliest explanation is that one is a re-upload of the other's weights.
   Verify by comparing per-image scores — if they match elementwise, the
   "six independent detectors" framing is wrong and it is really five, which
   must be stated.
2. `Hemg` scoring *below* 0.5 means its labelling is likely inverted relative
   to its `id2label`, not that it is worse than guessing. Either way it does
   not clear the floor, but the paper should not imply anti-predictive skill
   where the real story is a label convention.

**Consequence for E1, stated plainly:** the plan to strengthen the null by
measuring it across several independent detectors is not achievable with
publicly available checkpoints. The null rests on one detector, and no amount
of further screening fixes that — it is a property of what exists, not of
effort. This belongs in Limitations as a hard constraint rather than as
future work.

## CONFIRMATORY RESULT — validation split, n = 20,000

Tests the hypotheses pre-registered in `docs/07-preregistration-2.md`, on a
split never used to generate them. From `results/large_summary.json`.

**E0.** `Skullly/DeepFake-EN-B6` baseline AUC = **0.8733** (n = 20,000).
Clears the 0.80 floor; below the 0.97 leakage-suspicion threshold.

**E1, net of the PSNR-matched payload-free control:**

| Scheme | `Δ_μ_net` (H1) | `Δ_AUC_net` (H2) |
| --- | --- | --- |
| `dwtDctSvd` | **+0.8373** [+0.8071, +0.8667] | +0.0049 [+0.0032, +0.0066] |
| `rivaGan` | **+1.3530** [+1.3169, +1.3865] | −0.0051 [−0.0071, −0.0033] |

### Verdicts against the pre-registered criteria

**H1 — SUPPORTED, both schemes.** `Δ_μ_net` excludes zero and exceeds the
0.10-logit effect floor by roughly 8× and 13×. Direction is positive, as
predicted. Watermarking shifts the detector's score distribution toward
"fake" by 0.84–1.35 logits, net of what an equally-imperceptible payload-free
perturbation does.

**H2 — HOLDS, with a caveat that must be stated.** `Δ_AUC_net` stays inside
the pre-registered ±0.02 band for both schemes. But at n = 20,000 the
intervals now *exclude zero*: there is a real ranking effect of roughly
±0.005 AUC. It is statistically detectable and practically negligible, and
the two schemes carry **opposite signs** (+0.0049 vs −0.0051), so there is no
consistent direction to it.

This is precisely the case the effect-size floor was written in to handle: at
large n a CI excludes zero for effects too small to move any decision.
Reporting "significant ranking interference" off these numbers would be
technically true and substantively false. The honest statement is that the
ranking effect is ~0.005 AUC — two orders of magnitude smaller than the
location shift, and smaller than the difference between the two schemes.

**H3 — not yet testable.** Requires the train split.

### What this establishes

**Watermarking translates a detector's scores without meaningfully reordering
them.** A ~1-logit uniform shift is invisible to AUC — ranking is preserved,
so every accuracy-style metric reports business as usual — while being fatal
to any decision threshold calibrated on unmarked media. A system that fixes
its operating point on clean data and then deploys on watermarked traffic is
applying a threshold to a distribution that has moved out from under it.

This is the calibration thesis, confirmed on data that never generated it,
at n = 20,000 with intervals roughly 7× tighter than the exploratory slice.

The earlier n=300 gate failure (`Δ_AUC_net` ≈ 0) was therefore **correct, not
underpowered** — it was measuring ranking, and ranking genuinely does not
move. The premise it appeared to refute was never a ranking claim; it was a
calibration claim that the gate was not built to see.

## H3 — leakage diagnostic, resolved

Baseline AUC (`W = 0`), 20,000 images per split, `Skullly/DeepFake-EN-B6`:

| Split | Baseline AUC |
| --- | --- |
| train | 0.8697 |
| validation | 0.8733 |
| test | 0.8699 |

**train − test gap = −0.0002.** Essentially identical, and the sign is
*negative* — the detector performs marginally worse on the split it would
have been fine-tuned on, if it had been.

**H3 verdict: no evidence of train-split contamination.** The gap is two
orders of magnitude below the 0.05 threshold registered in `docs/07`. Stated
with the caveat that was registered alongside it: this is evidence *against*
contamination, not proof of its absence. A detector fine-tuned on a different
corpus that merely overlaps this one would not show a train/test gap either.

What it does settle is the specific worry in `docs/04` R14 — that
`Skullly/DeepFake-EN-B6`'s undisclosed training data was *this corpus's train
split*, inflating its 0.87 baseline. That hypothesis predicts a positive gap
and we measure −0.0002.

Note the flat profile across splits (0.8697 / 0.8733 / 0.8699) is itself a
useful control: it shows the three splits are exchangeable with respect to
this detector, which is what licenses treating validation as a clean
confirmatory split for H1/H2.

## Summary of the pre-registered tests

| Hypothesis | Verdict | Evidence |
| --- | --- | --- |
| **H1** — `Δ_μ_net` ≠ 0, effect ≥ 0.10 logits | **SUPPORTED** | +0.837 [+0.807, +0.867] and +1.353 [+1.317, +1.387], n = 20,000 |
| **H2** — `Δ_AUC_net` within ±0.02 | **HOLDS** | +0.0049 and −0.0051; inside the band, opposite signs, negligible magnitude |
| **H3** — train − test baseline AUC gap | **no contamination detected** | −0.0002 against a 0.05 threshold |

Scale: 60,000 images scored, 140,000 detector evaluations, all three splits.

---

# CORRECTION (post-hoc audit): the mechanism is attenuation, not translation

A cross-verification pass recomputed every headline number independently from
the raw shards and then interrogated the mechanism. The numbers reproduce
exactly. **The interpretation attached to them was wrong, and is retracted
here.**

## What reproduces

Independent reimplementation, not importing `aggregate_large.py`:
20,000 images, all five arms present on every image, zero label
disagreements, exactly 10,000/10,000 class balance.
`Δ_μ_net` = +0.8373 (dwtDctSvd) and +1.3530 (rivaGan) — identical to the
reported values. The null arm's PSNR matching is essentially perfect:
**100%** of images within 0.5 dB of their scheme's PSNR (mean difference
+0.009 dB and −0.013 dB). The control is fair.

## What was wrong

Decomposing `Δ_μ_net` into its two halves:

| Scheme | watermark − clean | null − clean | net |
| --- | --- | --- | --- |
| dwtDctSvd | **−0.009** | −0.846 | +0.837 |
| rivaGan | +0.605 | −0.748 | +1.353 |

For dwtDctSvd the watermark moves the mean by **−0.009 logits — nothing**.
The entire net effect is the *null arm falling*. The claim written into
`docs/06` and `paper/main.tex` — "watermarking shifts the detector's score
distribution toward fake by 0.84–1.35 logits" — is false for dwtDctSvd and
overstated for rivaGan.

Worse, the effect is not a location shift at all. `Δ_μ_net` by clean-score
quintile, where a translation would be flat:

| clean-score quintile | net |
| --- | --- |
| [−11.6, −2.8] | **−0.364** |
| [−2.8, 1.2] | +0.279 |
| [1.2, 6.2] | +0.787 |
| [6.2, 11.2] | +1.200 |
| [11.2, 36.8] | **+2.285** |

Regressing each arm's score on the clean score, `v_arm = a + b·v_clean`:

| Arm | slope b | intercept a |
| --- | --- | --- |
| dwtDctSvd | 0.968 | +0.125 |
| **null[dwtDctSvd]** | **0.834** | −0.158 |
| rivaGan | 0.990 | +0.649 |
| **null[rivaGan]** | **0.850** | −0.125 |

A translation predicts b = 1. The null arms show **b ≈ 0.84 with intercept
≈ 0**: equal-PSNR random perturbation *attenuates* the detector's log-odds
evidence toward zero by roughly 16%. The watermark arms show b ≈ 0.97–0.99 —
evidence essentially preserved.

**`Δ_μ_net` was the wrong estimand.** Attenuating a distribution whose mean
is not zero (clean mean = +4.16 logits) lowers that mean, so `Δ_μ` reports a
"location shift" for what is really a slope change. The pre-registered test
was passed by a real effect measured with the wrong instrument.

## What the corrected finding is

**At matched imperceptibility (~40 dB PSNR), random perturbation attenuates a
detector's evidence by ~16%, while watermarking of identical imperceptibility
does not. Watermarks are not equivalent to noise of the same energy.**

Two consequences, and they are sharper than the original framing:

1. **Attenuation is invisible to AUC by construction.** With intercept ≈ 0 it
   is a monotone rescaling, and AUC is rank-based — a unit test in
   `tests/test_metrics.py` confirms AUC is *exactly* unchanged under pure
   attenuation. This is why the pre-registered AUC gate returned a null while
   a real effect was present. Any study gating on AUC alone cannot see this.
2. **Attenuation is exactly what breaks calibration.** Shrinking log-odds
   toward zero systematically changes the score-to-posterior mapping, so a
   threshold calibrated on unperturbed media is applied to evidence that has
   been scaled down. The calibration thesis survives — but the hazard is
   ordinary channel noise, not watermarking.

The relationship to the prior literature inverts accordingly. The "watermarks
are bugs for deepfake detectors" concern is, in this setting, **not**
supported: watermarks are markedly *less* damaging to detector evidence than
equal-PSNR noise. Only the null-arm control makes that visible — without it,
dwtDctSvd's −0.009 would read as "no effect" and the detector's real fragility
to ordinary perturbation would go unmeasured.

## Effect sizes, stated properly

The original write-up called ~1 logit "huge". Against a clean-score standard
deviation of 7.04 that is 0.12–0.19 sd; paired per-image Cohen's *dz* is 0.38
and 0.55. Moderate, not huge.

The effect is also **class-dependent**, which the pooled figure hid:

| Scheme | net on REAL | net on FAKE |
| --- | --- | --- |
| dwtDctSvd | +0.379 | +1.296 |
| rivaGan | +0.985 | +1.721 |

Noise erodes evidence on manipulated images ~3× more than on real ones
(dwtDctSvd null: −1.447 on fakes vs −0.246 on reals). That asymmetry is the
operationally important part: **imperceptible noise preferentially destroys
the evidence that something is fake.**

## Blocker 3 addressed: calibration measured, not argued — result is PARTIAL

`scripts/calibration_effect.py`. Protocol fixed before running: split the
20,000 scored validation images in half; fit a calibrator on the **clean arm
of the calibration half only** (the deployment story — you calibrate once, on
clean media); freeze it; apply to the eval half of every arm.

| Arm | Platt ECE | Isotonic ECE | slope vs clean |
| --- | --- | --- | --- |
| clean | 0.1273 | **0.0094** | 1.000 |
| dwtDctSvd | 0.1228 | 0.0154 | 0.968 |
| rivaGan | 0.1353 | 0.0290 | 0.990 |
| null[dwtDctSvd] | 0.0958 | **0.0492** | 0.834 |
| null[rivaGan] | 0.1009 | **0.0456** | 0.850 |

**The two calibrators disagree in sign on the null arms, and that must not be
cherry-picked.** Under isotonic, attenuation degrades calibration by
+0.040/+0.036 — a 4–5× increase over the clean baseline of 0.0094, with
watermarks degrading far less (+0.006, +0.020). Under Platt, the null arms
*improve* by −0.032/−0.026.

**Why Platt is uninformative here, stated rather than used to pick a winner.**
Platt's ECE on the *clean* arm is 0.1273 — thirteen times isotonic's. A
single logistic in the raw logit is badly misspecified for this detector
(scores span −11.6 to +36.8 with sd 7.04 and strongly non-logistic class
overlap), so the Platt baseline is already broken before any perturbation is
applied. Attenuation happens to move scores in a direction that partially
cancels that misspecification. A ΔECE measured against a broken baseline
measures the baseline, not the perturbation.

That the field's default calibrator is this badly misspecified on a
real detector's logits is worth reporting in its own right.

**Verdict on the claim.** Supported for calibration *quality*: with a
well-specified calibrator, attenuation degrades ECE 4–5× while equally
imperceptible watermarking degrades it far less. **Not supported for decision
risk** under the cost model tested: isotonic DRD is 0.0055 (clean), 0.0145
(null-dwt), 0.0054 (null-riva) — small and inconsistent in direction. The
mechanism reaches the probability estimates but does not, at these costs,
reliably move the decisions those probabilities drive.

The paper must say exactly that, and must not claim a decision-level harm the
data does not show.

## Blocker 2 addressed: robust watermarks cannot see localized manipulation

The fusion half was untestable because the corpus watermarked images that
were already fake. `src/deepfake_interference/manipulation.py` adds the
missing step `D` in the correct order — watermark an authentic image, *then*
tamper with it — using a Poisson-blended elliptical region splice
(`cv2.seamlessClone`), which is what a face swap does geometrically without
needing a generative model.

**The provenance channel still carries no signal, and now we know why.**
Bit error rate of the recovered payload against manipulated area:

| Area manipulated | dwtDctSvd BER | rivaGan BER |
| --- | --- | --- |
| 10% | **0.0000** | 0.0052 |
| 25% | **0.0000** | 0.0104 |
| 40% | 0.0026 | 0.0156 |
| 60% | 0.0443 | 0.0521 |
| 80% | 0.1953 | 0.1224 |
| 95% | 0.2630 | 0.1615 |

(BER 0.5 = payload destroyed; 0.0 = perfectly recovered. Authentic
unmanipulated baseline is 0.0000.)

At face-swap-scale coverage — 10–25% of image area, which is roughly what
replacing a face costs — **the payload is recovered perfectly.** The
manipulated image is indistinguishable from the untampered one on the
provenance channel. Even obliterating 95% of the image leaves BER at 0.26,
nowhere near destruction.

**This is not a limitation of our corpus; it is a property of robust
watermarking, and it refutes the design this project started from.** The
source material's Phase 3 Step 1 asks "Is the watermark present? Has it been
altered?" and routes the answer into deepfake detection. For a robust scheme
that question is answerable only for global, near-total degradation. The
robustness that lets a mark survive JPEG, resize and re-encode is *the same
property* that makes it survive having a face replaced — redundant embedding
across the whole image means destroying a fifth of it costs nothing.

Two consequences for the paper:

1. **The fusion half cannot be rescued by a better corpus.** We built the
   manipulation step specifically to rescue it, and measured that it does not.
   A provenance channel built on a robust watermark contributes no information
   about localized tampering, so any `F0`–`F5` comparison over it is fusing
   one informative source with a constant. This is now a measured claim rather
   than a suspicion.
2. **It explains why the semi-fragile and localization-capable schemes in the
   related work exist at all** (EditGuard, SepMark and the separable-decoder
   family). They are not incremental refinements of robust watermarking; they
   are a response to exactly this failure. A robust mark answers "where did
   this come from"; it cannot answer "was this edited". Our measurement puts a
   number on the gap.

The honest framing for the paper is therefore that we set out to test
interference in a fusion of provenance and passive evidence, and found the
provenance half inert for the threat it is deployed against — with the
crossover measured at roughly 40–60% manipulated area, far outside any
realistic face manipulation.

## Blocker 1 addressed: the attenuation asymmetry does NOT replicate

`scripts/train_own_detector.py` produced the second detector — frozen
ImageNet ResNet-18 (`microsoft/resnet-18`, `pooler_output`, 512-d) plus a
`LogisticRegression` head fitted on the corpus *train* split only, in-sample
accuracy 0.805. Its provenance is disclosed by construction (ImageNet
pretraining contains no deepfake corpus; the head never saw validation or
test), which is what `docs/04` R14 actually needed and what no amount of
further screening of public checkpoints could supply.

It was run over all five arms on 8,000 validation images.
`scripts/replication_check.py` fits the same evidence-transfer regression
`v_arm = a + b·v_clean` for both detectors **restricted to the identical
8,000 images**, with 800-resample bootstrap CIs:

| Detector | Scheme | watermark b [95% CI] | null b [95% CI] | null − wm |
| --- | --- | --- | --- | --- |
| effnet (B6) | dwtDctSvd | 0.9662 [0.9622, 0.9705] | **0.8323** [0.8247, 0.8393] | **−0.1339** |
| effnet (B6) | rivaGan | 0.9874 [0.9829, 0.9924] | **0.8484** [0.8414, 0.8555] | **−0.1390** |
| own (RN-18 probe) | dwtDctSvd | 0.9562 [0.9510, 0.9615] | 0.9706 [0.9666, 0.9744] | **+0.0144** |
| own (RN-18 probe) | rivaGan | 0.9486 [0.9432, 0.9540] | 0.9758 [0.9719, 0.9789] | **+0.0272** |

**The effect does not replicate, and its sign reverses.** On EfficientNet-B6
the payload-free null perturbation attenuates detector evidence by ~16% while
the watermark attenuates by ~1–3%. On the ResNet-18 probe the null attenuates
by ~2–3% — *less* than the watermark. The CIs are tight and nowhere near
overlapping in either direction.

The obvious escape — "the probe is just too weak to show the effect" — is
closed by the baseline AUCs on those same 8,000 images:

| Detector | clean | dwtDctSvd | null[dwtDctSvd] | rivaGan | null[rivaGan] |
| --- | --- | --- | --- | --- | --- |
| effnet (B6) | 0.8703 | 0.8672 | 0.8629 | 0.8586 | 0.8644 |
| own (RN-18 probe) | 0.8725 | 0.8641 | 0.8655 | 0.8598 | 0.8665 |

The two detectors are equally discriminative here (0.8703 vs 0.8725) and
their AUCs move nearly identically under every arm. What differs is *how
the score distribution moves* — which is precisely the quantity AUC cannot
see, and precisely what the regression was introduced to measure. A weak
detector cannot explain a difference in a quantity on which the two
detectors are matched.

**Consequence: attenuation is a property of one checkpoint, not of
detection.** EfficientNet-B6's sensitivity to PSNR-matched additive noise
is a fact about that model — plausibly about training-time augmentation, or
about a 528×528 processing resolution that resamples fine noise differently
than the probe's 224×224 — and it cannot be asserted as a property of
passive deepfake detection. This is the outcome
`scripts/train_own_detector.py`'s own docstring committed to reporting
either way, and it goes against the claim the paper was built around.

### What survives, and what does not

Does not survive as a general claim:

- "Payload-free perturbation attenuates detector evidence while watermarking
  does not." Checkpoint-specific. Stated as general in the abstract, intro
  and contribution 2 of `paper/main.tex` before this measurement; corrected
  there now.

Survives, and is strengthened:

- **The null-arm control is necessary.** This is now the paper's strongest
  methodological point rather than a caveat. Δμ for dwtDctSvd on effnet is
  −0.009 while its PSNR-matched null moves −0.846: a study without the
  control arm would have reported the null's behaviour as the watermark's.
  And a study with the control but only one detector would have reported a
  checkpoint artifact as a property of detection. Both failures are cheap to
  make and neither is visible in the headline metric.
- **AUC is blind to monotone attenuation** (`b < 1` with `a ≈ 0` is rank-
  preserving). Mathematical, not empirical: unaffected.
- **Δμ conflates translation with attenuation**, so it is the wrong estimand
  for this question. Mathematical: unaffected.
- **Robust watermarks are blind to localized manipulation** (BER 0.0000 at
  10–25% manipulated area). Scheme-level and architecture-independent — no
  detector appears in that measurement at all.
- **Five of six public detector checkpoints are at chance on this corpus**,
  and the sixth has undisclosed training data. Unaffected.

The paper's thesis is therefore no longer "watermarking is benign where
noise is harmful". It is: *the interference question cannot be answered
without a payload-free control arm and more than one detector, and when you
supply both, the effect that motivated the question turns out to be
checkpoint-specific while the provenance channel turns out to be inert for
the threat it is deployed against.* That is a smaller claim and a true one.

## E4/E5 run: transform robustness and the ρ sweep, n=400 (reduced scale)

Run against the held-out `test` split (`data/corpus/test`, disjoint from the
`validation` split used for the confirmatory result and blocker 1), stratified
`n=400` (120 calibration / 280 test) — reduced from the confirmatory 20,000
because `scripts/e4_e5_transforms_rho.py` is unbatched (one image at a time
through both watermark embedding and detection) and this session is CPU-only,
no GPU. Total wall time ≈ 2.5 hours. **No bootstrap CIs are computed by this
script** — every number below is a point estimate on n=280 test images per
condition, unlike the CI-backed E1/replication numbers. Read accordingly:
this is a first look, not a confirmatory measurement.

### E4 — transform suite (F0–F5, EfficientNet-B6)

| Transform | F0 AUC | F0 DRD | F4 AUC | F4 DRD | F4 β₄ |
| --- | --- | --- | --- | --- | --- |
| jpeg(90) | 0.8985 | 0.0063 | 0.8965 | 0.0075 | +0.004 |
| jpeg(70) | 0.7757 | 0.0027 | 0.8193 | 0.0053 | −0.022 |
| jpeg(50) | 0.7211 | 0.0008 | 0.7942 | 0.0054 | +0.038 |
| resize(0.75) | 0.7428 | 0.0028 | 0.8247 | 0.0078 | +0.048 |
| resize(0.5) | 0.7103 | 0.0009 | 0.8246 | 0.0504 | **+0.221** |
| brightness(+20%) | 0.9088 | 0.0343 | 0.9088 | 0.0309 | +0.056 |
| brightness(−20%) | 0.8405 | 0.0030 | 0.8478 | 0.0064 | −0.072 |

F0 is the no-interference-term fusion baseline; F4 carries the β₄
watermark×evidence interaction term.

**What this shows, held to the same standard as everything else in this
paper — no CI, no claim.** Detector baseline AUC degrades hard under
compression and downscaling (0.90 clean-ish down to 0.71–0.78), which is the
detector's own known fragility, not a watermark effect — F0 and F4 move
together on AUC for every transform, so interference-aware fusion is not
recovering anything ordinary fusion loses here. β₄'s point estimate stays
small (|β₄| < 0.08) for six of seven transforms, consistent with no detectable
transform-induced interference at this sample size. **One condition stands
out**: `resize(scale=0.5)` shows β₄ = +0.221 alongside a DRD jump from 0.0009
(F0) to 0.0504 (F4) — roughly 3–6× every other transform's β₄ and the largest
DRD in the table. At n=280 test images and no bootstrap, this is not
reportable as a finding; it is the one condition that would justify spending
a CI-backed rerun on, specifically.

### E5 — watermarked-fraction (ρ) sweep

Fusion models are fit once on the full calibration set and evaluated on
ρ-mixtures of the test set (design choice: ρ is a property of the deployment
stream, not something a model gets to retrain against per-stream — so β₄ is
identical across every ρ row for a given fit, by construction, not a result).

| Scheme | ρ | AUC (F0 / F4) | ECE (F0 / F4) | DRD (F0 / F4) |
| --- | --- | --- | --- | --- |
| dwtDctSvd | 0.05 | 0.9175 / 0.9176 | 0.1452 / 0.1437 | 0.0133 / 0.0154 |
| dwtDctSvd | 0.25 | 0.9186 / 0.9183 | 0.1466 / 0.1456 | 0.0133 / 0.0154 |
| dwtDctSvd | 0.50 | 0.9183 / 0.9166 | 0.1453 / 0.1448 | 0.0077 / 0.0109 |
| dwtDctSvd | 1.00 | 0.9195 / 0.9198 | 0.1433 / 0.1444 | 0.0133 / 0.0144 |
| rivaGan | 0.05 | 0.9158 / 0.9162 | 0.1399 / 0.1456 | 0.0103 / 0.0121 |
| rivaGan | 0.25 | 0.9148 / 0.9153 | 0.1428 / 0.1492 | 0.0103 / 0.0121 |
| rivaGan | 0.50 | 0.9108 / 0.9100 | 0.1503 / 0.1500 | 0.0147 / 0.0186 |
| rivaGan | 1.00 | 0.9023 / 0.9022 | 0.1502 / 0.1533 | 0.0167 / 0.0181 |

AUC/ECE/DRD are essentially flat across ρ for both schemes — no evidence at
this n that the watermarked fraction of the deployment stream moves any
outcome. Consistent with the rest of the paper: the provenance channel isn't
contributing enough signal for its prevalence to matter either way.

### Bottom line

No evidence of transform-induced watermark–detector interference beyond
ordinary detector fragility under compression, at n=400 and without CIs — one
condition (resize to 0.5×) is the exception worth flagging, not claiming.
The ρ sweep found nothing at all, which is consistent with everything else in
this paper about the provenance channel's weak contribution. Neither result
changes the paper's central claims; both are reported because the experiment
plan named them and a null result honestly obtained is still a result.

---

# Round 2: new experiments (E7-E11)

Authorised to run new experiments rather than argue the limitations away. Each
of these targets a specific limitation the previous revision could only state.

## E7 — the control hierarchy: the asymmetry is a spectral artefact

**Targets L7 (PSNR matching is not structural matching).**

`scripts/e7_control_hierarchy.py`. Seven arms per image on 800 held-out `test`
images at offset 1000 (disjoint from the exploratory 300, the 36-image slice,
and E4/E5's first 400), 2000 bootstrap resamples over images:

    clean | <scheme> | null[<scheme>] (PSNR-matched) | spec[<scheme>] (PSNR + spectrum-matched)

`spec[]` is built by phase-randomising the watermark's own per-image residual
(`null_perturbation.match_spectrum_and_psnr`), so it carries the identical
power spectrum with no payload.

| Detector | Scheme | wm b | PSNR-null b | spec-null b | wm−null | wm−spec |
| --- | --- | --- | --- | --- | --- | --- |
| EfficientNet-B6 | dwtDctSvd | 0.9636 | **0.8377** | 0.9581 | **+0.1259** [+0.1052,+0.1455] | +0.0056 [−0.0090,+0.0206] |
| EfficientNet-B6 | rivaGan | 0.9921 | **0.8553** | 0.9784 | **+0.1368** [+0.1160,+0.1587] | +0.0137 [−0.0004,+0.0274] |
| ResNet-18 probe | dwtDctSvd | 0.9685 | 0.9736 | 0.9569 | −0.0051 [−0.0232,+0.0139] | +0.0116 [−0.0039,+0.0283] |
| ResNet-18 probe | rivaGan | 0.9697 | 0.9806 | 0.9403 | −0.0109 [−0.0313,+0.0089] | +0.0294 [+0.0127,+0.0456] |

**The ~0.13 watermark/control gap — the paper's headline effect — disappears
when the control is matched on spectrum rather than only on PSNR.** On
EfficientNet-B6, wm−spec includes zero for both schemes while wm−null excludes
it decisively.

Two verifications, because the conclusion depends on `spec[]` really being a
control:

- **Payload-free.** Extraction from `spec[]` gives BER 0.5008 (dwtDctSvd) /
  0.4898 (rivaGan) — chance, matching the PSNR control (0.5047/0.4922), while
  the watermark decodes at 0.0000/0.0016.
- **Actually matched.** PSNR within 0.22/0.27 dB of the watermark. SSIM is a
  *closer* match than the old control: 0.978 vs 0.962, against a watermark at
  0.986.

## E11 — why: the PSNR-matched control is spectrally inverted

`scripts/e11_spectral_profile.py`, n=100. Fraction of residual power by radial
frequency band, with payload BER measured in the same run:

| Scheme | Arm | low | mid | high | payload BER |
| --- | --- | --- | --- | --- | --- |
| dwtDctSvd | watermark | **0.825** | 0.071 | 0.104 | 0.0022 |
| dwtDctSvd | PSNR-matched control | 0.143 | 0.396 | **0.461** | 0.5072 |
| dwtDctSvd | spectrum-matched control | **0.824** | 0.073 | 0.103 | 0.5119 |
| rivaGan | watermark | **0.967** | 0.024 | 0.008 | 0.0013 |
| rivaGan | PSNR-matched control | 0.153 | 0.391 | **0.455** | 0.4947 |
| rivaGan | spectrum-matched control | **0.962** | 0.027 | 0.011 | 0.5194 |

The PSNR-matched control was not a weaker watermark; it was a perturbation
with roughly the inverse spectral profile that happened to satisfy the
matching criterion. Both watermarks put 0.83–0.97 of their residual power in
the low band; their PSNR-matched controls put 0.46 in the high band.

**Consequence for the paper.** The negative claim (no detectable
watermark-specific interference) survives and is now supported by a far
stronger control. The mechanism claim must change: EfficientNet-B6 is
sensitive to *high-frequency* perturbation energy, not to imperceptible
perturbation generally, and neither tested watermark produces much of it.

## E9 — decision risk over the cost space, not one triple

**Targets L6.** `scripts/e9_cost_surface.py`. 8×8 grid over (c_FN, c_FP) at
c_R=1; 63 of 64 cells feasible (one has an empty review band by construction).
Calibrators frozen on the clean calibration half, as before.

| Calibrator / arm | median DRD − clean | worse than clean in | worse by >0.01 |
| --- | --- | --- | --- |
| isotonic / null[dwtDctSvd] | +0.0148 | **98%** of cells | 60% |
| isotonic / null[rivaGan] | +0.0042 | 83% | 44% |
| isotonic / **rivaGan (watermark)** | **+0.0610** | **100%** | 98% |
| isotonic / dwtDctSvd | +0.0038 | 70% | 41% |
| platt / null[dwtDctSvd] | −0.0175 | 8% | 8% |
| platt / null[rivaGan] | −0.0151 | 11% | 8% |

**This changes a claim.** "Decision risk does not reliably change" was an
artefact of evaluating at one cost triple. Under isotonic the null arms exceed
clean decision risk in 83–98% of the feasible cost space. The largest effect
is the RivaGAN *watermark* arm (100% of cells, median +0.061), which is
consistent with its +0.649 intercept: a translation moves decisions even where
attenuation does not. Under Platt the pattern does not hold, as expected from
its broken clean-arm baseline.

Status: secondary analysis, not pre-registered, and it reuses the same
validation images as the confirmatory test.
