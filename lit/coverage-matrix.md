# Coverage Matrix — Proactive/Passive Deepfake Forensics
Compiled 2026-09-06. Sources: web search + abstracts. **Abstracts only — full texts not read.**

## Axis A — Proactive watermarking for deepfake detection
| Work | Venue/Year | Claim |
|---|---|---|
| FakeTagger | 2021 | Originated robust recoverable message embedding for provenance |
| FaceGuard | 2021 | Proactive deepfake detection |
| Proactive Deepfake Defence via Identity Watermarking | WACV 2023 | Identity-bound watermark |
| GAN-based Visible Watermarking | TOMM 2023 | Visible-mark proactive detection |
| SepMark | ACM MM 2023 | One encoder, robust+fragile decoders: source tracing AND detection |
| Robust Identity Perceptual Watermark | 2023 | Against face swapping |
| EditGuard | 2024 | Semi-fragile: detection + localization jointly |
| LampMark | 2024 | Training-free landmark perceptual watermarks |
| FractalForensics | 2025 | Fractal watermarks, detection + localization |
| Big Brother is Watching | 2025 | Learnable hidden face |
| DiffMark | 2025 | Diffusion-based robust watermark |
| DeepForgeSeal | 2025 | Latent semi-fragile, multi-agent adversarial RL |
| Watermarking + Knowledge Distillation | ACM MM 2025 | Proactive robust detection |
| ConMark | Inf. Sci. 2025 | Conditional watermarking; unified provenance+detection+enhancement |
| All in One | 2026 | Landmark-identity WM: detection+localization+tracing |
| GIFGuard | 2026 | Spatiotemporal WM for facial GIFs |
| LAVA | 2026 | Layered audio-visual anti-tampering WM |
| WaterLo | 2026 | Full-image WM, facial-region removal localization, compression module |
| Tamper-Resilient Versatile Watermarking | 2026 | Face content recovery |

**Verdict: saturated.**

## Axis B — Watermark <-> passive detector INTERACTION (the pivot area)
| Work | Venue/Year | Claim | Occupies |
|---|---|---|---|
| AdvMark | IJCAI 2024 | WMs overlap forgery signals & HARM detectors; fine-tune WM adversarially to HELP | "measure harm" + "fix via WM" |
| ConMark | Inf. Sci. 2025 | "First to recognize fundamental distinction between watermarking real vs deepfake images"; harmless WM | priority claim on the insight |
| Robust Detector vs Deep Image WM | PLOS One 2025-12-31 | MBRS/FaceSigns x SRM/UCF/CORE/MINet; degradation under UNKNOWN WM; Feature Dropout + EMA-Xception; NO retraining on WM data | "unknown WM, off-the-shelf, no retrain" |
| The Watermark Shortcut | 2026 | Provenance marking sabotages AUDIO deepfake detection | audio modality |
| Robustness of Audio DD under Audio Watermarking | arXiv 2608.24159 (2026-08) | Systematic audio WM x detector interaction study | **audio benchmark = the image version is the obvious next paper** |

**Verdict: pivot occupied. PLOS One covers the unknown-watermark/no-retrain case I hypothesised was open.**
**Residual: none of these do SCORE-LEVEL FUSION of provenance score P with passive score V.**

## Axis C — Passive detection / ViT+LoRA
NTIRE 2026 challenge (CLIP ViT-L/14 + LoRA r=64 a=128); meta-learned LoRA (2025); DINO dual supervision (2025);
Patch-Discontinuity Mining (2025); Open-Set PEFT + forgery style mixture (2024); "Generalizes Across Benchmarks" (2025).
**Verdict: ViT+LoRA is commodity. Not claimable.**

## Axis D — Calibration / abstention
| Work | Venue/Year | Occupies |
|---|---|---|
| Risk-Regulated Dual-Threshold Interval Selection | ICMR 2026 | class-conditional safety intervals + abstention = the 0.35/0.65 band |
| Towards reliable DD from uncertainty calibration | Visual Intelligence 2025 | calibration |
| Toward Calibrated, Fair, Accurate DD | 2026 | calibration |
| Deepfakebuster | Sci. Rep. 2026 | confidence-calibrated adaptive ensemble |
| Calibrated Deepfake Trust Score (CDTS) | 2026 | post-hoc trust calibration + competence monitor |

**Verdict: occupied.**

## Axis E — Score fusion
Score-Level Fusion Rules for DD (Appl. Sci. 2022); ADD Challenge score fusion (2022);
Evolutionary Multi-Objective Fusion of speech detectors (2026); DeepAgent dual-stream multi-agent fusion (2025);
LAVA 4-layer: temporal restoration -> reliability gate -> confidence-weighted fusion -> calibration (2026).
**Verdict: LAVA's pipeline is structurally the user's flowchart, for audio-visual.**

## Axis F — Watermark robustness / attacks
WAVES benchmark (DwtDctSvd = 0.64 AUC under JPEG); Attack-Resilient WM via Stable Diffusion (2024);
Diffusion-Based Editing Breaks Robust Watermarks (2025); Shallow Diffuse (2024); OptMark (2025); BiSLW (2026).
**Verdict: DWT-SVD documented as obsolete vs generative attacks.**

## Axis G — Provenance standards
C2PA v2.4 (Apr 2026), 6000+ members. Limits: cannot verify content truth (signed photo of a screen showing a deepfake);
metadata stripped by WhatsApp/iMessage/Facebook re-encode; forged manifests demonstrated (Hacker Factor);
consumer phones mostly don't sign. Regulatory: EU AI Act Art.50, California SB 942.
**Verdict: strong MOTIVATION material; unsigned content dominates in the wild.**

## Axis H — Existing surveys / benchmarks (competition for a review paper)
| Work | Venue/Year | Note |
|---|---|---|
| A Survey on Proactive Deepfake Defense: Disruption and Watermarking | **ACM Computing Surveys 2025** | novel taxonomy, visual+audio, 6 eval criteria. **Hard to beat.** |
| DD across image/video/audio + empirical eval | AI Review 2026 | survey WITH experiments |
| Enhancing DD: Proactive Forensics via Digital Watermarking | ScienceDirect 2025 | taxonomy of WM solutions |
| DeepfakeBench | NeurIPS 2023 | unified passive benchmark |
| SoK: Systematization & Benchmarking of Deepfake Detectors | 2024 | unified framework |
| VendorBench-100 | 2026 | 36 models/3 paradigms; **explicitly PASSIVE ONLY — excludes watermarking/provenance** |

**Verdict: narrative survey slot is taken by CSUR 2025. Benchmark slot for the PROACTIVE x PASSIVE INTERACTION is open for images (audio version exists as of Aug 2026).**
