# Experiment plan

**Status: v1 fast-track, 10-day budget.** Hardware: RTX 3050 6GB local +
Kaggle free-tier T4 (~30h/week, published quota) as overflow. Deadline forces
three hard constraints, in order of how much they cut:

1. **No gated datasets.** FaceForensics++, Celeb-DF, DFDC all require an access
   request that alone can consume the entire budget. v1 uses only datasets
   downloadable instantly, no approval step, no waiting.
2. **Zero training.** Every watermark embedder/extractor and every detector is
   used pretrained, as shipped. This is inference-only work, which is exactly
   why the hardware above is sufficient — there is no backprop in the core loop.
   Fitting the fusion logistic regression on a few thousand scalar pairs is not
   "training" in the sense that matters here; it runs on CPU in seconds.
3. **Narrower matrix.** One dataset, two watermark schemes, two detector
   families, a reduced transform set. The full matrix from the original plan
   (§6, "extensions") is preserved as the stated follow-on, not deleted — a
   journal revision or a second paper builds on v1 by widening it.

This is a genuine scope cut, not a repackaging of the old plan. Say so in the
paper's limitations section, don't imply otherwise.

## 0. Tooling — verify before depending on

Everything below is a stated plan, not yet confirmed by running it. Each item
carries what still needs checking, per the repo's citation-verification
discipline (`docs/01`) extended to tooling.

| Component | Candidate | Verify before committing |
| --- | --- | --- |
| Watermark library | `invisible-watermark` 0.2.0 (pip) | **VERIFIED, this session.** `DwtDctSvd` embed/extract round-trips with zero setup. `RivaGan`'s encoder/decoder ship as ONNX weights *inside the pip package itself* (`rivagan_{encoder,decoder}.onnx`) — no separate download, no training — but the package only loads them if `onnxruntime` is installed; add it to `requirements.txt` explicitly, it is not pulled in automatically. |
| Dataset | HF `TheKernel01/140k-Real-and-Fake-Faces` (mirror of Kaggle `xhlulu/140k-real-and-fake-faces`) | **VERIFIED and fetched.** The Kaggle account turned out not to be needed at all: the same dataset is mirrored on the HF Hub — 140k images (100k train / 20k val / 20k test), `real`/`fake` labels, plus a `generator` field distinguishing Real from StyleGAN, license `cc`. `scripts/fetch_dataset.py` streams a balanced subset rather than pulling the full ~4GB. **Still whole-image GAN synthesis, not face-swap/reenactment deepfakes — R8's framing constraint is unchanged by the easier access.** |
| Dataset (stretch) | Kaggle `manjilkarki/deepfake-and-real-images` | Same access limitation. If genuinely derived from face-swap manipulation (not GAN synthesis), this is the better instant-access option for calling the result "deepfake detection" without qualification. Confirm provenance and license before use — see R9. |
| Detector A | `Wvolf/ViT_Deepfake_Detection` (ViT) | **VERIFIED, this session.** Loads via `transformers.AutoModelForImageClassification`, produces raw 2-class logits (`id2label: {0: Real, 1: Fake}`). Apache-family HF hosting, no gate. **Leakage: UNRESOLVED** — model card states only "trained by [author] ... to detect deepfake images," names no dataset. Cannot confirm it wasn't trained on (a close relative of) the eval set. See R14. |
| Detector B | `Skullly/DeepFake-EN-B6` (EfficientNet-B6) | **VERIFIED, this session** — and it's the fix to a real gap: every ViT candidate the plan originally listed (`dima806`, `Wvolf`, `prithivMLmods`) shares one backbone family, which fails this table's own "genuinely different architecture" requirement. This one is a real CNN. Loads cleanly, produces raw 2-class logits (`id2label: {0: f, 1: r}` — note the reversed index order relative to Detector A; code must resolve the fake-class index from `id2label`, never assume index 1). **Leakage: WORSE than unresolved** — card reports 99.89% eval accuracy on an explicitly "unknown dataset." That number is itself a leakage red flag, not a reassurance. See R14. |
| Diffusion regeneration attack (stretch, E4) | A small pretrained img2img model via `diffusers`, run on Kaggle T4 | Only attempted if E1–E3 finish with days to spare. This is the single most interesting attack (erases hand-crafted marks by construction) and the first thing cut under time pressure |

**Do not write a single results sentence using a component from this table
until its "verify" column is actually checked.** Four of six rows are now
verified; the two dataset rows still need the Kaggle account that lives on
the local machine, and both detector rows carry an unresolved leakage risk
that changes what E0's floor check can actually prove — see R14.

## 1. Factors (v1)

**Dataset:** `140k-real-and-fake-faces`, or the manjilkarki set if it verifies
as genuine face-manipulation content — pick whichever verifies first, do not
spend more than one day deciding.

**Splits:** no identity metadata exists for GAN-synthesized faces, so
identity-level splitting (the standard in the FF++/Celeb-DF literature) is not
available here. Split by file/generation-seed where the dataset provides it,
otherwise a stratified random split with a fixed seed. **State this explicitly
as a limitation** — it is a real reduction in rigor relative to the original
plan's identity-level splits, not a detail to gloss over.

**Watermark schemes (`S`):**

| Scheme | Type | Role |
| --- | --- | --- |
| DwtDctSvd | hand-crafted transform | weak arm — the source design's original choice |
| RivaGan | learned encoder/decoder, pretrained | strong arm |
| `∅` null perturbation | payload-free noise, PSNR/SSIM-matched per image | **control arm** — separates watermark-specific interference from generic perturbation brittleness (`docs/02` §3.1). Not optional |
| none (`W = 0`) | — | Legacy Media Bypass control |

**The `∅` arm is not a nice-to-have.** Without it `Δ_AUC < 0` is equally explained
by "detectors are brittle to any imperceptible perturbation", which is the null
hypothesis a zero-shot detector trained on clean images makes *likely*, not
remote. It is cheap — the PSNR/SSIM matching machinery is already needed for T5 —
and it converts E1 from a result a reviewer can dismiss into one they cannot.

Two schemes, not five. The strength-axis argument in `docs/01` §4 only needs
one point on each side of the hand-crafted/learned divide to be made; it does
not need five points on the curve. Widening this axis is the first item in the
extension list (§6).

**Detectors:** two pretrained families (Detector A, Detector B from §0), used
zero-shot — no fine-tuning on our data. This is a real reduction from "trained
to convergence on FF++" and must be named as such: v1 measures interference
against *zero-shot* passive detectors, which is a legitimate and citable
setting (it is exactly Guo et al.'s setting) but a different claim than
measuring it against a purpose-trained detector.

**Transform suite `T`** — reduced from 8 classes to the 3 that are cheap,
fast, and already known from the watermarking-robustness literature to matter:

1. JPEG at q ∈ {90, 70, 50} — the standard first stress test, and the one
   WAVES already reports transform-domain marks struggling under.
2. Resize ×{0.75, 0.5}.
3. Brightness/contrast ±20% — called out because transform-domain marks are
   reported to fail here specifically.

Diffusion regeneration, rotation, crop, Gaussian noise, and the
watermark-overwrite attack move to the extension list (§6). Cutting them costs
real coverage — a reviewer may reasonably ask why regeneration (the attack
that motivates the strength axis in the first place) isn't tested. The honest
answer, stated in limitations, is the calendar.

## 2. Experiments (v1)

Same logical structure as the original plan, narrower factors.

### E0 — Detector floor check (precondition, days 1–2)

Before any interference measurement, confirm each detector clears a **baseline
AUC floor of 0.80 at `W = 0`** on this dataset. A detector near chance makes
`Δ_AUC` a measurement of noise, and the E1 gate cannot tell that apart from a
genuine null.

This runs in the day 1–2 tooling window, **not** at the day 3–4 gate, and the
reason is scheduling: if a detector fails the floor, the response is to swap
models, and a swap is only affordable while days 1–2 are still open. Discovering
it at the gate costs the swap and the gate together.

If neither candidate detector clears 0.80, that is itself a finding about
zero-shot detectors on this dataset — record it, then widen the candidate pool
before proceeding.

### E1 — Does interference exist here? (go/no-go gate, days 3–4)
Compute `Δ_μ`, `Δ_σ`, `Δ_AUC` per (scheme × detector × class), clean and per
transform — **including the `∅` null arm**, and report
`Δ_AUC_net = Δ_AUC(s) − Δ_AUC(∅)` as the headline quantity (`docs/02` §3.1).

**This gate is unchanged and non-negotiable under time pressure:** if
`Δ_AUC_net ≈ 0` everywhere — whether because nothing shifts, or because the
watermark arms shift no more than the null arm — stop and re-scope the paper as a
bounded replication result before spending the remaining week building on a
premise that didn't hold. Note the gate now tests the *net* quantity: a large
`Δ_AUC` that the null arm reproduces is a failed gate, not a passed one. A null result discovered on day 9 is a wasted week; discovered on day 4
it is still a paper (§ "fallback framing" in `docs/04` R1).

### E2 — Does it propagate into fusion? (days 5–6)
Fit `F1` on unwatermarked calibration data, evaluate on the mixed stream.
Reliability diagrams split by `W`, `ΔECE_W`, then apply cost-derived
`(τ_lo, τ_hi)` and report `DRD`. Unchanged from the original plan — this
experiment is cheap regardless of matrix size, since it operates on scalar
scores, not raw media.

### E3 — Does the correction work? (days 5–6, same window as E2)
Compare `F0–F5` (`docs/02` §4). Bootstrap CIs now over **samples**, not source
identity — the dataset has no identity metadata, so this is a weaker
guarantee than the original plan's identity-clustered bootstrap. Say so.

### E4 — Robustness under the reduced transform set (day 7)
Repeat E3 per transform class from §1. Diffusion regeneration only if time
remains (see §0's tooling note).

### E5 — Watermarked-fraction sweep (day 7, same window)
`ρ ∈ {0.05, 0.25, 0.5, 1.0}` — one fewer point than the original plan, same
purpose: report the realistic mixed regime honestly, not just the
watermark-saturated one.

### E6 — Ablations (day 8)
- `z_P` (LLR) vs raw BER as the provenance feature.
- Raw logit vs softmax probability for `V`.
- Nonlinear fuser (small MLP or gradient-boosted trees) as a control, per
  `docs/04` R4 — shows the calibration gap isn't fixed by a fancier fuser,
  which pre-empts the obvious reviewer objection to using logistic regression.

**Cut from v1, moved to extension list:** payload-length sweep, and the
Ed25519-vs-plain-payload forgery ablation. Both require the overwrite attack
(§1's cut transform), so they fall out together. The Ed25519 design change
itself stays in `docs/02` as a stated method contribution — it does not need
an experiment to be a correct fix to a stated flaw, only to be *evaluated*,
and that evaluation is deferred.

## 3. Table and figure inventory (v1)

Same artifacts as the original plan, same numbering, sourced from the
narrower matrix:

| # | Artifact | Source |
| --- | --- | --- |
| T1 | Interference matrix: `Δ_μ`, `Δ_σ`, `Δ_AUC`, `Δ_AUC_net`, 3 arms (2 schemes + `∅` null) × 2 detectors | E1 |
| T2 | Fusion comparison `F0–F5` | E3 |
| T3 | Per-transform breakdown (3 transform classes) | E4 |
| T4 | Ablations | E6 |
| T5 | Watermark imperceptibility controls (PSNR/SSIM/clean BER, 2 schemes) | setup |
| F1 | Reliability diagrams split by `W`, `F1` vs `F3` — money figure | E2/E3 |
| F2 | Risk-coverage curves | E3 |
| F3 | Selective risk vs `ρ` | E5 |

`F4` (`Δ_AUC` vs watermark strength across a PSNR-matched sweep) needs more
than two schemes to be a curve rather than a two-point line — moved to
extensions.

## 4. Statistical protocol (v1)

- Sample-level bootstrap for CIs (identity-level unavailable — see §1).
- Fusion parameters fit on a calibration split disjoint from test.
- Three seeds minimum on anything stochastic; the fusion fit itself is
  deterministic given a split.
- E1's go/no-go decision is pre-registered above, before it is run.

## 5. Build order (10 days)

| Days | Work |
| --- | --- |
| 1–2 | Verify §0's tooling table. Data pipeline. Embed/extract harness for both schemes **plus the `∅` null-perturbation generator, PSNR/SSIM-matched per image**; confirm PSNR/SSIM/clean-BER (T5). Detector inference harness producing raw logits. **E0 detector floor check — swap models now if either misses 0.80.** |
| 3–4 | **E1**, including the `∅` arm. Go/no-go on `Δ_AUC_net`. Do not proceed to day 5 on a premise that hasn't cleared this gate. |
| 5–6 | Fusion + calibration + Chow rule; E2, E3. |
| 7 | E4, E5. |
| 8 | E6. Diffusion regeneration only if ahead of schedule. |
| 9–10 | Writing. Limitations section written honestly against §1's cuts, not defensively. |

## 6. Extensions (explicitly deferred, not abandoned)

This is the original multi-week plan, kept as the stated next step rather than
deleted, per the "merge" resolution — v1 ships as a real, narrow, submittable
paper; this is what a revision or a follow-up widens toward once time and
dataset access allow:

- Gated datasets: FaceForensics++ (true face-swap/reenactment manipulations,
  the thing "deepfake detection" usually means), Celeb-DF, DFDC — once access
  requests clear.
- Full scheme axis: HiDDeN, StegaStamp, SepMark alongside DwtDctSvd/RivaGan.
- A third detector family, and at least one trained-not-zero-shot detector for
  comparison against the zero-shot setting.
- Full transform suite: rotation, crop, Gaussian noise/blur, diffusion
  regeneration, watermark-overwrite forgery attempt.
- Identity-level splits and identity-clustered bootstrap.
- Payload-length sweep and the Ed25519-vs-plain forgery ablation.
- `F4` (interference vs. watermark strength as an actual curve).
