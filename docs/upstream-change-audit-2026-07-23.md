# Upstream change audit: 2026-07-23

**状态：Completed（只读审计）；未合并 upstream 到当前 `main`**

## 1. Git 状态

已 fetch 原仓库 `upstream/main`，并创建本地快照分支：

- 当前分支：`main`
- 上游快照：`sync/upstream-main-20260723`
- 当前 `main`：`0b0907e 123`
- `upstream/main`：`0a95b3d feat: train SGNet branch router pilot`
- 分叉计数：`upstream/main` 独有 14 个提交；当前 `main` 独有 3 个提交。
- `upstream` push URL 已设为 `no_push`，避免误推原仓库。

直接合并不是快进。预检显示会冲突，并且 `upstream/main` 会删除当前 fork 的治理文档、文献索引和 `material_response_probe_v0` 预备资产。因此本轮只记录审计，不 merge。

## 2. 上游新增提交主题

上游 14 个独有提交围绕 SGNet/RGB-D-D 深度超分路线展开：

- 先记录单帧 RGB-D 物理关系实验和路线切换；
- 建立 SGNet 在 RGB-D-D/test2 的 16x clean/shift gate；
- 比较 C2PD standalone、C2PD 冻结 stitch、显式错位估计和 SGNet adapter；
- 发展 spatial reliability gate；
- 完成 full NYU 多 seed、adaptive frequency gate、阈值敏感性、运行时、真实 RGB-D-D 4x、未见纹理泛化和 router 修复实验；
- 保留多个 No-Go 结果，最终当前最佳为 synthetic RGB-D-D 16x 下的 absolute-threshold hard adaptive frequency gate。

## 3. 上游路线变化

上游报告 `reports/2026-07-19_depth_physics_and_rgbd_route_summary.md` 给出的路线判断是：

- AI2-THOR 双向物理干预数据可靠，可作为物理关系真值来源；
- DOP 短提示、REST3D 风格重力树文字先验、Visual Jenga inpainting、DPE 普通关系头、RGB+DPE 拼接和显式图关系头均未形成可靠收益；
- 单帧 RGB-D 支撑关系学习没有超过简单深度规则，且近期工作已覆盖宽泛 RGB-D 关系/VLM/scene graph 接口；
- 因此停止继续堆关系模块，转向 RGB 引导深度图超分辨率：输入低分辨率 depth 与高分辨率 RGB，恢复高分辨率 depth。

这与当前 fork 的材质恒常性主线是不同研究方向。可迁移的是 gate 设计、负对照、等预算对照、No-Go 记录和 RGB/Depth 负迁移警惕，不应直接把上游深度超分结果写成本 fork 材质路线结论。

## 4. 关键上游结果

### SGNet shift gate

`experiments/plans/2026-07-22_sgnet_rgbdd_x16_gate.md` 记录的 gate 目标是：在 RGB-D-D/test2 405 对样本上，先复现 SGNet 16x baseline，再测小幅 RGB-only shift 是否带来稳定深度边界错误。

`results/quantitative/sgnet_rgbdd_x16_gate/summary.json` 记录：

- 任务：RGB-guided depth super-resolution；
- 数据：RGB-D-D/test2；
- 样本：405；
- 倍率：16x；
- SGNet shift finding：`pass`；
- C2PD standalone robustness：`modest_mixed_signal`；
- SGNet+C2PD frozen stitch：`no_go`；
- raw gradient alignment：`no_go_clean_bias`；
- trained shift calibrator：`no_go_random_level_accuracy`；
- SGNet misalignment consistency adapter：`retain_mixed_gain`；
- adapter v2 clean/flat preservation：`no_go_dominated_by_v1_on_shifted_conditions`；
- SGNet spatial reliability gate：`retain_positive_pilot_all_metrics`；
- learned spatial gate controls：`pass_learned_beats_constant_and_shuffled`。

Spatial reliability gate 相对 SGNet 的 pilot 相对变化：

| 条件 | RMSE | Boundary RMSE | False-edge rate |
| --- | ---: | ---: | ---: |
| clean | -1.014% | -1.119% | -21.949% |
| shift x=1 | -1.241% | -1.401% | -21.531% |
| shift x=2 | -1.708% | -1.884% | -21.511% |
| shift x=4 | -2.157% | -2.126% | -21.431% |

Controls 显示 learned gate 不是简单降低 RGB 强度：

- learned vs constant clean：RMSE -0.504%，false-edge -15.790%；
- learned vs constant shift x=4：RMSE -1.420%，false-edge -16.352%；
- learned vs shuffled shift x=4：RMSE -1.762%，false-edge -17.428%。

### Full NYU multi-seed

`confirmatory_multiseed.json` 显示 full NYU 多 seed 运行完成，但严格标准未通过：

- all seed means improve all metrics：`false`；
- strict all seed paired significance pass：`false`；
- strict failure count：21；
- fully improved conditions：clean、x/y translation、scale 0.98/1.02；
- mixed conditions：checker texture amp 8 和 amp 16。

### Adaptive frequency gate

`adaptive_frequency_multiseed.json` 是上游当前最强 synthetic 协议结果：

- all seed means improve all metrics：`true`；
- selected conditions：clean、shift x=4、shift y=4、scale 0.98、scale 1.02、texture amp 8、texture amp 16；
- strict paired significance 未全通过，failure count 为 3，集中在 texture amp 8 的 MAE/flat RMSE CI 跨 0；
- 上游结果 README 写明：7 个 selected conditions、3 个 seed、5 个指标共 105 个 paired comparisons 中 102 个 CI 严格低于 0。

### Runtime

`runtime_benchmark.json`：

- 100 image benchmark，90 timed samples；
- baseline mean 277.53 ms/image；
- adaptive mean 277.63 ms/image；
- baseline peak CUDA memory 2206.78 MB；
- adaptive peak CUDA memory 2507.05 MB；
- device：RTX 4090；
- parameter count：baseline 86,620,109；gate variants 86,620,990。

这说明 gate 参数和延迟开销很小，但显存增加约 300 MB；仍需在目标服务器环境复核。

### Real RGB-D-D 4x

`rgbdd_real_protocol_summary.json` 明确限制结论：

- synthetic RGB-D-D 16x adaptive frequency gate 已确认；
- direct transfer 到 `SGNet_Real_R` 为 `no_go`；
- 200-sample real-domain calibration 为 `no_go`；
- identity-initialized native real-domain training 也更差；
- 因此 synthetic 结论不能外推到真实传感器 RGB-D-D 4x 输入。

### Router 修复与泛化

上游保留了多个 No-Go：

- `soft_routing_development.json`：No-Go，保留 hard adaptive routing；
- `ramp_routing_development.json`：No-Go；
- `relative_hard_confirmation.json`：No-Go，保留 original absolute hard routing；
- `learned_router_pilot.json`：oracle 有 headroom，但 pilot router 不通过；
- `nyu_branch_router_pilot.json`：No-Go，不扩到 2,000 NYU。

`unseen_texture_generalization.json` 给出较窄正结果：core metrics 多数 seed 通过，routing 强度随纹理强度单调增加，但 26 个 strict failures 存在，不能声称通用重建改进。

## 5. 合并风险

`git diff --stat main..upstream/main` 显示上游新增 73 个文件级变化、约 14,804 行新增和 2,350 行删除。高风险点：

- 删除 `AGENTS.md`、`rules.md` 和 `docs/` 下多数治理文档；
- 删除 `literature/paper-index.md`、`literature/paper-sha256.txt`；
- 删除当前 fork 的 `material_response_probe_v0` 配置、计划、脚本和测试；
- 新增 `results/quantitative/sgnet_rgbdd_x16_gate/` 下大量聚合 JSON，其中部分可能按当前 fork Git 边界需要复核是否应跟踪；
- 上游 `.gitignore` 与当前 fork 的数据/论文/结果边界不一致。

因此不建议直接 `git merge upstream/main`。

## 6. 建议迁移策略

1. 保留当前 fork 的治理文档、文献索引和 material response probe 资产。
2. 新建 `research/sgnet-rgbdd-migration` 或 `sync/merge-upstream-sgnet-audit` 分支。
3. 只 cherry-pick 或手工迁移以下上游资产：
   - SGNet 配置；
   - SGNet 评估/分析脚本；
   - `experiments/plans/2026-07-22_sgnet_rgbdd_x16_gate.md`；
   - `reports/2026-07-19_depth_physics_and_rgbd_route_summary.md`；
   - 脱敏聚合结果摘要和 README。
4. 不带入上游对 `AGENTS.md`、`rules.md`、`docs/` 和文献索引的删除。
5. 迁移后将 SGNet/RGB-D-D 方向标记为 `Needs verification` 或 `Completed upstream audit`，直到本 fork 补齐数据许可、环境、路径、commit、命令和测试。

## 7. 对当前 fork 研究路线的影响

- 当前 fork 的材质恒常性主线不应被上游 SGNet 结果自动替换。
- 上游 RGB-D-D 结果对本 fork 有方法学价值：它强化了“简单拼接可能负迁移”“正确物理证据也需要接口/路由”“负对照和 No-Go 必须保留”的判断。
- 若用户希望跟随上游 SGNet 主线，应把它作为新的候选主线重新预注册，而不是直接覆盖 `material_response_probe_v0`。
