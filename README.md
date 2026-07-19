# 多模态研究项目

这是本项目代码、实验协议、证据摘要和研究决策的统一入口。当前仓库事实主线是材质恒常性跨光照诊断，并保留一批待核验的 NYUv2 支撑审核资产。

开始工作前阅读：

1. `AGENTS.md`
2. `rules.md`
3. `docs/worknow.md`
4. `docs/project-status.md`

完整文档索引见 `docs/README.md`。

## 目录说明

| 目录 | 用途 |
| --- | --- |
| `data/` | 原始数据、处理中间数据与标准化数据；默认不跟踪。 |
| `models/` | 模型结构和模型卡片；权重与检查点不跟踪。 |
| `configs/` | 可复现实验的 YAML、JSON 或 TOML 配置。 |
| `scripts/` | 数据预处理、训练、评估、导出等命令行脚本。 |
| `notebooks/` | 探索分析和可视化 notebook；稳定流程应迁移到 `scripts/`。 |
| `experiments/` | 实验计划；完整日志和 manifest 保持本地。 |
| `results/` | 逐样本结果和可视化保持本地；聚合摘要进入文档。 |
| `literature/` | 阅读笔记与资源索引；论文原文件不跟踪。 |
| `reports/` | 可提交 Markdown；DOCX、PDF 和 QA 产物不跟踪。 |
| `assets/` | 图示、提示词样例、标注规范和其他小型辅助资源。 |
| `docs/` | 当前任务、状态、计划、决策、流程与实验模板。 |

## 使用约定

- 将原始数据放在 `data/raw/`，保持只读。
- 每次实验先在 `experiments/plans/` 建计划，再保存配置、commit、manifest hash、模型 revision、命令、环境和状态。
- 逐样本输出、完整日志、数据和权重仅留在本地或服务器；Git 只保留可复现代码和脱敏聚合证据。
- 共享配置不得包含密钥，避免机器绝对路径。
- 当前初始提交已经跟踪部分本地资产；处理方式见 `docs/repository-hygiene-audit.md`，在协作者确认前不得擅自删除或改写历史。
