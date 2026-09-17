# Tier 2 resource plan (planning estimates — not measured)

**Status: Tier 2 has not been started.** No Tier 2 code exists in this
repository. Per `docs/09-cli-handoff-context.md`, an active-adversarial
watermark-removal project was discussed in a prior chat session but was
never written to a repo file, and explicitly begins only after Tier 1 (this
manuscript) is submitted, not in parallel. This document is planning
material for that future work, written now so the plan is reviewed before
any of it is executed — the same pattern `docs/07-h100-panel-expansion-plan.md`
used for the Tier 1 panel expansion.

## Research question

Can an active adversary deliberately remove or damage a provenance watermark
through generative optimization while keeping perceptual degradation within
an acceptable budget?

## Phased plan

Every VRAM/RAM/storage figure below is an **estimate range**, explicitly not
a measurement. The actual numbers from the 10- and 100-image phases must
replace these ranges in any future research document before they are cited
as fact.

| Phase | Image count | Resolution | Est. VRAM | Est. RAM | Est. NVMe | RTX 3050 feasibility | 1×H100 feasibility | 8×H100 feasibility | Purpose | Success condition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Prototype | 10 | 256×256 | ~3–8 GB | 8–16 GB | <5 GB | Possible | Overkill but fine | Overkill | Confirm the attack loop runs end-to-end and produces a measurable BER/PSNR/SSIM change | Attack loop executes without crashing; metrics are logged per image |
| Pilot | 100 | 256×256 | ~6–12 GB | 16–32 GB | 20–50 GB | Possible only if memory-optimized (gradient checkpointing, small batch, reduced precision) | Recommended | Not needed at this scale | Establish whether the attack reliably degrades the watermark at an acceptable perceptual cost, across a small but real sample | Attack success rate and perceptual-budget trade-off are characterized well enough to size the production run |
| Production | 1,000 | 256×256 or 512×512 | ~12–24+ GB | 32–64 GB | 100–250 GB | Not expected to be feasible | Strongly recommended | Feasible, shortens wall clock | Run the full planned matrix: 2 watermark schemes × 3 attack strengths × 3 seeds × 1,000 images = 18,000 trajectories | Statistically stable attack-success and quality-degradation estimates across the matrix |
| Expanded (512×512, multi-seed) | larger than production | 512×512 | ~16–40+ GB | 64–128 GB | 200–500 GB | No | Constrained | Recommended | Only pursued after production-phase results justify a larger validation run | Confirms production-phase findings hold at higher resolution / larger sample |

## Ordering constraint

The 18,000-trajectory production matrix (1,000 × 2 × 3 × 3) is **not** to be
run before the 10-image and 100-image pilots establish that the attack
implementation actually works. This mirrors the discipline already present
in the Tier 1 project history (e.g., `docs/09`'s "Rejected scope" list, and
the E0 floor-check-before-interference-measurement ordering in
`docs/03-experiment-plan.md`) — compute availability is not a reason to skip
validating the method at small scale first.

## What to measure during the 10- and 100-image phases

Per-image, not aggregated only:

- Peak VRAM
- Wall-clock runtime
- Diffusion steps used
- Attack iterations
- BER change (pre/post attack)
- PSNR, SSIM, and a learned perceptual distance metric
- Attack success/failure under whatever budget is defined for that run

## Storage discipline

Do not save every diffusion intermediate image from every attack step —
this can produce unbounded storage growth over an 18,000-trajectory matrix.
Store per-trajectory: image identifier, content hash, watermark scheme,
attack configuration, seed, iteration count, BER/PSNR/SSIM/perceptual
metrics, success/failure, runtime, peak VRAM, and a configuration hash.
Save full intermediate image sequences only for a small diagnostic subset,
not the whole matrix — matching Tier 1's own `.gitignore` discipline of
keeping large regenerable artifacts (raw images, feature caches) out of
version control while keeping the small, information-dense measurement
files.

## H100 justification, stated correctly

The correct justification, if and when it is used, is: "the experimental
matrix contains many independent iterative generative optimization
trajectories, making distributed GPU execution useful for practical
turnaround" — not "we have a big GPU." That justification is only made after
the pilot phases produce real measured per-trajectory VRAM and runtime
numbers; until then this document's ranges are placeholders for sizing
discussion, not a resource request.
