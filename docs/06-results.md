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

_Filled from `results/e1_full_run.json`._

## E1 — interference (T1) and the go/no-go gate

_Filled from `results/e1_full_run.json`._

## E2/E3 — fusion and calibration (T2, F1, F2)

_Filled from `results/e2_e3_fusion.json`._

## E4/E5 — transforms and the ρ sweep (T3, F3)

_Filled from `results/e4_e5.json`._

## E6 — ablations (T4)

_Filled from `results/e6_ablations.json`._
