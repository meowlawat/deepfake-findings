# Research integrity report

Final audit pass, 2026-09-17, against `E:\deepfake-findings`, commit
`64ddd44` on `main` (working tree clean, tracking `origin/main`,
`origin = https://github.com/meowlawat/deepfake-findings.git`).

## Which results are independently verified?

"Independently verified" here means: located in a git-tracked file in this
repository, opened, and its numeric content compared against the claim.

- All 3 disclosed-probe baseline AUCs (ResNet-18 0.858, ConvNeXt-Base 0.987,
  ViT-B/16 0.973) — `results/e0_own_panel_floor.json`.
- All 16 evidence-transfer deltas (4 detectors x 2 schemes x {wm-null,
  wm-spec}) with their 95% bootstrap CIs — `results/e7_full_panel_analysis.json`.
- E8 localized-manipulation claim (9,600 measurements; 100% readable at 25%
  coverage across all 8 scheme/family combinations; mean BER 0.0042, under
  the manuscript's stated <=0.006) — `results/e8_manipulation_grid.json`,
  recomputed directly from the raw rows in this session.
- E12 frequency dose-response slopes (0.908/0.868/0.809 low/mid/high) —
  `results/e12_frequency_dose.json`, exact match to 3 decimals.
- 140,000 total detector evaluations — `results/large_summary.json`, exact
  match.
- 8,000-image second-detector replication — `results/replication_check.json`,
  exact match.
- Detector floor 0.80, both watermark scheme names, no absolute personal
  paths in config/code — `config.yaml`, `git grep`.
- All four git commit hashes named in the task brief (`1a39306`, `22909f6`,
  `2e4f14a`, `75d7191`) exist in `git log --all` and were inspected.

Full per-claim table: `docs/manuscript_audit.md`.

## Which results exist only in the manuscript (no artifact located)?

- The "22,000 total images, 50/50 StyleGAN/real" figure. Not found verbatim
  anywhere in `paper/main.tex`, `docs/`, or `results/`. The splits that *are*
  documented and backed (16,000 train / 20,000 confirmatory / 150+150
  exploratory / 800 panel / 8,000 replication) do not sum to or match this
  figure. Flagged in `docs/manuscript_audit.md`, not silently resolved.
- E9 (63-cell cost-risk grid), E10 (resolution ablation), and
  `detector_screen.json`'s individual per-model AUCs: artifact files exist
  and are git-tracked, but their individual values were not cross-checked
  number-by-number against the manuscript text in this pass (time-bounded
  scope decision, stated explicitly rather than silently skipped).

## Which checkpoints exist?

Three linear-probe checkpoints as JSON (coefficient vector + intercept, not
binary model weights, because the backbone is frozen and only the logistic
head is trained): `models/own_detector.json` (ResNet-18, n_train=16,000),
`models/own_detector_convnext-base.json`, `models/own_detector_vit-b16.json`.
No diffusion, GAN, or fine-tuned-backbone checkpoints exist in this
repository — none are claimed to.

## Which raw scores exist?

`results/large/{train,validation,test}/{effnet,own}/chunk_*.json` — 160
chunk files, per-image detector scores backing the 20,000-image confirmatory
run and the 8,000-image replication. `results/e7_control_hierarchy/`,
`results/e7_full_panel/`, `results/e7_newprobes/` hold the equivalent
chunked intermediate state for the 800-image 4-detector panel.

## Which experiment logs exist?

No separate stdout/stderr execution-log files were found (none were
claimed). `docs/06-results.md` functions as a narrative results log but has
a self-declared, confirmed-true gap: it stops after E9/E11 and does not
cover E10, E12, or the 4-detector panel expansion. `docs/09-cli-handoff-context.md`
covers the gap for the panel expansion specifically and was cross-checked
number-by-number against `results/e0_*` and `results/e7_*` — every number it
states matches.

## Which figures are regenerated?

None, in this session. `paper/figures/*.pdf` are committed artifacts;
`scripts/make_paper_figures.py` exists and is presumably what generated
them, but it was not re-run in this audit pass (no LaTeX toolchain was
available to verify the resulting document either — see below — and
re-running figure generation without being able to verify the compiled
output against it was judged lower value than the numeric audit actually
performed).

## Which tables are regenerated?

None as LaTeX tables. The underlying numbers behind the tables in
`paper/main.tex` were cross-checked programmatically by
`scripts/audit_manuscript.py` (26/26 checks passing) rather than by
re-typesetting the tables themselves.

## Which results are imported?

None. `results/imported_manuscript/` was deliberately not created — see
`results/PROVENANCE.md` for the reasoning. Nothing in `results/` was
reconstructed from a manuscript-stated number; the direction of verification
in this audit ran the other way (artifact -> manuscript check).

## Which experiments remain unreproduced (by this session)?

The full pipeline was not re-executed end-to-end against freshly downloaded
data and freshly scored public/fine-tuned detectors in this session — that
would require the dataset (not present locally: `data/` is gitignored and
empty on this machine) and, for EfficientNet-B6/ViT baselines, network
access to specific Hugging Face checkpoints, plus meaningful compute time.
What *was* executed in this session: the full `pytest` suite (38/38 passing,
after installing `scikit-image`, `opencv-python-headless`, and `onnxruntime`,
none of which were previously installed in this Python environment) and
`scripts/audit_manuscript.py` (26/26 numeric cross-checks passing). Both are
genuine re-execution; neither is a substitute for re-running the 20,000-image
confirmatory pipeline from raw images.

## Which limitations remain?

As stated in the manuscript itself (Discussion/Limitations) and
`docs/04-open-risks.md`: whole-image synthesis standing in for "deepfake";
two public detectors with undisclosed/leakage-flagged training provenance;
no identity-level splitting available; the ConvNeXt/ViT architectural
mechanism is genuinely unresolved (not merely unstated); EfficientNet-B6
confounds architecture with training regime relative to the frozen-probe
panel. None of these were newly discovered in this audit; all were already
disclosed in the manuscript before this session started.

## Which claims are supported?

Every quantitative claim listed under "independently verified" above, plus
the qualitative claims in Section 6 of the task brief (PSNR matching is
insufficient; EfficientNet-B6 shows the cleanest collapse; ConvNeXt-Base
retains a residual; ViT-B/16 reverses direction and does not universally
collapse; ResNet-18 is mixed) — all confirmed against the CI bounds in
`results/e7_full_panel_analysis.json` in `docs/manuscript_audit.md`.

## Which claims are hypotheses?

Explicitly, in the manuscript's own words: kernel-size/local-phase
sensitivity as an explanation for ConvNeXt-Base's residual, and
attention-level payload disruption as an explanation for ViT-B/16's reversal.
Both are labeled untested in `paper/main.tex` itself; this audit did not
find, and did not introduce, any stronger claim than that.

## What this audit session changed

- Added: `docs/source_provenance.md`, `docs/manuscript_audit.md`, this file,
  `docs/hardware_requirements.md`, `docs/tier2_resource_plan.md`,
  `scripts/audit_manuscript.py`, `results/PROVENANCE.md`, `LICENSE`,
  `CITATION.cff`, `pyproject.toml`, `.github/workflows/ci.yml`.
- Rewrote: `README.md` (was stale — described a pre-E0-E12 state — now
  reflects the actual current repository, with explicit reported/verified/
  reproduced provenance separation).
- Did not change: any number in `paper/main.tex`, any result JSON file, any
  scientific conclusion, any test.
- Installed (into this session's Python environment only, via `pip`, not
  committed as new hard requirements beyond what `requirements.txt` already
  specified): `scikit-image`, `opencv-python-headless`, `onnxruntime`.
- Could not do: rebuild `paper/main.pdf` from `paper/main.tex` (no LaTeX
  toolchain in this sandbox; a `chocolatey` install of `tectonic` was
  attempted and failed on a filesystem permission error requiring elevation
  this session does not have — not worked around). The committed PDF and
  the current `.tex` are from the same commit, so there is no known drift,
  but "same commit" is not the same claim as "independently recompiled and
  confirmed zero errors," and this report does not claim the latter.

## Bottom line

This is not a case of a manuscript describing work that doesn't exist. The
opposite risk applies here: an earlier assessment in this working session
(before this audit began) concluded the project was "design-stage, no
experiments run," based on reading only the stale `README.md` and the
pre-pivot `docs/00`-`04` planning documents. That conclusion was wrong. The
actual repository, 60+ commits deep on `main`, contains a complete,
internally-consistent, artifact-backed empirical study matching the
manuscript's claims to the numeral. The corrective in this session was
documentation and packaging (provenance tables, a real automated numeric
audit script, working `pytest`/`pip install -e .`, filled-in repo-quality
files, a truthful README) — not fabrication, and not a rescue of a project
that needed one.
