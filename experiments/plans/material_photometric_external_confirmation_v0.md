# Experiment: `material_photometric_external_confirmation_v0`

## Frozen decision contract

- Date frozen: 2026-07-26
- Track: confirmatory external-split stress test
- Question: does the censor-aware pixel photometric trajectory learned from the 30-scene development subset improve material classification on the official, untouched 30-scene test split?
- Independent unit: official test scene; region is the prediction unit.
- Primary condition: SigLIP region mean plus censor-aware photometric trajectory.
- Strong baselines: sample-level SigLIP classifier with five-light region majority, and SigLIP region-mean classifier.

## Source, split and license

- Official page: `https://projects.csail.mit.edu/illumination/`.
- Data license stated on that page: CC BY 4.0.
- Official JPG test archive: `multi_illumination_test_mip2_jpg.zip`, 214,841,949 bytes, local SHA-256 `7a142f0f4dcf8c6b038f91a32eee5962a12aa68e5c4ee43adf0d3059ea0f0ce0`; 2,400 ZIP entries passed CRC validation.
- Official SDK: `lmurmann/multi_illumination`, revision `a85aa9253065ff836ea97ba1a04b14259a06b3e0`, MIT license.
- The SDK defines scenes beginning with `everett` as test. All 30 current development scenes occur in the non-`everett` train pool; overlap with the 30 official test scenes is zero.

## Fixed external crop protocol

The archive contains mip2 images and indexed material masks. Images and masks are downsampled by four to mip4 before region selection. Masks use nearest-neighbor sampling; RGB uses Lanczos sampling.

- Crop size: 64x64 at mip4.
- Minimum connected-component area: 1,024 pixels.
- Minimum crop purity: 0.82.
- Maximum two regions per scene/material class.
- Up to 80 balanced regions, with at least 60 required.
- Five directions per region selected by the existing deterministic diversity rule over RGB mean and standard deviation.
- Target IDs: ceramic, fabric/cloth, glass, granite/marble, leather, metal, paper/tissue, clear plastic, opaque plastic, tile and wood.

The earlier development crops are 96x96. The 64x64 choice is frozen as a scale-domain stress test because a strict 96x96 external audit produced only 35 regions over 25 scenes, while 64x64 produced 80 regions over all 30 scenes before any model output was inspected. It is not a matched-scale benchmark.

## Train/test protocol

1. Build all external crops locally from the validated official ZIP; upload only the fixed bundle and hash manifest.
2. Extract SigLIP features with the same model revision and preprocessing used in `material_response_probe_v0`.
3. Extract the same 20 pixel measurements and censor-aware trajectory frozen in `material_photometric_trajectory_gate_v0`.
4. Fit each model only on the existing development regions/samples. Evaluate once on the external test regions.
5. Repeat only the randomized PCA/logistic head with seeds 20260801–20260803. No test-driven feature, crop, threshold or seed changes are permitted.

## Conditions and controls

- `siglip_sample_majority`: strongest prior-style RGB baseline trained at sample level, aggregated by five-light majority.
- `siglip_region_mean`: equal region-level semantic baseline.
- `photometric_censored_only`: physical appearance branch alone.
- `siglip_plus_censored`: primary method.
- `siglip_plus_exposure_only`: clipping/luminance artifact control.
- `siglip_plus_shuffled`: independently deranged physical trajectories in train and test.

## Metrics and Go / No-Go

- Region accuracy and macro class accuracy on the fixed test regions.
- Paired test-scene bootstrap, 10,000 draws per seed, 95% interval.

All three seeds must satisfy all conditions for `Go`:

- primary exceeds both RGB baselines by at least 3 percentage points;
- both primary-minus-baseline scene-bootstrap CI lower bounds are greater than zero;
- primary macro accuracy is no lower than the stronger RGB baseline;
- primary exceeds shuffled trajectory by at least 3 percentage points;
- exposure-only does not match or exceed primary.

Any failure is `No-Go` and closes conflict-verifier, deep BRDF, LoRA and distillation work on this mechanism. A pass does not itself validate a verifier; it only establishes that the physical trajectory generalizes enough to justify one.

## Git and attribution boundary

The official archive, extracted scenes, crops, manifests, feature caches, predictions and figures remain in ignored local/remote storage. Git may contain the code, portable config, plan, aggregate result and source/license record. Any publication or redistribution must preserve CC BY 4.0 attribution to Murmann et al. and the official project.
