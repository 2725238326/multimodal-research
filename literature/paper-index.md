# 论文索引

**建立日期：2026-07-21**  
**状态：Completed（首批基线，持续更新）**

## 使用与版权边界

- PDF 下载到本地 `paper/`，该目录已被 `.gitignore` 排除，不进入 Git 或上游 PR。
- arXiv 条目的具体分发许可见各自 abstract 页的 `view license`；CVF 论文版权由作者或其他权利人保留。当前副本仅用于本地研究阅读，不默认允许再分发。
- 下载 URL 使用官方 arXiv 或 CVF Open Access；`literature/paper-sha256.txt` 固定本次实际下载内容。
- “相关性”是对本仓库候选机制的阅读路由，不代表论文结论已在本项目中复现。

## A. 项目直接相关

| 论文 | 原始来源 | 本地文件 | 相关性 |
| --- | --- | --- | --- |
| A Dataset of Multi-Illumination Images in the Wild | [arXiv:1910.08131](https://arxiv.org/abs/1910.08131) | `1910.08131_multi_illumination_wild.pdf` | 当前多光照数据与 scene-level 独立单元审计 |
| One-shot Recognition of Any Material Anywhere / MatSim | [arXiv:2212.00648](https://arxiv.org/abs/2212.00648) | `2212.00648_matsim_material_recognition.pdf` | 跨环境材质表示与 physics-based rendering |
| Eyes Wide Shut? | [arXiv:2401.06209](https://arxiv.org/abs/2401.06209) | `2401.06209_eyes_wide_shut_visual_shortcomings.pdf` | 区分视觉编码缺陷与语言推理缺陷；Mixture of Features |
| C2KD | [CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/html/Huo_C2KD_Bridging_the_Modality_Gap_for_Cross-Modal_Knowledge_Distillation_CVPR_2024_paper.html) | `2024_cvpr_c2kd_cross_modal_distillation.pdf` | 跨模态负迁移、软标签错位与选择性蒸馏 |
| When Lighting Deceives / ITA | [ICCV 2025](https://openaccess.thecvf.com/content/ICCV2025/html/Liu_When_Lighting_Deceives_Exposing_Vision-Language_Models_Illumination_Vulnerability_Through_Illumination_ICCV_2025_paper.html) | `2025_iccv_when_lighting_deceives_ita.pdf` | VLM 光照脆弱性及物理合理照明干预 |

## B. Agent 与多模态工具使用

| 论文 | 原始来源 | 本地文件 | 机制 |
| --- | --- | --- | --- |
| Large Multimodal Agents: A Survey | [arXiv:2402.15116](https://arxiv.org/abs/2402.15116) | `2402.15116_large_multimodal_agents_survey.pdf` | agent 组件、类型、协作与评估框架 |
| ReAct | [arXiv:2210.03629](https://arxiv.org/abs/2210.03629) | `2210.03629_react_reasoning_acting.pdf` | reasoning/action 交错 |
| Toolformer | [arXiv:2302.04761](https://arxiv.org/abs/2302.04761) | `2302.04761_toolformer.pdf` | 自监督工具调用学习 |
| Reflexion | [arXiv:2303.11366](https://arxiv.org/abs/2303.11366) | `2303.11366_reflexion.pdf` | 语言反馈与 episodic memory |
| ViperGPT | [arXiv:2303.08128](https://arxiv.org/abs/2303.08128) | `2303.08128_vipergpt.pdf` | 用 Python 组合视觉模块 |
| MM-ReAct | [arXiv:2303.11381](https://arxiv.org/abs/2303.11381) | `2303.11381_mm_react.pdf` | LLM 与视觉专家池的多模态编排 |
| LLaVA-Plus | [arXiv:2311.05437](https://arxiv.org/abs/2311.05437) | `2311.05437_llava_plus_multimodal_agents.pdf` | 多模态工具使用训练 |
| VisualWebArena | [arXiv:2401.13649](https://arxiv.org/abs/2401.13649) | `2401.13649_visualwebarena.pdf` | 视觉网页 agent 与执行式任务 |
| OSWorld | [arXiv:2404.07972](https://arxiv.org/abs/2404.07972) | `2404.07972_osworld.pdf` | 真实计算机环境、执行式评估与 GUI grounding |

## C. 多模态连接与视觉机制

| 论文 | 原始来源 | 本地文件 | 机制 |
| --- | --- | --- | --- |
| CLIP | [arXiv:2103.00020](https://arxiv.org/abs/2103.00020) | `2103.00020_clip.pdf` | 对比式图文预训练 |
| Flamingo | [arXiv:2204.14198](https://arxiv.org/abs/2204.14198) | `2204.14198_flamingo.pdf` | Perceiver Resampler 与 gated cross-attention |
| BLIP-2 | [arXiv:2301.12597](https://arxiv.org/abs/2301.12597) | `2301.12597_blip2.pdf` | Q-Former 连接冻结视觉编码器与 LLM |
| LLaVA | [arXiv:2304.08485](https://arxiv.org/abs/2304.08485) | `2304.08485_llava_visual_instruction_tuning.pdf` | 线性 projector 与视觉指令微调 |
| SigLIP | [arXiv:2303.15343](https://arxiv.org/abs/2303.15343) | `2303.15343_siglip.pdf` | pairwise sigmoid 图文目标 |
| Segment Anything | [arXiv:2304.02643](https://arxiv.org/abs/2304.02643) | `2304.02643_segment_anything.pdf` | promptable segmentation 与区域工具 |
| DINOv2 | [arXiv:2304.07193](https://arxiv.org/abs/2304.07193) | `2304.07193_dinov2.pdf` | 自监督通用视觉特征 |
| DINOv3 | [arXiv:2508.10104](https://arxiv.org/abs/2508.10104) | `2508.10104_dinov3.pdf` | dense feature、Gram anchoring 与后处理对齐 |
| Depth Anything V2 | [arXiv:2406.09414](https://arxiv.org/abs/2406.09414) | `2406.09414_depth_anything_v2.pdf` | 单目深度基础模型与伪标签策略 |

## D. 可评测的开放模型家族

| 论文 | 原始来源 | 本地文件 | 关注点 |
| --- | --- | --- | --- |
| Qwen2.5-VL Technical Report | [arXiv:2502.13923](https://arxiv.org/abs/2502.13923) | `2502.13923_qwen2_5_vl.pdf` | native dynamic resolution、window attention、grounding 与 agent 能力 |
| InternVL 2.5 | [arXiv:2412.05271](https://arxiv.org/abs/2412.05271) | `2412.05271_internvl2_5.pdf` | 视觉/语言/数据/test-time scaling |
| PaliGemma | [arXiv:2407.07726](https://arxiv.org/abs/2407.07726) | `2407.07726_paligemma.pdf` | SigLIP + Gemma 的 transfer VLM |
| PaliGemma 2 | [arXiv:2412.03555](https://arxiv.org/abs/2412.03555) | `2412.03555_paligemma2.pdf` | 多尺寸、多分辨率与广泛迁移任务 |
| Gemma | [arXiv:2403.08295](https://arxiv.org/abs/2403.08295) | `2403.08295_gemma.pdf` | Gemma 家族起点与训练/安全报告 |
| Gemma 2 | [arXiv:2408.00118](https://arxiv.org/abs/2408.00118) | `2408.00118_gemma2.pdf` | local/global attention、GQA 与蒸馏 |
| Gemma 3 | [arXiv:2503.19786](https://arxiv.org/abs/2503.19786) | `2503.19786_gemma3.pdf` | Gemma 家族的多模态、长上下文与视觉输入 |
| Gemma 4 | [arXiv:2607.02770](https://arxiv.org/abs/2607.02770) | `2607.02770_gemma4.pdf` | 2026-07 的原生图像/音频、多模态与 thinking mode |

## E. 语义—物理融合与 2026 相邻工作

| 论文 | 原始来源 | 本地文件 | 对本项目的作用 |
| --- | --- | --- | --- |
| LEO: Mixture of Vision Encoders | [arXiv:2501.06986](https://arxiv.org/abs/2501.06986) | `2501.06986_leo_mixture_vision_encoders.pdf` | 语义与低层视觉能力分工；支持多编码器而非单一 VLM 表征包办 |
| CF-VLM: Counterfactual Fine-Tuning | [arXiv:2506.17267](https://arxiv.org/abs/2506.17267) | `2506.17267_cf_vlm_counterfactual.pdf` | 为提示/先验路径提供反事实训练与错误证据控制参考 |
| Harnessing Foundation Models for Accurate Material Classification | [CVPR 2026](https://openaccess.thecvf.com/content/CVPR2026/html/Lin_Harnessing_the_Power_of_Foundation_Models_for_Accurate_Material_Classification_CVPR_2026_paper.html) | `2603.17390_foundation_material_classification.pdf` | VLM 语义先验、DINOv2 视觉特征和合成材质数据的分工组合；与“直接语义判物理”区分 |
| ICTPolarReal | [CVPR 2026](https://openaccess.thecvf.com/content/CVPR2026/html/Yang_ICTPolarReal_A_Polarized_Reflection_and_Material_Dataset_of_Real_World_CVPR_2026_paper.html) | `2603.24912_ictpolarreal.pdf` | 偏振、漫/镜面反射和多光照真值；可支撑反射响应与材质属性验证 |
| Event-MLLM | [arXiv:2603.27558](https://arxiv.org/abs/2603.27558) | `2603.27558_event_mllm.pdf` | 依据照明质量动态路由事件/RGB，并用正常光语义修正；对应质量感知路由 |
| VLMaterial | [arXiv:2604.11671](https://arxiv.org/abs/2604.11671) | `2604.11671_vlmaterial_camera_radar.pdf` | VLM 提候选、雷达介电证据验证、冲突时按不确定性融合；是“语义提案—物理验证”的直接相邻路线 |
| UniPrior | [CVPR 2026](https://openaccess.thecvf.com/content/CVPR2026/html/Li_Towards_Generalized_Representations_for_Low-Light_Understanding_When_Signal_Constancy_Meets_CVPR_2026_paper.html) | `2026_cvpr_uniprior_low_light.pdf` | 信号恒常先验、视觉基础模型语义与测试时适配；支持不变因素与语义分支分工 |
| Zero-Shot Depth Completion with VLM | [CVPR 2026](https://openaccess.thecvf.com/content/CVPR2026/html/Yan_Zero-Shot_Depth_Completion_with_Vision-Language_Model_CVPR_2026_paper.html) | `2026_cvpr_zero_shot_depth_completion_vlm.pdf` | 将稀疏深度编码为视觉提示并加入文本监督；提示应携带测量而非仅靠类别共现 |
| DepthSAM | [CVPR 2026](https://openaccess.thecvf.com/content/CVPR2026/html/Han_Beyond_Appearance_Camouflaged_Object_Detection_via_Geometric_Structure_CVPR_2026_paper.html) | `2026_cvpr_depthsam_geometric_semantic_fusion.pdf` | 用稀疏 MoE 适配深度基础模型并做几何—语义融合；提示基础模型存在任务错位 |
| S3-PHYS | [CVPRW 2026](https://openaccess.thecvf.com/content/CVPR2026W/OpenSUN3D/html/Lan_Efficient_Structure-Guided_3D_Physical_Property_Reasoning_CVPRW_2026_paper.html) | `2026_cvprw_structure_guided_physical_reasoning.pdf` | 先用 DINO 建结构，再在高质量视图稀疏提取 CLIP 材质/物理属性；对应结构先于语义密集化 |
| SAIL | [WACV 2026](https://openaccess.thecvf.com/content/WACV2026/html/Chai_SAIL_Lighting-Invariant_Representation_for_Consistent_Semantic_Understanding_WACV_2026_paper.html) | `2026_wacv_sail_lighting_invariant.pdf` | 用生成先验学习照明不变表征；作为“只做不变性”对照，需防止丢失材质响应线索 |

## F. 本轮补充：基础数据、物理模态和可靠性方法

这些 PDF 下载到本地 `paper/这些文献是什么作用和思路的提供/`，并按作用分子目录保存。它们补的是基础定义、物理验证器、结构语义桥接、主动测量和校准/拒答，不改变既有实验结论。

| 论文 | 原始来源 | 本地文件 | 对本项目的作用 |
| --- | --- | --- | --- |
| Material Recognition in the Wild / MINC | [CVPR 2015](https://openaccess.thecvf.com/content_cvpr_2015/html/Bell_Material_Recognition_in_2015_CVPR_paper.html) | `paper/这些文献是什么作用和思路的提供/01_材质数据与基准/2015_cvpr_minc_material_recognition.pdf` | 材质分类经典野外基准；用于类别、patch/segment 输入和简单视觉基线设计 |
| OpenSurfaces | [Cornell project PDF](https://www.cs.cornell.edu/~paulu/opensurfaces.pdf) | `paper/这些文献是什么作用和思路的提供/01_材质数据与基准/2013_siggraph_opensurfaces.pdf` | 表面级外观、材质、分割和场景上下文标注；补充材质标签与 provenance 思路 |
| Intrinsic Images in the Wild | [Cornell project PDF](https://www.cs.cornell.edu/~sbell/pdf/siggraph2014-intrinsic.pdf) | `paper/这些文献是什么作用和思路的提供/02_内禀图像_反射_材质估计/2014_siggraph_intrinsic_images_in_the_wild.pdf` | 内禀图像相对反射标注协议；用于审计 albedo 辅助证据 |
| Intrinsic Image Diffusion for Indoor Single-view Material Estimation | [CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/html/Kocsis_Intrinsic_Image_Diffusion_for_Indoor_Single-view_Material_Estimation_CVPR_2024_paper.html) | `paper/这些文献是什么作用和思路的提供/02_内禀图像_反射_材质估计/2024_cvpr_intrinsic_image_diffusion.pdf` | 更强 intrinsic/material estimator 候选；只能作为组件或 teacher，不替代 gate |
| Intrinsic Image Fusion for Multi-View 3D Material Reconstruction | [CVPR 2026](https://openaccess.thecvf.com/content/CVPR2026/html/Kocsis_Intrinsic_Image_Fusion_for_Multi-View_3D_Material_Reconstruction_CVPR_2026_paper.html) | `paper/这些文献是什么作用和思路的提供/02_内禀图像_反射_材质估计/2026_cvpr_intrinsic_image_fusion.pdf` | 多视角 intrinsic fusion；为多光照/多视角 teacher 和外部验证提供参考 |
| Multimodal Material Segmentation | [CVPR 2022](https://openaccess.thecvf.com/content/CVPR2022/html/Liang_Multimodal_Material_Segmentation_CVPR_2022_paper.html) | `paper/这些文献是什么作用和思路的提供/03_多物理模态与材质分割/2022_cvpr_multimodal_material_segmentation.pdf` | RGB、flash、polarization 等物理模态的材质分割；支持物理验证器设计 |
| Glass Segmentation Using Intensity and Spectral Polarization Cues | [CVPR 2022](https://openaccess.thecvf.com/content/CVPR2022/html/Mei_Glass_Segmentation_Using_Intensity_and_Spectral_Polarization_Cues_CVPR_2022_paper.html) | `paper/这些文献是什么作用和思路的提供/03_多物理模态与材质分割/2022_cvpr_glass_polarization_segmentation.pdf` | 玻璃/透明材料的强度与偏振验证；支撑光学属性纠错子集 |
| Beyond Appearances: Material Segmentation with Embedded Spectral Information from RGB-D | [CVPRW 2024](https://openaccess.thecvf.com/content/CVPR2024W/LXCV/html/Perez_Beyond_Appearances_Material_Segmentation_with_Embedded_Spectral_Information_from_RGB-D_CVPRW_2024_paper.html) | `paper/这些文献是什么作用和思路的提供/03_多物理模态与材质分割/2024_cvprw_rgbd_spectral_material_segmentation.pdf` | RGB-D 到光谱线索的材质分割；作为深度/谱先验的邻接参考 |
| Physical Property Understanding from Language-Embedded Feature Fields / NeRF2Physics | [CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/html/Zhai_Physical_Property_Understanding_from_Language-Embedded_Feature_Fields_CVPR_2024_paper.html) | `paper/这些文献是什么作用和思路的提供/04_结构语义桥接与物理属性/2024_cvpr_nerf2physics.pdf` | 语言嵌入特征场与物理属性；为结构化物理 claim 和 3D 场景候选提供参考 |
| SAM-CLIP | [CVPRW 2024](https://openaccess.thecvf.com/content/CVPR2024W/ELVM/html/Wang_SAM-CLIP_Merging_Vision_Foundation_Models_Towards_Semantic_and_Spatial_Understanding_CVPRW_2024_paper.html) | `paper/这些文献是什么作用和思路的提供/04_结构语义桥接与物理属性/2024_cvprw_sam_clip.pdf` | SAM 空间能力与 CLIP 语义能力桥接；对应结构先于语义密集化 |
| CLIP-DINOiser | [ECCV 2024](https://www.ecva.net/papers/eccv_2024/papers_ECCV/html/141_ECCV_2024_paper.php) | `paper/这些文献是什么作用和思路的提供/04_结构语义桥接与物理属性/2024_eccv_clip_dinoiser.pdf` | CLIP 与 DINO 特征融合；作为 DINO/SigLIP frozen-feature gate 的对照 |
| GenNBV | [CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/html/Chen_GenNBV_Generalizable_Next-Best-View_Policy_for_Active_3D_Reconstruction_CVPR_2024_paper.html) | `paper/这些文献是什么作用和思路的提供/05_主动测量与下一视角/2024_cvpr_gennbv_next_best_view.pdf` | 主动 next-best-view 策略；为主动光照 agent 的固定/随机/oracle 对照提供参考 |
| On Calibration of Modern Neural Networks | [ICML 2017 / PMLR](https://proceedings.mlr.press/v70/guo17a.html) | `paper/这些文献是什么作用和思路的提供/06_可靠性_校准_拒答/2017_icml_calibration_modern_neural_networks.pdf` | 置信度校准；用于 teacher 可靠性、路由器和拒答阈值 |
| SelectiveNet | [ICML 2019 / PMLR](https://proceedings.mlr.press/v97/geifman19a.html) | `paper/这些文献是什么作用和思路的提供/06_可靠性_校准_拒答/2019_icml_selectivenet_reject_option.pdf` | 选择性预测与拒答；用于冲突时降级、拒答或请求额外测量 |
| Distilling the Knowledge in a Neural Network | [arXiv:1503.02531](https://arxiv.org/abs/1503.02531) | `paper/这些文献是什么作用和思路的提供/07_蒸馏基础/2015_arxiv_distilling_knowledge_neural_network.pdf` | 普通 KD 基线；选择性特权蒸馏必须优于朴素 KD 与等容量学生 |

## 阅读顺序

1. `Multi-Illumination`、`ITA`、`Eyes Wide Shut`：先定位本项目现象和视觉缺陷。
2. `FMMC`、`UniPrior`、`VLMaterial`、`S3-PHYS`：比较语义先验、物理验证、不变性和结构优先四种角色分工。
3. `CLIP/SigLIP`、`DINOv2/v3`：设计同容量 frozen-feature gate。
4. `C2KD`：仅在融合 teacher 通过后设计选择性迁移。
5. `ICTPolarReal`、`Zero-Shot Depth Completion`、`DepthSAM`：核查物理测量如何进入视觉模型及任务适配。
6. `BLIP-2`、`LLaVA`、`Flamingo`：理解视觉桥接方案及其消融。
7. `Qwen2.5-VL`、`InternVL 2.5`、`PaliGemma/Gemma`：选择不同机制、不同规模的可运行基线。
8. `ViperGPT`、`MM-ReAct`、`LLaVA-Plus`：只有任务确实需要工具组合时再进入 agent 层。
