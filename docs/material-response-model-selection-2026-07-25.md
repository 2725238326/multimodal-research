# Material response model selection: 2026-07-25

**状态：Completed（官方模型元数据与模型卡核验）；不构成任务性能结论**

## Candidates

| Model | Official revision | Date in official metadata | License | Role decision |
| --- | --- | --- | --- | --- |
| `google/siglip2-base-patch16-224` | `75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2` | 2025-02-21 | Apache-2.0 | Primary frozen visual measurement encoder |
| `Qwen/Qwen3-VL-2B-Instruct` | `89644892e4d85e24eaac8bacfd4f463576704203` | 2025-10-23 | Apache-2.0 | Same-scale semantic reference and deployment smoke only |
| `OpenGVLab/InternVL3_5-2B-HF` | `3f301ffcf3dcbb47893afae6650ea3e78d96fb6d` | 2025-09-08 | Apache-2.0 | Retained comparison; not selected because the repository already has completed InternVL3.5 prompting evidence and Qwen3-VL is the newer same-scale reference |
| `facebook/dinov3-vitb16-pretrain-lvd1689m` | Gated official model | N/A without accepted access | Meta DINOv3 terms | Not selected for this run because reproducible local download is gated |

## Decision

The gate tests whether measured multi-light response adds information, not which generative VLM wins. SigLIP2 exposes a direct image embedding, is ungated, and is small enough to cache all 330 RGB/albedo crops on one TITAN RTX. Qwen3-VL-2B is retained as the current same-scale VLM reference, but its generated label is not used as physical evidence.

No model is called universally SOTA. The selection claim is narrower: these are current official, openly downloadable candidates suitable for the repository's frozen-feature protocol and available 24 GB GPU budget.

## Provenance checks

- Source metadata: official Hugging Face model API and model cards.
- Qwen3-VL server copy reports the same official revision and model weight LFS SHA-256 `7de1838c87a5349b016c26a1c3f7d2bc400a3d485f95ef39a7059ffd734977a0`.
- New downloads must use the exact revisions above and enter the ignored transfer manifest before upload.
