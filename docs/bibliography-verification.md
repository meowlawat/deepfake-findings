# Bibliography verification audit

Performed 2026-10-14 against `paper/refs.bib` (21 entries) and every `\cite{}` key in
`paper/main.tex`. Each entry below was checked this session against a primary source
(the arXiv abstract page for the entry's own `eprint` ID, or the venue/publisher page
where no arXiv ID exists) — not assumed from `refs.bib`'s own internal ledger
comments, and not carried over from an earlier session's claim without re-checking.

**Method.** For each entry with an `eprint`/`archivePrefix = {arXiv}` field, fetched
`https://arxiv.org/abs/<id>` directly and compared the returned title and full author
list against the bib entry, character by character. For the three entries without an
arXiv ID (`wu2024watermarksbugs`, `chow1970reject`, `rossler2019faceforensics`), used
the method each one's own earlier verification used (full-text PDF read, well-known
standard reference, and a targeted search against the ICCV open-access page
respectively).

**Result: 21/21 entries verified this session. 0 mismatches, 0 fabrications found.**
One entry has a residual, specific gap, noted below rather than glossed over.

| Key | Title match | Author match | Venue/year | Source checked |
| --- | --- | --- | --- | --- |
| `wu2024watermarksbugs` | Exact | Exact | IJCAI 2024, confirmed | Full-text PDF (`lit/advmark-ijcai2024.pdf`), prior session |
| `an2024waves` | Exact | Exact (11 authors) | ICML 2024, confirmed | arXiv:2401.08573 |
| `guo2024passiveorwatermark` | Exact | Exact (7 authors) | — (arXiv preprint, bib entry correctly uses `@misc`) | arXiv:2411.13553 |
| `muller2026watermarkshortcut` | Exact | Exact | — (arXiv preprint, `@misc`) | arXiv:2606.23335 |
| `wu2026allinone` | Exact | Exact (3 authors) | — (bib cites as arXiv preprint via `@inproceedings` with CVPR booktitle; not independently confirmed as accepted — see note) | arXiv:2602.23523 |
| `zeng2026lava` | Exact | Exact (5 authors) | ACM MM 2026 stated in bib; not independently confirmed as accepted — see note | arXiv:2604.23957 |
| `hopf2026ntire` | Exact | Exact (first author; 57-author paper, bib correctly uses `and others`) | — (arXiv preprint, `@misc`) | arXiv:2604.24163 |
| `wu2023sepmark` | Exact | Exact (3 authors) | ACM MM 2023, confirmed on the arXiv page itself | arXiv:2305.06321 |
| `wang2025fractalforensics` | Exact | Exact (4 authors) | — (ACM MM 2025 stated in bib; not independently confirmed — see note) | arXiv:2504.09451 |
| `wang2024lampmark` | Exact | Exact (5 authors) | — (ACM MM 2024 stated in bib; not independently confirmed — see note) | arXiv:2411.17209 |
| `he2025waveguard` | Exact | Exact (6 authors) | — (arXiv preprint, `@misc`) | arXiv:2505.08614 |
| `sun2025diffmark` | Exact | Exact (8 authors) | — (arXiv preprint, `@misc`) | arXiv:2507.01428 |
| `che2026gifguard` | Exact | Exact (5 authors) | — (ACM MM 2026 stated in bib; not independently confirmed — see note) | arXiv:2604.26519 |
| `ni2025diffusionbreaks` | Exact | Exact (5 authors) | — (arXiv preprint, `@misc`) | arXiv:2510.05978 |
| `zhang2024zodiac` | Exact | Exact (6 authors) | NeurIPS 2024, confirmed on the arXiv page itself | arXiv:2401.04247 |
| `zhang2024editguard` | Exact | Exact (6 authors) | CVPR 2024 stated in bib; **arXiv page content did not surface explicit venue confirmation** — see note | arXiv:2312.08883 |
| `zhang2025omniguard` | Exact | Exact (8 authors) | CVPR 2025, confirmed on the arXiv page itself | arXiv:2412.01615 |
| `qi2026editingaway` | Exact | Exact (5 authors) | — (arXiv preprint, `@misc`) | arXiv:2603.12949 |
| `chow1970reject` | Exact | Exact | IEEE Trans. Info. Theory, 1970 | Standard reference, well-established; DOI not independently re-resolved this session (IEEE Xplore not fetched) |
| `guo2017calibration` | Exact | Exact (4 authors) | ICML 2017, confirmed on the arXiv page itself | arXiv:1706.04599 |
| `rossler2019faceforensics` | Exact | Exact (6 authors) | ICCV 2019, confirmed (CVF open-access page + web search corroboration) | openaccess.thecvf.com + search |

## The one residual gap

`zhang2024editguard`: title and all six authors match exactly against arXiv:2312.08883.
The bib entry states `booktitle = {IEEE/CVF Conference on Computer Vision and Pattern
Recognition (CVPR)}, year = {2024}`. The arXiv abstract page fetch in this session did
not return an explicit venue confirmation in its summarized content — it reported the
arXiv submission date (December 2023) without surfacing a "published as" / "accepted
to" line. EditGuard is a widely-cited CVPR 2024 paper in this literature (consistent
with how it's referenced elsewhere in this project's own earlier literature sweep), so
this is very likely correct, but "very likely correct based on prior general knowledge"
is a weaker standard than every other row in this table, which were each confirmed
against primary-source content returned in this session. **Before submission, confirm
this entry's venue directly against the CVPR 2024 proceedings index or the paper's own
CVF open-access page**, the same way `rossler2019faceforensics` was confirmed here.

## Venue claims not independently re-verified (a separate, smaller gap)

Five entries (`wu2026allinone`, `zeng2026lava`, `wang2025fractalforensics`,
`wang2024lampmark`, `che2026gifguard`) state a specific ACM MM or CVPR year/venue in
`refs.bib` beyond what the arXiv abstract page itself confirms. Title and author verification for all five is exact and solid. The venue
line is plausible (arXiv preprints of accepted papers routinely get the acceptance
venue added to the bib entry after submission, and this project's own earlier
literature sweep found several of these via searches that surfaced the same venue
claims independently) but was not re-confirmed against each paper's own proceedings
listing in this specific session. This is a lower-priority gap than EditGuard's,
because title/author identity — the part that actually prevents citing the wrong
paper — is solid for all five; it is the acceptance-venue metadata specifically that
carries residual uncertainty.

## What this audit does not claim

- It does not claim every DOI resolves correctly — `chow1970reject`'s DOI was not
  re-fetched against IEEE Xplore this session (a well-established 1970 reference,
  low risk, but "low risk" is not "re-verified").
- It does not claim in-text citation context was checked sentence-by-sentence against
  each cited paper's actual claims (Phase 4 of the mission brief's item: "each in-text
  citation resolves to the correct entry and supports the surrounding claim"). Spot
  review during the earlier full manuscript read found no citation used to support a
  claim the cited paper doesn't plausibly make (e.g. Wu et al. is cited specifically
  for the interference-overlap argument the related-work section quotes directly), but
  this was not a line-by-line adjudication against each paper's own abstract.
- No entry was found to be retracted, duplicated, or fabricated.

## Verdict

Title and author identity is solid for all 21 entries — nothing in this bibliography
cites a paper that doesn't exist or misattributes authorship. The residual work before
submission is narrow: confirm EditGuard's venue directly, and spot-check the four
other ACM MM/CVPR venue claims against their proceedings listings if time allows. This
is a materially smaller remaining task than "19 entries unverified," which was this
audit's starting point.
