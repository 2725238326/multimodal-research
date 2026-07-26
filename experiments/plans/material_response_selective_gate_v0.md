# Experiment: `material_response_selective_gate_v0`

## Decision contract

- Date frozen: 2026-07-26
- Track: exploratory feasibility gate; the same 30-scene dataset generated this hypothesis, so this run cannot be confirmatory.
- Question: can cross-light response disagreement identify errors from an unchanged RGB material classifier better than RGB confidence alone?
- Hypothesis: at identical 80% and 90% region coverage, a response-aware error router improves selective accuracy over an RGB-confidence-only selector and lowers risk-coverage AUC.
- Independent unit: scene for splitting and bootstrap; region for classification, rejection and reported accuracy.
- Modal roles: frozen RGB embedding is `Measurement`; cross-light disagreement is `Router`; it may reject but may not replace the RGB prediction.

## Evidence and inputs

- Source cache: the SigLIP2 feature cache produced by `material_response_probe_v0`; 330 samples, 66 regions, 30 scenes, 11 labels and five controlled light observations per region.
- Encoder: `google/siglip2-base-patch16-224`, revision `75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2`, Apache-2.0 model license.
- Data permission: unresolved. Inputs and per-region outputs remain local/remote-only; publication and redistribution are blocked pending license verification.
- No new model, data or weight download is authorized for this gate.

## Protocol

1. Use five outer `GroupKFold` splits by scene. Within each outer training set, use four inner scene folds to create out-of-fold RGB probabilities without fitting on the scored region.
2. Fit the frozen-feature RGB PCA + logistic head on outer-training samples and preserve its outer-test prediction.
3. Aggregate probabilities to regions. RGB uncertainty contains `1-confidence`, `1-margin` and normalized entropy.
4. Compute three label-free response signals per region: embedding variance energy, mean current-minus-region-mean L2 magnitude and mean pairwise cosine dispersion across lights.
5. Fit an error detector on inner-OOF outer-training regions. Compare RGB uncertainty only with RGB uncertainty plus response signals.
6. Freeze deployment-style acceptance thresholds from inner-region score quantiles, then apply them to outer-test regions. Separately compute exact fixed-coverage results by label-free score rank for the primary comparison.
7. Repeat with three fixed seeds. Keep per-region predictions outside Git; commit only aggregate summaries.

## Controls

- `rgb_confidence_only`: strongest simple selector using the same nested RGB probabilities.
- `shuffled_response_router`: independently permute response vectors across regions in train and test while preserving feature dimension.
- `random_score`: deterministic random ranking independent of labels and inputs.
- Equal-coverage random rejection is the fixed-coverage evaluation of `random_score`.

## Metrics and inference

- Primary: region selective accuracy at exactly 80% and 90% coverage.
- Secondary: macro selective accuracy, risk-coverage AUC from 50% to 100% coverage, error-detection AUROC and average precision, plus achieved coverage/accuracy under inner-selected thresholds.
- For each seed and coverage, hold acceptance masks fixed and paired-bootstrap scenes 10,000 times. Report response-router minus baseline and response-router minus shuffled deltas with 95% intervals.
- Ties are broken deterministically by region ID; no test label is used to choose an acceptance mask or threshold.

## Go / No-Go

`Go` requires, for every seed and both fixed coverages:

- response-router minus RGB-confidence selective-accuracy CI lower bound is greater than zero;
- response-router risk-coverage AUC is lower;
- response-router minus shuffled-response CI lower bound is greater than zero;
- macro selective accuracy is no more than 1 percentage point below RGB confidence.

Otherwise the mechanism is `No-Go` for training expansion. Any Go only authorizes a separately frozen confirmation on independent scenes; it does not establish a stable claim on this dataset.

## Resource and failure limits

- CPU-only shallow evaluation over the existing 1.7 MiB feature cache; expected runtime below ten minutes and no GPU requirement.
- First run `--dry-run`, then a reduced one-seed/200-bootstrap smoke. Full evaluation starts only after schema, scene isolation, probability normalization, exact coverage and deterministic-control tests pass.
- Stop as `Blocked` if cache provenance changes, region-to-scene/label consistency fails, or data leave the approved local/remote boundary.

## Reproducible command

```bash
python scripts/evaluate_material_response_selective_gate.py \
  --features /path/to/siglip2_features.npz \
  --config configs/material_response_selective_gate_v0.json \
  --output /path/to/aggregate/summary.json \
  --predictions-output /path/to/local_only/predictions.jsonl
```

The feature and output paths are machine-local overrides and must not be committed.
