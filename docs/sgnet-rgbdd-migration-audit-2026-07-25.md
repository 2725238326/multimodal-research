# SGNet/RGB-D-D selective migration audit: 2026-07-25

**状态：Smoke test（静态迁移完成）；上游实验结果仍为 Needs verification**

## 1. Source and branch boundary

- Source: `upstream/main=0a95b3d55f5f745f434629da93da2389e98f2549`，共 14 个 SGNet/RGB-D-D 提交。
- Target base: `main=42b1ac9b346940f096f7e4fef2ec5607eaee26f6`。
- Working branch: `research/sgnet-rgbdd-migration`。
- 本轮没有 merge `upstream/main`，没有提交或推送；迁移内容留在暂存区供审查。
- 本 fork 的 `AGENTS.md`、`rules.md`、`docs/` 治理文档、`platform/`、文献索引和 `material_response_probe_v0` 均保留。

## 2. Migrated assets

迁移后共 50 个文件级变化，其中 22 个 Python 脚本、4 个 shell 驱动脚本、5 个配置、1 个实验计划、1 个路线报告、13 个聚合结果 JSON、结果说明和文档更新。未迁入数据、权重、checkpoint、逐样本 JSONL、完整日志或生成图片。

上游聚合结论的解释边界保持不变：synthetic RGB-D-D 16x adaptive frequency gate 是上游确认性候选；real RGB-D-D 4x direct transfer、real-domain calibration、soft/ramp/relative routing 和 branch-router pilot 保持 No-Go。它们尚未在本 fork 独立复现。

## 3. Static verification

- 18 个新增 JSON 均可由 PowerShell `ConvertFrom-Json` 解析。
- 22 个新增 Python 文件均通过 AST 解析；逐个 CLI `--help` 检查中，21 个原样通过，router 分析脚本经惰性导入修复后通过。
- 4 个 shell 脚本经 LF 规范化后全部通过 `bash -n`；新增 `.gitattributes` 规则 `*.sh text eol=lf`。
- `python -m unittest discover -s tests -v`：3/3 通过。
- `python -m unittest discover -s platform/tests -v`：14/14 通过。
- 敏感路径/凭据模式扫描无命中；新增文件中没有 checkpoint、日志、逐样本输出或超过 1 MiB 的文件。

## 4. Local environment finding

当前本机可导入 `numpy 2.4.3`、`torch 2.12.0+cpu`、`Pillow 12.1.1`、`scipy 1.18.0` 和 `matplotlib 3.10.8`；`scikit-learn` 未安装，且没有 CUDA PyTorch。该环境只支持静态检查，不支持复现上游 GPU 训练/评估。router 分析脚本仍需在正式环境中安装并锁定 `scikit-learn`。

## 5. Remaining blockers

1. 官方来源与当前仓库 revision 已登记在 `docs/sgnet-rgbdd-provenance.md`，但 upstream 实际运行所用的 SGNet/C2PD commit 仍未知；RGB-D-D 授权登记、NYU v2 明确许可和数据哈希尚未闭合。
2. SGNet/C2PD 第三方工程与 checkpoint 均未迁入；脚本通过 `--sgnet-dir`、`--c2pd-dir` 和 checkpoint 参数引用本地外部资产。
3. 尚无锁文件或容器定义；当前包版本不能视为复现实验环境。
4. 未运行数据读取、模型加载、单样本 smoke 或聚合重算，因此上游结果只能标为 `Needs verification`。
5. 上游计划记录了首个 shift gate，但后续训练/路由分支的预注册字段没有全部按本 fork 模板闭合；在补齐前不运行训练。

## 6. Next executable check

先向 upstream 执行者核对实际 SGNet/C2PD commit、checkpoint 下载来源、RGB-D-D 授权登记和 NYU v2 许可/split；同时建立可移植环境描述。完成后增加不依赖真实数据和权重的张量形状/路由单元测试；只有这些检查通过，才允许在具备 GPU 的隔离环境执行 `--max-samples 1`。
