# Photometric trajectory and external confirmation

**Status:** development gate `No-Go`; official external confirmation `No-Go`

## Method

The new method replaced frozen-embedding response summaries with direct pixel appearance measurements: clipping, robust luminance, chromaticity, saturation, highlight fractions, gradients and Laplacian energy across five light conditions. A censor-aware trajectory excluded observations with more than 20% all-channel near-white pixels, with a deterministic least-clipped fallback.

This is an appearance descriptor for sRGB JPEG crops, not a calibrated BRDF estimate. The design included equal-capacity SigLIP baselines, uncensored and exposure-only ablations, independently shuffled physical trajectories and scene-level bootstrap inference.

## Development result

On 66 regions from 30 development scenes, the primary SigLIP-plus-censored method reached 68.69% mean region accuracy versus 63.13% for SigLIP region mean, an average increase of 5.56 percentage points. Uncensored fusion reached 67.68%, exposure-only 63.64%, shuffled trajectory 54.55% and photometric-only 36.36%.

The direction was consistent, but the three pre-registered scene-bootstrap intervals had lower bounds of 0, 0 and -1.67 percentage points. The strict gate therefore remained `No-Go`. The result only justified an external confirmation because it also did not exceed the prior sample-majority RGB mean of 69.70%.

## Independent official test

The official source and CC BY 4.0 license were verified. The untouched SDK test split contains 30 `everett*` scenes with zero overlap with development. A fixed pre-model audit selected 80 regions over all 30 scenes using 64x64 mip4 crops; this is explicitly a scale-domain stress test because strict 96x96 crops yielded only 35 regions.

| Condition | Mean region accuracy | Mean macro accuracy |
| --- | ---: | ---: |
| RGB sample-majority baseline | 43.33% | 42.17% |
| SigLIP region mean | 38.75% | 40.50% |
| Censor-aware photometric fusion | 30.83% | 34.52% |
| Exposure-only fusion | 36.25% | 35.99% |
| Shuffled photometric fusion | 39.58% | 37.89% |
| Photometric-only | 16.25% | 14.53% |

Against the strong RGB baseline, the primary method lost 11.25, 12.50 and 13.75 percentage points across the three seeds. The corresponding 95% test-scene bootstrap intervals were `[-21.89, -3.83]`, `[-24.11, -5.67]` and `[-24.94, -6.06]` percentage points. All exclude zero in the harmful direction.

## Decision

The development improvement does not transfer. Exposure-only and shuffled controls outperforming the primary method indicate sensitivity to development-domain scale, scene and appearance statistics rather than a reusable material response measurement.

This closes the current multi-light response family:

1. frozen embedding response concatenation harmed discrimination;
2. embedding disagreement did not improve selective rejection;
3. pixel photometric trajectories produced an uncertain development gain and a significant external loss.

Do not train a conflict verifier, deep BRDF module, LoRA adapter or privileged student from this mechanism. A materially different next route requires calibrated HDR/light-probe information, polarization/flash measurements, or a task where geometry provides a falsifiable verifier.

## Reproducibility

- Development summary SHA-256: `7dab129c1fed0a80895ce5bcf967ca390e052213df60997548be58a37e35992f`.
- External summary SHA-256: `3ff457fdcdbdbcb3d609182540d0cc32b5ab065162a3a9d2cda08e3e395e224c`.
- External test manifest SHA-256: `871a577e29f2463385efa05ff1a1473ad9c5ea94a5fc4b2620108d7e70d9f6ed`.
- Figure SHA-256: PNG `dd1695043bd9f841b3e5a8296e5885d31375f80ccf293860b1ca19e0d39f8fde`; PDF `e7eab8cc0c220b735b197afcabead97eb21b0b62eb77953f8ebb90cd8eff31e9`.
- Full external evaluation took 3.84 seconds and peaked at 163,332 KiB RSS; SigLIP extraction took 16.51 seconds on an NVIDIA TITAN RTX.
- Per-region predictions, source archive, crops, feature caches and generated figures remain outside Git.
