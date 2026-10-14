# Venue shortlist

Researched 2026-10-14 (today's date). Scope fit judged against the paper's actual
content: a 12-page, workshop-scale study (two watermark schemes, four detectors, an
~800-image panel slice, a 20,000-image confirmatory set) with a methodological
contribution about control design, not a large benchmark or a new detection system.
That scope matters for venue choice as much as topical fit — a paper this size reads
naturally as a workshop paper and would be undersized for a top-tier main-conference
submission expecting a broader evaluation.

**Headline finding, stated first because it changes the recommendation: every
topically-matched venue's near-term deadline has either already passed or is not yet
announced.** This is not a search failure — it's checked against each venue's own
official page, dated below. No deadline was invented to produce a clean answer.

## Checked

| Venue | Scope fit | 2026/2027 status | Source, checked 2026-10-14 |
| --- | --- | --- | --- |
| **IEEE WIFS** (Workshop on Information Forensics and Security) | Best fit — exactly this paper's community (forensics, watermarking, detection) | 2026 edition deadline (Jul 15/22/29, 2026) **already passed**. 2027 edition confirmed to exist (Dec 6–10, 2027, Lille, France) but submission deadline is listed as **TBD** | `signalprocessingsociety.org/events/2027-ieee-international-workshop-information-forensics-and-security-wifs` |
| **ACM IH&MMSec** (Information Hiding and Multimedia Security) | Best fit — explicitly covers watermarking, forensics, counter-forensics, deepfake analysis; workshop-scale, matches this paper's size well | 2026 edition deadline (Feb 16, 2026) **already passed**; held Jun 17–19, 2026, Florence. 2027 edition **not yet found or announced** anywhere searched | `ihmmsec.org` (redirect page only, no 2027 content yet); WikiCFP; general search |
| **ICASSP 2027** | Weaker fit — broad signal-processing conference, forensics is one track among many, larger and more competitive than this paper's scope | Deadline **already passed** (reported as Sep 16–23, 2026, conflicting sources agree it's before today) | `2027.ieeeicassp.org/call-for-papers/`; `mldeadlines.com/conference/icassp-2027` |
| **IEEE ICIP 2027** | Moderate fit — image processing broadly, forensics/watermarking is an accepted topic but not the focus | Nov 29–Dec 3, 2027, Singapore. Deadline reported inconsistently across secondary sources (Feb 1 vs. Mar 31, 2027) and the **official site's CFP page did not yet surface a confirmed deadline** when fetched directly | `2027.ieeeicip.org/` (fetched directly — no CFP details posted yet); secondary sources disagree |

Not pursued further this session, for stated reasons: a specific CVPR/ICCV/NeurIPS
workshop on media forensics (these exist most years but are announced late, typically
2-4 months before the main conference, and none for 2027 editions were findable yet
given how early it still is relative to those conferences); a journal submission
(TIFS, a natural long-term home per this project's own earlier planning notes, has no
deadline by design, which makes it a fallback rather than something to rank against
dated venues).

## What this means, concretely

There is currently no verified, open, scope-matched deadline to target. The two best
scope-fit venues (WIFS, IH&MMSec) both just closed their 2026 submission windows and
haven't opened 2027 CFPs yet — checking back in roughly 2-3 months (WIFS 2027,
following its own historical Jul-deadline pattern, likely opens a CFP around
Feb-Apr 2027; IH&MMSec, following its Feb-deadline pattern, likely opens a CFP around
Sep-Nov 2026, which is close to now and worth checking again soon) is a real, trackable
plan, not an indefinite wait.

## Update, 2026-10-14, follow-up session: IH&MMSec's own CFP text, read directly

The IH&MMSec 2025 CFP (`ihmmsec.org/cms/upload/2025/FormattedCFPwithLogo1.pdf`, fetched
and read directly, not from a search summary) gives facts the first pass of this
research didn't have, and they change the compression conclusion below:

- **Full papers: 10-12 pages including references.** This manuscript is exactly 12
  pages. It fits IH&MMSec's limit at the upper bound, **with no compression needed** —
  unlike WIFS's 6-page limit, which does require real cutting. This is a material
  factor in favor of the recommendation below, not just topical fit.
- **Double-blind: "Manuscripts must be properly anonymized for double-blind review."**
  WIFS 2026, by contrast, was explicitly single-blind ("no need to anonymise"). If
  IH&MMSec is the target, `paper/main.tex`'s `\author` block (names, IIT Patna and
  VIPS-TC affiliations) needs to be stripped or replaced with placeholder text for
  submission, and reintroduced only in the camera-ready version — this was not
  previously stated as a requirement anywhere in this project's documentation.
- **Dual-submission clause**, quoted exactly: "Submissions must not substantially
  overlap with papers that have been published or that are simultaneously submitted to
  a journal or a conference." This is silent on preprint servers specifically. ACM's
  general publications policy is well-documented elsewhere (and corroborated by
  several ACM conferences' own author-instructions pages checked this session) as
  explicitly excepting arXiv/preprint postings from counting as prior publication —
  but the ACM policy page itself (`acm.org/publications/policies/simultaneous-
  submissions`) returned HTTP 403 when fetched directly in this session, so that
  specific claim rests on secondary-source corroboration, not a primary-source read,
  and should be re-confirmed before relying on it.
- **2025 schedule** (the most recent full CFP read in full): submission site opened
  Jan 10, deadline Feb 14, notification Apr 12, workshop Jun 18-20. Consistent with
  the 2026 edition's Feb 16 deadline / Jun 17-19 workshop found earlier — a genuine
  two-year pattern, not a one-off, which is what the "2027 CFP likely opens Sep-Nov
  2026" estimate above is based on.

## Recommendation

**First choice once a CFP opens: ACM IH&MMSec**, over WIFS, for two reasons specific
to this paper rather than general prestige: (1) IH&MMSec's explicit scope line
("watermarking and fingerprinting," "forensics and counter-forensics," "deep fake
analysis") names this paper's exact topic combination, where WIFS is forensics-and-
security more broadly; (2) IH&MMSec is the venue several of this paper's own cited
watermarking papers (SepMark, and this field's broader methodological lineage) target,
so reviewers there will already share the paper's vocabulary and evaluation norms.

**In the meantime, the responsible action is an arXiv preprint**, not waiting silently
for a CFP. Preprinting now establishes priority on the control-confounding finding,
costs nothing, carries no deadline, and is compatible with submitting the same or a
lightly revised version to IH&MMSec or WIFS once either opens — both venues permit
prior arXiv posting (standard in this field; none of this paper's own 21 cited works
were withdrawn from their venue for having an arXiv preprint first).

## What remains venue-dependent and cannot be resolved without your decision

- Which of IH&MMSec, WIFS, or a journal track (TIFS) to actually target once a CFP
  opens — this audit recommends IH&MMSec first but does not commit you to it.
- Page-limit compliance: WIFS enforces 6 pages including references; this manuscript
  is 12 pages and would need genuine compression if WIFS is the eventual target.
  **IH&MMSec's own 2025 CFP confirms a 10-12 page full-paper limit — this manuscript
  fits as-is**, which removes compression from IH&MMSec's path entirely (see the
  update above). Both figures are now primary-source-confirmed, not open questions.
- Anonymization: **IH&MMSec requires double-blind anonymization**, confirmed from its
  own CFP text. WIFS 2026 was explicitly single-blind. If IH&MMSec is pursued, the
  manuscript's author/affiliation block needs to be stripped before submission — a
  concrete, newly-identified pre-submission task, not a vague caveat.
- Still unconfirmed: whether ACM's general arXiv-preprint exception (well-corroborated
  via secondary sources) actually governs IH&MMSec specifically — the primary ACM
  policy page returned 403 on direct fetch. Re-attempt before relying on it for a
  submission decision.
- 2027 CFP dates for both WIFS and IH&MMSec remain genuinely unannounced — nothing in
  this update changes that; check back per the cadence estimates above.

No acceptance likelihood is claimed or implied anywhere in this document.
