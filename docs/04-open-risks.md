# Open risks and what must be resolved

Ordered by how much damage they do if ignored.

## R1 — The premise may not replicate in this setup
Everything rests on watermark-detector interference being measurable here. Wu et
al. show it; the audio paper replicates it in another modality. But their
detectors, schemes and data are not ours. If E1 returns `Δ_AUC ≈ 0`, the
"interference breaks calibration" framing collapses.

*Mitigation:* E1 is a go/no-go gate before any writing. The fallback framing —
a replication study delimiting *when* interference appears and when it does not —
is written into the plan in advance so a null result is still a paper.

## R2 — Unverified citations
`docs/01-positioning.md` §5 has an UNVERIFIED block. Several are 2026 works
that were surfaced by search but not read in full.
**Do not cite anything from that block.** Several verified entries were read at
abstract depth only; the positioning claims made from them ("X does not do
fusion") need full-text confirmation before appearing in a related-work section.

Highest-priority reads:
1. ICMR 2026 dual-threshold paper — closest neighbour on the abstention half of
   the contribution. ACM DL returned 403; obtain it. If it also fuses evidence
   sources, the contribution narrows and must be re-scoped.
2. Guo et al. 2411.13553 full text — confirm it truly does not fuse and does not
   report watermark effects on its passive detectors.
3. WAVES tables — either source the DwtDctSvd/JPEG number or drop it.

## R3 — The claimed gap may be occupied by something not yet found
One search pass over one engine is not a literature review. Before committing:
Google Scholar forward-citations of Wu et al. (IJCAI 2024) and of Guo et al.
Anything citing both is the direct competitor. This is the single highest-value
hour available right now.

## R4 — Reviewers will attack the fusion's simplicity
"Logistic regression over three terms" invites a dismissal. The defence must be
stated explicitly in the paper, not implied: the model is a measurement
instrument, `β₄` is the finding, and a black-box fuser would hide the very
effect being reported. Include a nonlinear fuser (small MLP / gradient boosting)
as a control showing it does not fix calibration either — that closes the
objection instead of arguing with it.

## R5 — Effort scope
The full factorial (4 datasets × 5 schemes × 3 detectors × 8 transforms) is a
large grid. Plan a core grid (FF++ + Celeb-DF × DWT-SVD + one learned scheme × 2
detectors × 4 transforms) that produces every headline claim, and treat the rest
as extensions run only if time allows.

## R6 — Venue fit
Target stated: a journal that strengthens a masters / research-internship
application. Realistic candidates given the contribution shape (measurement study
plus a decision-theoretic fix, no new architecture): IEEE TIFS, IEEE T-BIOM,
Pattern Recognition, Neurocomputing, or a strong CV/security workshop as a
faster-turnaround first outing. TIFS is the right aim and the hardest; it also
demands the most rigour on statistics and baselines, which is why §4 of the
experiment plan is non-negotiable.

## R7 — Novelty of components must not be claimed
ViT + LoRA, DWT-SVD, logistic fusion, Chow's rule: all standard. The paper claims
none of them. The claim is the interaction between provenance marking and passive
detection under fusion, and the decision rule that survives it. Any sentence that
drifts toward claiming a component is a liability.
