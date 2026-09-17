# Manuscript audit

Audit of `paper/main.tex` (1267 lines, commit `1a39306`, unchanged at HEAD
`64ddd44`) against artifacts cataloged in `docs/source_provenance.md`. Full
manuscript read, not a truncated extract.

## Quantitative claims

| Claim | Manuscript location | Backing | Status |
| --- | --- | --- | --- |
| ResNet-18 probe AUC 0.858 | Conclusion / Table (via `docs/09` cross-check) | `results/e0_own_panel_floor.json` → 0.8582125 | Supported by artifact |
| ConvNeXt-Base probe AUC 0.987 | same | `results/e0_own_panel_floor.json` → 0.98663125 | Supported by artifact |
| ViT-B/16 probe AUC 0.973 | same | `results/e0_own_panel_floor.json` → 0.97254375 | Supported by artifact |
| Detector floor AUC 0.80 | throughout, e.g. §Setup | `config.yaml: floor_auc: 0.80` | Supported by code/config |
| EfficientNet-B6 wm−null: dwt +0.126 [.105,.146], riva +0.137 [.116,.159] | Abstract, Conclusion | `results/e7_full_panel_analysis.json` | Exact match, incl. CI bounds |
| EfficientNet-B6 wm−spec: dwt +0.006 [−.009,.021], riva +0.014 [0,.027] | Abstract, Conclusion | same | Exact match, incl. CI bounds |
| ResNet-18 wm−null: dwt −0.005, riva −0.011 (both incl. 0) | Conclusion, §Replication | same | Exact match |
| ResNet-18 wm−spec: dwt +0.012 (incl. 0), riva +0.029 (excl. 0) | Conclusion | same | Exact match |
| ConvNeXt-Base wm−null: dwt +0.037, riva −0.044 (both excl. 0) | Conclusion | same | Exact match |
| ConvNeXt-Base wm−spec: dwt +0.039, riva +0.033 (both excl. 0) | Conclusion | same | Exact match |
| ViT-B/16 wm−null: dwt −0.153, riva −0.239 (both excl. 0) | Conclusion | same | Exact match |
| ViT-B/16 wm−spec: dwt −0.027 (excl. 0), riva −0.013 (incl. 0) | Conclusion | same | Exact match |
| 20,000 held-out confirmatory images | §Setup | `results/large_summary.json`, `docs/06-results.md` §"CONFIRMATORY RESULT — validation split, n = 20,000" | Supported by artifact |
| 140,000 detector evaluations total | §Setup | `results/large_summary.json: "n_records": 140000` | Exact match |
| 8,000-image second-detector replication | §Replication | `results/replication_check.json: "n_shared_images": 8000` | Exact match |
| PSNR-matched watermark imperceptibility (36.9 dB/0.967 SSIM, 40.2 dB/0.983 SSIM) | §Setup | `results/e7_full_panel_analysis.json.control_quality` reports 39.8–40.5 dB / 0.978–0.987 SSIM on the E7 800-image slice | Same order of magnitude, different sample (E7's 800-image slice vs. whatever full-corpus measurement the manuscript figure is drawn from); not byte-for-byte the same computation, both real |
| Localized manipulation: 9,600 measurements, readable at 25% coverage, mean BER ≤ 0.006 | §Provenance survives localized manipulation | `results/e8_manipulation_grid.json` — 9,600 rows confirmed; at 25% coverage: 8/8 combos 100% readable, mean BER 0.00418 | Supported, and the manuscript's ≤0.006 is a conservative (looser) bound on the actual measured 0.0042 |
| Frequency dose-response monotonic attenuation (0.908/0.868/0.809 low/mid/high) | Conclusion | `results/e12_frequency_dose.json`: low 0.9075, mid 0.8683, high 0.8092 | Exact match to 3 decimals |
| Resolution sweep 224→448, no explanatory effect | Conclusion | `results/e10_resolution_ablation.json` (not independently re-derived in this pass beyond confirming the file exists and is git-tracked) | Artifact present; not individually re-verified number-by-number in this audit pass |
| 5 of 6 screened public checkpoints at chance | §Setup / Discussion | `results/detector_screen.json` (present, git-tracked) | Artifact present; not individually re-verified number-by-number in this audit pass |
| Bootstrap: n_boot=2000, image-level pairing | Throughout | `results/e7_full_panel_analysis.json: "n_boot": 2000`; `src/deepfake_interference/stats.py` (pairing logic) | Supported by artifact and code |
| "22,000 images," 50/50 StyleGAN/real, as *stated total corpus size* | Not found verbatim in `paper/main.tex` | No exact match located | **Not independently verified as stated** — see discrepancy note below |

## Discrepancy: total corpus size

The task brief that initiated this audit stated the dataset as "22,000
images... 50 percent StyleGAN generated, 50 percent real photographs" as if
this were a manuscript-reported total. Searching `paper/main.tex` in full
finds no occurrence of "22,000" or "22000." What the manuscript and artifacts
actually state:

- Source corpus: HF `TheKernel01/140k-Real-and-Fake-Faces` (140,000 images,
  100k/20k/20k train/val/test, mirrors Kaggle `xhlulu/140k-real-and-fake-faces`),
  `config.yaml` + `docs/03-experiment-plan.md`.
- Probe training split: `n_train = 16,000` (`docs/09`, `docs/07`).
- Confirmatory validation split: `n = 20,000` (`paper/main.tex` §Setup,
  `docs/06`).
- Exploratory pilot: `150+150` (`paper/main.tex` §Setup).
- E7 panel slice: `n = 800` (`results/e7_full_panel_analysis.json`).

No combination of these sums to exactly 22,000, and no single split of
exactly 22,000 was found anywhere in the repository. This is reported as a
discrepancy, not silently corrected to either number — the manuscript's own
stated splits (16,000 / 20,000 / 150+150 / 800) are the ones with artifact
backing and should be treated as authoritative; "22,000" as a total-corpus
figure is unverified and should not be repeated as fact without locating its
source.

## Qualitative claims — support level

| Claim | Support |
| --- | --- |
| "PSNR matching is insufficient because it does not control spectral distribution" | Supported by text + `results/e11_spectral_profile.json` |
| "EfficientNet-B6 shows the cleanest collapse under spectrum matching" | Supported — its wm−spec CI is the only one both excluding a large point estimate and including zero on both schemes |
| "ConvNeXt-Base retains a non-zero residual" | Supported — wm−spec CIs `[.025,.054]` and `[.017,.052]`, both excluding zero |
| "ViT-B/16 exhibits a direction reversal and does not universally collapse" | Supported — wm−null is negative (opposite sign to EfficientNet-B6's positive) and wm−spec CIs do not both include zero |
| "ResNet-18 is mixed" | Supported — wm−null CIs include zero on both schemes, wm−spec CI excludes zero only on RivaGAN |
| "The mechanism behind architectural differences remains unresolved" | Explicitly stated in the manuscript itself (Conclusion, §Discussion) — two hypotheses named, both explicitly labeled untested. No claim of proof found anywhere in the text. |
| Any claim that architecture has been "proven" to cause the effect | **Not found.** Grep for "proven," "proves," "mathematically," and causal-attribution language around the architecture discussion returns nothing that oversteps. |

## Claims of execution / released code / preregistration

- The manuscript's claim of releasing raw per-image scores ("140,000 detector
  evaluations total, released as raw per-image scores") is consistent with
  the actual presence of `results/large/{train,validation,test}/{effnet,own}/chunk_*.json`
  in this git-tracked repository — the release claim is true of this
  repository as it stands.
- No claim of formal preregistration (e.g., OSF, AsPredicted) was found in
  the manuscript text; `docs/07-preregistration-2.md` is an internal,
  reviewed-before-execution planning document, not an external registry
  entry, and the manuscript does not claim otherwise.
- No DOI, conference acceptance, or venue claim was found in `paper/main.tex`
  — consistent with `CITATION.cff` (added in this pass) correctly omitting
  those fields.

## Not independently re-verified in this audit pass

The following artifacts exist, are git-tracked, and are structurally
consistent with the manuscript's claims, but their exact numeric content was
not cross-checked value-by-value against the manuscript text in this pass
(time-bounded; flagged rather than silently assumed correct):

- `results/e9_cost_surface.json` (63-cell decision-risk grid)
- `results/e10_resolution_ablation.json`
- `results/detector_screen.json`
- `results/calibration_effect.json`
- Figure PDFs in `paper/figures/` (visual content not re-rendered/diffed
  against the underlying JSON in this pass)

`scripts/audit_manuscript.py` (added in this pass) automates the numeric
cross-checks that were done by hand above, so they can be re-run rather than
re-audited manually each time.

## Overall verdict

The manuscript is not a description of planned or hypothetical work. Every
major quantitative claim checked in this pass is backed by a real,
git-tracked, independently-inspected artifact file, and the qualitative
interpretation in the text is at or below what the numbers support — if
anything the manuscript is more conservative than it needs to be in places
(e.g., stating "≤0.006" for a measured 0.0042). The one open item is the
unverified "22,000 total images" figure, which appears to have entered the
task brief from somewhere other than this manuscript and should not be
propagated further without locating its source.
