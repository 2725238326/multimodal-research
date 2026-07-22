# Experiment: `material_response_probe_v0`

## Decision

- Owner: TBD
- Date: 2026-07-22
- Status: Planned
- Decision requested: Decide whether multi-illumination response features contain material information beyond invariant or single-RGB frozen features before any teacher/student training.

## Research contract

- Research question: For the existing material constancy regions, does controlled illumination response add reliable material-discriminative information beyond single RGB or illumination-invariant summaries?
- Falsifiable hypothesis: A shallow classifier using multi-light response features will improve region-level material accuracy and reduce cross-light answer flips relative to the best single-RGB frozen-feature baseline, while shuffled or wrong-region controls will not.
- Track: Exploratory gate before confirmatory training.
- Design patterns used: RP-01 falsifiable contract, RP-02 evidence ladder, RP-03 strong simple baseline, RP-04 single mechanism increment, RP-05 counterfactual controls, RP-08 invariant-response factorization, RP-09 quality/conflict-aware routing, RP-12 reproducible experiment capsule.
- Existing failure being addressed: Frozen VLM RGB+albedo, intrinsic text, and shared region markers did not produce cross-model stable gains; direct prompting is already No-Go.
- Closest prior work and collision risk: MINC/OpenSurfaces for material recognition data; IIW and Intrinsic Image Diffusion/Fusion for intrinsic cues; C2KD for cross-modal distillation; LEO/Eyes Wide Shut for multi-encoder visual feature gaps; SAIL/UniPrior for invariant representations; VLMaterial and multimodal material segmentation work for semantic proposal plus physical verification. The remaining claim is not "multi-modal fusion works"; it is whether this repository's multi-light response signal passes a cheap local gate under wrong/shuffled controls.
- Novel claim after collision check: If supported, the project may claim a local gate showing material identity should be modeled as invariant identity plus discriminative illumination response before selective privileged distillation. This does not claim a final trained system yet.
- Go threshold: On the full 66-region gate, the best response condition must improve mean region accuracy over the best single-RGB frozen-feature condition by at least 5 percentage points with paired scene/bootstrap 95% CI lower bound above 0, reduce region flip rate by at least 10 percentage points with CI upper bound below 0, and beat each wrong/shuffled/random control by at least 3 percentage points on accuracy.
- No-Go threshold: Stop if response features do not beat the best single-RGB baseline, if confidence intervals cross 0 on the primary gain, if shuffled/wrong controls match the gain, or if macro class accuracy drops by more than 2 percentage points.
- Complexity / compute budget: 1-2 day gate; frozen encoders only, cached features, shallow linear/logistic or small MLP heads, no LoRA, no VLM prompting expansion, no new data download.

## Mechanism and modality roles

| Component / modality | Role | Information available | May it determine the target? |
| --- | --- | --- | --- |
| RGB crop | Measurement | Target-region appearance under one light | Yes, as baseline measurement |
| Multi-light RGB crops | Measurement | Same region under selected light directions | Yes, only through measured response features |
| Estimated albedo | Measurement / Verifier | Current Marigold IID albedo estimate aligned to target crop | No by itself; it must pass controls and cannot override observed response |
| RGB/albedo residual | Verifier | Difference between observed RGB and estimated stable appearance | No by itself; used to test response signal |
| Frozen DINO / SigLIP / CLIP features | Measurement | Visual embeddings extracted from crop or region | Yes through shallow heads only |
| Candidate material labels | Prior | Closed label set from existing manifest | No; labels constrain output space but cannot replace measurements |
| Reliability score / router | Router | Observable quality, confidence, conflict between branches | No; may select or reject branch, not invent target evidence |

- Semantic authority boundary: Semantics only names classes and optionally supplies interpretable attributes after measurement. It cannot infer material from object co-occurrence.
- Physical verification or veto: Wrong-region albedo, shuffled light pairing, random residual, and information-matched irrelevant evidence must fail to match the correct response condition.
- Deployment-time inputs: Final target remains RGB-only; this gate may use multi-light/albedo as training-time privileged inputs only.
- Cross-domain mechanism source: Intrinsic image estimation, multimodal material segmentation, calibration/selective prediction, and cross-modal distillation.
- Assumptions that do not transfer: Other datasets' material labels, multi-view availability, polarization/radar/depth sensor availability, and any paper's trained model performance.

## Data

- Dataset and version: Existing MIT Multi-Illumination-derived material constancy gate v2 assets in this repository.
- Source URL: Original source recorded in existing build script as `https://data.csail.mit.edu/multilum`; license and allowed use still need an explicit project-level record before confirmatory claims.
- License / allowed use: Needs verification before any publication or upstream distribution.
- Local asset location: `data/raw/`, `data/processed/material_constancy_rgb_gate_v2/`, `data/processed/material_constancy_albedo_v1/` remain local/tracked-history assets; new generated manifests remain ignored.
- Manifest hash:
  - RGB gate v2: `0651737375c61300bd60055e70e155c627a855e09bf1cfcf11ffcb13112f9828`
  - Albedo v1: `c3b52b82589e22b2fc8b02cdd7b2b0b89c1b8ec716bf465ef69f9c853cd297d2`
- Split: scene-grouped split; no crop from a scene may appear in both train and test for a confirmatory run.
- Samples: Full gate has 330 samples.
- Independent scenes / objects / regions: 30 scenes / 66 regions. Statistical unit is region; bootstrap should be scene-aware when possible.
- Leakage checks: Verify no sample ID duplicates, no region crosses scene split, each region has multiple light directions, all path fields are repository-relative in newly generated smoke manifests, and all controls preserve labels while breaking the intended evidence.

## Model and code

- Model ID: Candidate frozen families are SigLIP, DINOv2/DINOv3, and CLIP. Exact model IDs, local paths, revisions, and licenses must be resolved in a local override before feature extraction.
- Weight source and revision: TBD; record exact Hugging Face or official source revision before running beyond manifest smoke.
- License: TBD per selected encoder.
- Repository commit: Record `git rev-parse HEAD` before execution.
- Environment lock: Not yet complete. This prep stage only uses Python standard library for manifest/test checks.
- Device: Manifest preparation is CPU-only; later feature extraction may use GPU but must record device and batch settings.

## Conditions and metrics

| Condition | Purpose | Changed variable |
| --- | --- | --- |
| Single RGB frozen feature | Strong simple baseline | One light crop only |
| Multi-light mean | Invariant summary | Average same-region frozen features over lights |
| Multi-light mean + variance | Simple response summary | Adds light-driven feature variance |
| Pairwise response | Main intervention | Adds directed differences between same-region lights |
| RGB + albedo | Prior No-Go bridge | Re-tests old intervention through shallow trained head |
| RGB + RGB/albedo residual | Physical-response proxy | Tests whether residual carries material signal |
| Shuffled light pair | Negative control | Breaks same-region illumination pairing |
| Wrong-region albedo | Negative control | Preserves extra image evidence but misaligns material evidence |
| Random residual | Negative control | Preserves feature dimension without physical meaning |
| Equal-parameter branch | Equal-compute control | Adds capacity without response evidence |

- Primary metric: mean region accuracy on held-out scenes.
- Guardrail metrics: macro class accuracy, region flip rate, worst-light accuracy, invalid/missing feature count, calibration/rejection coverage if a router is tested.
- Statistical unit and method: region-level paired bootstrap; scene-aware bootstrap preferred for final gate.
- Resource limits: Full gate must finish feature extraction and shallow-head evaluation within 1-2 days on available local hardware.

### Counterfactual controls

- Correct relevant evidence: same-region multi-light response and aligned albedo/residual.
- Wrong / reversed evidence: wrong-region albedo or reversed response direction.
- Shuffled region or sample: shuffled light pairs across regions within material-balanced strata.
- Information-matched irrelevant evidence: random residual or unrelated region features with same dimensionality.
- Equal-parameter / equal-compute control: MLP branch with matched parameter count but no response input.

## Execution

Preparation-only command:

```text
python scripts/prepare_material_response_probe.py --config configs/material_response_probe_v0.json --check-files
python -m unittest tests/test_prepare_material_response_probe.py
```

Future gate command placeholder:

```text
python scripts/extract_material_response_features.py --config configs/material_response_probe_v0.local.json
python scripts/evaluate_material_response_probe.py --config configs/material_response_probe_v0.local.json
```

- Config: `configs/material_response_probe_v0.json`
- Seed: 20260722
- Start/end time: TBD
- Exit status: TBD
- Local log: `experiments/logs/material_response_probe_v0/` (ignored)

## Result

- Valid sample count: TBD
- Invalid outputs: TBD
- Aggregate metrics: TBD
- Confidence interval: TBD
- Resource usage: TBD
- Deviations from plan: TBD

## Review

- Claim supported: TBD
- Claim not supported: TBD
- Known uncertainty: Dataset license and environment lock still need closure before final claims.
- Claim-to-evidence mapping: TBD after gate.
- Strongest alternative explanation: Any gain may come from stronger frozen encoders, extra parameters, class imbalance, scene leakage, or extra file/path artifacts rather than true illumination response.
- Design pattern violations: None allowed; failure to include counterfactual controls makes the run exploratory only.
- Decision: Planned; no training authorized yet.
- Next action: Generate and validate the smoke manifest, then implement frozen-feature extraction only after environment/model provenance is frozen.
