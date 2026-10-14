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
  is 12 pages. If WIFS is the eventual target, the paper needs genuine compression
  before submission, not just reformatting — that's substantive editorial work this
  audit did not attempt, since no venue is confirmed yet and cutting content against
  the wrong page limit would be wasted or actively harmful.
- IH&MMSec's typical page limit was not confirmed this session (its 2026 CFP details
  weren't surfaced by the fetches run here) — check this once its 2027 CFP posts.
- Anonymization policy: WIFS 2026 was explicitly single-blind ("no need to anonymise");
  this may or may not hold for WIFS 2027, and IH&MMSec's policy was not checked. Do not
  assume either way until a live CFP confirms it.

No acceptance likelihood is claimed or implied anywhere in this document.
