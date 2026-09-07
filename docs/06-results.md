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
