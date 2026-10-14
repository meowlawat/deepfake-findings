# Comparison: E:\tier1-watermark-detector-study vs. this repository

Performed 2026-10-14, against `E:\deepfake-findings` commit `11b03da` (pre-doc-correction)
and `E:\tier1-watermark-detector-study` as it existed on disk at that time (not a git
repository, no commit to pin). This file lives in the real repo, not the orphaned
directory, so it survives deletion of the latter.

## Method

1. Full file inventory of both trees (`find`), 42 files in the orphan vs. 830 here.
2. Basename-level set comparison to find names present only in the orphan.
3. For names present in both trees, MD5 content comparison.
4. For files that differ in content, manual inspection of the actual diff.

## Result: no unique material

**Basenames present only in the orphan (3):**

| File | Finding |
| --- | --- |
| `src/controls/controls.py` | Every function (`match_to_target`, `_spectral_surrogate`, `match_spectrum_and_psnr`, `_add_scaled_noise`, class `NullPerturbationResult`) exists verbatim under a different name: `src/deepfake_interference/null_perturbation.py` in this repo. |
| `src/analysis/statistics.py` | Identical function/class signatures to `src/deepfake_interference/stats.py` here (`diff` on `^def |^class` lines: empty). |
| `manuscript/references.bib` | Byte-identical (MD5 match) to `paper/refs.bib` here. |

**Basenames present in both trees (34), MD5-compared:**

- **29 byte-identical.** Includes every `results/*.json` file and all result JSONs — the orphan's data layer is a stale, exact copy of this repo's.
- **5 differ**, inspected individually:
  - `main.pdf` — expected; different build.
  - `main.tex` — a full-file replace (every line differs), but it is the **pre-rewrite** manuscript prose (same title, same authors, same structure, before commit `52243ac` "Rewrite manuscript prose in a plainer, more direct style"). This exact text already exists in this repo's own git history (`git log -p` on `paper/main.tex` prior to `52243ac`), so it is redundant even against the orphan's own claim to uniqueness.
  - `watermark.py`, `pipeline.py` — 4 and 12 line diffs respectively against `src/deepfake_interference/{watermark,pipeline}.py`. Inspected directly: package-naming/import-path cosmetics, not logic differences.
  - `__init__.py` — expected; different package names.

## Conclusion

`E:\tier1-watermark-detector-study` is a structurally and substantively confirmed stale
duplicate of an earlier stage of this project: same algorithms under different file
names, same result data, an older manuscript draft already preserved in this repo's
git history. No content was found in it that is not already present, in a
better-organized or more current form, in `E:\deepfake-findings`.

Recommendation: safe to delete, once the safeguard commands below have been run and
their output reviewed.
