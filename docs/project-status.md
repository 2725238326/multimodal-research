# 项目状态

**更新时间：2026-07-19**

状态定义：`Verified`、`Completed`、`Needs verification`、`No-Go`、`Blocked`、`Not started`。

## 研究资产

| 工作项 | 证据 | 状态 | 结论或缺口 |
| --- | --- | --- | --- |
| Material constancy RGB gate v1 | 115 样本、23 区域、10 场景；Qwen 汇总与日志存在 | Completed | 初步准确率 70.43%；规模较小，不能作为最终结论 |
| Material constancy RGB gate v2 | 330 样本、66 区域、30 场景；Qwen/InternVL 逐样本结果与跨模型汇总存在 | Completed | 两模型均出现大量跨光照翻转；尚缺数据许可和环境锁定审计 |
| RGB + albedo intervention | 两模型配对比较和 bootstrap CI 存在 | No-Go | Qwen +0.91 pp、InternVL -1.82 pp，两个准确率 CI 均跨零 |
| Shared region marker | 两模型、330 样本报告与结果存在 | No-Go | 相对单框有同方向小幅变化，但 CI 跨零，且不能恢复 Qwen RGB 基线 |
| NYUv2 support review | 167 张候选图；14 条人工审核记录 | Needs verification | 当前 CSV 为 2 support、11 non-support、1 uncertain；生成链和数据许可未在仓库内闭合 |
| 文献证据库 | `literature/notes/` 为空 | Not started | 缺论文索引、来源、许可和与实验的对应关系 |

## 工程与复现

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| 自有实验脚本 | Completed | 材质数据构建、两模型推理、albedo、统计和报告脚本存在 |
| 可移植配置 | Needs verification | 四个 JSON 配置含 `/home/xjy/...` 绝对路径 |
| 环境锁定 | Not started | 未发现 `requirements`、Conda、锁文件或容器定义 |
| 自动化测试 | Not started | 未发现单元测试或 smoke-test 自动化 |
| 数据/模型 provenance | Needs verification | 模型 ID/revision 部分存在；数据许可、哈希和完整下载来源未统一登记 |
| Git 忽略边界 | Completed | 已新增 `.gitignore` 防止后续新增本地资产 |
| 已跟踪资产治理 | Blocked | 1,237 个文件中含 781 个 data、249 个 results、117 个 Office/QA 临时项；清理方式待协作者决策 |

