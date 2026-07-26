# Material response selective gate v0

**Status:** `Completed` exploratory gate; `No-Go`

**Experiment ID:** `material_response_selective_gate_v0`

**Date:** 2026-07-26

## Question

The preceding frozen-feature probe showed that direct multi-light response concatenation improved prediction stability but reduced material discrimination. This separate experiment tested the narrower hypothesis that cross-light disagreement could identify errors from an unchanged RGB classifier and support selective rejection.

Because the preceding result on the same dataset generated this hypothesis, this gate is explicitly exploratory. It cannot provide a confirmatory claim even if it passes.

## Protocol

- 330 light-conditioned samples, 66 material regions, 30 scenes and 11 classes.
- Frozen 768-dimensional SigLIP2 RGB features from revision `75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2`.
- Five outer scene folds for evaluation and four inner scene folds for RGB out-of-fold probabilities and router training.
- Three seeds: 20260726, 20260727 and 20260728.
- RGB prediction was held fixed across all selectors. The router could only rank regions for rejection.
- Response signals were region variance energy, mean residual magnitude and pairwise cosine dispersion across lights.
- Controls were RGB confidence only, independently shuffled response features and random equal-coverage rejection.
- Primary metrics were selective region accuracy at exactly 80% (53/66 regions) and 90% (59/66 regions) coverage. Paired intervals used 10,000 scene-bootstrap draws per seed.

## Results

| Selector | Risk-coverage AUC | Error AUROC | Error AUPRC | Accuracy at 80% | Accuracy at 90% |
| --- | ---: | ---: | ---: | ---: | ---: |
| RGB confidence only | 0.2577 | 0.6616 | 0.4713 | 72.96% | 70.06% |
| Response router | 0.2575 | 0.6554 | 0.4652 | 74.21% | 70.06% |
| Shuffled response | 0.2662 | 0.6373 | 0.4522 | 72.96% | 70.62% |
| Random rejection | 0.3042 | 0.5296 | 0.3417 | 70.44% | 67.80% |

Values are means over the three nested-CV seeds. At 80% coverage the response router's mean gain was 1.26 percentage points, corresponding to only one additional correct accepted region in two seeds. The seed-level response-minus-RGB intervals were `[-4.09, 4.08]`, `[0.00, 5.32]` and `[0.00, 5.63]` percentage points. None had a lower bound greater than zero.

At 90% coverage, the accuracy delta was exactly zero in all three seeds. The mean response-router error AUROC and AUPRC were lower than the RGB-confidence baseline. Risk-coverage AUC improved in only one seed; the mean difference was 0.0002, too small and inconsistent to support the mechanism. Shuffled response could not be excluded at either primary coverage.

The generated PNG/PDF figure remains in the ignored result staging directory. It shows the full risk-coverage profiles, paired fixed-coverage seed results and seed ranges for error detection.

## Decision

`No-Go` for this response-router formulation. It failed every pre-registered primary requirement: the fixed-coverage confidence intervals did not exclude zero, AURC did not improve consistently, and the shuffled-response control was not excluded.

The two completed gates jointly rule out both immediate uses of these frozen response summaries on this dataset:

1. direct concatenation as classifier input harms discrimination; and
2. simple response disagreement does not add reliable rejection information beyond RGB confidence.

No LoRA, full-model training, selective distillation or further threshold tuning is justified for this mechanism. A future revisit requires a genuinely different physical measurement or independent dataset, not additional optimization on these 30 scenes.

## Reproducibility and limits

- Feature cache SHA-256: `0673a2a660e29d77699b0a74d3db55b7f56648b03bab2c7ce334fce43420c0fd`.
- Full aggregate summary SHA-256: `2d2fd696652d3ea15b215350068a95b8b2e3b4d2d8b38b0f6e0cf411dd1cc557`.
- Figure SHA-256: PNG `5c83163f34bb6fa86fd11dd81062757d0b073c1f43a9ceb0d12bd65fe79868e6`; PDF `fd9917a5f0d3739a0755f20036475a6c4548d3d5bded6a70828afda5f1773727`.
- Full evaluation took 27.37 seconds and peaked at 163,736 KiB RSS in the remote `summer` environment.
- Per-region predictions and scores remain outside Git.
- Dataset provenance was subsequently verified as CC BY 4.0; see `docs/multi-illumination-provenance.md`. Per-region outputs remain outside Git under the project artifact boundary.
