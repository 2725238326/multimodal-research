# Fork 与上游协作说明

**核验日期：2026-07-23**

## 1. 当前关系

| 名称 | 地址 | 角色 |
| --- | --- | --- |
| `origin` | `https://github.com/2725238326/multimodal-research.git` | 你的 fork；日常推送目标 |
| `upstream` | `https://github.com/aspera11011/multimodal-research.git` | 原仓库；最终合并目标 |

GitHub 页面确认 `2725238326/multimodal-research` fork 自 `aspera11011/multimodal-research`。本地已有正确的两个 remote。

本地远端引用在 2026-07-23 检查时显示 `main` 与 `upstream/main` 已明显分叉：

- fork 独有：3 个提交，当前 `main` 为 `0b0907e 123`；
- upstream 独有：14 个提交，当前 `upstream/main` 为 `0a95b3d feat: train SGNet branch router pilot`；
- 本地快照分支：`sync/upstream-main-20260723`；
- `upstream` push URL 已设为 `no_push`。

因此当前不是可直接 `--ff-only` 合并的状态。上游变化审计见 `docs/upstream-change-audit-2026-07-23.md`。合并预检显示直接 merge 会删除当前 fork 的治理文档、文献索引和 `material_response_probe_v0` 资产；不建议在 `main` 上直接 merge。

当前推荐的同步策略是：

```powershell
git switch -c research/sgnet-rgbdd-migration main
git cherry-pick <reviewed-upstream-commit>
```

或手工迁移上游 SGNet/RGB-D-D 的配置、脚本、计划和聚合摘要，同时保留本 fork 的 `AGENTS.md`、`rules.md`、`docs/` 治理文档和文献索引。

## 2. 推荐贡献方式

向上游交付的单位应是一个聚焦、可审查的 Pull Request，而不是整个个人 `main`。

```powershell
git fetch upstream --prune
git status --short
git switch -c research/<topic> upstream/main
```

然后只把准备贡献的自有代码、测试、可移植配置、实验计划和脱敏聚合摘要带到该分支。若成果已存在于其他本地分支，优先挑选聚焦提交：

```powershell
git cherry-pick <reviewed-commit>
```

审核后推送到 fork：

```powershell
git push -u origin research/<topic>
```

在 GitHub 创建：

- base repository：`aspera11011/multimodal-research`
- base branch：`main`
- head repository：`2725238326/multimodal-research`
- compare branch：`research/<topic>`

上游审查提出修改时，继续提交到同一 fork 分支，PR 会自动更新。不要向共享 `upstream/main` 强推或改写历史。

## 3. PR 应包含什么

- 问题、范围和明确不在范围的内容；
- 代码 commit、配置和可复现命令；
- 数据/模型来源、版本、许可证和允许用途；
- smoke test / Completed / Needs verification / No-Go / Blocked 状态；
- 样本数、独立统计单元、指标定义、随机种子和置信区间；
- 已运行的测试和失败项；
- 对上游现有工作是否有覆盖、冲突或迁移成本。

PR 不应包含：

- `paper/` PDF、原始/处理数据、权重、完整日志、逐样本预测；
- 个人绝对路径、密钥、服务器信息；
- 旧工作区的代码、数据或未经本仓库独立验证的结论；
- 无关格式化、批量生成物或第三方完整工程。

## 4. 个人 fork 的长期维护

每次新任务从最新 `upstream/main` 建分支，可以避免个人 `main` 的历史分叉污染上游 PR。个人 `main` 是否合并、rebase 或重建，应在确认 `89e8ef0` 的用途和协作者依赖后单独决定；本轮不自动处理。

如果成果只适合个人研究而不适合上游，可继续保留在 fork 的主题分支，并用 release/README 指向可公开的聚合成果；本地数据和 PDF 仍不进入 Git。

## 5. 提交前核验

```powershell
git fetch upstream --prune
git rev-list --left-right --count upstream/main...HEAD
git diff --check
git diff --stat upstream/main...HEAD
git status --short
```

确认 PR 只包含允许公开、来源清楚且能由上游复核的成果。
