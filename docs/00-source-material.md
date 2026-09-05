# Source material (preserved verbatim)

Text extracted from the two PDFs this project started from. Kept unedited so
the original design intent stays auditable as the work diverges from it.

## 1. `deepfake_findings.pdf` — architecture and technique outline

```

--- PAGE 1 =====
System Architecture 
Phase 1: Content Creation 
1.Input original media (image/video) 
2.Apply robust watermarking 
◦ Invisible watermark embedded 
◦ Encrypted for security 
Phase 2: Distribution 
• Media shared across platforms 
• May undergo: 
◦ Compression 
◦ Editing 
◦ Deepfake manipulation 
Phase 3: Verification & Detection 
Step 1: Watermark Extraction 
• Check: 
◦ Is watermark present? 
◦ Has it been altered? 
Step 2: AI-Based Detection 
• CNN / Transformer analyzes: 
◦ Facial inconsistencies 
◦ Texture artifacts 
◦ Temporal anomalies 
Step 3: Decision Engine 
• Combine both outputs: 
◦ Authentic  
◦ Tampered  
◦ Deepfake  
--- PAGE 2 =====
Techniques that can be used for better results 
 1. Watermarking Techniques 
Use hybrid transform-based methods: 
• DWT (Discrete Wavelet Transform) 
• SVD (Singular Value Decomposition) 
• DCT (Discrete Cosine Transform) 
2. Encryption Layer 
• Advanced Encryption Standard (Prevents attackers from forging the watermark) 
3. AI Detection Models 
Options: 
• CNN (ResNet, EfficientNet) 
• Vision Transformer (ViT) 
• CNN + LSTM (for video) 
Can Detect: 
• Face warping 
• Lighting mismatch 
• Eye/blink anomalies 
Challenges 
1. Watermark Robustness 
◦ Compression 
◦ Cropping 
◦ Deepfake transformations 
2. Synchronization Problem 
• Deepfake may distort watermark location 
3.  Adaptive Attacks 
• Attackers may: 
◦ Remove watermark 
◦ Inject fake watermark 
--- PAGE 3 =====
Evaluation Metrics 
 Watermarking Metrics 
• PSNR (image quality) 
• SSIM (structural similarity) 
• Bit Error Rate (BER) 
Detection Metrics 
• Accuracy 
• Precision / Recall 
• F1 Score 
• ROC-AUC 
•```

## 2. `Media_Score_Calculation.pdf` — pipeline flowchart (node labels)

```

--- PAGE 1 =====
Yes (Check Watermark)
No (Legacy Media Bypass)
ŷ  < 0.35 0.35 ≤  ŷ  ≤  0.65ŷ  > 0.65
Raw Media Input
Hardware-Aware 
Preprocessing
CPU/NVMe I/O
Extract I-Frames
Trusted Source
Acquisition?
DWT-SVD Extraction
AES-256 Decryption
Calculate Bit Error Rate BER
Provenance Score: P
ViT + LoRA Inference
Spatial Anomaly Score: V
Learned Meta-Classifier
Logistic Regression
Calculate Probability: ŷ
Dynamic Thresholding
Authentic
 Inconclusive / Manual 
Review
Deepfake
Forensic Explainability XAI
Attention Rollout Heatmaps```

## Reading of the flowchart

The second PDF is a single-page decision flow. Reconstructed control flow:

1. Raw media input -> hardware-aware preprocessing (CPU/NVMe I/O) -> extract I-frames.
2. Branch on `Trusted Source Acquisition?`
   - **Yes** -> DWT-SVD extraction -> AES-256 decryption -> bit error rate (BER)
     -> provenance score `P`.
   - **No** -> "Legacy Media Bypass" — the provenance branch is skipped entirely.
3. In parallel: ViT + LoRA inference -> spatial anomaly score `V`.
4. `P` and `V` -> logistic regression ("learned meta-classifier") -> probability `y-hat`.
5. Dynamic thresholding on `y-hat`:
   - `y-hat < 0.35` -> Authentic
   - `0.35 <= y-hat <= 0.65` -> Inconclusive / manual review
   - `y-hat > 0.65` -> Deepfake
6. Forensic explainability via attention-rollout heatmaps.

Note the score orientation: low `y-hat` means authentic, high means deepfake.
This is preserved throughout `docs/02-method.md`.

Four properties of this diagram drive the rest of the project:

- The `Legacy Media Bypass` branch means most real-world media never touches the
  provenance channel, so the watermark half contributes nothing on that traffic.
  The watermarked fraction of the evaluation set is therefore a first-class
  experimental variable, not a footnote.
- The 0.35/0.65 band is fixed, which contradicts the box labelled "Dynamic
  Thresholding". Either it is derived from something, or the word is wrong.
- AES-256 provides confidentiality of the payload. It provides neither
  unforgeability nor removal-resistance, which are the two properties the
  threat model actually needs.
- `P` and `V` are computed from the same pixels, so feeding them to a logistic
  regression as if they were independent evidence is an assumption, not a given.
