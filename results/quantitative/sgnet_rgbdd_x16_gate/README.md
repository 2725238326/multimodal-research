# SGNet RGB-D-D reliability-gate results

This directory contains aggregate, reviewable results only. Checkpoints, complete logs, datasets, and server-specific paths are intentionally excluded.

## Result files

- `summary.json`: original 200-sample spatial-gate pilot and control comparisons.
- `confirmatory_multiseed.json`: three-seed full-NYU evaluation on clean, translation, scale, and synthetic texture conditions.
- `adaptive_frequency_multiseed.json`: fixed-threshold adaptive full/high-frequency gate evaluation across three seeds.
- `adaptive_threshold_sensitivity.json`: fixed-threshold sweep from `0.70` to `0.80` using the same paired predictions.
- `runtime_benchmark.json`: 100-image CUDA timing and peak-memory comparison for baseline/full/high-frequency/adaptive modes.
- `qualitative_examples_summary.json`: selected success, branch-selection, and failure examples; generated panels remain local-only.
- `rgbdd_real_protocol_summary.json`: RGB-D-D real-input 4× baseline, direct-transfer failure, and 200-sample real-domain calibration failure.
- `unseen_texture_generalization.json`: fixed-protocol sinusoidal/noise generalization, three-seed paired bootstrap, and branch-selection diagnostics.
- `soft_routing_development.json`: pre-registered 100-sample sigmoid-soft routing development gate; all temperatures fail.
- `relative_hard_confirmation.json`: locked clean-relative hard-threshold confirmation on two held-out checkpoints; No-Go despite improved routing agreement.
- `ramp_routing_development.json`: one-sided dead-zone ramp development gate; all widths fail.
- `learned_router_pilot.json`: image-holdout logistic-router pilot and checker8 oracle upper bound; not a formal trained result.
- `nyu_branch_router_pilot.json`: frozen-SGNet NYU 200/100 branch-router training gate; both fixed objectives are No-Go.

## Interpretation boundary

The adaptive frequency gate is retained for the cross-dataset synthetic 16× protocol. Every seed improves every mean metric in the seven selected clean, translation, scale, and texture conditions; 102 of 105 paired confidence intervals are strictly below zero.

The same claim does not extend to real sensor input. Direct transfer to `SGNet_Real_R` and a 200-sample real-domain calibration both perform significantly worse than the real-input baseline on all five reported metrics. These experiments are retained as No-Go evidence.

The native real-domain gate pilot, trained from identity initialization on 200 real training pairs, also performs worse on all five metrics. Real-domain gate training is therefore stopped pending a redesigned normalization or objective.

Held-out texture types give a narrower positive result. RMSE, boundary RMSE, and false-edge rate improve for a majority of seeds in all four sinusoidal/noise conditions, and stronger texture always increases high-frequency routing. However, only 34 of 60 per-seed metric comparisons are significant and the sinusoidal amplitude-8 condition worsens mean MAE/flat RMSE. This supports core edge robustness beyond checkerboards, not universal reconstruction improvement. Post-hoc diagnostics identify low cross-seed routing agreement at amplitude 8; they are not used to retune the reported threshold.

Three parameter-free routing repairs were then reviewed under a fixed development/confirmation protocol. Sigmoid soft routing damages clean false-edge performance, clean-relative hard calibration improves cross-seed agreement but not sinusoidal reconstruction, and a one-sided ramp degrades checkerboard-8 metrics. All are retained as No-Go evidence; the original absolute-threshold hard-adaptive router remains the current best synthetic-protocol method.

An oracle gate shows checker8 still has headroom, but a fixed 200/205-image RGB-D-D logistic pilot does not meet the hard-routing preservation gate. This is only a feasibility diagnosis; any formal learned router must be trained on NYU and evaluated on RGB-D-D as an external dataset.

The subsequent NYU 200-train/100-validation router gate also fails. Both label objectives improve reconstruction metrics, but clean false-edge rate regresses versus hard routing. The pilot is not expanded to 2,000 NYU samples, and no router checkpoint is published.
