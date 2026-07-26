# 决策记录

| ID | 日期 | 决策 | 证据 | 后果 | 复核条件 |
| --- | --- | --- | --- | --- | --- |
| D-001 | 2026-07-19 | 项目管理和研究结论只依据本仓库内容 | 用户明确要求；仓库已有独立实验资产 | 不导入其他仓库的任务、路线或状态 |
| D-002 | 2026-07-19 | RGB+albedo 和共同区域标记保持 No-Go | 两模型配对 CI 未证明稳定准确率收益；区域标记报告明确未过门槛 | 不继续扩大同类零训练提示实验 | 新机制针对明确失败且通过预注册 gate |
| D-003 | 2026-07-19 | 本轮只新增忽略规则，不删除已跟踪资产 | 初始提交已跟踪 1,237 个文件，且不清楚是否被协作者使用 | 先防止新增泄漏；清理方案单独决策 | 确认协作者和历史使用情况 |
| D-004 | 2026-07-19 | 新实验先治理、复现，再研究扩展 | 缺环境锁定、测试、统一 provenance 和可移植配置 | Phase 0/1 完成前不启动新训练 | 仓库和复现门禁全部通过 |
| D-005 | 2026-07-21 | 只迁移旧工作区的研究流程，不迁移研究内容 | 用户要求隔离；本仓库为唯一项目事实来源 | 采用查新、oracle/frozen gate、反证控制和停损条件；旧结论、数据、代码、状态不进入本项目 | 任何候选机制均须用本仓库证据重新预注册 |
| D-006 | 2026-07-21 | 论文 PDF 仅保存于本地 `paper/`，Git 跟踪索引与哈希 | 项目 Git 边界与第三方版权要求 | `paper/` 加入忽略；PR 不包含 PDF | 取得明确再分发许可并完成仓库资产复核 |
| D-007 | 2026-07-21 | 向原仓库贡献采用 fork 分支到 upstream 的聚焦 PR | origin/upstream 角色已确认；双方 main 当前存在分叉 | 新贡献从最新 upstream/main 建主题分支；不直接强推或混入个人 main 历史 | 网络恢复后 fetch 并复核分叉 |
| D-008 | 2026-07-21 | 新方向统一使用科研设计模式和机制迁移卡 | 多方向探索需要复用结构同时避免模块堆叠 | 模式、反模式、单机制增量和 1–2 天门禁进入实验计划 | 模式无法提升归因或产生过高文档成本 |
| D-009 | 2026-07-21 | 语义负责提案/约束/路由，物理证据负责验证和否决物理 claim | 本仓库冻结 VLM 拼接无稳定收益；相邻工作显示强方法采用结构、质量和冲突感知 | 不再把 VLM 语义当物理真值；优先双向、可证伪的信息流 | 新证据证明直接语义估计在反常/冲突子集仍可靠 |
| D-010 | 2026-07-21 | 研究组合限制为一主线、两邻接 gate、一高风险探索 | 控制 WIP、算力和多重比较 | 其余方向只进入候选池；未过 gate 不并行扩大 | 资源和协作者规模发生明确变化 |
| D-011 | 2026-07-22 | 下一主线 gate 部署为 `material_response_probe_v0`，先做 smoke manifest 与 frozen-feature/oracle 准备 | 已有 RGB+albedo/共同框 No-Go；路线审计建议先验证光照响应是否提供额外材质信息 | 建立预注册计划、相对路径配置、本地覆盖样例和 unittest；训练仍未授权 | smoke 链路失败、数据许可/环境锁无法闭合，或 response probe 被负对照解释 |
| D-012 | 2026-07-23 | 不直接 merge `upstream/main`；先审计并选择性迁移 SGNet/RGB-D-D 资产 | `upstream/main` 独有 14 提交、本 fork `main` 独有 3 提交；合并预检显示会删除治理文档、文献索引和 `material_response_probe_v0` 资产 | 新增上游变化审计；SGNet/RGB-D-D 结果标为待本 fork 复核，不覆盖当前材质主线 | 用户明确决定切换主线并完成迁移分支冲突处理、数据许可、环境和测试复核 |
| D-013 | 2026-07-25 | SGNet/RGB-D-D 选择性迁移只升级为静态 Smoke test，不切换当前材质主线 | 50 个文件级变化已迁移且静态检查通过；本机缺 sklearn/CUDA，第三方来源、许可证、环境和数据/权重哈希未闭合 | 保留上游聚合结果及 No-Go 证据供复核；在 provenance 和单样本执行通过前不训练、不宣称复现 | 用户明确切换主线，且 Phase 0/1 与 SGNet 专项复现门禁全部通过 |
| D-014 | 2026-07-25 | `material_response_probe_v0` 直接响应特征拼接判为 No-Go，停止 LoRA/全模型扩展 | 三 seed 下 pairwise response 区域准确率均低于 RGB baseline 且 CI 跨零，宏准确率下降 7.87 pp；稳定性改善不能补偿辨识损失 | 保留响应作为潜在不确定性信号；若继续，必须新建选择性拒答计划并使用 nested threshold 与 held-out confirmation | 新数据或独立确认表明响应路由在固定覆盖率下提高选择性准确率且不损害基线 |
| D-015 | 2026-07-26 | `material_response_selective_gate_v0` 判为 No-Go，关闭 frozen response summary 的分类与拒判路线 | outer-5/inner-4 scene nested gate 中，80% coverage 平均 +1.26 pp 但三个 seed 的 CI 下界均不大于 0；90% coverage 增量为 0；AURC/错误检测无稳定改善且 shuffled response 未排除 | 不做额外阈值调优、LoRA、选择性蒸馏或全模型训练；释放该邻接 gate 资源，优先闭合数据许可并选择新物理证据路线 | 新物理测量或独立场景数据提供可证伪 oracle 上限，且重新预注册的 gate 显著优于 RGB confidence 与 shuffled controls |
| D-016 | 2026-07-26 | 官方 Multi-Illumination 来源与许可闭合；使用零重叠 test split确认新 pixel photometry 方法 | 正确项目页明确 CC BY 4.0；SDK commit `a85aa925...` 定义 30 个 `everett` test scenes；官方 ZIP SHA/CRC 与 0 scene overlap 已验证 | 更正“HTTP 403 等于许可不可核验”的旧判断；原始/派生数据仍不进 Git，任何再分发保留 CC BY attribution | 官方页面、许可或固定 archive 发生可核验变化 |
| D-017 | 2026-07-26 | 关闭当前五光照 LDR response 家族，不训练 conflict verifier、BRDF 深层模块、LoRA 或蒸馏 | Pixel trajectory 在 development 平均 +5.56 pp 但 CI 未过；官方 external test 上 primary 30.83% 对 RGB 43.33%，平均 -12.50 pp，三 seed CI 均显著为负，exposure/shuffled controls 更高 | 后续候选必须引入标定 HDR/light probe、偏振/flash 或几何验证等不同可观测证据；禁止在当前 30+30 scenes 上继续调 descriptor、crop 或阈值 | 新测量在独立数据上先通过 oracle 和 control gate |
| D-018 | 2026-07-26 | light-probe normalization 判为 No-Go；calibrated HDR 不单独立项；触发 SGNet/RGB-D-D 回退分支 | 6 train-pool scenes、25 光照、90 个官方 mask 区域、0 训练参数：gray probe 动态范围中位 1.72 倍而场景 17.35 倍，相关系数中位 -0.019，归一化后 within-region 方差中位升 2.5%、判别力增益 0.977，仅 1/6 场景增益超 10%；HDR 实测找回中位 5.8% 截断像素但属同一观测量去截断 | 不为 light probe 设计描述符、不训练、不上传服务器；Multi-Illumination 无偏振通道与几何真值，次优先候选同样不可得，主线转向 SGNet/RGB-D-D provenance 与单样本 smoke | 取得带逐表面几何（法向/深度）或独立物理测量的数据集，使探针辐照度可转为逐表面辐照度 |
