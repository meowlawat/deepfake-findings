# Source provenance

Produced by an audit pass on 2026-09-17, against commit `64ddd44` on `main`.
Every row below was checked by opening the file and, where the artifact is a
number that also appears in `paper/main.tex`, diffing the two. Evidence
levels:

- **A** — Raw experimental artifact (a result file produced by running a
  script in this repo against real data/models).
- **B** — Executable generated result (derived from A by a second script,
  e.g. an aggregation or merge step).
- **C** — Git-tracked source (code, config, manuscript source — not itself a
  measurement).
- **D** — Manuscript-reported value with no artifact file located to back it.
- **E** — Conversation/planning note (a doc describing intent or status, not
  a measurement).
- **F** — Unverified (name suggests relevance; contents not confirmed, or
  claimed but not found).

## Experiment result artifacts

| Artifact | Path | Type | Git tracked | Experiment | Evidence | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| E0 floor check (3-detector panel) | `results/e0_own_panel_floor.json` | JSON | Yes | E0 | A | Backs the 3 disclosed-probe AUCs (0.8582, 0.9866, 0.9725) quoted in the "locked" spec and in `paper/main.tex`/`docs/09`. n=800, split=test, offset=1000. |
| E7 full-panel evidence-transfer analysis | `results/e7_full_panel_analysis.json` | JSON | Yes | E7 | A | Backs all 16 wm−null / wm−spec point estimates + 95% bootstrap CIs (n_boot=2000, n=800) quoted in the spec and paper. Every one of the 16 values in the spec matches this file to 3+ decimals before rounding. |
| E8 manipulation grid | `results/e8_manipulation_grid.json` | JSON | Yes | E8 | A | 9,600 rows confirmed (200 images × 6 coverage levels × 4 families × 2 schemes). At target_area=0.25: all 8 (scheme×family) combinations 100% readable, mean BER=0.00418, consistent with the paper's "mean BER ≤ 0.006" at that coverage. |
| E9 cost surface | `results/e9_cost_surface.json` | JSON | Yes | E9 | A | 8×8 cost grid, referenced in `docs/06-results.md` decision-risk section. |
| E10 resolution ablation | `results/e10_resolution_ablation.json` | JSON | Yes | E10 | A | Not summarized in `docs/06` (gap noted below); present and git-tracked. |
| E11 spectral profile | `results/e11_spectral_profile.json` | JSON | Yes | E11 | A | Backs the "watermark residual power concentrated in the low band, PSNR-matched control inverted into the high band" claim. |
| E12 frequency dose-response | `results/e12_frequency_dose.json` | JSON | Yes | E12 | A | n=400, n_boot=2000, four dose arms (watermark/low/mid/high). |
| Calibration effect | `results/calibration_effect.json` | JSON | Yes | E2/E3 | A | Backs the Platt/isotonic ECE table. |
| Detector screen | `results/detector_screen.json` | JSON | Yes | pre-E0 | A | Community-detector screening (5 of 6 at chance), referenced in `docs/06`. |
| E1 full run / timing tests | `results/e1_full_run.json`, `e1_timing_test*.json` | JSON | Yes | E1 | A | Early go/no-go gate; superseded narratively by later corrections but kept as historical evidence (repo rule: never delete). |
| E4/E5 transform + rho sweep | `results/e4_e5_test400.json` | JSON | Yes | E4/E5 | A | n=400, transform robustness. |
| Confirmatory large run (per-chunk scores) | `results/large/{train,validation,test}/{effnet,own}/chunk_*.json` | JSON, 160 files | Yes | confirmatory | A | Raw per-image detector scores backing the 20,000-image confirmatory split and the 8,000-image replication slice. |
| Large-run summary | `results/large_summary.json` | JSON | Yes | confirmatory | B | Aggregated from `results/large/*` by `scripts/aggregate_large.py`. `n_records: 140000` matches the paper's "140,000 detector evaluations total" exactly. |
| Replication check | `results/replication_check.json` | JSON | Yes | replication | B | n_shared_images=8000, produced by `scripts/replication_check.py` from the large-run chunks. |
| E7 chunk checkpoints | `results/e7_control_hierarchy/`, `results/e7_full_panel/`, `results/e7_newprobes/` | JSON, many files | Yes | E7 | A | Intermediate/resumable chunk state behind the E7 analysis file above. |

## Model / probe artifacts

| Artifact | Path | Type | Git tracked | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| ResNet-18 linear probe | `models/own_detector.json` | JSON (coef+intercept, not a binary checkpoint) | Yes | A | `n_train: 16000`, 512-dim `coef`, frozen-backbone logistic head. This is "own" in E0/E7, reported as ResNet-18. |
| ConvNeXt-Base linear probe | `models/own_detector_convnext-base.json` | JSON | Yes | A | Same structure, larger `coef`. |
| ViT-B/16 linear probe | `models/own_detector_vit-b16.json` | JSON | Yes | A | Same structure. |
| Frozen backbone feature cache | `cache/features/` | — | No (`.gitignore`'d) | — | Not present on this machine currently; regenerable per `docs/09` (`{backbone}_{split}_{n}.npz`, keyed cache). Its absence does not affect the artifacts above, which are already-computed outputs, not intermediate cache. |
| Public detector checkpoints (ViT, EfficientNet-B6) | HF Hub (`Wvolf/ViT_Deepfake_Detection`, `Skullly/DeepFake-EN-B6`) | External | N/A | C (config-referenced) | Not vendored in-repo (correctly — these are third-party weights). `config.yaml` records the exact identifiers. Leakage status for both is explicitly flagged UNRESOLVED in `docs/03-experiment-plan.md` — this is disclosed in the paper's limitations, not glossed over. |

## Code / manuscript

| Artifact | Path | Type | Git tracked | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| Manuscript source | `paper/main.tex` | LaTeX | Yes | C | Title/authors match the spec exactly. |
| Compiled PDF | `paper/main.pdf` | PDF | Yes | C | Committed in the **same commit** (`1a39306`) as the current `main.tex` — no drift between source and compiled artifact as of that commit. HEAD (`64ddd44`) is one commit later and does not touch `paper/`. Could not be independently rebuilt in this session (no LaTeX toolchain available and no admin rights to install one — see Section 28 note in the integrity report). |
| Pipeline source | `src/deepfake_interference/*.py` | Python | Yes | C | Watermarking, crypto-binding, metrics, transforms, fusion, stats, pipeline. |
| Analysis scripts | `scripts/e0_*.py` … `scripts/e12_*.py`, `analyze_e7.py`, `aggregate_large.py`, `replication_check.py` | Python | Yes | C | The actual code that produced every A/B artifact above. |
| Test suite | `tests/*.py` | Python | Yes | C | 38 tests; **independently re-run in this session after installing missing deps (`scikit-image`, `opencv-python-headless`, `onnxruntime`) — 38/38 pass.** This is genuine re-execution, not a claim taken on faith. |
| Config | `config.yaml`, `e4e5_config.yaml` | YAML | Yes | C | No absolute personal paths found (`git grep` clean). |

## Documentation / status notes

| Artifact | Path | Evidence | Notes |
| --- | --- | --- | --- |
| CLI handoff context | `docs/09-cli-handoff-context.md` | E, but corroborated | Every specific number it cites was independently checked against the A-level artifacts above and matched. Treated as the most current narrative status doc. |
| Running results log | `docs/06-results.md` | E/B mixed | Self-declared gap: "stops after E9/E11; does not cover E10, E12, or the 4-detector panel expansion" — confirmed true by inspection. `paper/main.tex` and `docs/09` are authoritative over this file for anything after E9. |
| Top-level README (pre-audit) | `README.md` | F (stale) | As found, stated "no experiment has been run on real data yet" — this was true when written but is now **false**: 60+ commits and the entire E0–E12 experimental record postdate it. Corrected in this pass (see commit log). |
| Positioning / method / risks / plan docs | `docs/00`–`04` | E | Design-stage planning docs from before the pivot to the current empirical result; still accurate as *background*, not as current status. |
| Preregistration | `docs/07-preregistration-2.md` | E | Not audited line-by-line in this pass; referenced by `docs/09` as reviewed-before-execution material for the panel expansion. |

## Numbers checked against artifacts (the "locked" figures)

Every quantitative value in the task brief's Section 6 was independently
located in the repository and matched against a real artifact file, not
taken on the brief's word:

- 3 disclosed-probe AUCs: exact match, `results/e0_own_panel_floor.json`.
- 16 wm−null / wm−spec deltas (4 detectors × 2 schemes × 2 comparisons):
  exact match, `results/e7_full_panel_analysis.json`.
- Detector floor 0.80: exact match, `config.yaml` and `results/e0_*`.
- Two watermark schemes (DWT-DCT-SVD, RivaGAN): exact match, `config.yaml`.
- 20,000-image confirmatory split: exact match, `docs/06-results.md`,
  `results/large_summary.json` (`n_records: 140000` = 20,000 × 7 arms across
  both detectors, consistent).
- Localized-manipulation claim (25% coverage, all family/scheme combos
  readable, mean BER ≤ 0.006): exact match, `results/e8_manipulation_grid.json`
  (measured mean at 25% = 0.00418).

One figure in the brief does **not** have a located exact match:

- **"22,000 images" / "50% StyleGAN / 50% real photographs" as the stated
  total corpus size** — not found verbatim anywhere in `paper/main.tex`,
  `docs/`, or the result JSON files. What is confirmed: `n_train=16,000`
  (probe training split), `n=20,000` (confirmatory validation split),
  `n=8,000` (second-detector replication subset of validation), exploratory
  `150+150`, source dataset is HF `TheKernel01/140k-Real-and-Fake-Faces`
  (140k total, 100k/20k/20k train/val/test). No single figure of exactly
  22,000 was found. This is flagged, not silently corrected or silently
  repeated — see `docs/manuscript_audit.md`.
