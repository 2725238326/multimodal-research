# HDR + light-probe oracle audit v0

This directory contains the aggregate, reviewable result only. Downloaded EXR/JPEG archives, extracted images, material masks and per-direction records remain in ignored local storage.

- Experiment ID: `hdr_light_probe_oracle_audit_v0`
- Status: `Completed training-free audit gate`; verdict `No-Go` for gray-probe normalization
- Data: official Multi-Illumination per-scene `mip2` EXR and 256px light probes, CC BY 4.0
- Independent units: 6 scenes from the official train pool, 25 illumination directions each, 90 material regions total
- Trained parameters: 0 — regions come from the official material mask and no head is fitted
- Aggregate summary SHA-256: `14332b9f18fc6b251fefa13851b74a614e79113593a5d6ad65fd36fe53c1093c`

Two questions were separated. Linear HDR does recover real signal that the released JPEGs destroy: a median 5.8% of pixels per scene have at least one saturated channel (up to 69.4% in the worst single illumination), and the linear data extends a median 35x above the measured JPEG clip point.

Gray-probe normalization, however, fails its own oracle test. The gray probe spans a median dynamic range of 1.72x across the 25 illuminations while the scene it is meant to normalize spans 17.35x, and the median correlation between the two is -0.02. Dividing region radiance by the probe therefore does not reduce across-illumination spread: the median between-region / within-region discriminability ratio changes by 0.98x, and only 1 of 6 scenes improves by more than 10%.

The chrome probe retains directional information (median dynamic range 27.8x, median correlation 0.41), but turning it into per-surface incident irradiance requires surface normals, which this dataset does not provide.

Thresholds in `summary.json` were set after inspecting the measurements. They are reporting aids, not a pre-registered gate; the load-bearing evidence is the raw measurement.
