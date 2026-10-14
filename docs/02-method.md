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
| `W ∈ {0,1}` | watermark presence indicator (0 = Legacy Media Bypass path). **Observable, not inferred** — `W = 1` iff the payload's signature verifies (§2.1) |
| `S` | watermark scheme identity, when `W = 1`. Includes the null-perturbation control arm `S = ∅` (§3.1) |
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

**The `p_0` selection problem — an inference-time dependency, stated not hidden.**
Per-transform-class `p_0` presumes the transform class is *known* at scoring time.
In evaluation it is, because we apply `T` ourselves. In deployment it is not: a
file arrives having been through an unknown channel. Three honest resolutions,
and v1 takes the third:

1. Marginalise: `p(k_e | H_P) = Σ_t π(t) · Binomial(k_e; L, p_0(t))` over a prior
   `π` on transform classes. Correct, but requires a deployment-specific `π`.
2. Infer the transform class first, which imports a second classifier and its
   errors into the provenance path.
3. **Pooled `p_0`**, one value per scheme across all transform classes, and report
   the cost. This is what v1 uses. The per-transform values are reported alongside
   as an *oracle-informed upper bound* on how much sharper `z_P` could be, which
   makes the gap between pooled and oracle a measured quantity rather than an
   unstated assumption.

Whichever is used, the claim in the bullet above that `p_0` is "*not* assumed"
holds only for the estimation of `p_0`; **which** `p_0` applies to a given item is
a modelling choice, and pretending otherwise would smuggle an assumption back in
through the side door.

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

**The signature also makes `W` identifiable, which the fusion needs.** Without it,
"is this watermarked?" would be answered by thresholding BER — but `z_P` is *also*
a function of BER, so `W` and the provenance evidence would be two readings of one
measurement, and `β₁` and `β₃` in §4 would be entangled by construction. Signature
verification breaks that: it is a test whose false-accept rate is ~2^-128 and
which is **independent of `b`**. `W` becomes genuinely observed rather than
inferred, and `F2`/`F3` are identifiable.

This upgrades §2.1 from a security fix into a load-bearing part of the method.
Its *forgery-resistance* still awaits the overwrite-attack evaluation deferred in
`docs/03` §6; its *identifiability* role needs no experiment, only a correct
argument.

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

### 3.1 The null-perturbation control (`S = ∅`)

A bare `Δ_AUC < 0` does **not** establish interference. It is equally consistent
with two hypotheses:

- **H_interference** — the watermark's *structure* overlaps the forgery cues the
  detector relies on. This is the paper's claim, and Wu et al.'s.
- **H_brittle** — the detector degrades under *any* imperceptible perturbation,
  and a watermark is merely one instance. Nothing about watermarking specifically.

H_brittle is the more likely null in this setup, because v1's detectors are
zero-shot and were trained on clean images: watermarking is an unseen distribution
shift regardless of what the watermark encodes. A design that cannot separate these
two is not measuring what the paper says it measures, and this is the first
objection a reviewer will raise.

**Control.** Add a third level to `S`: a payload-free perturbation `∅`, drawn as
random noise (or a random DCT-domain perturbation) whose energy is tuned per image
so that PSNR and SSIM match the watermarked arm within a stated tolerance. It is a
watermark in every respect the detector can see *except* that it carries no
structured payload. Then report

```
Δ_AUC_net(s)  =  Δ_AUC(s)  −  Δ_AUC(∅)
```

| Observation | Reading |
| --- | --- |
| `Δ_AUC(s) ≈ Δ_AUC(∅)` | No watermark-specific interference. The reported effect is generic perturbation brittleness — a **sharper negative result** than the field currently has, and still publishable (see `docs/04` R1's fallback framing) |
| `Δ_AUC(s) ≪ Δ_AUC(∅)` | Structured interference beyond energy alone. The paper's claim, now defended against its main objection |

`Δ_AUC_net`, not `Δ_AUC`, is therefore the headline quantity of E1, and the control
runs **inside** the go/no-go gate rather than as an extension. The matching
machinery already exists — PSNR/SSIM are computed for the T5 imperceptibility
controls, so the marginal cost is hours, not days.

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

**But a wider band is not automatically a better one.** `τ_lo = 0.01`,
`τ_hi = 0.95` routes everything between those bounds to a human, which on a
realistic score distribution is most of the traffic — a system that abstains on
the large majority of its inputs has not automated much. The cost model is
therefore incomplete on its own: it prices errors but not reviewer capacity,
which in any real deployment is the binding constraint.

So the operational framing inverts. Rather than deriving `τ` from costs and
discovering the coverage after the fact, **fix coverage at what review capacity can
absorb and report the risk that buys** — which is exactly what E3's selective risk
at coverage {0.8, 0.9, 0.95} measures. Chow's rule remains the right derivation of
*where* the thresholds go for a given cost model; the coverage constraint decides
*which* cost models are deployable at all. Both are reported, and any cost model
quoted in the paper carries its realised coverage next to it.

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
