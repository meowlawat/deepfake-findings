# Code map and how to run it

Everything under `src/deepfake_interference/` implements a named quantity
from `docs/02-method.md`; every module's docstring cites the section it
implements, so the paper's equations and the code that produces numbers for
it cannot silently drift apart. `scripts/` are thin orchestration on top.

## Status as of this session

Verified by actually running it, not by plan:

- **Watermarking** (`watermark.py`): `DwtDctSvd` and `RivaGan` (both via
  `invisible-watermark`) embed/extract round-trip correctly. RivaGan's ONNX
  weights ship inside the pip package - no download, no training - but need
  `onnxruntime` added explicitly (`requirements.txt` has it).
- **Detectors** (`detectors.py`): `Wvolf/ViT_Deepfake_Detection` (ViT) and
  `Skullly/DeepFake-EN-B6` (EfficientNet-B6) both load via `transformers` and
  produce genuine two-class logits. This resolves a real gap in the original
  `docs/03` draft, whose three ViT candidates all shared one backbone family.
  **Both carry an unresolved training-data leakage risk - see `docs/04` R14.**
- **Crypto binding** (`crypto_binding.py`): implements docs/02 S2.1 with one
  necessary design correction discovered while building it - the Ed25519
  signature does not fit in-band alongside a 32-bit watermark payload, so the
  payload carries a key-ID only and the signature lives in an out-of-band
  `ProvenanceRegistry`, the same pattern C2PA uses. **Measured, not assumed,
  false-negative rate on synthetic photo-like content was 62.5% in one run -
  see `docs/04` R15.** This does not block the interference/fusion
  experiments, which use ground-truth `W` (docs/02 S2.1's original
  "verification observes W" framing does not hold operationally yet).
- **Null-perturbation control** (`null_perturbation.py`): PSNR-matched
  payload-free noise, per docs/02 S3.1 / docs/04 R11. Binary-search matching
  verified to land within ~1dB of target.
- **Metrics, fusion, stats** (`metrics.py`, `fusion.py`, `stats.py`): every
  quantity named in docs/02 - `z_P`, `Delta_mu/sigma/AUC/AUC_net`, ECE,
  `Delta-ECE_W`, Chow thresholds, DRD, AURC, selective risk, the F0-F5 fusion
  models and `beta_4` (the interference coefficient) - implemented and unit
  tested, including a from-first-principles check that Chow's rule reproduces
  both the source design's 0.35/0.65 band and docs/02's plausible
  0.01/0.95 example from their respective cost assumptions.
- **E1 gate** (`scripts/e1_interference.py`): runs end-to-end (data load ->
  embed both schemes + null arm -> score with both detectors -> interference
  table -> gate verdict -> JSON). Smoke-tested on a tiny synthetic dataset in
  this session; **not yet run on the real dataset**, which requires the
  Kaggle account that lives on the local machine, not this environment.

- **Dataset** (`scripts/fetch_dataset.py`): the Kaggle account turned out to
  be unnecessary. `TheKernel01/140k-Real-and-Fake-Faces` on the HF Hub
  mirrors the same corpus (140k images, real/fake labels, a `generator`
  field separating Real from StyleGAN, license `cc`), and the script streams
  a balanced subset rather than pulling the full ~4GB.
- **E0/E1** (`scripts/e1_interference.py`): E0's floor check is computed
  inside this script from the clean-arm scores it already gathers, rather
  than as a separate pass - including the docs/04 R14 leakage flag, where a
  baseline AUC above the configured suspicion threshold is reported as
  suspect rather than celebrated.
- **E2-E6** (`scripts/e2_e3_fusion.py`, `e4_e5_transforms_rho.py`,
  `e6_ablations.py`) plus `scripts/make_report.py`, which emits the paper's
  LaTeX tables and figures from the result JSONs.
- All experiment scripts take `--limit N` for a stratified smoke run. That
  flag exists because the first version sliced `items[:N]` after
  `data.discover()` had already grouped by class, so every dry run was
  silently single-class and every AUC came back NaN.

## Running it

```bash
pip install -r requirements.txt
PYTHONPATH=src python3 -m pytest tests/ -q          # 27 tests, ~5s, no GPU/network needed

python3 scripts/00_verify_tooling.py                 # confirms the environment can run everything above
# place the Kaggle dataset (docs/03 S0) as data/raw/{real,fake}/*.jpg, then:
python3 scripts/e1_interference.py --config config.yaml --limit 50   # fast dry run
python3 scripts/e1_interference.py --config config.yaml              # full E1 gate
```

`config.yaml` is the single source of truth for every constant a script
uses - dataset path, schemes, detector model IDs, transform grid, cost
model, bootstrap settings. Change it there, not in script arguments, so a
run's configuration is always reconstructible from one file plus a git commit.

## Design corrections made while implementing (not visible from the docs alone)

Three things changed between "the method as written" and "the method as it
actually runs," each because running the code surfaced a problem the prose
didn't catch:

1. **Payload capacity vs. signature size** (`crypto_binding.py`). Fixed by
   moving the signature out-of-band, keyed by a short in-band key-ID.
2. **`log_likelihood_ratio`'s zero-crossing is not at `k_e = L/2`** for small
   `p_0` - it's much closer to `k_e = 0`. This was a wrong intuition baked
   into an early test, not a code bug; the test now asserts the actual
   mathematical behaviour (`tests/test_fusion.py`).
3. **A location shift in V is not what `beta_4` (F3's interaction term)
   measures** - it's what `beta_3` (F2's presence term) measures. An earlier
   synthetic-data test conflated the two and consequently "failed" for the
   right reason: it was checking for the wrong effect. Fixed by generating
   test data forward through the actual logistic model with a designed
   `beta_4`, rather than backward from a confounded causal story.

All three are the kind of bug that a plan-only document cannot catch - they
only showed up once equations became code that had to actually run.
