# Experiment plan

Design constraint: this must be runnable by one person on modest hardware. No
generative model is trained. Every experiment is measurement plus a fusion layer
with a handful of parameters.

## 1. Factors

**Datasets** (face manipulation, standard and citable):

| Dataset | Role |
| --- | --- |
| FaceForensics++ (c23 and c40) | primary; four manipulation types, two compression levels |
| Celeb-DF-v2 | cross-dataset generalisation |
| DFDC-preview | second cross-dataset check, in-the-wild degradation |
| A diffusion-edit set (e.g. face edits via an off-the-shelf inpainting model) | modern manipulation the transform-domain marks are expected to fail on |

Splits are **by source identity**, never by frame. Frame-level splitting inflates
every number in this literature and reviewers check for it.

**Watermark schemes (`S`)** — chosen to span a strength axis, which is what turns
DWT-SVD's weakness into an experimental variable:

| Scheme | Type | Expected role |
| --- | --- | --- |
| DWT-DCT-SVD (`invisible-watermark`) | hand-crafted transform | weak arm; the source design's original choice |
| HiDDeN | learned encoder/decoder | mid |
| StegaStamp | learned, print/display robust | strong under physical-ish transforms |
| SepMark | learned, purpose-built for deepfake settings | strong arm |
| none (`W = 0`) | — | Legacy Media Bypass control |

**Detectors** (≥2 families, so results are not a backbone artifact):

- Xception / EfficientNet-B4 trained on FF++ — the field's standard baselines.
- CLIP ViT-L/14 + LoRA — the source design's detector.
- One robustness-oriented model in the spirit of NTIRE-2026 top entries
  (foundation backbone + degradation training).

**Attack / channel suite `T`** — applied *after* embedding, before detection:

1. JPEG q ∈ {90, 70, 50, 30}
2. H.264 CRF ∈ {23, 28, 35}
3. Resize ×{0.75, 0.5}, centre crop {90%, 75%}
4. Brightness / contrast ±20% (called out because transform-domain marks are
   reported to fail here)
5. Rotation ±5°
6. Gaussian noise, blur
7. **Diffusion regeneration** (img2img at low strength) — the attack that
   erases hand-crafted marks by construction
8. Watermark-removal / overwrite attempt (adversary embeds their own mark)

## 2. Experiments

### E1 — Does interference exist here? (measurement)
Compute `Δ_μ`, `Δ_σ`, `Δ_AUC` for every (scheme × detector × class) cell, on
clean and on each transform class. Deliverable: the interference matrix.

*Pre-registered expectation:* `Δ_AUC < 0` for at least the learned schemes, per
Wu et al. **If `Δ_AUC ≈ 0` everywhere, the pivot's premise fails for images** and
the paper becomes a replication-boundary result — still publishable, but the
framing changes. This branch is written down in advance, not discovered later.

### E2 — Does it propagate into fusion? (the failure)
Fit `F1` (naive fusion) on unwatermarked calibration data, apply to the mixed
stream. Report ECE, Brier, reliability diagrams **split by `W`**, and `ΔECE_W`.
Then apply the cost-derived `(τ_lo, τ_hi)` and report `DRD`.

*Claim under test:* `F1` is calibrated on `W = 0` and miscalibrated on `W = 1`,
so its risk-derived thresholds miss their target risk on watermarked traffic.

### E3 — Does the correction work? (the fix)
Compare `F0 … F5` on identical splits: ECE, `ΔECE_W`, AURC, selective risk at
fixed coverage, `DRD`. Report `β₄` with cluster-bootstrap CIs over source
identity.

*Claim under test:* `F3`/`F5` cut `ΔECE_W` and `DRD` substantially relative to
`F1` at equal or better AUC — i.e. the fix is a calibration fix, not an accuracy
trade.

### E4 — Does it hold under attack?
Repeat E3 per transform class, including diffusion regeneration and watermark
overwrite. Expected and interesting: as the mark degrades, `z_P` correctly loses
strength (that is what the LLR is for), and the fusion should degrade gracefully
toward `F0` rather than confidently wrongly.

### E5 — The realistic mixed regime
Sweep the watermarked fraction `ρ ∈ {0.05, 0.1, 0.25, 0.5, 1.0}`. Report system
selective risk vs `ρ`.

*Purpose:* honesty about the Legacy Media Bypass. Watermark-saturated evaluation
(`ρ = 1`) is the standard flattering setting and is not the deployment regime.
Reporting `ρ = 0.05` alongside it pre-empts the obvious reviewer objection and
is itself a finding worth stating.

### E6 — Ablations
- `z_P` (LLR) vs raw BER as the provenance feature — isolates §2's contribution.
- Raw logit vs softmax probability for `V`.
- Payload length `L ∈ {64, 128, 256}`.
- Ed25519-signed payload vs plain payload under the overwrite attack (E4.8) —
  demonstrates the crypto change does real work rather than being cosmetic.

## 3. Table and figure inventory (what the paper must contain)

| # | Artifact | Source |
| --- | --- | --- |
| T1 | Interference matrix: `Δ_μ`, `Δ_σ`, `Δ_AUC` per scheme × detector | E1 |
| T2 | Fusion comparison `F0–F5`: AUC, ECE, `ΔECE_W`, AURC, `DRD` | E3 |
| T3 | Per-transform breakdown of T2's key rows | E4 |
| T4 | Ablations | E6 |
| T5 | Watermark imperceptibility controls: PSNR / SSIM / clean BER per scheme | setup |
| F1 | Reliability diagrams, split by `W`, `F1` vs `F3` — **the paper's money figure** | E2/E3 |
| F2 | Risk-coverage curves, `F0` / `F1` / `F3` | E3 |
| F3 | Selective risk vs watermarked fraction `ρ` | E5 |
| F4 | `Δ_AUC` vs watermark strength (PSNR-matched) | E1 |

Attention-rollout heatmaps from the source design are **demoted to an appendix
qualitative figure**. They are illustration, not evidence, and treating XAI
output as a result is a standard reviewer target.

## 4. Statistical protocol

- Identity-level splits; cluster bootstrap over identity for all CIs.
- Fusion parameters fit on a calibration split disjoint from test.
- Three seeds minimum; report mean ± CI, never a single run.
- Pre-register E1's failure branch (above) before running it.

## 5. Build order

1. Data pipeline + identity-level splits.
2. Embed/extract harness for the scheme axis; verify PSNR/SSIM/clean-BER (T5).
3. Detector inference harness producing raw logits.
4. Transform suite `T`.
5. **E1.** Decide here whether the premise holds before building the rest.
6. Fusion + calibration + Chow rule; E2, E3.
7. E4, E5, E6.
8. Paper.

Step 5 is a genuine go/no-go gate. Do not write the introduction before it.
