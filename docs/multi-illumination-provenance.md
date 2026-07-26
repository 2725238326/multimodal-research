# Multi-Illumination dataset provenance

**Verified:** 2026-07-26

## Official source

- Project: *A Dataset of Multi-Illumination Images in the Wild* / *A Multi-Illumination Dataset of Indoor Object Appearance*.
- Authors: Lukas Murmann, Michael Gharbi, Miika Aittala and Fredo Durand.
- Official page: `https://projects.csail.mit.edu/illumination/`.
- Paper: ICCV 2019, arXiv `1910.08131`.
- Official SDK: `https://github.com/lmurmann/multi_illumination`.

The project page explicitly states that the dataset is licensed under CC BY 4.0 and links to the Creative Commons license. The SDK repository reports an MIT code license. The earlier project record used the directory URL `https://data.csail.mit.edu/multilum`, which returns HTTP 403 because directory listing is forbidden; this did not imply that the official project or files were unavailable. The correct project page and direct archive URLs are accessible.

## Fixed versions and checks

- SDK revision: `a85aa9253065ff836ea97ba1a04b14259a06b3e0`.
- SDK `scenes.json` SHA-256: `567e399ed61433c88d3aff161e529e08bde29f6ae16732ee5ebb6d420aca229e`.
- Official test JPG archive URL: `https://data.csail.mit.edu/multilum/multi_illumination_test_mip2_jpg.zip`.
- HTTP metadata: 214,841,949 bytes; last modified 2019-10-18; ETag `cce3a5d-59528522bc3c6`.
- Local archive SHA-256: `7a142f0f4dcf8c6b038f91a32eee5962a12aa68e5c4ee43adf0d3059ea0f0ce0`.
- ZIP validation: 2,400 entries, 2,340 files, no CRC failure; 30 scenes, each with images, indexed material mask and metadata.

The SDK defines all `everett*` scenes as the 30-scene test set and all remaining 985 scenes as train. The repository's existing 30 development scenes all occur in the official train pool; overlap with official test is zero.

## Allowed use and repository boundary

CC BY 4.0 permits use and adaptation with attribution and license notice. This repository records source, version and aggregate results, but the downloaded archive, extracted images, material masks, crops, per-sample manifests and feature caches remain in ignored local or remote storage. Redistribution is not needed for the current collaboration and should not be added to Git.

Any paper, artifact or redistributed derivative must credit Murmann et al., link the official project and CC BY 4.0, identify modifications such as downsampling/cropping, and avoid implying author endorsement.
