# Experiment: `material_photometric_trajectory_gate_v0`

## Decision contract

- Date frozen: 2026-07-26
- Track: exploratory oracle gate
- Question: do exposure-audited pixel photometric trajectories add scene-disjoint material information beyond a frozen SigLIP region representation?
- Hypothesis: a shallow classifier using SigLIP region mean plus censor-aware pixel trajectory features improves region accuracy by at least 3 percentage points over the same-capacity SigLIP baseline, with a positive scene-bootstrap interval and controls excluded.
- Independent unit: scene for split and bootstrap; material region for prediction.
- Role assignment: pixel photometry is `Measurement`; SigLIP is the semantic-visual baseline. Neither VLM labels nor generated albedo are used.

## Why this differs from the stopped route

The two prior No-Go experiments summarized variation in frozen semantic embeddings. This gate instead reads the RGB crop pixels and measures exposure, luminance, chromaticity, highlight and spatial-gradient behavior. The input audit found 46/330 crops with more than 20% near-white pixels, so it explicitly separates reliable photometric variation from clipping artifacts.

These JPEG crops are not radiometrically calibrated. The method therefore tests robust appearance trajectories, not BRDF recovery, photometric stereo or a claim of physical parameter estimation.

## Mechanism migration card

- Source field: multi-illumination appearance analysis and robust/censored measurement.
- Original tension: illumination reveals reflectance behavior but saturation corrupts intensity evidence.
- Migrated mechanism: reject or downweight corrupted observations before aggregating response statistics.
- Task variables: five RGB crops per material region; near-white fraction is the censoring indicator.
- Assumptions that do not transfer: known camera response, calibrated light direction/intensity, surface normals and pixel-perfect alignment.
- Closest local evidence: the Multi-Illumination Images in the Wild dataset paper and the repository's multimodal material/polarization literature index.
- Simple baseline: mean frozen SigLIP embedding per region with the same PCA + logistic head.
- Controls: uncensored trajectory, exposure-only trajectory and independently shuffled censored trajectory.
- One-day No-Go: primary CI crosses zero, gain is below 3 pp, macro accuracy falls, or shuffled/exposure-only features explain the gain.

## Pixel measurements

Each 96x96 crop yields label-free measurements:

- all-channel and any-channel near-white fractions, dark fraction and usable-pixel fraction;
- robust luminance quantiles;
- mean and spread of normalized red/green chromaticity;
- color saturation statistics;
- absolute bright-pixel and bright-low-saturation fractions;
- luminance gradient magnitude quantiles and Laplacian energy.

For each region, measurements are aggregated across lights using mean, standard deviation, minimum, maximum and range. The censor-aware trajectory uses lights with all-channel near-white fraction no greater than 20%; if fewer than two survive, it uses the two least-clipped observations and records this fallback. The uncensored ablation uses all five lights. Exposure-only features retain only clipping, darkness, usable fraction and luminance statistics.

## Conditions

1. `siglip_region_mean`: strong frozen semantic-visual baseline.
2. `photometric_censored_only`: physical appearance oracle without SigLIP.
3. `siglip_plus_censored`: primary intervention.
4. `siglip_plus_uncensored`: tests whether censoring is responsible for any gain.
5. `siglip_plus_exposure_only`: checks whether scene/exposure artifacts explain the result.
6. `siglip_plus_shuffled`: permutes censored trajectories across regions independently in train and test.

All classifiers use five scene-grouped folds, PCA capped at 16 dimensions and balanced L2 logistic regression. The PCA dimension and head capacity are identical across conditions. Three fixed seeds are evaluated.

## Metrics and decision

- Primary: region accuracy.
- Guardrail: macro class accuracy.
- Inference: paired scene bootstrap, 10,000 draws per seed, 95% interval.

`Go` requires all three seeds to satisfy:

- primary minus baseline accuracy is at least +3 pp and its CI lower bound is above zero;
- primary macro accuracy is no lower than baseline;
- primary accuracy exceeds shuffled trajectory by at least 3 pp;
- exposure-only does not produce an equal or larger gain.

Failure of any requirement is `No-Go` for learning-based BRDF modules, LoRA or privileged distillation on this mechanism. A Go result only authorizes independent-scene confirmation.

## Provenance, resources and outputs

- Source manifest and SigLIP cache are the immutable outputs of `material_response_probe_v0`; their hashes must be recorded at runtime.
- Existing 330 RGB crops only; no downloads and no GPU required.
- Expected runtime below ten minutes in the remote `summer` environment.
- Raw crops, descriptor cache, predictions, logs and figures remain outside Git. Only code, portable config, plan and aggregate summary may be tracked.
- Dataset license remains unresolved, so publication and redistribution remain blocked.
