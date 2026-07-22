# 项目状态

**更新时间：2026-07-22**

状态定义：`Verified`、`Completed`、`Smoke test`、`Planned`、`Needs verification`、`No-Go`、`Blocked`、`Not started`。

## 研究资产

| 工作项 | 证据 | 状态 | 结论或缺口 |
| --- | --- | --- | --- |
| Material constancy RGB gate v1 | 115 样本、23 区域、10 场景；Qwen 汇总与日志存在 | Completed | 初步准确率 70.43%；规模较小，不能作为最终结论 |
| Material constancy RGB gate v2 | 330 样本、66 区域、30 场景；Qwen/InternVL 逐样本结果与跨模型汇总存在 | Completed | 两模型均出现大量跨光照翻转；尚缺数据许可和环境锁定审计 |
| RGB + albedo intervention | 两模型配对比较和 bootstrap CI 存在 | No-Go | Qwen +0.91 pp、InternVL -1.82 pp，两个准确率 CI 均跨零 |
| Shared region marker | 两模型、330 样本报告与结果存在 | No-Go | 相对单框有同方向小幅变化，但 CI 跨零，且不能恢复 Qwen RGB 基线 |
| NYUv2 support review | 167 张候选图；14 条人工审核记录 | Needs verification | 当前 CSV 为 2 support、11 non-support、1 uncertain；生成链和数据许可未在仓库内闭合 |
| 文献证据库 | 57 篇官方来源 PDF、本地 SHA-256、分类索引与使用边界 | Completed | 已覆盖语义—物理融合、材质、深度、低照度、事件、偏振、结构引导、材质基准、内禀图像、主动测量、校准拒答和蒸馏基础；PDF 保持本地忽略 |
| 科研设计模式库 | 12 个核心模式、反模式、机制迁移卡、探索/确认分轨与组合上限 | Completed | 新方向须引用模式并预注册角色、控制与门槛 |
| 语义—物理路线审计 | 本仓库负结果与 2024–2026 相邻工作碰撞矩阵 | Completed | 直接语义替代物理和冻结 VLM 拼图保持 No-Go；三类受控路线进入候选 |
| Material response probe v0 | 预注册计划、相对路径配置、smoke manifest 准备脚本和 unittest 存在；本地 smoke 生成 18 样本/6 区域/6 场景 | Smoke test | 下一主线 gate 已部署到预备资产；尚未抽取 frozen features、未训练、未形成研究结论 |

## 工程与复现

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| 自有实验脚本 | Completed | 材质数据构建、两模型推理、albedo、统计和报告脚本存在 |
| 可移植配置 | Needs verification | 旧四个 JSON 配置仍含 `/home/xjy/...` 绝对路径；已新增 `material_response_probe_v0` 相对路径配置与本地覆盖样例 |
| 环境锁定 | Not started | 未发现完整 `requirements`、Conda、锁文件或容器定义；本轮只建立本地覆盖样例，不构成环境锁 |
| 自动化测试 | Smoke test | 已新增标准库 unittest 覆盖 `material_response_probe_v0` smoke manifest 的路径归一化、抽样和文件校验逻辑 |
| 数据/模型 provenance | Needs verification | 模型 ID/revision 部分存在；数据许可、哈希和完整下载来源未统一登记 |
| Git 忽略边界 | Completed | 已新增 `.gitignore` 防止后续新增本地资产 |
| 已跟踪资产治理 | Blocked | 1,237 个文件中含 781 个 data、249 个 results、117 个 Office/QA 临时项；清理方式待协作者决策 |
| fork/upstream 协作 | Needs verification | 已确认 origin 为个人 fork、upstream 为原仓库；远端引用显示双方各 1 个独有提交，正式同步前需在网络恢复后重新 fetch |
| 项目任务技术报告 | Completed | 已依据代码、配置、manifest、聚合结果和治理文档形成自包含 HTML 与可审计 artifact；自动浏览器 QA 受阅读器顶部栏约 8 px 横向溢出限制，结构校验通过 |
