# Method

Notation follows the source flowchart's orientation: **`y_hat` near 1 means
deepfake, near 0 means authentic.**

## 1. Setup and notation

| Symbol | Meaning |
| --- | --- |
| `x` | media item (image, or an I-frame of a video) |
| `m ∈ {0,1}^L` | watermark payload, `L` bits |
| `E, X` | watermark embedder / extractor |
| `x̃ = E(x, m, k)` | watermarked media under key material `k` |
| `T` | channel transform: compression, resize, crop, colour shift, re-encode |
| `D` | deepfake manipulation (face swap, reenactment, diffusion edit) |
| `W ∈ {0,1}` | watermark presence indicator (0 = Legacy Media Bypass path) |
| `S` | watermark scheme identity, when `W = 1` |
| `b` | measured bit error rate of the recovered payload |
| `V ∈ ℝ` | passive detector score — **raw logit, not softmax probability** |
| `Y ∈ {0,1}` | ground truth, 1 = manipulated |
| `y_hat` | fused posterior `P(Y = 1 | evidence)` |

Using the raw logit for `V` is deliberate. Softmax-normalised confidences are
known to be unreliable under perturbation and out-of-distribution input, which is
the regime this system operates in; calibration is applied once, at the fusion
stage, rather than inherited from an uncalibrated per-detector softmax.

## 2. Provenance evidence: from BER to a likelihood ratio

The source design used BER directly. Replace it with a likelihood ratio, which is
the quantity fusion actually needs and costs nothing extra to compute.

Let `k_e = b·L` be the observed number of bit errors. Two hypotheses:

- `H_P` (**intact provenance**): the payload survived an authentic distribution
  channel. Bit errors are channel noise: `k_e ~ Binomial(L, p_0)`, with `p_0` the
  scheme's residual error rate, estimated on a held-out clean-transform calibration
  set — *not* assumed.
- `H_0` (**no valid provenance**): the mark is absent, destroyed, or forged under
  a key we do not hold, so recovered bits are uninformative: `k_e ~ Binomial(L, ½)`.

The provenance log-likelihood ratio is

```
z_P  =  log [ p_0^{k_e} (1-p_0)^{L-k_e} ]  -  log [ (1/2)^L ]
     =  L·log 2  +  k_e·log p_0  +  (L - k_e)·log(1 - p_0)
```

Properties that matter:

- `z_P` is in log-odds units, so it enters a logistic fusion additively and
  the fitted coefficient is directly readable as "how much this evidence is
  trusted".
- It is monotone decreasing in `k_e`, and it is **calibrated in `L`**: a 64-bit
  and a 256-bit payload with the same BER produce different, correctly scaled
  evidence. Raw BER discards this.
- `p_0` is measured per scheme and per transform class, which makes the
  robustness weakness of any given scheme show up *as reduced evidence strength*
  rather than as silent corruption of the score.

`z_P` is defined only when `W = 1`. When `W = 0` it is **missing, not zero** —
§4 treats this properly, because conflating the two is one of the concrete flaws
in the original design.

### 2.1 Cryptographic binding (replaces the AES-256 box)

AES-256 gives payload confidentiality. The threat model needs *unforgeability*.
Payload becomes:

```
m = ID_key ‖ sig ,   sig = Ed25519_sign(sk, H(perceptual_hash(x) ‖ ID_key ‖ ts))
```

Verification is public-key, so every verifier can check provenance without
holding a secret that would let them forge it. This directly addresses the
"attacker injects a fake watermark" challenge listed in the source material,
which a symmetric cipher does not. AES is retained only where the payload itself
must be confidential, and the key-distribution model is stated explicitly rather
than assumed.

## 3. Passive evidence and the interference it carries

`V = f_θ(T(D(x̃)))` — the detector sees watermarked pixels. Published work
(Wu et al., IJCAI 2024; Müller & Debus, audio) reports that the watermark signal
overlaps with the forgery signal the detector relies on. Define, for scheme `s`
and class `y`, the **interference shift** and **discriminative interference**:

```
Δ_μ(s, y) = E[ V | W=1, S=s, Y=y ]  −  E[ V | W=0, Y=y ]
Δ_σ(s, y) = sd[ V | W=1, S=s, Y=y ] / sd[ V | W=0, Y=y ]
Δ_AUC(s)  = AUC( V ; W=1, S=s )     −  AUC( V ; W=0 )
```

`Δ_μ ≠ 0` is a location shift, `Δ_σ ≠ 1` a scale change; either breaks a fusion
calibrated on unwatermarked data. `Δ_AUC < 0` is the effect Wu et al. report.
These three quantities are the paper's primary measurements — Experiment E1.

## 4. Fusion models

All are logistic in the evidence, deliberately. Interpretability is the point:
the interference must be legible as a coefficient, not buried in a network.

| ID | Model | Purpose |
| --- | --- | --- |
| `F0` | `σ(β₀ + β₂V)` | detector-only baseline |
| `F1` | `σ(β₀ + β₁ z_P + β₂V)`, `z_P := 0` when `W=0` | **the naive fusion of the source design** — treats missing provenance as neutral evidence and assumes independence |
| `F2` | `F1 + β₃W` | presence-aware: corrects the intercept, not the slope |
| `F3` | `F2 + β₄(W·V)` | **interference-aware (proposed).** The detector's weight is allowed to differ on watermarked media |
| `F4` | `F3 + β₅(b·V)` | degradation-aware: heavy channel damage shifts both scores; `b` is an observable proxy |
| `F5` | `F3` + per-group post-hoc calibration (separate Platt/temperature for `W=0`, `W=1`, optionally per `S`) | decouples fusion from calibration |

**The empirical claim of the paper is `β₄ ≠ 0`,** with an effect size large
enough to move calibration. `β₄` is exactly the coefficient that the independence
assumption forces to zero, so a significant `β₄` *is* the measurement of
interference in the fusion, reported with confidence intervals from a
cluster-bootstrap over source identities (not over frames — frames within a video
are not independent).

`F5` is what a deployment would ship; `F3` is what makes the argument.

## 5. Decision rule: deriving the band instead of asserting it

Costs: `c_FN` (a manipulated item accepted as authentic), `c_FP` (an authentic
item declared fake), `c_R` (routing to human review). Expected costs:

```
declare Authentic :  y_hat · c_FN
declare Deepfake  :  (1 − y_hat) · c_FP
abstain           :  c_R
```

Minimising gives **Chow's rule**:

```
Authentic    if  y_hat < τ_lo = c_R / c_FN
Deepfake     if  y_hat > τ_hi = 1 − c_R / c_FP
Review       otherwise
```

with a non-empty review band iff `c_R/c_FN + c_R/c_FP < 1`.

**What the source design's 0.35/0.65 band implies.** Solving backwards:
`c_R = 0.35·c_FN` and `c_R = 0.35·c_FP`, i.e. symmetric error costs and a human
review costing 35% of a forensic error. In a setting where a missed deepfake can
carry legal or reputational consequence, that is not a defensible cost model. A
plausible one — `c_R = 1`, `c_FP = 20`, `c_FN = 100` — yields `τ_lo = 0.01`,
`τ_hi = 0.95`, a far wider review band. The constants were never the problem;
the absence of a model behind them was. With the model stated, "dynamic
thresholding" becomes literally true: `τ` moves with the deployment's costs.

**The load-bearing dependency.** Chow's rule is optimal *only if `y_hat` is
calibrated*. If interference miscalibrates `y_hat` on watermarked media, the
derived thresholds do not deliver the risk they were derived for — on exactly the
traffic the provenance system exists to protect. This is the through-line from
§3 to the contribution.

## 6. Metrics

**Interference (E1):** `Δ_μ`, `Δ_σ`, `Δ_AUC` per (scheme × detector × class).

**Calibration (E2/E3):** ECE (equal-mass bins), adaptive ECE, Brier score, and
the headline quantity

```
ΔECE_W  =  ECE( y_hat | W=1 )  −  ECE( y_hat | W=0 )
```

the **calibration gap induced by watermarking**. Reliability diagrams plotted per
group, never pooled — pooling hides exactly the effect under study.

**Decision quality (E3/E4):** risk-coverage curves, AURC, selective risk at fixed
coverage {0.8, 0.9, 0.95}, and

```
DRD  =  | realised risk under (τ_lo, τ_hi)  −  risk targeted by the cost model |
```

*Decision Risk Deviation* — how far the deployed rule lands from the risk it was
designed for. This is the number that makes miscalibration operationally
concrete rather than an abstract plot.

**Watermark quality (reported, not optimised):** PSNR, SSIM, BER — as in the
source material, but as controls confirming schemes are compared at matched
imperceptibility, not as results.
