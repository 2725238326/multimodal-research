# Agent Continuation Guide

## Mission

维护本项目的多模态研究代码、实验协议、证据记录和阶段决策。项目事实只来自本仓库的代码、配置、实验记录、结果摘要和经核验的外部来源。

## Required start sequence

1. 执行 `git pull --ff-only` 和 `git status --short`。
2. 阅读 `rules.md`、`docs/worknow.md`、`docs/project-status.md` 和本文件。
3. 保留已有改动；不得重置、覆盖或批量删除研究资产。
4. 开始非只读工作前，在 `docs/worknow.md` 记录目标、证据、预期产出和下一步。

## Working conventions

- 研究问题、数据、模型、指标和停止条件必须在运行前写入实验计划。
- 结果必须区分 `Smoke test`、`Completed`、`Needs verification`、`No-Go` 和 `Blocked`。
- 数据、权重、逐样本预测、完整日志、缓存和生成报告默认不进入 Git。
- 可提交内容限于自有代码、可移植配置、实验计划、聚合结果摘要、文献索引和项目管理文档。
- 配置不得写入密钥；共享配置避免机器绝对路径，使用相对路径、环境变量或本地覆盖文件。
- 第三方数据、模型和代码必须记录来源、版本、许可证及允许用途。

## Handoff checklist

1. 更新 `docs/worknow.md` 的完成项、阻塞项和下一条可执行检查。
2. 状态变化同步到 `docs/project-status.md`；方向或门槛变化同步到 `docs/project-plan.md` 和 `docs/decision-log.md`。
3. 执行与改动对应的测试或数据检查。
4. 检查 `git diff --check`、`git diff --stat` 和 `git status --short`。
5. 确认没有数据、权重、逐样本输出、缓存、临时文件、敏感路径或密钥进入提交。

