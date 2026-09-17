# Hardware requirements

## Tier 1 (this manuscript: watermark–detector interference)

Tier 1's method is inference-only: frozen backbones, linear-head scoring,
watermark embed/extract, PSNR/spectrum-matched controls, bootstrap
resampling. No generative model training, no gradient-based attack
optimization, no diffusion sampling occurs anywhere in this pipeline.

**What actually ran this study:** one RTX 3050 (6GB) laptop GPU plus
Kaggle's free-tier T4 as overflow (`docs/00`, `README.md`), with CPU-only
fallback for the smallest runs. Measured (not estimated) throughput on a
4-core CPU sandbox, from `docs/09-cli-handoff-context.md`: ConvNeXt-Base
~10.4 img/s, ViT-B/16 ~10.1 img/s. The 20,000-image confirmatory run, the
800-image 4-detector panel, and the 9,600-measurement manipulation grid were
all completed on this hardware tier — they are not aspirational.

Tier 1 does not need, and this repository makes no claim that it needs,
server-class GPU hardware. A consumer GPU or a free-tier cloud notebook is
sufficient for every experiment in `paper/main.tex`.

Practical minimums:

- **RAM:** 8–16 GB (frozen backbone feature extraction, batched).
- **VRAM:** not required at all for CPU-only runs; 4–6 GB comfortable
  headroom for GPU-accelerated feature extraction with ConvNeXt-Base/ViT-B/16
  at batch sizes that fit a 6 GB card.
- **Storage:** dataset subset (tens of thousands of 256×256 PNGs) plus
  `results/` (~21 MB of raw JSON scores, intentionally not gitignored — see
  `.gitignore` comment) plus `cache/features/` (regenerable, gitignored,
  can reach several GB depending on how many backbone/split combinations are
  cached simultaneously).
- **No multi-GPU, no H100, no distributed training** is used or claimed
  anywhere in Tier 1.

## Tier 2 (separate project: active adversarial watermark removal)

Tier 2 has not started — see `docs/tier2_resource_plan.md` and the
"Rejected scope" section of `docs/09-cli-handoff-context.md`. It has a
different computational profile because its research question is different:
whether an adversary can *actively* damage a provenance watermark through
gradient-based optimization over a generative (likely diffusion) trajectory,
subject to a perceptual-degradation budget. That is an iterative optimization
workload per image, not a single forward pass.

**What genuinely runs on an RTX 3050:**

- Environment setup and dependency validation.
- Watermark embed/extract/BER validation (identical code path to Tier 1).
- Small-scale debugging (single-image forward/backward passes through a
  diffusion model to confirm the attack loop is wired correctly).
- A 10-image development experiment at 256×256.
- Possibly a 100-image pilot at 256×256 if memory-optimized (gradient
  checkpointing, small batch, fp16/bf16) — not guaranteed, to be measured,
  not assumed.

**Why production-scale sweeps benefit from H100-class hardware, stated as a
scientific justification rather than an assertion of need:**

The experimental matrix contains many independent iterative generative
optimization trajectories — the planned 1,000-image × 2-scheme × 3-strength ×
3-seed matrix is 18,000 trajectories (`docs/tier2_resource_plan.md`). Each
trajectory requires backpropagating through multiple diffusion steps, which
is far more VRAM- and compute-intensive per sample than Tier 1's single
forward pass. Larger VRAM allows larger batches per trajectory and more
trajectories in flight at once; more/faster GPUs shorten wall-clock turnaround
across the matrix. This is a throughput argument, not a claim that any
individual Tier 2 stage is impossible on smaller hardware — the 10- and
100-image pilots specifically are designed to run on the RTX 3050 first, and
H100 access is not requested or justified until those pilots establish that
the attack implementation actually works and produce measured (not
estimated) VRAM/runtime numbers to size the production run.

**What Tier 2 does not justify:** "we have a big GPU" is not a stated reason
anywhere in this repository's planning documents for using H100 hardware, and
this document does not introduce that framing either.
