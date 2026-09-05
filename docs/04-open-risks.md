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

## R5 — Effort scope (superseded by the 10-day constraint)
The original full factorial (4 datasets × 5 schemes × 3 detectors × 8
transforms) is now explicitly out of scope for v1. `docs/03` §1 defines the
core grid actually being run — 1 dataset × 2 schemes × 2 detectors × 3
transforms — and §6 keeps the full factorial as a named extension rather than
discarding it. The risk that remains: even the narrow grid assumes §0's
tooling table verifies cleanly on day 1–2. If a candidate detector or the
RivaGan pretrained weights don't load without training, the schedule has no
slack to absorb a second search-and-verify cycle. Budget day 1's afternoon as
a hard checkpoint — if nothing in the tooling table has verified by then, cut
further (one detector, not two) rather than let it eat day 3–4's E1 gate.

## R6 — Venue fit
Target stated: leverage for a masters or research-internship application
abroad, with a 10-day hard deadline on this v1. Those two constraints are in
tension: IEEE TIFS or T-BIOM are the right long-term aim for the application's
sake, but neither fits a 10-day cycle and both would rightly reject a
single-dataset, zero-shot-detector, no-gated-data study as too narrow. The
realistic near-term move is an arXiv preprint plus submission to a
faster-turnaround workshop or a shorter venue (a CV/security workshop, or a
conference short-paper track) that fits the scope in `docs/03`, with the
extensions in `docs/03` §6 forming the basis of a fuller journal submission
afterward once gated-dataset access clears. Say this explicitly to whoever
evaluates the application: "preprint + workshop now, TIFS-track journal
extension in progress" is a defensible, honest story; overselling a 10-day
single-dataset study as journal-ready is not, and is exactly the kind of claim
that damages credibility with the audience this is meant to impress.

## R7 — Novelty of components must not be claimed
ViT + LoRA, DWT-SVD, logistic fusion, Chow's rule: all standard. The paper claims
none of them. The claim is the interaction between provenance marking and passive
detection under fusion, and the decision rule that survives it. Any sentence that
drifts toward claiming a component is a liability.

## R8 — Dataset scope-honesty: GAN synthesis is not face-swap deepfakes
`docs/03`'s primary v1 dataset candidate (`140k-real-and-fake-faces`) is
whole-image StyleGAN synthesis versus real FFHQ photographs. That is a
different and easier problem from face-swap or reenactment manipulation
(what FaceForensics++ tests, and what "deepfake" usually means to a reader).
Passive detectors trained or evaluated on GAN-synthesis artifacts often key on
generator fingerprints that face-swap methods don't leave, so a result here
may not transfer, and a reviewer who catches the substitution without it being
flagged will read it as a bait-and-switch rather than a scoped study.

*Mitigation:* state the substitution in the paper's title, abstract, and
limitations — "AI-generated image detection" or "synthetic-image provenance",
not an unqualified "deepfake detection" claim, unless the manjilkarki dataset
verifies as genuine face-manipulation content and is used instead. Either way,
this must be decided and written down before the abstract is drafted, not
patched in during the writing days.

## R9 — Community-redistributed datasets carry their own provenance risk
The stretch dataset candidate (`manjilkarki/deepfake-and-real-images`) is,
if it is what it appears to be, a redistribution of face-manipulation content
whose original release (e.g. FF++) is itself access-gated. Using it sidesteps
the gate but does not resolve why the gate exists (consent, license,
responsible-disclosure terms on manipulated-face content). Confirm the
dataset's actual license and provenance before using it in anything intended
for submission — "instantly downloadable" is not the same as "cleared for use
in a publication." If provenance can't be confirmed, default to the GAN-only
dataset and take R8's framing constraint instead of an unresolved licensing
risk.

## R10 — Zero-shot detectors change the claim, not just the difficulty
v1 uses detectors pretrained by someone else, unmodified. This is a real,
citable setting (it's Guo et al.'s setting), but it is a different empirical
claim than "interference degrades a detector trained for this task and
distribution." State in the paper, plainly, that E1–E6 measure interference
against zero-shot passive detectors, and that whether the same effect and
magnitude holds for a purpose-trained detector is exactly what the
FF++-based extension in `docs/03` §6 is for. Do not let the zero-shot
qualifier quietly disappear between the experiments section and the abstract.
