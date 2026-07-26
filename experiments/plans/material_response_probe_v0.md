# Experiment: `material_response_probe_v0`

## Decision

- Owner: TBD
- Date: 2026-07-22
- Status: Completed exploratory gate; No-Go (2026-07-25)
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
- License / allowed use at run time: the directory endpoint returned HTTP 403 and no explicit license text was then recorded locally. Subsequent verification on 2026-07-26 found the correct official project page at `https://projects.csail.mit.edu/illumination/`, which explicitly licenses the data under CC BY 4.0; see `docs/multi-illumination-provenance.md`.
- Local asset location: `data/raw/`, `data/processed/material_constancy_rgb_gate_v2/`, `data/processed/material_constancy_albedo_v1/` remain local/tracked-history assets; new generated manifests remain ignored.
- Manifest hash:
  - RGB gate v2: `0651737375c61300bd60055e70e155c627a855e09bf1cfcf11ffcb13112f9828`
  - Albedo v1: `c3b52b82589e22b2fc8b02cdd7b2b0b89c1b8ec716bf465ef69f9c853cd297d2`
- Split: scene-grouped split; no crop from a scene may appear in both train and test for a confirmatory run.
- Samples: Full gate has 330 samples.
- Independent scenes / objects / regions: 30 scenes / 66 regions. Statistical unit is region; bootstrap should be scene-aware when possible.
- Leakage checks: Verify no sample ID duplicates, no region crosses scene split, each region has multiple light directions, all path fields are repository-relative in newly generated smoke manifests, and all controls preserve labels while breaking the intended evidence.

## Model and code

- Model ID: Primary encoder `google/siglip2-base-patch16-224`; semantic deployment reference `Qwen/Qwen3-VL-2B-Instruct`.
- Weight source and revision: Official Hugging Face snapshots pinned to SigLIP2 `75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2` and Qwen3-VL `89644892e4d85e24eaac8bacfd4f463576704203`.
- License: Apache-2.0 for both selected models; selection audit is `docs/material-response-model-selection-2026-07-25.md`.
- Repository commit: Record `git rev-parse HEAD` before execution.
- Environment lock: Conda environment name `summer`; exact package export and GPU stack must be captured before smoke execution.
- Device: One TITAN RTX 24 GB, default GPU 0 after an immediate availability recheck; feature extraction batch size starts at 8 and backs off on OOM.

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
- Fixed evaluation: five scene-grouped folds; seeds `20260722`, `20260723`, `20260724`; logistic head with train-fold standardization, at most 32 train-only PCA components, L2 penalty and no hyperparameter search.
- Response representation: current-light embedding plus same-region mean, current-minus-mean deviation and per-dimension standard deviation. This is the only new mechanism in the main condition.

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

- Valid sample count: 330 samples / 66 regions / 30 scenes; zero missing inputs.
- Invalid outputs: 0 feature extraction failures.
- Aggregate metrics: single RGB region accuracy 69.70%, macro accuracy 69.16%, flip rate 61.11%; pairwise response 64.65%, 61.29%, 29.80% respectively.
- Confidence interval: pairwise region-accuracy deltas are -1.67 pp CI[-9.44, 6.11], -5.56 pp CI[-13.33, 1.67], and -7.22 pp CI[-15.56, 1.11] across seeds. Flip-rate CIs are strictly below zero for all seeds.
- Resource usage: SigLIP2 extraction 11.835 seconds on one TITAN RTX; complete extraction/evaluation command 99 seconds; feature cache SHA-256 `0673a2a660e29d77699b0a74d3db55b7f56648b03bab2c7ce334fce43420c0fd`.
- Deviations from plan: scikit-learn 1.8 expresses the frozen L2 head using `l1_ratio=0.0`; mathematically equivalent to the registered L2 penalty. Dataset license was unresolved at run time and was subsequently verified as CC BY 4.0 on 2026-07-26. The run remains exploratory because its hypothesis and data were not an untouched confirmation.

## Review

- Claim supported: Multi-light response features consistently reduce cross-light prediction flips under the tested interface.
- Claim not supported: Response features do not improve held-out region accuracy beyond single RGB and reduce macro class accuracy; direct concatenation is No-Go.
- Known uncertainty: Dataset allowed use remains unresolved; rare light-direction groups make `worst_light_accuracy` unusable.
- Claim-to-evidence mapping: Aggregate JSON and detailed review in `reports/material_response_probe_v0.md`.
- Strongest alternative explanation: Any gain may come from stronger frozen encoders, extra parameters, class imbalance, scene leakage, or extra file/path artifacts rather than true illumination response.
- Design pattern violations: None allowed; failure to include counterfactual controls makes the run exploratory only.
- Decision: No-Go for direct response concatenation; no LoRA or full-model expansion.
- Next action: If pursued, pre-register a separate response-as-uncertainty/rejection gate with nested threshold selection and held-out confirmation.
