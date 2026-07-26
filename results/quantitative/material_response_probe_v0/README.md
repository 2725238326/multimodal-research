# Material response probe v0

This directory contains the aggregate, reviewable result only. Frozen feature caches, per-sample predictions, logs, model weights, environment exports and figures remain in ignored local or server storage.

- Experiment ID: `material_response_probe_v0`
- Status: `No-Go`
- Samples / independent units: 330 samples, 66 regions, 30 scenes
- Evaluation: five scene-grouped folds, seeds 20260722/20260723/20260724
- Primary condition: frozen SigLIP2 pairwise response feature with a fixed shallow logistic head
- Aggregate summary SHA-256: `263247e1fb796eba3416fa6f0584ba2415995fab5f4e174141962cec2d8a9b0e`

The primary response condition lowers cross-light flip rate but does not improve region accuracy. Direct response concatenation is stopped; the observation may motivate a separately pre-registered selective-rejection gate.
