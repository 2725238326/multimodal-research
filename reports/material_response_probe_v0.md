# Material response probe v0 result

**Status: Completed exploratory gate; No-Go for direct response-feature concatenation**

## Protocol

- Experiment ID: `material_response_probe_v0`
- Data: existing Multi-Illumination-derived crops; 330 samples, 66 regions, 30 scenes, 11 material labels.
- Split: five scene-grouped folds; no scene crosses train/test within a fold.
- Seeds: 20260722, 20260723, 20260724.
- Encoder: frozen `google/siglip2-base-patch16-224`, revision `75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2`, Apache-2.0, 768-dimensional normalized image feature.
- Head: fixed train-fold standardization, at most 32 train-only PCA components, L2 logistic regression; no hyperparameter search.
- Environment: Conda `summer`, Python 3.11.15, PyTorch 2.5.1+cu121, Transformers 5.9.0, scikit-learn 1.8.0, TITAN RTX.
- Statistics: scene-level paired bootstrap, 10,000 draws per seed.

The directory endpoint returned HTTP 403 during the original run. Subsequent verification on 2026-07-26 located the correct official project page and confirmed CC BY 4.0; see `docs/multi-illumination-provenance.md`. The result remains exploratory for statistical-design reasons, not because the dataset license is still unknown.

## Aggregate results

| Condition | Region accuracy | Macro class accuracy | Region flip rate |
| --- | ---: | ---: | ---: |
| Single RGB | 69.70% | 69.16% | 61.11% |
| Multi-light mean | 66.67% | 63.46% | 0.00% |
| Mean + variance | 66.67% | 63.15% | 23.23% |
| Pairwise response | 64.65% | 61.29% | 29.80% |
| RGB + albedo | 58.59% | 53.47% | 63.64% |
| RGB + residual | 62.63% | 61.05% | 67.68% |
| Shuffled response | 42.42% | 39.89% | 57.07% |
| Wrong-region albedo | 46.97% | 45.41% | 55.56% |
| Random residual | 63.13% | 59.88% | 64.14% |
| Equal-capacity RGB | 69.70% | 69.16% | 61.11% |

Pairwise response region-accuracy deltas versus single RGB are -1.67, -5.56 and -7.22 percentage points across the three seeds. All three 95% confidence intervals cross zero: [-9.44, 6.11], [-13.33, 1.67] and [-15.56, 1.11] pp. The required +5 pp gain is not met.

Pairwise response flip-rate deltas are -32.78, -25.00 and -33.33 pp. Their confidence intervals are strictly below zero, so the response feature consistently stabilizes predictions. This stability is not sufficient: region accuracy and macro accuracy are worse, and the equal-capacity RGB control retains a 5.05 pp region-accuracy advantage over the primary condition.

RGB + albedo is worse than RGB alone for all three seeds, with accuracy confidence intervals strictly below zero. This independently reproduces the direction of the earlier prompting No-Go under a trained shallow feature interface.

## Interpretation

The measured response is not a useful direct classifier input under this fixed shallow interface. It carries a strong stability signal, but concatenating it with identity features suppresses class discrimination. The result rules out expanding this exact mechanism to LoRA or full-model training.

A justified next hypothesis is narrower: use response disagreement only as an uncertainty or rejection signal while leaving the RGB classifier unchanged. That route requires a new pre-registration, nested threshold selection and held-out confirmation; it is not validated by this post-hoc observation.

`worst_light_accuracy` is zero for every condition because rare light-direction groups are too sparse under the scene folds. It is not interpreted and must be replaced by a minimum-support or region-balanced light robustness metric in any successor plan.

## Deployment smoke

`Qwen/Qwen3-VL-2B-Instruct` revision `89644892e4d85e24eaac8bacfd4f463576704203` loaded in FP16 on the TITAN RTX and completed a deterministic one-image inference in 2.254 seconds. The one example was incorrect (`ceramic` predicted as `tile`); this is a deployment smoke only, not a performance estimate.

## Evidence boundary

- Reviewable aggregate: `results/quantitative/material_response_probe_v0/summary.json`.
- Per-sample predictions, feature caches, logs, environment exports and PNG/PDF figures remain outside Git.
- No LoRA, encoder update or full-model training was performed.
