# Pre-registration #2: the location-shift hypothesis

**Committed before the confirmatory data was scored. The git timestamp on
this file is the evidence of that ordering, and it is the whole point of
writing it down separately rather than adding a paragraph to the results.**

## Why a second pre-registration exists

Pre-registration #1 (`docs/03` §2, E1) fixed a gate on `Δ_AUC_net`, ran it at
n=300, and the gate **failed** — no watermark-specific effect on detector
*ranking*. That result stands and is reported as-is.

While fixing an unrelated bug (the `∅` null arm was being subtracted from
`Δ_AUC` but not from `Δ_μ`), a different quantity became visible for the
first time: `Δ_μ_net`, the location shift net of the null control. On a
36-image slice of the **test** split it came out at **+1.27 [+0.73, +1.86]**
and **+1.24 [+0.65, +1.87]** for the two schemes — intervals excluding zero.

That observation is **post-hoc**. It was not the gate's target, and
retargeting a gate after seeing data is exactly how a null becomes a false
positive. So it cannot be reported as a confirmed finding on the data that
produced it. What it *can* do is generate a hypothesis to test on data not
yet examined.

## What has and has not been looked at

| Split | n | Status |
| --- | --- | --- |
| `test` | 20,000 | **Contaminated for this hypothesis.** A 300-image subset was used for pre-registration #1, and a 36-image slice generated the `Δ_μ_net` observation above. Results on `test` are exploratory for H1/H2 below. |
| `validation` | 20,000 | **Never scored.** Confirmatory. |
| `train` | 100,000 | **Never scored.** Confirmatory for H1/H2, and the leakage diagnostic (H3). |

## Hypotheses, fixed in advance

**H1 (primary, confirmatory).** On the `validation` and `train` splits,
`Δ_μ_net` for at least one watermark scheme is non-zero, in the sense that
its 95% bootstrap CI excludes 0.

*Direction:* predicted **positive** (watermarking shifts the detector's score
toward "fake"), matching the sign seen on the exploratory slice. A
significant shift in the opposite direction counts as a **failure** of H1,
not a success, and will be reported as such.

*Effect size floor:* `|Δ_μ_net| ≥ 0.10` logits. Below that the effect is
declared negligible regardless of significance — at n≥20,000 a CI can exclude
zero for an effect too small to move any decision, and significance without
magnitude is not a finding.

**H2 (secondary, confirmatory).** On the same splits, `Δ_AUC_net` remains
within `±0.02` (the pre-registration #1 gate threshold) — i.e. the location
shift is **not** accompanied by a ranking effect.

*This is a prediction that the first null replicates at 60× the sample size.*
If `Δ_AUC_net` instead becomes clearly non-zero at n=120,000, then
pre-registration #1's null was a power failure and must be reported as such,
explicitly retracting the "no interference" reading.

**H3 (leakage diagnostic, confirmatory).** Baseline `AUC(W=0)` on `train`
minus the same on `test`, per detector. A gap `> 0.05` is read as evidence
the detector saw the train split during fine-tuning, and requires absolute
accuracies throughout the paper to be labelled contaminated.

*No direction is predicted.* This is a measurement, not a hypothesis with a
preferred answer.

## Analysis specified in advance

- `Δ_μ_net = Δ_μ(scheme) − Δ_μ(∅)`, with `∅` the PSNR-matched payload-free
  arm; `Δ_AUC_net` likewise. Both as implemented in
  `src/deepfake_interference/metrics.py` at this commit.
- 95% percentile bootstrap, 1,000 resamples, resampling **images** so an
  image's clean/scheme/null arms move together.
- Detectors: only those clearing the E0 floor (AUC ≥ 0.80 at `W=0`) on the
  split being analysed. A detector at chance produces noise, not a measurement.
- Splits analysed and reported separately. No pooling across splits, since
  the whole point of the split structure here is that the splits differ in
  contamination status.
- Every cell reported with its CI, whatever the outcome.

## Stopping rule

The corpus is fixed at all 140,000 images before scoring begins. The run does
not stop early on a favourable interim result, and shard-level checkpointing
exists for session limits, **not** as an opportunity to peek and halt.

## What a failure looks like

Written down now so it cannot be reframed later:

- H1 fails → the location shift was an artefact of a 36-image slice. The
  paper reports a null on both ranking *and* location, which is a cleaner and
  stronger negative result than the one currently drafted, not a worse one.
- H2 fails → pre-registration #1's null was underpowered. The paper leads
  with that correction.
- H1 holds and H2 holds → the paper's finding is that watermarking
  **translates** a detector's scores without **reordering** them: invisible to
  AUC, consequential for any threshold calibrated on unmarked media. This is
  the calibration thesis, confirmed on data never used to generate it.
