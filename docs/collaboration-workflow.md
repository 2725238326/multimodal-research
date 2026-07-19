# 协作流程

## 1. 开始任务

```powershell
git pull --ff-only
git status --short
```

阅读 `AGENTS.md`、`rules.md`、`docs/worknow.md` 和 `docs/project-status.md`。在 `docs/worknow.md` 登记目标、范围、证据、产出和阻塞。

## 2. 分支

- 一个可审查目标对应一个短期分支。
- 分支名使用 `codex/<topic>`、`research/<topic>`、`fix/<topic>` 或团队约定前缀。
- 不在功能分支混入数据、输出、批量格式化或无关重构。

## 3. 研究提案

在 `experiments/plans/<experiment-id>.md` 复制实验模板。计划通过前，只允许只读审计和极小的接口 smoke test。

## 4. 运行

- 配置进入 `configs/`，共享版本不得包含机器绝对路径或密钥。
- 本地覆盖、manifest、日志、逐样本预测、数据和权重不进入 Git。
- 每次运行记录代码 commit、配置 hash、manifest hash、模型 revision、环境、命令、设备和退出状态。

## 5. 结果审查

- 先验证样本数、独立单元数、解析失败和数据泄漏。
- 报告主指标、保护指标、置信区间和资源消耗。
- 将结论标为 `Completed`、`Needs verification`、`No-Go` 或 `Blocked`。
- 只提交聚合且脱敏的结果摘要。

## 6. 合并前

```powershell
git diff --check
git diff --stat
git status --short
```

确认没有数据、权重、缓存、逐样本输出、Office 临时文件、个人路径或密钥。更新工作状态、计划和决策记录。

