# 仓库卫生审计

**审计日期：2026-07-19**  
**基线提交：`62100d7`**

## 发现

README 声明数据、权重、运行输出和未公开资料应由 `.gitignore` 排除，但基线提交没有 `.gitignore`。

| 类别 | 已跟踪数量 |
| --- | ---: |
| 全部文件 | 1,237 |
| `data/` | 781 |
| `results/` | 249 |
| `reports/` | 136 |
| Python cache / `.pyc` | 13 |
| LibreOffice profile、QA/Office 临时项 | 117 |

此外：

- 新增忽略规则后，共有 1,208 个“已跟踪但现在符合忽略规则”的文件；忽略规则不会自动把它们移出历史；
- `configs/*.json` 和多个 manifest 含 `/home/xjy/multimodal-research/...` 绝对路径；
- `experiments/logs/`、逐样本 JSONL、处理后图片、PDF、DOCX、QA 渲染页和 LibreOffice profile 已进入历史；
- 未发现环境锁定文件和自动化测试；
- 文本扫描未发现明显的口令或 API 密钥，但个人服务器路径已经公开进入提交；
- Multi-Illumination 数据来源与 CC BY 4.0 许可已在 `docs/multi-illumination-provenance.md` 闭合；其他既有数据、生成图片和第三方资产的再分发许可仍未形成完整清单。

## 本轮已做

- 新增 `.gitignore`，阻止后续新增数据、权重、日志、manifest、逐样本结果、缓存和生成报告。
- 未删除、移动或取消跟踪任何已有文件。
- 未改写历史、提交或推送。

## 待决定的清理方式

### 方案 A：前向清理

适合提交已经被他人使用的情况。

- 从下一次提交开始取消跟踪不应公开的资产；
- 文件可保留在本地或服务器；
- Git 历史仍包含旧资产；
- 不需要强制推送，协作风险较低。

### 方案 B：重写历史

仅适合仓库很新、没有其他人基于该提交工作，且所有协作者明确同意的情况。

- 从历史彻底移除生成物和不应公开的资产；
- 需要所有副本重新克隆或重置；
- 需要强制推送；
- 执行前必须备份并确认远端权限。

## 分类建议

| 保留跟踪 | 停止跟踪 |
| --- | --- |
| `scripts/*.py`、稳定 shell 脚本 | `data/**` |
| 可移植且脱敏的 `configs/` | `models/checkpoints/**` |
| `experiments/plans/*.md` | `experiments/logs/**`、完整 manifests |
| 聚合且脱敏的 Markdown/小型 JSON 摘要 | 逐样本 predictions 和大 JSONL |
| 文献索引和自有报告 Markdown | DOCX、PDF、QA 页面、Office profile |
| 项目规则和文档 | caches、临时文件、压缩包 |

## 2026-07-26 新发现：声明边界与已跟踪事实不一致

`.gitignore` 对 `results/quantitative/` 只放行每个实验目录的 `README.md` 与 `summary.json`。已用未跟踪探针文件实测，该白名单对**新增文件**生效正确。

但 `results/quantitative/sgnet_rgbdd_x16_gate/` 中另有 11 个 JSON 处于跟踪状态（`adaptive_frequency_multiseed.json`、`adaptive_threshold_sensitivity.json`、`confirmatory_multiseed.json`、`learned_router_pilot.json`、`nyu_branch_router_pilot.json`、`qualitative_examples_summary.json`、`ramp_routing_development.json`、`relative_hard_confirmation.json`、`rgbdd_real_protocol_summary.json`、`runtime_benchmark.json`、`soft_routing_development.json`、`unseen_texture_generalization.json`）。它们来自上游迁移时的强制添加；已跟踪文件不受 `.gitignore` 约束，因此规则收紧没有回溯生效。

按内容判断，这些文件是聚合摘要（1.5 KB–122 KB 的多 seed 汇总、阈值敏感性扫描与运行时基准），属于 `rules.md` 允许提交的"聚合结果摘要"，不是逐样本预测。因此矛盾出在**白名单过窄**，而不是文件不该存在。

两个可选修法，需与已跟踪资产治理一并决策，本轮不擅自执行：

1. 放宽白名单，允许 `results/quantitative/*/` 下的聚合 JSON，使声明与事实一致；
2. 保持白名单，把这 11 个文件合并进各自的 `summary.json` 或停止跟踪。

## 决策前需要回答

0. `results/quantitative/` 白名单采用上述哪一种修法？
1. `62100d7` 是否已经被学姐或其他协作者拉取或基于它提交？
2. `origin` 与 `upstream` 中哪个是团队正式合并目标？
3. 当前数据、裁剪图和 NYUv2 审核图是否具有公开再分发许可？
4. 聚合结果摘要希望保留在 Git，还是全部只保留服务器？
5. 是否需要 Git LFS；若原始资产不应公开，则不应以 LFS 代替访问控制。
