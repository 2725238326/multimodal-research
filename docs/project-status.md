# 项目状态

**更新时间：2026-07-26**

状态定义：`Verified`、`Completed`、`Smoke test`、`Planned`、`Needs verification`、`No-Go`、`Blocked`、`Not started`。

## 研究资产

| 工作项 | 证据 | 状态 | 结论或缺口 |
| --- | --- | --- | --- |
| Material constancy RGB gate v1 | 115 样本、23 区域、10 场景；Qwen 汇总与日志存在 | Completed | 初步准确率 70.43%；规模较小，不能作为最终结论 |
| Material constancy RGB gate v2 | 330 样本、66 区域、30 场景；Qwen/InternVL 逐样本结果与跨模型汇总存在 | Completed | 两模型均出现大量跨光照翻转；Multi-Illumination 来源/CC BY 4.0 已闭合，旧模型运行环境仍需统一锁定审计 |
| RGB + albedo intervention | 两模型配对比较和 bootstrap CI 存在 | No-Go | Qwen +0.91 pp、InternVL -1.82 pp，两个准确率 CI 均跨零 |
| Shared region marker | 两模型、330 样本报告与结果存在 | No-Go | 相对单框有同方向小幅变化，但 CI 跨零，且不能恢复 Qwen RGB 基线 |
| NYUv2 support review | 167 张候选图；14 条人工审核记录 | Needs verification | 当前 CSV 为 2 support、11 non-support、1 uncertain；生成链和数据许可未在仓库内闭合 |
| 文献证据库 | 57 篇官方来源 PDF、本地 SHA-256、分类索引与使用边界 | Completed | 已覆盖语义—物理融合、材质、深度、低照度、事件、偏振、结构引导、材质基准、内禀图像、主动测量、校准拒答和蒸馏基础；PDF 保持本地忽略 |
| 科研设计模式库 | 12 个核心模式、反模式、机制迁移卡、探索/确认分轨与组合上限 | Completed | 新方向须引用模式并预注册角色、控制与门槛 |
| 语义—物理路线审计 | 本仓库负结果与 2024–2026 相邻工作碰撞矩阵 | Completed | 直接语义替代物理和冻结 VLM 拼图保持 No-Go；三类受控路线进入候选 |
| Material response probe v0 | 330 样本、66 区域、30 场景；SigLIP2 frozen features、五个 scene folds、三 seed、四类控制与 10,000 次 scene bootstrap；见 `reports/material_response_probe_v0.md` | No-Go | Pairwise response 将 flip rate 从 61.11% 降至 29.80%，但区域准确率从 69.70% 降至 64.65%，三个准确率 CI 均跨零且宏准确率下降 7.87 pp；停止直接拼接和 LoRA 扩展 |
| Material response selective gate v0 | 同一 330 样本缓存；outer-5/inner-4 scene folds、三 seed、固定 80%/90% coverage、AURC、错误 AUROC/AUPRC、三类控制与 10,000 次 scene bootstrap；见 `reports/material_response_selective_gate_v0.md` | No-Go | 80% coverage 平均仅 +1.26 pp 且三个 CI 下界均不大于 0；90% coverage 增量为 0；错误检测与 AURC 无稳定收益且 shuffled control 未排除，停止该响应拒判机制 |
| Photometric trajectory gate v0 | 66 区域、30 development scenes；像素亮度/色度/高光/梯度、曝光 censor、三 seed、scene bootstrap 与 shuffled/exposure controls | No-Go | Primary 比 SigLIP region mean 平均 +5.56 pp，但三个 CI 下界均不大于 0，且未超过旧 sample-majority RGB；只授权外部确认，不授权训练 verifier |
| Photometric external confirmation v0 | 官方 CC BY 4.0 test split；80 区域、30 untouched `everett` scenes、10 类、三 seed、10,000 次 test-scene bootstrap；见 `reports/material_photometric_trajectory_external_confirmation_v0.md` | No-Go | Primary 平均 30.83%，强 RGB 43.33%，下降 12.50 pp；三 seed CI 全部在负区间，exposure/shuffled controls 均更高，关闭当前 multi-light response 路线 |
| HDR + light-probe oracle audit v0 | 6 train-pool scenes、25 光照、90 个官方 mask 区域、0 个训练参数；见 `docs/hdr-light-probe-candidate-audit-2026-07-26.md` | No-Go（light-probe）/ Partially supported（HDR） | Gray probe 动态范围中位 1.72 倍对场景 17.35 倍、相关系数中位 -0.019、判别力中位增益 0.977，归一化不可用；线性 HDR 实测找回中位 5.8% 被截断像素（最差单方向 69.4%，clip 之上延伸中位 35 倍），真实但不足以解释 -12.50 pp，且非新观测量 |
| Upstream SGNet/RGB-D-D updates | 14 个上游提交已选择性迁移到 `research/sgnet-rgbdd-migration`；18 个 JSON、22 个 Python CLI 和 4 个 shell 脚本完成静态检查；见 `docs/sgnet-rgbdd-migration-audit-2026-07-25.md` | Smoke test | 治理资产均保留，但未完成第三方 provenance、环境锁、数据/权重核验或单样本模型执行；上游结果仍为 Needs verification，real 4x transfer/calibration 保持 No-Go |

## 工程与复现

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| 自有实验脚本 | Completed | 材质数据构建、两模型推理、albedo、统计和报告脚本存在 |
| 可移植配置 | Needs verification | 旧四个 JSON 配置仍含 `/home/xjy/...` 绝对路径；已新增 `material_response_probe_v0` 相对路径配置与本地覆盖样例 |
| 环境锁定 | Smoke test | 远端 Conda `summer` 已建立并导出 environment/explicit/pip freeze；本地忽略区保留回传副本，尚未形成跨机器容器复现 |
| kykt 远端研究目录 | Completed | `ssh kykt` 已可用；`/hdd3/kykt26/{training,experiments,results}` 权限 `775`；`summer` 环境、固定模型、实验代码和隔离结果目录已实际用于 smoke/full gate |
| 自动化测试 | Smoke test | Material response 与 photometric gate 的单元、CLI、真实缓存 dry-run 和计算 smoke 均通过；最终全量数量见 `docs/worknow.md` |
| 数据/模型 provenance | Needs verification | Multi-Illumination 数据来源、CC BY 4.0、archive/SDK hash 和 split 已闭合；SigLIP/Qwen revision 已闭合。其他旧数据、SGNet/NYUv2 checkpoint 与许可仍待统一登记 |
| Git 忽略边界 | Completed | 已新增 `.gitignore` 防止后续新增本地资产 |
| 已跟踪资产治理 | Blocked | 1,237 个文件中含 781 个 data、249 个 results、117 个 Office/QA 临时项；清理方式待协作者决策 |
| fork/upstream 协作 | Needs verification | `upstream` 已 fetch 且 push URL 设为 `no_push`；当前 `upstream/main` 独有 14 提交、本 fork `main` 独有 3 提交，直接 merge 会删除治理文档并冲突 |
| 项目任务技术报告 | Completed | 已依据代码、配置、manifest、聚合结果和治理文档形成自包含 HTML 与可审计 artifact；自动浏览器 QA 受阅读器顶部栏约 8 px 横向溢出限制，结构校验通过 |
