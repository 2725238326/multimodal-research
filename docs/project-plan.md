# 项目计划

## Phase 0 — 仓库治理

退出条件：

- 确认初始提交是否已被他人使用；
- 完成已跟踪资产的保留/移除分类；
- 选择前向清理或经同意的历史重写；
- 配置中不再新增机器绝对路径；
- 数据、模型、输出和报告生成物的边界与 README 一致。

## Phase 1 — 复现基线

退出条件：

- 建立环境锁定文件；
- 为现有材质实验补齐数据来源、许可、哈希、划分和独立统计单元；
- 为核心脚本增加最小输入、解析和统计测试；
- 用固定 manifest 复跑一个小型 smoke test；
- 聚合摘要与既有结果在容许误差内一致。

## Phase 2 — 研究方向决策

当前有效结论：

- 零训练 RGB+albedo 输入没有跨模型稳定收益；
- 共同区域标记没有通过预设门槛；
- 不继续堆叠同类提示元素。

下一研究方向必须通过以下门禁：

1. 明确说明要解决的既有失败；
2. 与最近工作完成结论级碰撞检查；
3. 数据真值和许可可用；
4. 至少一个简单基线、一个负对照和一个停止条件；
5. 在 1–2 天可完成的 oracle 或 frozen-feature gate 上有明确 Go/No-Go。

研究组织采用 `docs/research-design-patterns.md` 的“一主线、两邻接、一高风险”上限。当前候选组合见 `docs/semantic-physical-route-audit.md`：

- 主线候选：不变身份—光响应因子化与选择性特权蒸馏；
- 邻接 gate：语义提案—光学验证；
- 邻接方向：结构引导的物理关系 agent，当前受数据闭环阻塞；
- 高风险探索：主动反事实光照 agent，只在真实光照选择 gate 通过后考虑生成式干预。

当前已部署的下一步预备资产为 `material_response_probe_v0`：先用固定 smoke manifest、相对路径配置和 unittest 验证输入链路，再进入 frozen-feature/oracle gate。该阶段不授权训练、LoRA、VLM 提示扩展或新数据下载。

2026-07-25 `material_response_probe_v0` 已完成并判为 No-Go：直接拼接多光照响应降低了翻转率，但没有提高区域准确率且损害宏准确率。该机制不进入 LoRA/全模型训练。响应作为不确定性/拒答信号仅保留为新候选，必须另行预注册和使用独立确认数据。

2026-07-26 `material_response_selective_gate_v0` 已按独立探索计划完成并判为 No-Go：response router 在 80%/90% 固定覆盖率下未取得 CI 排除零的收益，AURC 与错误检测也未稳定优于 RGB confidence，且 shuffled response 对照无法排除。当前 frozen response summary 路线关闭，不再进行阈值调优、LoRA、选择性蒸馏或全模型训练；重新开启必须引入新物理测量或独立数据并从 oracle gate 开始。

2026-07-26 新的 censor-aware pixel photometric trajectory 在 development scene CV 中获得平均 +5.56 pp，但预注册 CI 未过门槛；随后在官方 CC BY 4.0、零 scene overlap 的 30-scene test split 上显著反转，平均比 sample-majority RGB 低 12.50 pp，三个 bootstrap CI 均排除零于负方向。由此关闭当前所有基于五张 LDR crop 的 multi-light response 分类、拒判和 verifier 路线。下一候选必须改变可观测证据，例如使用标定 HDR/light probe、偏振/flash 或几何验证；不得只在当前 descriptor/threshold 上继续优化。

2026-07-26 已对优先候选“标定 HDR + light-probe normalization”完成零训练审计。测量资源确实存在且许可未变，但机制在训练前的 oracle 检验上失败：gray probe 跨光照动态范围中位 1.72 倍，而它要归一化的场景亮度中位 17.35 倍，中位相关系数 -0.019，归一化后 within-region 跨光照方差中位反升 2.5%。物理原因是探针处辐照度对闪光方向近似不变；chrome probe 虽保留方向信息，但转为逐表面辐照度需要该数据集不提供的法向。线性 HDR 单独看只是同一观测量的去截断（实测找回中位 5.8% 像素），不满足“改变可观测证据”的要求。Multi-Illumination 亦无偏振通道与几何真值，次优先候选同样不可得。据此回退分支生效：主线转向 SGNet/RGB-D-D 的 provenance、许可、checkpoint/hash 与单样本 smoke。

2026-07-23 已审计 `upstream/main` 的 SGNet/RGB-D-D 深度超分更新。该路线是上游新增方向，不自动替换当前 fork 的材质恒常性主线；若要采用，必须作为新的候选主线重新预注册，并优先迁移可复核的配置、脚本、计划和聚合摘要，不直接合并上游对治理文档的删除。

2026-07-25 已在 `research/sgnet-rgbdd-migration` 完成上述资产的选择性静态迁移。该状态仅为 `Smoke test`：在第三方 provenance、环境锁、数据/权重哈希和单样本执行闭合前，不进入训练，也不把上游结果视为本 fork 复现结论。

任何候选在 Phase 0/1 完成前只允许数据审计、离线分析和不启动训练的计划工作。

## Phase 3 — 受控实验

- 实验配置、manifest hash、代码 commit 和命令齐全；
- 先 smoke test，再完整运行；
- 按独立场景/区域而非仅按图片计算统计；
- 逐样本输出留在服务器，Git 只保留脱敏聚合摘要；
- 结论同步到状态表和决策日志。
