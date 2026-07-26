# 项目快照

**日期：2026-07-26**

- 当前分支：`research/sgnet-rgbdd-migration`；工作区已有大量 staged 改动，必须保留，不提交/推送，除非用户明确要求。
- 已关闭的材质 LDR 多光照路线：直接 response 分类、response selective rejection、像素 photometric trajectory 及其官方零重叠 test confirmation 均为 `No-Go`。不得继续调 descriptor、crop、threshold、LoRA、BRDF deep head、verifier 或蒸馏。
- 最强外部反证：官方 CC BY 4.0 Multi-Illumination test split（80 regions / 30 untouched scenes）中，photometric primary 30.83%，RGB sample-majority 43.33%；三 seed 的 test-scene bootstrap CI 均显著为负。
- 数据 provenance：Multi-Illumination 官方来源、SDK revision、archive hash、CC BY 4.0 和 train/test 零 overlap 已闭合，见 `docs/multi-illumination-provenance.md`。SGNet/RGB-D-D、NYUv2 资产的许可、checkpoint 和运行 provenance 仍未闭合。
- 优先候选已在审计门禁关闭：6 train-pool scenes、25 光照、90 个官方 mask 区域、0 训练参数的 oracle 检验显示 gray probe 动态范围中位 1.72 倍对场景 17.35 倍、相关系数中位 -0.019、判别力中位增益 0.977，light-probe normalization 为 `No-Go`；线性 HDR 实测找回中位 5.8% 截断像素（最差单方向 69.4%），真实但属同一观测量去截断。Multi-Illumination 无偏振通道与几何真值，次优先候选不可得。见 `docs/hdr-light-probe-candidate-audit-2026-07-26.md`、`D-018`。
- 当前可执行入口：回退分支已生效——转向 SGNet/RGB-D-D 的 provenance、许可、checkpoint/hash 与单样本 smoke，按 `docs/sgnet-rgbdd-provenance.md` 的 execution gate 逐项闭合；闭合前不训练，不把上游聚合结果称为本 fork 复现。
- 关键 Git 阻塞：初始提交中的已跟踪 data/results/生成资产治理仍未获协作者决策；不得擅自清理历史。
- 交接入口：`docs/worknow.md`、`docs/project-status.md`、`docs/decision-log.md`、`reports/material_photometric_trajectory_external_confirmation_v0.md`。
