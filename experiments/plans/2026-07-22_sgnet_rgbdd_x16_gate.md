# SGNet RGB-D-D 16× baseline and shift gate

## Purpose

Recover a traceable SGNet baseline on the existing 405-pair RGB-D-D `test2` set, then measure whether small RGB-only shifts create reproducible depth-boundary errors.

## Boundary

- This is a cross-dataset synthetic 16× pilot using the NYU-trained SGNet checkpoint.
- RMSE/MAE are reported in 8-bit depth levels after the historical 6-pixel crop.
- It is not the official RGB-D-D real-sensor 4× protocol.
- No C2PD code or training is started until the shift finding passes the gate.

## Required records

- experiment ID and Git commit;
- checkpoint SHA-256;
- 405 RGB/depth filename pairs;
- Python/PyTorch/CUDA and GPU;
- command, stdout, per-sample JSONL and summary JSON;
- clean and 1/2/4-pixel horizontal/vertical shifts.

## Execution

Use environment variables for server-local paths:

```bash
python scripts/evaluate_sgnet_rgbdd_x16.py \
  --sgnet-dir "$SGNET_DIR" \
  --data-root "$RGBDD_TEST2" \
  --checkpoint "$SGNET_X16_CHECKPOINT" \
  --output-dir "$EXPERIMENT_DIR/clean" \
  --device cuda:0
```

Run `--max-samples 1` first. Expand to 405 only after the sample name, tensor shapes and clean metrics pass inspection.

## Gate

Proceed to a C2PD deformation/continuity audit only when at least two small-shift levels consistently worsen RMSE, boundary RMSE or false-edge rate, with a paired-bootstrap 95% confidence interval excluding zero. Otherwise stop the misalignment route.

The implemented decision rule is intentionally stricter: at least two conditions must have paired-bootstrap 95% CI lower bounds above zero for both RMSE and boundary RMSE. `false_edge_rate` remains a supporting diagnostic rather than the sole pass criterion.

After Gate 1 passes, evaluate the official C2PD 16× checkpoint under the same clean/shift protocol before modifying SGNet. Only consider transplanting CAPO/PCGD when C2PD shows a smaller paired degradation curve than SGNet; otherwise the source module has not demonstrated the target property.

## Gate 2 result and next test

C2PD shows a modest mixed robustness advantage rather than a decisive win. At 2/4 px, its relative RMSE degradation is 5.624%/12.119% versus SGNet's 6.262%/13.264%, and its false-edge increase is 22.838%/77.126% versus 26.335%/83.900%. At 1 px, C2PD's RMSE and boundary-RMSE degradation is slightly worse.

Do not launch the original 501-epoch C2PD training. First test a frozen, fully traceable composition that passes the SGNet prediction through the pretrained C2PD deformation pipeline. Run one sample before the 405-pair clean/shift evaluation. Only if this composition improves the target robustness metrics should any refiner parameters be trained.

The frozen composition passed the one-sample execution check but failed the 405-pair clean gate. RMSE increased from 2.3355 to 3.6605 (+56.73%), boundary RMSE from 6.8525 to 10.3459 (+50.98%), and false-edge rate from 4.33% to 10.24% (+136.36%). Stop this stitch before shift evaluation or training. Preserve the C2PD standalone comparison as evidence and move to an explicit alignment or RGB-reliability module.

## Gate 3: alignment and consistency adaptation

Raw RGB/depth gradient alignment failed because it also shifted clean pairs. A trained nine-class shift calibrator on 1,800 NYU pairs remained at random-level validation accuracy (10%), so explicit global shift estimation is No-Go for this input resolution.

The next pilot freezes 82.43M SGNet parameters and trains only the early RGB branch plus first fusion bridge (4.19M parameters) on 200 NYU crops for one epoch. Random horizontal shifts in `[-4, 4]` are supervised with depth reconstruction and clean/shift output consistency. Training takes 115 seconds, peaks at 6.73 GB, has finite gradients, and produces a reloadable adapter checkpoint.

On all 405 RGB-D-D pairs, the adapter significantly improves RMSE, boundary RMSE and false-edge rate over the frozen SGNet at clean and 1/2/4 px shifts; all paired-bootstrap 95% intervals exclude zero. False-edge rate falls by 10.66%–14.24%. MAE and flat-region RMSE become slightly worse, so retain the module as a positive pilot but do not call it a final model. The next loss revision must preserve the original clean output in flat regions before expanding the training budget.

## Gate 4: clean/flat preservation v2

The second 200-sample run uses the same split, seed, trainable 4.19M parameters and one-epoch budget. It adds a frozen SGNet clean teacher plus clean and flat-region reconstruction weights of 0.5 each. The run completes in 205.6 seconds, peaks at 13.30 GB and passes gradient/checkpoint checks.

V2 partially reduces V1's clean MAE and flat-RMSE penalty, but the original SGNet still remains significantly better on both metrics. Against V1, V2 is significantly worse on RMSE, boundary RMSE and false-edge rate in every condition; at 2/4 px it also fails to improve MAE or flat RMSE. Mark V2 No-Go and retain V1 as the current pilot. Do not expand either run to full NYU yet; the next revision should use smaller preservation weights or a spatial gate instead of global clean/flat penalties.

## Gate 5: spatial reliability gating

Insert an 881-parameter spatial gate immediately before `bridge1` while freezing all 86.62M SGNet parameters. The gate receives normalized RGB-luminance gradient, upsampled LR-depth gradient and their absolute disagreement. Training-time GT depth generates a soft reliability target that suppresses RGB edges without GT-depth support; GT is not used by the inference path.

The unregularized reconstruction objective alone remains near identity, while `identity_weight=0.01` collapses exactly to identity. Direct soft-target supervision produces a nontrivial gate (mean 0.789, mean spatial standard deviation 0.136) after 200 NYU samples and one epoch. Training takes 112.6 seconds, peaks at 6.60 GB and updates only 881 parameters.

On 405 RGB-D-D pairs, the learned gate significantly improves all five metrics over SGNet and V1 at clean and 1/2/4 px shifts. Relative to SGNet, false-edge rate falls by 21.43%–21.95%, while RMSE improves by 1.01%–2.16%. Paired-bootstrap intervals exclude zero for every reported comparison. Learned spatial gating also beats an equal-mean constant gate on clean/4 px and a spatially shuffled gate on 4 px, showing that the gain is not explained by globally reducing RGB strength. Retain this module as the current positive pilot and move next to full NYU, multiple seeds, vertical/scale/texture perturbations and an official real-sensor protocol.
