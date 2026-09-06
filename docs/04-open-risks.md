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

## R11 — `Δ_AUC < 0` does not by itself demonstrate interference
The paper's premise is that a watermark's *structure* overlaps the forgery cues
a detector uses. But any imperceptible perturbation shifts a zero-shot
detector trained on clean images, so a raw `Δ_AUC < 0` is equally explained by
generic brittleness with nothing watermark-specific about it. Left uncontrolled
this is not a weakness a reviewer might find — it is the first thing they will
say, and it goes to the paper's central claim rather than to a detail.

**Mitigation, now in the plan:** the `∅` null-perturbation arm (`docs/02` §3.1,
`docs/03` §1), payload-free noise matched per image on PSNR/SSIM, with
`Δ_AUC_net = Δ_AUC(s) − Δ_AUC(∅)` as E1's headline quantity and the go/no-go
gate testing the net value. Cost is hours, since the matching machinery is
already required for T5.

**Residual risk:** PSNR/SSIM matching equalises *energy*, not spatial or
spectral distribution. A watermark concentrated in mid-frequency DCT bands and
uniform noise can match on PSNR and still differ in ways a detector responds to.
`Δ_AUC_net` is therefore evidence of structured interference, not proof of it —
report it in those terms. A frequency-matched null is the stronger control and
belongs in the extension list.

## R12 — `z_P` depends on knowing the transform class, which deployment does not
Per-transform-class `p_0` is estimable in evaluation only because we apply the
transforms ourselves. A deployed verifier receives files from unknown channels
and cannot select the matching `p_0`. v1 resolves this by using a **pooled**
`p_0` per scheme and reporting per-transform values as an oracle-informed upper
bound, making the pooled-vs-oracle gap a measured quantity (`docs/02` §2).

The risk is presentational as much as technical: §2 claims `p_0` is estimated
rather than assumed, and that remains true of its *estimation* while the choice
of *which* `p_0` applies to a given item stays a modelling decision. If the paper
reports only oracle per-transform numbers it will have overstated deployable
performance. Report pooled as the headline, oracle as the bound.

## R13 — A cost-derived band can be wide enough to abstain on almost everything
Chow's rule with a defensible cost model (`c_R=1, c_FP=20, c_FN=100`) gives
`τ_lo=0.01, τ_hi=0.95`, which on a realistic score distribution routes most
traffic to human review. The derivation is correct; the omission is that the
cost model prices errors but not reviewer capacity, which is the binding
constraint in any real deployment.

**Mitigation:** every cost model quoted in the paper carries its realised
coverage beside it, and E3's selective risk at fixed coverage {0.8, 0.9, 0.95}
is the operational reporting (`docs/02` §5). Presenting a wide review band as
straightforwardly better than the source design's narrow one, without saying
what it does to coverage, would repeat the original design's error of asserting
thresholds without accounting for their consequences.

## R14 — Detector training-data provenance is unconfirmed, and one card's own number is a red flag
`docs/03` §0 required confirming each candidate detector "was not trained on
the exact eval dataset (leakage)" before use. Neither surviving candidate
clears that bar:

- `Wvolf/ViT_Deepfake_Detection`'s card names no training dataset at all —
  "trained ... to detect deepfake images," nothing more specific.
- `Skullly/DeepFake-EN-B6`'s card reports **99.89% accuracy on an explicitly
  "unknown dataset."** That is not a reassuring number in this context — it is
  the number a model gets when it has memorized the exact distribution it is
  evaluated on, and `140k-real-and-fake-faces` is a common enough Kaggle
  target that a fine-tune landing on it by coincidence is plausible, not
  exotic.

If either detector saw this dataset (or a close derivative) during training,
v1 is not measuring "zero-shot passive detection" as `docs/03` §1 and R10
claim — it is measuring interference against a detector that has partly
memorized the answer key, which changes both the E0 floor check (a
leakage-inflated detector clears 0.80 trivially, telling you nothing about
zero-shot robustness) and E1 (a memorized detector's response to a watermark
perturbation is a different, harder-to-interpret quantity than a genuinely
zero-shot one's).

**Mitigation, must be built into the code, not just noted in prose:**

1. **Report E0's baseline AUC honestly, and treat a suspiciously high one as
   a finding, not a pass.** An AUC above roughly 0.97 at `W=0` on a dataset
   this easy (whole-image GAN synthesis vs. real photos, no adversarial
   effort) is grounds to suspect leakage rather than celebrate the floor
   check clearing with room to spare. State whatever baseline AUC is
   measured, plainly, in T5/T1 — do not round it down to "clears the floor"
   without comment if it lands at 0.99+.
2. **Make every headline interference and calibration number a within-model,
   within-image delta, never an absolute accuracy claim.** `Δ_μ`, `Δ_σ`,
   `Δ_AUC`, `Δ_AUC_net`, and `ΔECE_W` all compare the *same* model's response
   to the *same* underlying images across conditions (watermarked vs. clean,
   `W=1` vs. `W=0`). Memorization of the clean-vs-fake boundary is common-mode
   across those conditions and cancels in the subtraction to first order;
   it does not automatically cancel if the memorized features are exactly the
   frequencies a given watermark perturbs, which is itself worth checking
   (compare the `∅` null arm's `Δ_AUC` against each scheme's — R11's control
   already buys most of this). Absolute AUC/accuracy is reported in tables as
   context only, explicitly labelled as such, never as a claim about
   real-world zero-shot performance.
3. **State the unresolved leakage risk in the paper's limitations section
   by name**, with both candidates' model-card evidence quoted as above. A
   reviewer who finds this independently and sees it unacknowledged will
   read the whole zero-shot framing as unreliable; a reviewer who sees it
   named and mitigated reads it as a well-scoped study.

This does not block v1 — no leakage-free deepfake detector with disclosed
training data and instant access is know to exist for this timeline — but it
is not optional to fix in the paper's prose, and the within-model-delta
convention in item 2 must be enforced in the analysis code itself, not left
to each script author's discretion.

## R15 — Measured: the crypto-binding verification path is unreliable, not just theoretically fragile
`docs/03`'s tooling verification (`scripts/00_verify_tooling.py`) measures
`crypto_binding.verification_reliability_rate` directly rather than assuming
it. On one 8-image batch of synthetic photo-like content (smooth, spatially
correlated noise - not a real photograph, no dataset is available in this
environment), the false-negative rate came back **62.5%** - more than half
of legitimately watermarked images failed their own signature check. A
single earlier spot-check on one image had shown 0/16 mismatches at the
tuned hash size; the 8-image batch shows that anecdote does not generalize,
and the failure rate varies enormously across synthetic samples.

This does **not** block v1's interference/fusion experiments (E1-E6): those
already use ground-truth `W`, from knowing which images the pipeline
embedded, and never call `crypto_binding.verify_entry`/`resolve_and_verify`
to produce it (see `fusion.py`'s `FusionInputs.w` docstring - this design
decision was made *before* this measurement, for a different reason
identified while testing, and it turns out to also be load-bearing for this
one). What it does affect: `docs/02` S2.1's claim that the Ed25519 binding
gives real deployments an *operational* mechanism for observing `W` is not
supported by what's been measured so far. As written that claim is aspirational.

**Before the paper asserts anything about the crypto binding as a deployment
mechanism (as opposed to a stated design correction to the source material's
AES-256 choice, which stands on its own merits):**

1. **Done, this session, once real data was fetched (`scripts/fetch_dataset.py`,
   see docs/03 S0).** Re-ran `verification_reliability_rate` on real
   photographs from `TheKernel01/140k-Real-and-Fake-Faces` (the HF mirror of
   the v1 Kaggle dataset). Result: **7% false-negative rate**, n=100, for
   *both* `dwtDctSvd` and `rivaGan` - a large improvement on the 62.5%
   measured on synthetic smooth-noise content, confirming that synthetic
   content was indeed a bad proxy for this specific failure mode. 7% is a
   real, reportable number, not zero: state it plainly wherever the crypto
   binding is discussed, and do not round it down to "works."
2. At 7%, replacing the average-hash with a proper perceptual hash / fuzzy
   commitment scheme is a nice-to-have for a deployment claim, not a blocker
   for v1's experiments (which use ground-truth `W` regardless, per
   `fusion.py`). Leave it as a named extension unless time allows more.
3. Report the measured 7% rate, plainly, wherever `docs/02` S2.1 is
   presented in the paper - do not let "we corrected AES-256 to Ed25519" read
   as "and it works perfectly," when only the unforgeability *argument* has
   been checked at 100% and the hash-stability *mechanism* the argument
   depends on to be
   invokable at all.
