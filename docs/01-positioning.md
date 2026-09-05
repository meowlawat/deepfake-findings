# Positioning, prior work, and the gap

## 1. Why the original framing fails

The original design's headline — "combine a proactive watermark with a passive AI
detector" — is a populated space, not an opening. A reviewer at a competent venue
will name three or four of the following within a minute of reading the abstract:

- **SepMark** (ACM MM 2023) — one embedding, two decoders of differing robustness,
  giving source tracing *and* deepfake detection from a single mark.
- **EditGuard** (CVPR 2024) — semi-fragile watermark performing tamper detection
  and localization simultaneously.
- **LampMark** (ACM MM 2024) — training-free landmark perceptual watermarks for
  proactive deepfake detection.
- **FractalForensics** (2025) — fractal watermarks for proactive detection and
  localization.
- **All in One** (CVPR 2026) — landmark-identity watermark unifying detection,
  localization and source tracing.
- **LAVA** (ACM MM 2026) — layered audio-visual anti-tampering watermarking for
  detection and localization.

Stating "we combine watermarking with a ViT" against that backdrop produces a
systems-integration report, not a contribution. The integration is the *setting*.
The contribution has to be something learned inside it.

## 2. The finding that both threatens and rescues the design

**Wu, Liao, Ou, Liu, Qin. "Are Watermarks Bugs for Deepfake Detectors? Rethinking
Proactive Forensics." IJCAI 2024.** Read in full-text; abstract quoted verbatim:

> "we argue that current watermarking models, originally devised for genuine
> images, may harm the deployed Deepfake detectors when directly applied to
> forged images, since the watermarks are prone to overlap with the forgery
> signals used for detection."

Their remedy, **AdvMark**, fine-tunes robust watermarking into *adversarial*
watermarking so the mark pushes detectors the right way instead of the wrong way.

The same pathology is reported independently in audio: **"The Watermark Shortcut:
How Provenance Marking Sabotages Audio Deepfake Detection"** (Müller & Debus,
arXiv 2606.23335) — detectors latch onto the watermark as a shortcut for
"synthetic", so watermarked genuine speech gets flagged as fake and unmarked
fakes slip through. Cross-modality replication of an effect is strong evidence
the effect is structural, not an artifact of one image pipeline.

**Consequence for the original design.** `V` is computed on watermarked media.
The watermark contaminates the very score being fused with the provenance score
derived from that same watermark. `P` and `V` are not independent evidence.
The logistic fusion, and every threshold derived from its output, inherits that
dependence.

## 3. What is *not* occupied

Three neighbours bound the gap. None of them close it.

| Prior work | What it does | What it does not do |
| --- | --- | --- |
| Wu et al., IJCAI 2024 (AdvMark) | Establishes watermark-detector interference; fixes it by fine-tuning the **watermark** | Single detector. No fusion. No calibration analysis. No decision rule. |
| Guo et al., *AI-generated Image Detection: Passive or Watermark?* (arXiv 2411.13553) | Head-to-head benchmark: 5 passive detectors vs 4 watermark detectors, 8 common + 3 adversarial perturbations; concludes watermark-based detectors consistently win | Explicitly a **comparison**, not a fusion. Does not study whether watermarking degrades the passive detectors it benchmarks. |
| *Enhancing Deepfake Detection Reliability via Risk-Regulated Dual-Threshold Interval Selection*, ICMR 2026 | Risk-regulated dual thresholds with an abstention interval; criticises softmax probabilities as unreliable under perturbation and OOD | Single detector. No provenance channel. No interference. |

The intersection — *interference-aware, calibration-preserving fusion of
provenance and passive evidence, with risk-derived abstention that stays valid
under that interference* — is unoccupied as of this search.

**Gap statement (paper's thesis):**

> Chow's optimal reject rule is valid only for calibrated posteriors.
> Watermark-detector interference systematically miscalibrates the fused
> posterior on watermarked media — precisely the media the system exists to
> protect. We quantify that miscalibration across watermark schemes and
> detectors, show naive score fusion inherits it, and give an interference-aware
> fusion that restores calibration and hence the validity of risk-derived
> decision thresholds.

This is a negative-result-into-positive-contribution arc. It is cheap (no
generative model to train — a measurement study plus a small fusion layer), and
defensible because it *builds on* a published finding instead of colliding with
one.

## 4. Design changes this pivot forces

| Original element | Problem | Change |
| --- | --- | --- |
| DWT-SVD watermark | Hand-crafted transform marks are weak under compression, brightness/contrast, rotation, and are largely erased by diffusion regeneration. If BER is noise under deepfake transforms, `P` is noise on the cases that matter. | Keep it, but as the **weak arm of a comparison axis**, not the system's watermark. Add at least one learned scheme (HiDDeN / StegaStamp / SepMark). Watermark strength becomes an independent variable, which turns a weakness into an experiment. |
| AES-256 | Provides confidentiality only. Does not prevent removal, and does not prevent an attacker embedding their own mark — the stated "inject fake watermark" threat is untouched by a cipher. Symmetric key shared with every verifier is a key every attacker has. | Ed25519 signature over (content hash ‖ payload); watermark carries the signature/key-ID. Verification becomes public, forgery becomes hard. Retain AES only where payload confidentiality is genuinely required, and state the key-distribution model. |
| "Learned meta-classifier" | Overclaims a logistic regression over two scalars; invites attack on the language | Reframe as a deliberately **interpretable, calibrated** fusion rule. Interpretability is the point: the interference shows up as a readable coefficient. |
| Fixed 0.35/0.65 "dynamic" band | Contradiction in terms; arbitrary constants | Derive the band from an explicit cost model (Chow's rule). See `docs/02-method.md` §5. |
| Inconclusive band | Reads as an accuracy escape hatch | Mandatory risk-coverage curves. Selective prediction is legitimate only when the accuracy/coverage tradeoff is reported. |
| ViT + LoRA | Not novel; CLIP ViT-L/14 + LoRA is standard, and known weak cross-manipulation | Fine as a component. Claim nothing for it. Use ≥2 detector families so results are not an artifact of one backbone. |
| Legacy Media Bypass | Unwatermarked media uses `V` alone, i.e. most real traffic | Make the watermarked fraction ρ an explicit experimental sweep. |

## 5. Citation verification ledger

**Rule: nothing enters `paper/refs.bib` until it is VERIFIED here.** Depth of
reading is recorded, because "the abstract says so" is not the same as "the paper
shows so".

| Work | ID | Status | Depth read |
| --- | --- | --- | --- |
| Wu et al., Are Watermarks Bugs for Deepfake Detectors? (IJCAI 2024) | ijcai.org/proceedings/2024/0673 | VERIFIED | Title/authors/abstract/intro read from PDF |
| An et al., WAVES: Benchmarking the Robustness of Image Watermarks (ICML 2024) | arXiv 2401.08573 | VERIFIED (existence, authors, venue) | Abstract only |
| Müller & Debus, The Watermark Shortcut (audio) | arXiv 2606.23335 | VERIFIED | Abstract only |
| Wu et al., All in One (CVPR 2026) | arXiv 2602.23523 | VERIFIED | Abstract only |
| Zeng et al., LAVA (ACM MM 2026) | arXiv 2604.23957 | VERIFIED | Abstract only |
| Hopf et al., Robust Deepfake Detection, NTIRE 2026 Challenge Report | arXiv 2604.24163 | VERIFIED | Abstract only |
| Guo et al., AI-generated Image Detection: Passive or Watermark? | arXiv 2411.13553 | VERIFIED | Abstract only |
| SepMark | arXiv 2305.06321 | VERIFIED (ID resolves) | Search result only — read before citing |
| FractalForensics | arXiv 2504.09451 | VERIFIED (ID resolves) | Search result only — read before citing |
| LampMark | arXiv 2411.17209 | VERIFIED (ID resolves) | Search result only — read before citing |
| Risk-Regulated Dual-Threshold Interval Selection (ICMR 2026) | 10.1145/3805622.3810714 | VERIFIED (DOI, venue, pages 2115-2123) | Partial abstract; ACM DL returned 403 — obtain full text |
| EditGuard | — | UNVERIFIED | Not checked this session |
| WaveGuard | arXiv 2505.08614 | UNVERIFIED | Not checked this session |
| DiffMark | arXiv 2507.01428 | UNVERIFIED | Not checked this session |
| GIFGuard | arXiv 2604.26519 | UNVERIFIED | Surfaced in search only |
| Full-Defense Framework (FITEE) | 10.1631/FITEE.2401012 | UNVERIFIED | Not checked this session |
| Diffusion-Based Editing Breaks Robust Watermarks | arXiv 2510.05978 | UNVERIFIED | Not checked this session |
| Attack-Resilient Watermarking / regeneration attacks | arXiv 2401.04247 | UNVERIFIED | Not checked this session |

### Numeric claims under quarantine

- "DwtDctSvd achieves 0.64 AUC under JPEG compression in WAVES" — **NOT
  CONFIRMED.** The WAVES abstract does not contain per-scheme AUCs. Do not cite
  this number until it is read out of the paper's own tables. It is load-bearing
  for the argument that DWT-SVD is too weak, so it must be either sourced or
  replaced by our own measurement.
- "CLIP ViT-L/14 + LoRA, r=64, alpha=128, was an NTIRE 2026 entry" — challenge
  report exists and states top methods used large foundation models, ensembles
  and degradation training. The specific rank/hyperparameters are unconfirmed.
