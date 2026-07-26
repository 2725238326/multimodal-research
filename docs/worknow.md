# 当前工作

**更新时间：2026-07-26**

## 当前任务：标定 HDR + light-probe 候选审计（不训练）

- **状态**：`Completed training-free audit gate`；light-probe normalization 判为 `No-Go`，calibrated HDR 判为 `Partially supported`，回退分支生效。
- **目标**：判定“标定 HDR + light-probe normalization”这一优先候选是否具备新的可观测测量资源；若具备，闭合来源/许可/体积/本地可读性，并冻结机制迁移卡与预注册计划；若不具备，按既定规则转向 SGNet/RGB-D-D provenance。
- **范围**：官方 URL 元数据核验；已下载 test archive 的条目结构清点；单场景 EXR/probe 的最小下载与弧度尺度一致性 smoke；审计文档、机制迁移卡、预注册计划与可移植配置。
- **不在范围**：不训练任何模型；不做完整特征抽取或 gate 运行；不在服务器执行下载；不改动既有 staged 研究资产；不提交或推送。
- **证据（本轮已核验）**：
  - 已下载并 CRC 通过的官方 test archive 内含 **每场景 25 个 chrome256 与 25 个 gray256 光探针 JPG**（750 + 750），即 LDR 光探针已在本地，从未被任何已关闭路线使用。
  - 官方 SDK `a85aa925` 的 `query_images(hdr=True)` / `query_probes(hdr=True)` 走 `*_mip{m}_exr.zip` 与 `*_probes_256px_exr.zip`，即官方发布线性 HDR。
  - HTTP HEAD 实测：`multi_illumination_test_mip2_exr.zip` = 1,648,079,881 B；dev 场景 mip2 EXR 约 53.6–72.2 MB/场景；HDR probes 约 3.86–4.68 MB/场景。三个 dev 场景与 test 场景均返回 200。
  - 本地 `E:` 剩余 1.5 TB；本机 `cv2 4.13.0` 可在 `OPENCV_IO_ENABLE_OPENEXR=1` 下读 EXR，无需新增依赖。
- **判定规则**：测量资源存在，因此“若无新测量资源”分支不成立，本轮继续检验机制本身而不是直接回退。
- **多重比较边界**：官方 30 个 `everett` test scenes 已在 `material_photometric_external_confirmation_v0` 用过一次；本审计未消耗该 split，保留为将来最终一次性确认。
- **完整记录**：`docs/hdr-light-probe-candidate-audit-2026-07-26.md`、`results/quantitative/hdr_light_probe_oracle_audit_v0/`。

### 本轮完成

- 已闭合测量资源可得性：单场景 `{scene}_mip2_exr.zip` 自足包含 25 张场景 EXR、25 张 chrome EXR、25 张 gray EXR、`materials_mip2.png` 与 `meta.json`，无需单独下 probes 包；dev 场景 49.7–81.5 MB/场景，官方 test bulk EXR 为 1,648,079,881 B。
- 已新增 `scripts/fetch_ranged_asset.py`：单流仅 33 KB/s，16 路 HTTP range 并行后达到 8.1–9.7 MB/s，并强制输出 SHA-256 与 ETag/Last-Modified 侧车；6 个场景 EXR + 6 个场景 JPG 全部 ZIP CRC 通过。
- 已新增 `scripts/audit_hdr_probe_radiometry.py` 与 `scripts/summarize_hdr_probe_audit.py`，在 6 场景 × 25 光照 × 90 个官方 mask 区域上完成**零训练参数**的 oracle 检验。
- **light-probe normalization 判为 `No-Go`**：gray probe 跨光照动态范围中位 1.72 倍，而它要归一化的场景亮度中位 17.35 倍；中位相关系数 -0.019（6 场景中 3 个为负）；归一化后 within-region 跨光照方差中位不降反升 2.5%，判别力中位增益 0.977，仅 1/6 场景增益超过 10%。物理原因是 gray ball 处的辐照度对闪光方向近似不变，不携带逐表面辐照度信息。
- **calibrated HDR 判为 `Partially supported`**：以 JPEG 最后未截断码值定位 clip point（实测均值 1.14），逐像素实测每场景平均截断比例中位 5.8%、跨场景 2.2%–45.0%、最差单方向 69.4%，线性数据在 clip point 之上延伸中位 35 倍。信号真实但幅度不足以解释官方 test split 上的 -12.50 pp，且属同一观测量去截断而非新观测量。
- 已确认 polarization 与几何 verifier 在本数据集不可得：Multi-Illumination 无偏振通道，也无深度/法向真值。
- 新增 12 项单测全部通过；聚合摘要 SHA-256 `14332b9f18fc6b251fefa13851b74a614e79113593a5d6ad65fd36fe53c1093c`；所有下载与派生资产留在忽略目录，服务器未执行任何下载。

### 当前判断与下一条可执行检查

- 优先候选在其审计门禁处关闭，且失败原因是可解释的测量学事实而非调参不足；不进入描述符设计、不训练、不上传服务器。
- 次优先候选（polarization/flash、几何 verifier）在当前数据集不可得，因此**回退分支正式生效**。
- **下一条检查**：转向 SGNet/RGB-D-D，按 `docs/sgnet-rgbdd-provenance.md` 的 execution gate 逐项闭合——upstream 实际 SGNet/C2PD commit、checkpoint 官方 URL/许可/SHA-256、RGB-D-D Release Agreement 与 split 哈希、NYU v2 许可与 split、锁定环境；全部闭合前只做 provenance 与单样本 smoke，不训练，不把上游聚合结果称为本 fork 复现。

## 当前可执行入口：下一主线候选审计

- **状态**：`Superseded`，已由上述审计解决；保留原始边界供追溯。
- **已关闭边界**：五光照 LDR crop 的直接分类、拒判、像素光度轨迹及 conflict verifier 全部为 `No-Go`；不得在当前 30 development + 30 official test scenes 上继续优化同类 descriptor、crop、阈值、LoRA、BRDF deep head 或蒸馏。
- **仅允许的候选**：改变可观测证据的最小 oracle，例如标定 HDR + light-probe normalization、polarization/flash，或由深度/几何程序执行可证伪 verifier。
- **若无新测量资源**：转向已迁移 SGNet/RGB-D-D 资产的 provenance、数据许可、checkpoint/hash 和单样本 smoke；不把上游聚合结果写为本 fork 复现。
- **开始前要求**：填写机制迁移卡和实验计划，声明模态角色、独立单元、强基线、四件套控制、Go/No-Go、来源/许可/哈希以及资源上限。
- **权威证据**：`reports/material_photometric_trajectory_external_confirmation_v0.md`、`results/quantitative/material_photometric_external_confirmation_v0/summary.json`、`docs/multi-illumination-provenance.md`。

## 已完成任务：曝光审查的像素光度轨迹 oracle gate

- **实验 ID**：`material_photometric_trajectory_gate_v0`；状态 `Completed exploratory gate; No-Go`。
- **目标**：检验直接从多光照 RGB 像素测得的亮度、色度、高光、饱和和纹理响应轨迹，是否包含 frozen semantic embedding 未捕获的材料辨识信息。
- **新证据**：330 张 96x96 RGB crop 中，46 张有超过 20% 像素达到近白饱和；66 个区域虽各有 5 个光照，但按 20% 饱和阈值只有 32 个区域保留 5 个可靠曝光，另有 2 个区域仅保留 1–2 个。旧 embedding response 很可能混合了材质响应与曝光失真。
- **方法**：从像素提取稳健亮度分位数、RGB 色度、绝对/相对高光、裁剪比例、梯度与纹理能量；在 region 内形成曝光审查、未审查和 exposure-only 轨迹统计；用 scene-disjoint shallow oracle 比较 SigLIP region mean、物理轨迹、二者融合和 shuffled trajectory。
- **模式与角色**：采用 RP-01、RP-02、RP-03、RP-04、RP-05、RP-08、RP-12；RGB pixel photometry 为 `Measurement`，SigLIP embedding 为语义视觉基线，不使用 VLM 生成标签。反模式是继续对失败的 embedding response 调阈值，或把饱和伪影直接当材料真值。
- **范围边界**：只用服务器已有 crop 和 feature cache；不下载新模型/数据，不训练深网，不修改标签，不公开逐样本结果；运行后已核验官方 CC BY 4.0 来源，见 `docs/multi-illumination-provenance.md`。
- **主指标**：region accuracy 与 macro class accuracy；以 scene 为 bootstrap 单元，三 seed、10,000 draws。主候选为 SigLIP region mean + censor-aware photometric trajectory，强基线为 SigLIP region mean。
- **Go 条件**：三 seed 的候选相对基线 region-accuracy 增量均至少 +3 pp 且 95% CI 下界大于 0；平均 macro accuracy 不下降；候选至少领先 shuffled trajectory 3 pp；exposure-only 不得解释同等收益。
- **停止条件**：路径/像素/分组 smoke 失败，可靠曝光不足导致描述符不可定义，任一主 CI 不排除 0，或 shuffled/exposure controls 解释收益，则标记 `No-Go`，不进入学习式 BRDF、LoRA 或蒸馏。
- **结果**：虽有 development directionality，但预注册 CI 未通过，且官方外部确认显著反转；该机制关闭。

### 阶段结果

- `material_photometric_trajectory_gate_v0` 已完成 66 region、30 scene、三 seed 的 exploratory full gate。Primary 相对 SigLIP region-mean 每 seed 提升 4.55–6.06 pp，平均达到 68.69%；censor-aware 比 uncensored 平均高 1.01 pp，exposure-only 接近基线，shuffled trajectory 明显更差。
- 严格 Go 门槛未通过：三个 scene-bootstrap CI 下界为 0、0 和 -1.67 pp，因此当前状态仍为 `No-Go`，不在同一 30-scene 数据上继续训练 verifier。
- 与旧 sample-majority RGB 逐 region 配对后，新分支平均略低，但二者 oracle 三次均为 77.27%，存在 4–7 个纠错与 5–6 个破坏，支持“独立数据上的冲突验证器”新假设。

## 已完成任务：官方独立 test split 光度轨迹确认

- **实验 ID**：`material_photometric_external_confirmation_v0`；状态 `Completed confirmatory stress test; No-Go`。
- **来源与许可**：官方项目页 `https://projects.csail.mit.edu/illumination/` 明确数据为 CC BY 4.0；SDK `lmurmann/multi_illumination` 固定 commit `a85aa9253065ff836ea97ba1a04b14259a06b3e0`、代码 MIT。官方 test JPG ZIP 已在本地下载并通过全 ZIP CRC，SHA-256 为 `7a142f0f4dcf8c6b038f91a32eee5962a12aa68e5c4ee43adf0d3059ea0f0ce0`。
- **独立性**：SDK 定义 30 个 `everett*` 场景为 test；当前开发用 30 场景全部属于 985-scene train pool，与 test overlap 为 0。
- **固定数据协议**：官方 mip2 图与 mask 下采样到 mip4；使用 64x64 crop、纯度至少 0.82、component area 至少 1024、每 scene/class 最多 2 region、最多 80 region、每 region 选择 5 个外观差异最大的光照。64x64 是尺度域移 stress test；选择依据是严格 96x96 仅产生 35 region，而 64x64 在未看模型结果时可覆盖 80 region/30 scenes。
- **强基线**：用开发集 330 sample 训练 SigLIP sample head，在外部 test 的每个 region 做五光照 majority；另报 SigLIP region-mean。Primary 为 SigLIP region mean + censor-aware pixel trajectory。
- **Go 条件**：三 seed 下 primary 必须同时比 sample-majority RGB 和 region-mean RGB 至少高 3 pp且 scene-bootstrap CI 下界大于 0；宏准确率不下降；exposure-only 与 independently shuffled trajectory 均不能解释收益。
- **停止条件**：外部 mask/crop/标签协议不闭合、有效类别少于 8、region 少于 60，或任一 Go 条件失败，则不训练 conflict verifier、深层 BRDF、LoRA 或蒸馏。
- **结果**：Primary 在官方 test 上显著低于强 RGB baseline；不训练 conflict verifier、deep BRDF、LoRA 或蒸馏。

### 本轮完成

- 已本地下载官方 test JPG archive，按 16 个 byte ranges 合并为 214,841,949 bytes，SHA-256 `7a142f0f4dcf8c6b038f91a32eee5962a12aa68e5c4ee43adf0d3059ea0f0ce0`；2,400 entries 全 ZIP CRC 通过。官方页面明确 CC BY 4.0，SDK commit 与 train/test 规则已固定。
- 已在看模型结果前完成 crop feasibility：严格 96x96 仅 35 regions；预注册 64x64 scale stress protocol 后，本地构建 80 regions、30 scenes、400 crops、10 classes，400/400 解码与尺寸检查通过，manifest SHA-256 `871a577e29f2463385efa05ff1a1473ad9c5ea94a5fc4b2620108d7e70d9f6ed`。
- 412 文件 confirmation bundle 在本地生成哈希清单并压缩上传，远端逐文件验证 0 mismatch；服务器未下载任何外部资产。
- 远端 SigLIP2 提取 400 samples 成功，test feature cache SHA-256 `be70519f7735dc3f85a627baa107a3a7f7f260b8f9fdf1a44db1de3a6f94ce14`；photometric descriptor SHA-256 `7ee8638b111424af83a14d78823094a42e0967db15207330826f66a9eaec0763`。
- External full gate 三 seed 完成：strong RGB 43.33%，primary 30.83%，平均 -12.50 pp；三 seed 差值 CI 分别为 `[-21.89, -3.83]`、`[-24.11, -5.67]`、`[-24.94, -6.06]` pp，均显著有害。完整摘要 SHA-256 `3ff457fdcdbdbcb3d609182540d0cc32b5ab065162a3a9d2cda08e3e395e224c`。
- 已完成最终验证：项目测试 30/30、平台测试 14/14、59 个 JSON 解析、新增 Python 编译/CLI、`git diff --check`、逐文件 trailing-whitespace 与敏感路径扫描均通过；测试产生的已跟踪 pyc 变化已单文件恢复，未改动其他工作资产。

### 当前判断与下一条可执行检查

- `material_photometric_external_confirmation_v0` 为明确 `No-Go`。Development gain 属于不可迁移的 scene/scale appearance statistics；不训练 verifier、deep BRDF、LoRA 或 privileged student。
- 当前五光照 LDR response 家族已经完成三类反证：直接分类、选择性拒判、像素物理轨迹/外部确认均失败。继续在同一观测上换 head 或阈值属于反模式。
- **下一条检查**：从候选池重新选择改变可观测性的路线。优先级为标定 HDR + light-probe normalization 的最小 oracle，其次是 polarization/flash verifier；若资源不允许获取标定测量，则转向已有 SGNet/RGB-D-D 迁移的 provenance/单样本复现，而不是继续材质 response 调参。

## 当前任务：material response 选择性拒判探索 gate

- **目标**：检验已观察到的跨光照响应不一致是否能作为 RGB 材质分类器的错误检测与选择性拒判信号，而不改变 RGB 分类预测。
- **证据**：`material_response_probe_v0` 中 pairwise response 将区域 flip rate 降低 31.31 pp，但区域准确率降低 5.05 pp；远端缓存保留 330 个样本、66 个区域、30 个场景的 SigLIP2 frozen features，足以离线重建 RGB 概率与响应离散度。
- **范围**：新建独立探索实验 `material_response_selective_gate_v0`；使用 outer/inner scene-grouped 嵌套评估；比较 RGB confidence only、RGB confidence + response router、shuffled response、random score 和等覆盖随机拒判；报告固定 80%/90% coverage、risk-coverage AUC、错误检测 AUROC/AUPRC、宏选择性准确率和 scene bootstrap CI。
- **不在范围**：不修改 RGB 分类器的最终预测；不继续直接特征拼接、LoRA 或全模型训练；不将同一数据生成并检验的结果称为确认性证据；不公开或再分发许可未闭合的数据和逐样本输出。
- **模式与角色**：采用 RP-01、RP-03、RP-05、RP-09、RP-12；RGB 为 `Measurement`，跨光照响应仅为 `Router`，标签只作监督与离线评估；反模式为用响应分支替代 RGB 决策或在测试标签上调阈值。
- **预期产出**：可移植配置、预注册计划、nested selective-risk 评估脚本与测试、远端 smoke/full 聚合摘要、严肃学术风格图表、状态和决策记录。
- **Go 条件**：在 80% 与 90% 固定覆盖率下，response router 相对 RGB-confidence-only 的 scene-bootstrap 选择性准确率差值均为正且 95% CI 下界大于 0；risk-coverage AUC 更低；shuffled/random 对照不能解释收益；宏选择性准确率不下降超过 1 pp。
- **停止条件**：smoke 的分组、概率、接受掩码或指标链失败即停止；任一固定覆盖率主 CI 不排除 0、risk-coverage AUC 不改善、控制条件出现同等收益，或资源/许可边界失守则标记 `No-Go` 或 `Blocked`，不进入训练扩展。
- **下一步**：冻结独立计划和配置，随后实现 region-level nested OOF 路由、负对照与单元测试；smoke 通过后才运行完整探索 gate。

### 本轮完成

- 已冻结独立实验计划和可移植配置；实现 outer-5/inner-4 scene-grouped RGB OOF、region-level error router、80%/90% 精确覆盖率、inner-quantile 阈值、AURC、AUROC/AUPRC、scene bootstrap 和三类控制。
- 本地 14 项相关单测、远端 7 项新单测、真实缓存 dry-run 和一 seed/200-bootstrap 计算 smoke 均通过；4 个上传文件的远端 SHA-256 全部一致，服务器未执行下载。
- 已在远端 `summer` 环境完成 3 seeds、每比较 10,000 次 scene bootstrap 的 full gate；运行 27.37 秒、峰值 RSS 163,736 KiB，完整聚合摘要 SHA-256 为 `2d2fd696652d3ea15b215350068a95b8b2e3b4d2d8b38b0f6e0cf411dd1cc557`。
- 已回传聚合结果并生成 PNG/PDF 科研图；逐 region 预测和错误分数仍留在远端/忽略目录，没有进入 Git。
- 已完成全量验证：项目单测 17/17、平台单测 14/14、55 个 JSON 解析、Python 编译/CLI、`git diff --check` 均通过；Git 仅放行实验目录中的 `README.md` 和 `summary.json` 聚合资产。

### 当前判断与下一条可执行检查

- `material_response_selective_gate_v0` 为 `No-Go`：80% 覆盖率下 response router 平均仅提高 1.26 pp，三个 seed 的 CI 下界均不大于 0；90% 覆盖率下三 seed 的准确率增量均为 0。
- Response router 的平均错误检测 AUROC/AUPRC 低于 RGB confidence；AURC 只在一个 seed 改善，且 shuffled response 对照无法排除。
- 不继续该 frozen response summary 的阈值调优、LoRA、选择性蒸馏或全模型训练。**下一条检查**：关闭当前响应路线；先解决数据许可，随后从候选池选择具有新物理测量或独立数据的机制，重新做 provenance、碰撞审计和 oracle gate。

## 当前任务：部署并执行 material response frozen-feature gate

- **目标**：在本地准备所有需联网获取的代码、模型与依赖资产，经哈希校验后上传到 `kykt`；创建 Conda 环境 `summer`，执行预注册的 material response smoke、受控浅层训练与评估，回传聚合结果并形成科研图表和结论。
- **范围**：盘点远端已有 GPU/Conda/数据/权重；联网核验同量级最新视觉编码器；补齐实验计划、特征抽取、浅层头评估和控制条件；创建 Git 忽略的本地传输暂存区；本地下载后上传；远端只使用已上传资产安装/运行；回传脱敏聚合结果和图表。
- **不在范围**：不在服务器运行下载命令；不上传密钥、原始 Git 历史或无关本地文件；不把 smoke/单 seed 结果写成稳定结论；未过门禁不做 LoRA、全量微调或扩大数据；不提交或推送。
- **研究问题**：跨光照响应特征能否在 scene-disjoint split 上提供超出 RGB-only frozen feature 的材料辨识信息，并在错误、打乱和无关响应控制下保持可归因收益？
- **预期产出**：忽略目录中的可审计传输包和 SHA-256 manifest；远端 `summer` 环境；固定 smoke manifest；RGB-only/response/oracle/control 的聚合指标与置信区间；回传的 CSV/JSON 和严肃学术风格图表。
- **停止条件**：单样本输入/模型/指标链失败即停止；响应条件相对 RGB-only 的 scene-bootstrap 主指标 CI 不排除 0，或错误/打乱控制解释同等收益时标记 `No-Go`；资源超出预估或许可/来源不闭合时标记 `Blocked`。
- **下一步**：先完成只读资产与硬件盘点，再冻结模型 revision、数据 split、指标、seed、命令和上传清单；计划闭合前不启动训练。

### 本轮完成

- 已创建并验证 Git 忽略的 `transfer_staging/`；本地下载 SigLIP2 与 Qwen3-VL-2B 官方固定 revision，权重 SHA-256 与官方 LFS 元数据一致；677 文件传输包在远端逐文件校验 0 mismatch。
- 已创建 Conda 环境 `summer`，复用服务器 CUDA/PyTorch 并通过阿里云 PyPI 补齐 Transformers/Qwen 依赖；已导出 environment、explicit 与 pip freeze。
- 已新增 frozen feature 抽取、scene-grouped 浅层评估、四类负对照、运行脚本、7 项单元测试和科研绘图脚本；本地/远端测试与 18 样本 GPU smoke 通过。
- 已完成 330 样本、66 区域、30 场景、五 folds、三 seed 的探索性 gate；全命令 99 秒，结果回传并生成 PNG/PDF 图。
- 已完成 Qwen3-VL-2B FP16 单图部署 smoke；推理成功但样例分类错误，未升级为性能结论。

### 当前判断与下一条可执行检查

- `material_response_probe_v0` 为 `No-Go`：pairwise response 降低 flip rate 31.31 pp，但区域准确率降低 5.05 pp、宏准确率降低 7.87 pp，准确率 CI 不满足 Go 门槛。
- 不继续直接响应拼接、LoRA 或全模型训练。结果只支持生成“响应作为不确定性/拒答信号”的新假设。
- **下一条检查**：如继续该方向，先写独立的 selective-rejection 预注册计划，使用 nested threshold、固定覆盖率指标和 held-out confirmation；数据允许用途未核验前不做公开/确认性 claim。

## 当前任务：初始化 kykt 远端研究工作目录

- **目标**：核验本机 SSH 入口和远端身份，在 `/hdd3/kykt26` 下建立训练、实验与结果收集目录，为后续 SGNet/RGB-D-D 环境和 smoke test 提供隔离工作区。
- **范围**：修复本机 `kykt` SSH 别名；只在用户自有目录 `/hdd3/kykt26` 下创建 `training/`、`experiments/`、`results/`；验证所有者、权限、磁盘空间和重复执行安全性。
- **不在范围**：不上传仓库、数据或权重；不安装环境；不启动训练/评估；不修改远端现有目录内容；不提交或推送。
- **证据**：两个既有 SSH 入口均已验证可登录同一远端，身份为 `kykt26`；`/hdd3/kykt26` 属于 `kykt26:kykt26` 且访问权限为 `rwx`，目标挂载点可用空间约 3.0 TB。
- **预期产出**：可直接执行的 `ssh kykt` 别名，以及 `/hdd3/kykt26/{training,experiments,results}` 三个用户目录。
- **下一步**：创建后用 `stat`、`test -w` 和第二次 `mkdir -p` 验证目录身份、可写性和幂等性。

### 本轮完成

- 已将本机既有 SSH 条目扩展为等价别名 `kykt`；`ssh kykt` 已通过批处理登录验证，主机地址和密钥信息仅保留在本机 SSH 配置中。
- 已在 `/hdd3/kykt26` 创建 `training/`、`experiments/`、`results/`；三者所有者均为 `kykt26:kykt26`、权限均为 `775`，写权限检查通过。
- 已第二次执行相同 `mkdir -p` 并核对目录元数据哈希，幂等检查通过；未改动远端既有目录，也未上传代码、数据、权重或结果。

### 当前判断与下一条可执行检查

- 远端目录初始化状态为 `Completed`，但这只代表存储入口可用，不代表 SGNet/RGB-D-D 训练环境或数据授权已就绪。
- **下一条检查**：取得 upstream 实际 SGNet/C2PD commit、checkpoint 来源、RGB-D-D 登记授权与 NYU v2 许可/split 后，在 `/hdd3/kykt26/envs` 建立锁定环境，并先执行不使用真实数据/权重的单元测试。

## 当前任务：选择性迁移 upstream SGNet/RGB-D-D 资产

- **目标**：在独立研究分支重放已审计的 14 个 upstream SGNet/RGB-D-D 提交，保留本 fork 的治理文档、材质主线、研究平台和文献索引，并形成可静态复核的迁移结果。
- **范围**：从 `main` 新建 `research/sgnet-rgbdd-migration`；逐提交迁移 SGNet 配置、实验计划、报告、评估/分析脚本和脱敏聚合摘要；处理 README 或忽略规则冲突；运行不需要数据、权重或 GPU 的静态检查与测试。
- **不在范围**：不直接 merge `upstream/main`；不删除本 fork 资产；不运行训练或完整评估；不下载数据或权重；不把 upstream 结果升级为本 fork 已复现结论；不提交或推送。
- **证据**：`upstream/main=0a95b3d`，当前 `main=42b1ac9`，`git rev-list --left-right --count upstream/main...main` 为 `14 4`；`docs/upstream-change-audit-2026-07-23.md`；14 个 upstream 提交的文件级增量。
- **预期产出**：`research/sgnet-rgbdd-migration` 工作分支；保留治理边界的 SGNet/RGB-D-D 代码与研究资产；迁移审计、测试结果和更新后的项目状态。
- **下一步**：逐提交 cherry-pick；若某提交会覆盖治理文档、引入机器绝对路径/敏感信息或依赖未登记第三方资产，则停止并先记录为 `Blocked` 或 `Needs verification`。

### 本轮完成

- 已新建 `research/sgnet-rgbdd-migration`，选择性迁移 `upstream/main` 的 14 个 SGNet/RGB-D-D 提交增量；当前分支仍指向 `main=42b1ac9`，没有新增提交或推送。
- 已迁移 5 个配置、实验计划、路线报告、22 个 Python 脚本、4 个 shell 脚本和 13 个聚合结果 JSON；未带入治理文档删除、数据、权重、逐样本输出、日志或生成图片。
- 18 个 JSON 解析、22 个 Python AST/CLI、4 个 shell 语法检查通过；修复 router 脚本的 sklearn 惰性导入和 shell CRLF 兼容性。
- 现有 `tests/` 3 项、`platform/tests/` 14 项单测均通过；迁移审计见 `docs/sgnet-rgbdd-migration-audit-2026-07-25.md`。

### 当前判断与下一条可执行检查

- 迁移状态为 `Smoke test`，上游实验结论仍为 `Needs verification`；当前材质恒常性主线不变。
- 本机为 CPU-only PyTorch 且缺 `scikit-learn`；已在 `docs/sgnet-rgbdd-provenance.md` 登记官方来源、当前 revision 和已知许可边界，但 upstream 实际代码 commit、数据授权/split 和 checkpoint 来源仍未闭合。
- **下一条检查**：向 upstream 执行者核对实际 SGNet/C2PD commit、checkpoint 来源、RGB-D-D 登记授权和 NYU v2 许可/split，并建立环境清单；未完成前不运行训练或完整评估。

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
