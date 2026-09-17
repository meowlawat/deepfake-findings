# Provenance of files in this directory

The task brief that prompted this audit asked for a physical split into
`results/imported_manuscript/`, `results/verified_raw/`, and
`results/reproduced/`. That was not done as a file move, for a concrete
reason: every file already in this directory **is** a verified raw artifact
(evidence level A or B — see `docs/source_provenance.md` for the full,
per-file table), every script in `scripts/` and every cross-reference in
`docs/` and `paper/main.tex` points at these files by their current relative
path, and this repository's own `.gitignore` comment explains why these 21MB
of scores are deliberately committed rather than treated as disposable —
moving them risks breaking that chain of evidence for no benefit, and
Section 23 of the audit brief itself says not to create files (or, by the
same logic, directories) without a real reason.

So, stated plainly instead of restructured:

- **Everything under `results/*.json` and `results/{e7_*,large}/` is
  verified-raw** (evidence A) or **derived-from-verified-raw**
  (evidence B — `large_summary.json`, `replication_check.json`, which are
  produced by `scripts/aggregate_large.py` / `scripts/replication_check.py`
  reading the per-chunk files). None of it was reconstructed from manuscript
  numbers; the manuscript numbers were checked *against* these files (see
  `docs/manuscript_audit.md`), not the other way around.
- **`results/imported_manuscript/` is empty and not created** — there was
  nothing to import. Every "locked" numeric claim in the task brief that
  could be located in the manuscript was also located in one of these raw
  artifact files. The one exception (total corpus size stated as "22,000")
  is documented as an open discrepancy in `docs/manuscript_audit.md`, not
  silently imported as if it had a source file.
- **`results/reproduced/` is empty and not created** — no experiment was
  independently re-executed end-to-end against the real dataset and public
  detector checkpoints in this audit session (no local dataset copy, and
  full re-execution was out of scope for a documentation/audit pass; see
  `docs/research_integrity_report.md`). What *was* independently re-executed
  in this session is the unit/integration test suite (`pytest`, 38/38
  passing) and `scripts/audit_manuscript.py` (26/26 numeric cross-checks
  passing) — both are artifact-level verification, not full pipeline
  reproduction, and are reported as such rather than conflated with it.

If a future session does re-run the full pipeline end-to-end against real
data and wants a `results/reproduced/` directory, that's the right time to
create it — populated, not as an empty placeholder.
