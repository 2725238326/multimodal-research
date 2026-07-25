# 当前工作

**更新时间：2026-07-23**

## 当前任务：审计 upstream 新变化并更新记录

- **目标**：读取已 fetch 的 `upstream/main` 新提交，记录 fork 与 upstream 的分叉状态、上游新增研究路线、关键聚合结果、No-Go 项和合并风险。
- **范围**：只读审计 `upstream/main` 的 README、报告、实验计划、配置、聚合结果和脚本清单；在本仓库文档中新增审计记录并同步状态/决策。
- **不在范围**：不合并 `upstream/main` 到当前 `main`；不删除本地治理文档；不运行上游训练或评估；不把上游结果直接升级为本 fork 的已复现实验结论。
- **证据**：`git rev-list --left-right --count upstream/main...main`、`git diff --stat main..upstream/main`、`upstream/main` 中的 `reports/2026-07-19_depth_physics_and_rgbd_route_summary.md`、`experiments/plans/2026-07-22_sgnet_rgbdd_x16_gate.md`、`results/quantitative/sgnet_rgbdd_x16_gate/` 聚合 JSON。
- **预期产出**：`docs/upstream-change-audit-2026-07-23.md`，并更新 `docs/worknow.md`、`docs/project-status.md`、`docs/project-plan.md`、`docs/decision-log.md`、`docs/fork-upstream-collaboration.md` 和 `docs/README.md`。
- **下一步**：完成审计后，决定是否从 `upstream/main` 新建迁移分支，逐项 cherry-pick SGNet 相关资产，而不是直接 merge。

### 本轮完成

- 已确认当前 `main` 对 `origin/main` 为 up to date，工作区干净；`upstream` 已 fetch，且 push URL 已设为 `no_push`。
- 已确认分叉状态为 `upstream/main` 独有 14 个提交、当前 `main` 独有 3 个提交；本地上游快照分支为 `sync/upstream-main-20260723`。
- 已读取上游新增 RGB-D-D/SGNet 路线报告、计划、配置、结果 README 和聚合 JSON；上游主线从单帧 RGB-D 物理关系 gate 转向 RGB 引导深度超分辨率。
- 已确认直接合并存在高风险：`upstream/main` 会删除本 fork 的 `AGENTS.md`、`rules.md`、`docs/` 多数治理文档、`material_response_probe_v0` 计划/脚本/测试和文献索引，同时新增 SGNet/RGB-D-D 代码与结果。
- 已新增 `docs/upstream-change-audit-2026-07-23.md`，并同步状态、计划、决策日志、fork 协作说明和文档索引。

### 当前判断与下一条可执行检查

- 不应直接 merge `upstream/main` 到当前 `main`；应先保留本 fork 治理文档，再在单独分支迁移 SGNet/RGB-D-D 资产。
- 上游 SGNet adaptive frequency gate 对 synthetic RGB-D-D 16x 协议是强候选，但 real RGB-D-D 4x direct transfer 和 real-domain calibration 均为 No-Go；不能把 synthetic 结论外推到真实传感器输入。
- **下一条检查**：新建 `sync/merge-upstream-sgnet-audit` 或 `research/sgnet-rgbdd-migration`，先只 cherry-pick 上游 SGNet 配置、脚本、计划和聚合摘要，再运行静态检查，不带入上游对治理文档的删除。

## 当前任务：部署 material response probe 阶段预备工作

- **目标**：将下一阶段主线 gate 落到可执行的研究与测试预备资产上，优先建立 `material_response_probe_v0` 的预注册计划、可移植配置、固定 smoke 清单和最小自动化校验。
- **范围**：只做计划、配置、清单生成/校验脚本、测试和文档状态更新；可使用现有 manifest/result 聚合信息生成小型脱敏 smoke manifest。
- **不在范围**：不训练模型；不运行大规模特征抽取；不下载新数据或权重；不删除或重写已跟踪研究资产；不提交或推送。
- **证据**：`docs/semantic-physical-route-audit.md`、`docs/research-design-patterns.md`、`docs/experiment-log-template.md`、现有 RGB/albedo/region alignment 聚合结果、现有 manifests 和配置中的路径问题。
- **预期产出**：`experiments/plans/material_response_probe_v0.md`、`configs/material_response_probe_v0.json`、smoke manifest 生成/校验工具、最小测试入口，以及更新后的状态/交接说明。
- **下一步**：读取现有脚本和 manifest schema，按最小风险方式实现离线可验证的预备资产。

### 本轮完成

- 已建立 `experiments/plans/material_response_probe_v0.md`，冻结研究问题、独立统计单元、scene split、条件、反事实控制、Go/No-Go 阈值和禁止训练边界。
- 已新增 `configs/material_response_probe_v0.json`，全部使用仓库相对路径；新增 `configs/material_response_probe_v0.local.example.json` 和 `.gitignore` 规则，防止本机覆盖配置进入 Git。
- 已新增 `scripts/prepare_material_response_probe.py`，可从现有 albedo manifest 生成相对路径 smoke manifest，并校验必需字段、路径、region/light 结构和源 manifest SHA-256。
- 已新增 `tests/test_prepare_material_response_probe.py`，使用 Python 标准库 unittest 覆盖路径归一化、目标材料抽样和文件存在检查。
- 已运行 `python -m unittest tests/test_prepare_material_response_probe.py`，3 项测试通过。
- 已运行 `python scripts/prepare_material_response_probe.py --config configs/material_response_probe_v0.json --check-files`，本地生成 18 样本、6 区域、6 场景、6 材料 smoke manifest；输出 SHA-256 为 `61e0b22a493c0c6b0475a49006ae998b3c523247368ece635d328548e4e7fffc`。生成 manifest 与结果摘要位于忽略目录，未进入 Git。

### 当前判断与下一条可执行检查

- `material_response_probe_v0` 已具备输入链路 smoke 基础，但还没有环境锁、模型 revision 和 frozen feature 代码，因此仍不能启动训练或声称机制有效。
- 本机旧 manifest 中存在非必需 `albedo_full_path` 文件缺失；probe 配置当前只要求 `rgb_crop_path` 和 `albedo_crop_path` 存在，后续若要使用 full-frame albedo 必须单独修复或重建。
- **下一条检查**：补 `scripts/extract_material_response_features.py` 的只读特征缓存接口和 `scripts/evaluate_material_response_probe.py` 的浅层头评估框架，先支持 dry-run/schema 验证，再接入实际 frozen encoder。

## 当前任务：文档复核、文献补充与推进建议

- **目标**：依据本仓库文档、聚合结果和本地文献库，给出后续研究推进建议；梳理 `paper/` 中可借鉴的方法，并补充下载若干官方来源论文，按“这些文献是什么作用和思路的提供”归类。
- **范围**：读取项目治理、状态、计划、决策、报告和文献索引；只从官方论文页面或原始 arXiv/CVF/ACL 等来源补充 PDF；记录文献用途、来源、下载位置和可用思路。
- **不在范围**：不运行新训练；不扩大数据集实验；不把未复现论文结论写成项目稳定事实；不提交或推送。
- **证据**：`AGENTS.md`、`rules.md`、`docs/`、`reports/material_constancy_region_alignment_v1.md`、聚合结果摘要、`literature/paper-index.md`、`paper/` 现有 PDF 及经核验的外部论文原始来源。
- **预期产出**：面向用户的最新推进意见；本地新增文献 PDF 与按作用分类的说明文件；必要时补充本地 SHA-256 校验记录。
- **下一步**：盘点现有 42 篇论文的方法作用，联网核验并下载补充文献，最后执行文档/下载资产的边界检查。

### 本轮完成

- 已按项目启动序列执行 `git pull --ff-only` 和 `git status --short`；读取 `AGENTS.md`、`rules.md`、`docs/worknow.md`、`docs/project-status.md` 以及计划、决策、审计、报告和文献索引。
- 已复核现有结果：RGB+albedo、intrinsic text 和共同区域标记仍保持 `No-Go`；当前最优先路线仍是不变身份—光照响应因子化 + 选择性特权蒸馏，且训练前必须先过 Phase 0/1 与 frozen-feature/oracle gate。
- 已从官方或原始来源补充下载 15 篇 PDF 到 `paper/这些文献是什么作用和思路的提供/`，分为材质数据、内禀/反射、多物理模态、结构语义桥接、主动测量、可靠性拒答和蒸馏基础。
- 已为新增目录写入本地 `README.md`，并同步 `literature/paper-index.md` 与 `literature/paper-sha256.txt`；本地文献库由 42 篇扩展到 57 篇。
- 已校验新增 PDF 文件头和页数，15/15 均为可解析 PDF；`paper/` 忽略规则确认命中，PDF 本体不会进入 Git。

### 当前判断与下一条可执行检查

- 当前不建议继续扩大冻结 VLM 的提示堆叠；应先完成可移植配置、环境锁定、数据许可/哈希和固定 smoke manifest。
- 文献能直接借的方法是：MINC/OpenSurfaces 的材质基准与标注框架、IIW/Intrinsic Diffusion/Fusion 的内禀证据、Multimodal Material Segmentation/Glass Polarization 的物理验证器、SAM-CLIP/CLIP-DINOiser 的结构—语义特征桥接、Calibration/SelectiveNet 的可靠性与拒答、KD/C2KD 的选择性蒸馏对照。
- **下一条检查**：建立 `experiments/plans/material_response_probe_v0.md`，冻结独立统计单元、scene split、oracle/frozen-feature 条件、错误/打乱/无关证据控制和 1–2 天 No-Go 阈值；未完成前不启动训练。

## 当前任务：完整解释本仓库的研究任务

- **目标**：依据仓库代码、配置、manifest、聚合结果和治理文档，形成一份对新协作者也易懂、同时可审计的项目任务技术报告。
- **范围**：解释研究问题、数据与样本、模型与干预、指标、已有结果、负结果、候选创新、工程状态、协作边界和下一步；区分主线材质恒常性与待核验 NYUv2 支撑资产。
- **不在范围**：不运行新训练；不把候选方向写成已验证结论；不导入旧工作区事实；不提交或推送。
- **证据**：`README.md`、`rules.md`、`docs/`、四个实验配置、核心脚本、固定 manifests、聚合结果和现有报告。
- **预期产出**：`reports/project-task-guide/artifact.json` 与经验证的自包含 `reports/project-task-guide/report.html`，并在本轮交接中给出结论摘要。
- **下一步**：从报告建议中建立 Phase 1 复现任务；优先修复可移植路径、环境锁定、provenance 和最小 smoke test。

### 本轮完成

- 已核对 README、项目规则、状态、计划、决策、四个配置、核心数据/推理/统计脚本、固定 manifests、两模型聚合结果、干预比较和 NYUv2 人工审核资产。
- 已生成 `reports/project-task-guide/artifact.json` 与自包含 `reports/project-task-guide/report.html`，完整解释任务边界、数据链路、指标、已有结论、No-Go、候选创新、工程阻塞和完成标准。
- 报告 artifact 规范校验与离线打包通过，共 15 个正文区块和 1 张来源可追溯图；最终 HTML 约 395 KiB。
- 实际 Chromium 渲染检查确认首页层级、中文和正文正常；严格自动 QA 检出阅读器顶部栏在长页面上约 8 px 的横向溢出，因此最终收据为 `structural_only`，未宣称完整浏览器验证通过。
- 生成 HTML、QA 失败截图和调试图已纳入忽略边界；未运行训练、未修改实验结果、未提交或推送。

### 当前判断与下一条可执行检查

- 仓库主任务是跨光照材质恒常性及语义—物理证据分工；NYUv2 支撑关系仍是未闭环的邻接候选，不是当前等成熟主线。
- 已有负结果足以停止冻结 VLM 的 albedo/文本/区域框提示堆叠，但不足以否定经过专门训练的物理辅助模态。
- **下一条检查**：建立一个固定的极小 smoke manifest 和环境文件，修复配置绝对路径后复跑 RGB 数据读取、标签解析与区域级统计，不启动新模型训练。

## 上一任务：科研设计模式库与语义—物理研究路线审计

- **目标**：建立可复用的科研设计模式、创新组合规范和多方向任务组合门禁；重新评估“多模态大模型语义帮助物理特征识别”的适用边界，并形成与本项目证据相符的新路线候选。
- **范围**：模式定义、反模式、最小验证单元、方向组合规则、结论级查新和候选研究路线；只使用本仓库证据与经原始来源核验的论文。
- **不在范围**：不启动新训练；不把候选路线写成已验证结论；不导入旧工作区内容；不提交或推送。
- **证据**：本仓库 RGB、albedo、共同区域标记与跨光照翻转结果；2024–2026 年官方论文原文；现有项目治理文档和实验模板。
- **预期产出**：科研设计模式库、方向组合/淘汰矩阵、语义—物理路线判断、强化后的实验模板与项目规则、扩充的文献索引。
- **下一步**：按主线候选写一页预注册计划，先做不训练的 illumination-pair oracle 与 frozen-feature probe；在 Phase 0/1 治理门禁通过前不启动训练。

### 本轮完成

- 已建立 `docs/research-design-patterns.md`：12 个模式、跨领域机制迁移卡、探索/确认分轨及“一主线、两邻接、一高风险”组合上限。
- 已建立 `docs/semantic-physical-route-audit.md`：将“语义直接替代物理”与冻结特征简单拼接判为 `No-Go`，将语义提案—物理验证、物理结构—稀疏语义解释和选择性特权蒸馏列为受控候选。
- 已强化 `rules.md` 与 `docs/experiment-log-template.md`：新实验必须声明模态角色、语义权限、物理否决、四件套反事实控制、等计算基线和部署输入。
- 已完成 2024–2026 相邻工作碰撞检查；新增 11 篇官方来源论文，本地文献库现为 42 篇、共 1,012 页；PDF 文件头、页数解析、索引覆盖和 SHA-256 交叉检查均为 0 错误。
- 已同步 `docs/project-plan.md`、`docs/project-status.md`、`docs/decision-log.md` 和文档索引；未运行训练、未导入旧工作区内容、未提交或推送。

### 当前判断与下一条可执行检查

- “语义帮助物理”不是整体错误；失败点是让类别共现取代测量，或不经角色分工与冲突控制直接融合。语义适合提案、路由和解释，几何/反射/跨光照响应/其他传感器应负责验证、校准和否决。
- 主线候选为“不变身份—光照响应因子化 + 选择性特权蒸馏”；邻接 gate 为“语义提案—光学验证”和“结构引导物理关系 agent”；主动反事实照明 agent 仅保留为高风险探索。
- **下一条检查**：在 `docs/experiment-log-template.md` 上冻结主线的独立统计单元、illumination-pair split、oracle 上限、四件套控制和 1–2 天 No-Go 阈值；未完成前不训练融合模型。

## 上一任务：研究范式迁移审计、文献基线与 fork 协作路径

- **目标**：评估旧工作区中可复用的研究流程与验证策略，为本仓库建立 agent、多模态、视觉机制及相关开源模型的论文基线，并明确向上游贡献成果的协作方式。
- **范围**：旧工作区仅作为流程范式样本；项目事实、研究方向、证据和结论仍只来自本仓库及经原始来源核验的论文。论文 PDF 下载到本地 `paper/`，Git 只记录文献索引、来源、版本、许可与允许用途。
- **不在范围**：不导入旧工作区的研究结论、状态、数据、代码或路线；不运行新实验；不清理或改写已有 Git 历史；不提交或推送。
- **证据**：本仓库治理文档、代码与结果摘要；旧工作区的协作流程、实验模板和查新审计结构；论文原文、官方项目页/模型报告及上游 Git 关系。
- **预期产出**：研究范式迁移审计、经核验的文献索引与本地 PDF 集、fork/upstream 协作说明、更新后的项目状态与决策记录。
- **下一步**：完成外部原始来源核验，下载并校验 PDF，随后执行文档一致性与 Git 边界检查。

### 本轮完成

- 已完成 `docs/research-paradigm-transfer-audit.md`：流程迁移为 `Go`，旧工作区研究内容迁移为 `No-Go`，新训练仍受 Phase 0/1 门禁阻塞。
- 已从 arXiv/CVF 官方来源下载 31 篇论文到本地 `paper/`，共约 297.76 MiB、851 页；PDF 解析、文件头和 SHA-256 均通过。
- 已建立 `literature/paper-index.md` 与 `literature/paper-sha256.txt`，覆盖项目直接相关、agent、多模态工具使用、视觉连接机制及 Gemma/Qwen/InternVL 等模型。
- 已将 `paper/` 加入 `.gitignore` 并验证命中，PDF 不进入 Git 或上游 PR。
- 已建立 `docs/fork-upstream-collaboration.md`：确认 `origin` 为个人 fork、`upstream` 为原仓库，并记录聚焦 PR 流程。

### 当前判断与下一条可执行检查

- 可迁移的是查新、oracle/frozen-feature gate、反证控制、独立单元统计、停损条件和交接流程；不可迁移旧工作区的研究事实、路线、数据、代码和结论。
- agent 只在任务确实需要工具组合、状态管理或失败恢复时进入候选；必须与固定流水线、规则程序和单模型比较。
- 本地远端引用显示 fork 与 upstream 的 `main` 各有 1 个独有提交；本轮 `git fetch upstream --prune` 遇到网络连接重置。
- **下一条检查**：网络稳定后重新执行 `git fetch upstream --prune` 与 `git rev-list --left-right --count upstream/main...main`。若准备向原仓库贡献，从最新 `upstream/main` 新建主题分支，不直接改写当前个人 `main`。

## 上一任务：建立目标仓库自己的研究治理基线

- **目标**：为本仓库建立可执行的项目管理、实验门禁、证据状态和 Git 边界。
- **范围**：只依据本仓库现有材质恒常性实验、NYUv2 支撑审核资产、代码、配置和结果。
- **不在范围**：不导入其他仓库的研究结论或路线；不删除已跟踪资产；不改写 Git 历史；不提交或推送。
- **证据**：当前 `HEAD=62100d7`；1,237 个跟踪文件；现有配置、脚本、结果摘要和 `reports/material_constancy_region_alignment_v1.md`。
- **预期产出**：规则、文档索引、当前状态、路线图、实验模板、决策日志、`.gitignore` 和仓库卫生审计。

## 完成情况

- 已在 `codex/project-governance` 分支建立完整治理文档和新增资产边界。
- 已核对所有状态描述只来自本仓库；跨项目研究内容扫描无命中。
- `git diff --check` 通过，UTF-8 替换字符扫描通过。
- `.gitignore` 已验证覆盖数据、权重、日志、manifest、逐样本结果、生成报告和缓存。
- 新规则命中 1,208 个已经跟踪的文件；它们没有被删除或取消跟踪。

## 当前判断

- 材质恒常性实验已有较完整的运行证据，但缺少统一的实验计划、环境锁定、数据许可记录和可移植配置。
- RGB+albedo 与共同区域标记没有形成跨模型稳定收益，当前应保持 `No-Go`，不继续扩大同类零训练提示实验。
- NYUv2 支撑审核包含 167 张候选图和 14 条人工标签，但本仓库缺少生成脚本、配置和完整来源记录，状态为 `Needs verification`。
- 仓库声明与 Git 事实不一致：数据、结果、缓存和生成报告已被初始提交跟踪；本轮只防止新增，不执行清理。

## 下一条可执行检查

确认初始提交是否已被其他协作者使用，并完成 `docs/repository-hygiene-audit.md` 中的资产分类复核，决定采用：

1. 保留历史、从下一提交停止跟踪生成物；或
2. 在所有协作者同意后重写尚未共享的历史。

在该决策前，不运行新实验，不扩大数据下载。

## 阻塞项

- 尚未确认初始提交是否已被其他协作者基于或拉取。
- 数据集和生成图片的再分发许可尚未形成清单。
- 缺少统一环境文件与自动化测试。
