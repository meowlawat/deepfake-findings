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
