# Conference readiness audit

Performed 2026-10-14 against `E:\deepfake-findings`, `main`, starting commit `041dfea`.
Scope: `paper/main.tex` (1269 lines, read in full), `paper/refs.bib` (21 entries),
`paper/figures/` (7 files, 5 referenced), the result artifacts in `results/`, and the
compiled `paper/main.pdf`. This document reports what was checked, what was changed and
why, what was deliberately left alone, and a verdict. It does not repeat
`docs/manuscript_audit.md`'s per-claim table; it extends it with what this pass added
(bibliography, compilation, visual layout) and references it rather than duplicating it.

## Starting-state finding

**The manuscript was already in substantially strong shape before this pass.** This is
worth stating plainly rather than inventing problems to justify a large diff: the paper
reads as a carefully argued research paper, not a lab log. Specifically, already present
before this session touched anything:

- Consistent terminology for the central estimator (evidence-transfer slope `b`, paired
  per-image OLS, 95% percentile bootstrap, 800–2,000 resamples, explicitly stated per
  analysis).
- A pre-registration chronology with a disclosed mid-run deviation, checkable against
  git history rather than asserted.
- Explicit separation of confirmatory results (H1–H3, pre-registered) from exploratory
  ones (E4/E5 transform analysis, the calibration/decision-risk analysis) — the paper
  never lets a post-hoc finding borrow confirmatory status.
- Two independent analytic results (AUC's blindness to monotone rescaling; mean-shift
  conflating attenuation with translation) stated as structural facts, verified by a
  unit test, and kept separate from the empirical claims.
- A detector-provenance confound (EfficientNet-B6 fine-tuned/undisclosed vs. three
  frozen, disclosed probes) disclosed prominently in Experimental Setup, repeated in
  Limitations, and repeated again in the Conclusion — not buried once and forgotten.
- Architecture-specific explanations (ConvNeXt kernel sensitivity, ViT attention/
  tokenisation) explicitly and repeatedly labeled as untested hypotheses, not findings,
  including in the final Discussion section's framing ("we report the fracture as a
  result in search of a mechanism, not a mechanism").
- A closing Discussion section ("One checkpoint is not a detector, and one cell is not
  a cost model") that states its own meta-finding: every generality claim in the paper
  that was checked against a wider design either reversed or narrowed under widening.
  This is an unusually self-critical thing for a paper to say about itself, and it is
  accurate to what the results sections show.

Given that starting point, this pass's job was narrower than the original mission
brief assumed: verify, find the genuine remaining gaps, fix what was cheaply fixable,
and report honestly on what remains.

## What was checked

### 1. Citations (`paper/refs.bib`, 21 entries)

- Every `\cite{}` key used in `main.tex` (21 unique keys) has a matching `refs.bib`
  entry; `tectonic`'s BibTeX pass produced zero "undefined citation" warnings.
- Spot-verified `wu2024watermarksbugs` (Wu, Liao, Ou, Liu, Qin, IJCAI 2024,
  "Are Watermarks Bugs for Deepfake Detectors?") against the actual IJCAI PDF, read in
  full in an earlier session of this project (`lit/advmark-ijcai2024.pdf`, gitignored,
  kept local). Author list, title, and venue match exactly.
- `chow1970reject` (Chow, "On Optimum Recognition Error and Reject Tradeoff," IEEE
  Trans. Information Theory, 1970) is a well-known, independently checkable citation;
  the DOI format (`10.1109/TIT.1970.1054406`) is consistent with IEEE's scheme for that
  era.
- The remaining 19 entries were **not** individually re-verified against publisher
  records in this pass — this would require live web access to each publisher/
  proceedings page, which was not exercised here. Several keys (`wu2026allinone`,
  `zeng2026lava`, `an2024waves`, `guo2024passiveorwatermark`, `wang2025fractalforensics`,
  `zhang2024editguard`, `wu2023sepmark`, `muller2026watermarkshortcut`) correspond to
  papers surfaced via web search in an earlier session of this same project while
  mapping the literature (see `lit/coverage-matrix.md`), which is corroborating but not
  equivalent to a fresh per-entry check. **Before submission, re-verify each entry
  against its publisher/proceedings listing** — this is flagged as a named remaining
  task, not silently treated as done.
- No DOIs, page numbers, or venues were invented in this pass. Nothing in `refs.bib` was
  edited.

### 2. Compilation

- `tectonic` 0.17.0 is installed and available in this environment (contrary to an
  earlier session's report that no LaTeX toolchain was available — that constraint no
  longer holds here).
- Compiled `paper/main.tex` from source: **zero errors, zero undefined references,
  zero undefined citations**, BibTeX ran cleanly. 12 pages.
- Two genuine layout defects found and fixed (below); all other compiler warnings are
  routine sub-pixel over/underfull-hbox noise from IEEEtran's narrow two-column
  justification and were left alone — chasing them further has no visible effect and
  real risk of making table spacing worse.
- `paper/main.pdf` was regenerated from the current source and committed in place of
  the previous build. The previous committed PDF (724,572 bytes, built Sep 17) and the
  new one (724,562 bytes) are near-identical in size; the content difference is the two
  table-width fixes below plus whatever normal rebuild variation Tectonic introduces
  between runs.

### 3. Visual inspection

All 12 pages were rendered to PNG at 150 DPI (via PyMuPDF, since `pdftoppm` is not
available in this environment) and visually inspected in full — title/abstract,
introduction, related work, method, experimental setup, every results subsection,
every table, every figure, limitations, discussion, conclusion, and the reference list.
No clipped figures, no text bleeding off a page edge, no broken symbols, no overlapping
elements. Every referenced figure renders; all 5 cited figures (`fig_replication`,
`fig_spectral_profile`, `fig_control_hierarchy`, `fig_ber_area`, `fig_calibration`)
are present and legible at normal reading size.

### 4. Statistical and methodological audit (Phase 3A–3D of the mission brief)

Read in full against the actual method section (`\S`III) and results (`\S`V):

- **Paired structure confirmed.** `\S`III-B states explicitly that bootstrap resampling
  moves "all arms together" per image, and `\S`V-E's four-detector panel states the
  two scoring passes were merged only after verifying identical image coverage with no
  detector-name overlap (`merge_e7_results.py`) — the paired design is implemented, not
  just claimed.
- **CI-vs-absence-of-effect discipline is already correct throughout.** E.g. `\S`V-E:
  "a strictly increasing rescaling... It does not follow that the measured
  transformation is exactly affine... The correct reading is that AUC *cannot* register
  the pure-attenuation component, not that an observed AUC null proves the change was
  pure attenuation." This distinction is maintained consistently, not just stated once.
- **Multiple-comparisons / bootstrap replicate counts are disclosed per analysis**
  (800–2,000 resamples, stated per table), not hidden in a single global number.
- **Exploratory analyses are explicitly labeled**, including the E4/E5 point-estimate
  table (no bootstrap intervals, flagged as such in-table) and the post-hoc calibration/
  decision-risk analysis (explicitly stated as reusing non-independent data and
  reported as "supporting evidence about the mechanism, not as a second confirmatory
  result").
- No post-hoc analysis is presented as pre-registered anywhere in the manuscript.
- **No new computation was run in this pass.** Per the mission brief's own instruction
  ("run new computations only when they resolve a clearly identified, material
  weakness") and because nothing in the existing statistical reporting had a material,
  fixable gap — the paper's own `\S`VI-VII limitations already state every genuine
  remaining weakness (listed below) more precisely than a generic rewrite would.

### 5. Experimental provenance (Phase 3C)

Cross-checked against `docs/manuscript_audit.md`'s existing per-claim table (26/26
independently reproduced via `scripts/audit_manuscript.py`, re-run again in this
session, still 26/26) and `docs/source_provenance.md`. Dataset splits are kept
distinct in the manuscript text itself (exploratory 150+150, confirmatory 20,000,
replication subset 8,000, panel slice 800) and nowhere summed into a single
"total unique images" figure. The "22,000 images" figure, previously traced to an
external task prompt rather than this manuscript, remains correctly excluded — verified
again this session (`scripts/audit_manuscript.py` output, "NOT A MANUSCRIPT CLAIM"
section) and not reintroduced anywhere in this pass's changes.

Leakage: the manuscript states plainly that EfficientNet-B6's training data is
undisclosed and contamination "cannot be excluded," mitigated only by within-model,
within-image deltas (`\S`IV, `\S`VII). This is the honest position given available
artifacts — stated as a limitation, not claimed as resolved.

## What was changed, and why

Two material, narrowly-scoped fixes, both typographic/layout, neither touching a
number, a claim, or an interpretation:

1. **`tab:resolution` (Table VIII)**: default `\tabcolsep` produced an 8.8pt overfull
   hbox — the table was measurably wider than the column, which risked a visible
   margin overrun in print. Added `\setlength{\tabcolsep}{3pt}`, consistent with the
   spacing convention already used in five of this paper's other tables. Confirmed by
   recompiling (warning gone) and by visual inspection of the rendered page (clean,
   compared against the pre-fix render where the issue was visible in the warning log).
2. **`tab:cost-surface` (Table XI)**: a 15.5pt overfull hbox, the worst in the document
   — large enough to be clearly visible. The column header "median DRD $-$ clean" was
   the primary width driver in a four-column table already packed with long arm names
   (`null[DWT]`, `RivaGAN (wm)`). Shortened to "med. $\Delta$DRD" (the caption already
   states "DRD relative to the clean arm," so the abbreviation loses no information),
   shortened "Calibrator" to "Calib.", and reduced `\tabcolsep` from 4pt to 2.5pt.
   Confirmed the same way.
3. **`paper/main.pdf` rebuilt** from the corrected source via `tectonic`, replacing the
   Sep 17 build. Verified zero compile errors/warnings beyond the routine sub-pixel
   noise, and visually re-inspected all 12 pages of the new build.

Both fixes are pure LaTeX table formatting (column separation, header wording that
loses no information given the caption). No number in any table changed. No sentence
of prose interpreting a result changed. `scripts/audit_manuscript.py` (26/26) and
`pytest` (38/38) were re-run after each change and pass identically to before.

## What was deliberately not changed

- **No rewriting of already-strong prose.** The abstract, introduction, and discussion
  already state the question, design, findings, and qualified conclusion precisely —
  rewriting working prose to satisfy a generic "make it read like a strong paper"
  instruction when it already does would be exactly the kind of low-value, high-risk
  busywork the mission brief itself warns against (Phase 6).
- **No related-work expansion.** The existing `\S`II is narrow and precise about what
  this paper's novelty is (the control-design problem and detector-dependent behavior,
  not a universal theory) and does not claim an exhaustive review. Expanding it without
  a named gap to fill would risk introducing an unverified citation under time pressure
  — the opposite of what this audit is for.
- **Two unused figure files** (`paper/figures/fig_e4_beta4.pdf`, `fig_rho_sweep.pdf`)
  exist on disk but are not referenced anywhere in `main.tex`. They are almost certainly
  a prior draft's figures for the E4/E5 exploratory table and the `\rho`-sweep mentioned
  in prose (`\S`V-J) but not as a standalone figure in the current text. Harmless as
  dead weight, not deleted in this pass — flagged for you to decide, consistent with
  "do not delete without asking" for anything not explicitly authorized.
- **No venue-specific formatting.** No venue has been named. The manuscript stays in
  its current `IEEEtran` journal-class format. If a specific venue is chosen, its
  template, page limit, anonymization rules, and supplementary-material requirements
  need to be checked against this document before submission — not assumed from the
  current format.

## Remaining limitations (the manuscript's own list, not invented)

`main.tex` `\S`VI already states these precisely; reproduced here only as a checklist,
not reworded, because the original wording is exact and reworking it risks weakening
it:

- Spectrum matching is second-order (energy-and-spectrum matched, not every
  higher-order or phase property).
- Architecture, training data, and training augmentation remain untested confounds
  behind the four-detector fracture.
- The mechanism behind EfficientNet-B6's frequency-dependent attenuation is narrowed
  (resolution excluded) but not identified.
- EfficientNet-B6's training provenance is undisclosed; contamination cannot be
  excluded, only mitigated.
- The `\beta_4` resize-to-0.5× outlier (`n=280`) has no confidence interval and is
  explicitly flagged as unclaimed.
- The corpus is whole-image GAN synthesis against real photographs, not face-swap or
  reenactment manipulation, and carries no identity metadata, so bootstrap intervals
  are image-level only.

## Bibliography re-verification (named remaining task)

19 of 21 `refs.bib` entries were not individually re-checked against a publisher or
proceedings record in this session. This is the single largest named gap in this audit.
Recommended before submission: fetch each entry's DOI/proceedings page directly and
confirm title, author list, venue, and year match exactly.

## Final state

- Branch: `main`. Commits this session not yet made at time of writing this document
  (see final commit list in the session's closing report) — the table fixes and PDF
  rebuild are staged for a single commit, consistent with "small, auditable changes."
- `scripts/audit_manuscript.py`: 26/26 passing (unchanged by this pass — no claim or
  number was touched).
- `pytest`: 38/38 passing.
- `paper/main.pdf`: recompiles cleanly from `paper/main.tex` via `tectonic 0.17.0`,
  zero errors, zero undefined references/citations, visually verified across all 12
  pages.
- Nothing pushed. No remote branch created, deleted, or modified. No GitHub setting
  touched. `E:\tier1-watermark-detector-study` untouched.

## Verdict

**Conditionally ready for venue-specific submission checks**, not yet "ready for
submission" outright, pending exactly these named items and nothing else:

1. Re-verify the 19 unchecked bibliography entries against publisher/proceedings
   records.
2. Select a venue and check its template, page limit, anonymization policy, and
   supplementary-material rules against this manuscript — none of that has been done
   because no venue has been named.
3. Decide on the two unused figure files (keep as supplementary, or remove).

The manuscript's scientific content — the statistical methodology, the control
construction and its stated limits, the detector-panel reporting, the pre-registration
discipline, and the honestly-scoped conclusion — was already at a defensible standard
before this session and required no substantive change. This audit's contribution is
two fixed layout defects, a verified clean compile with full visual inspection, and a
scoped, honest list of what is not yet checked rather than a claim that everything is.
