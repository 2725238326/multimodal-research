# 标定 HDR + light-probe 候选审计

**日期：2026-07-26**
**状态：`Completed training-free audit gate`；light-probe normalization 判为 `No-Go`，calibrated HDR 判为 `Partially supported`**

## 审计目的

五光照 LDR response 家族已全部关闭（`D-017`）。既定规则是：下一候选必须**改变可观测证据**，优先顺序为标定 HDR + light-probe normalization、polarization/flash、几何 verifier；若无新测量资源则转向 SGNet/RGB-D-D provenance。

本审计只回答“优先候选是否具备可用的新测量资源，且其机制在训练前是否已经站得住”。不训练任何模型，不拟合任何分类头，不改动已关闭实验的资产。

## 1. 测量资源确实存在

| 事实 | 证据 |
| --- | --- |
| LDR 光探针早已在本地 | 已 CRC 通过的官方 test archive 内含每场景 25 张 `chrome256` 与 25 张 `gray256` JPG（750 + 750），从未被任何已关闭路线使用 |
| 官方发布线性 HDR | SDK `a85aa925` 的 `query_images(hdr=True)` / `query_probes(hdr=True)` 指向 `*_mip{m}_exr.zip` 与 `*_probes_256px_exr.zip` |
| 单场景 EXR 包自足 | 每个 `{scene}_mip2_exr.zip` 含 25 张场景 EXR、25 张 chrome EXR、25 张 gray EXR、`materials_mip2.png` 与 `meta.json`；无需单独下载 probes 包 |
| 体积可承受 | dev 场景 mip2 EXR 约 49.7–81.5 MB/场景；官方 test bulk EXR 为 1,648,079,881 B |
| 本机可读 | `cv2 4.13.0` 在 `OPENCV_IO_ENABLE_OPENEXR=1` 下解码 EXR，`meta.json` 提供 chrome/gray 的全分辨率 bounding box 与边界点 |
| 许可未变 | 与 `docs/multi-illumination-provenance.md` 同源，CC BY 4.0；派生数据仍不进 Git |

单流下载约 33 KB/s，实际不可行；新增 `scripts/fetch_ranged_asset.py` 用 16 路 HTTP range 并行取到 8.1–9.7 MB/s，并强制输出 SHA-256 与 ETag/Last-Modified 侧车文件。

因此规则中的“若无新测量资源”分支**不成立**，本审计继续检验机制本身。

## 2. 训练前 oracle 检验

在 6 个官方 train-pool 场景（`14n_office7`、`joy_bedroom14`、`kingston_dining7`、`state_smallbathroom3`、`west_bathroom4`、`willow_living19`；按房间类型多样性选取，非随机抽样）上，每场景 25 个光照方向，用官方 material mask 的连通域取 90 个区域。描述符为区域线性辐射中位数的 log10；normalization 条件为逐方向、逐通道减去 gray probe 圆盘均值的 log10。

判别力指标是 between-region 方差与 within-region（跨光照）方差之比。该指标不需要分类器，也不需要 mask 之外的标签。

| 场景 | 场景亮度动态范围 | gray probe 动态范围 | r(场景, gray) | B/W raw | B/W 归一化 | 增益 |
| --- | --- | --- | --- | --- | --- | --- |
| 14n_office7 | 64.68 | 1.66 | -0.293 | 0.841 | 0.818 | 0.972 |
| joy_bedroom14 | 42.60 | 1.74 | 0.255 | 1.769 | 1.737 | 0.982 |
| kingston_dining7 | 26.31 | 5.01 | -0.456 | 1.876 | 1.554 | 0.828 |
| state_smallbathroom3 | 7.48 | 1.27 | 0.366 | 2.072 | 2.264 | 1.093 |
| west_bathroom4 | 4.15 | 1.71 | 0.448 | 1.645 | 2.307 | 1.403 |
| willow_living19 | 8.40 | 3.76 | -0.366 | 1.396 | 1.135 | 0.813 |
| **中位数** | **17.35** | **1.72** | **-0.019** | **1.707** | **1.646** | **0.977** |

结论：**gray probe 不能作为 normalizer**。它要归一化的场景亮度跨方向变化 17.35 倍，而它自身只变化 1.72 倍，二者中位相关系数为 -0.02，6 个场景中 3 个为负。归一化后 within-region 跨光照方差中位数不降反升 2.5%，判别力中位增益 0.977；6 个场景中只有 1 个增益超过 10%。

物理解释与测量一致：gray ball 位于房间中一个固定点，接收的是整个半球的积分辐照度。闪光灯总功率恒定，只是朝向不同，房间把它重新分配，因此**探针处的辐照度近似与光照方向无关**，不携带逐表面辐照度信息。

chrome probe 保留了方向信息（动态范围中位 27.78，相关系数中位 0.41），但要把镜面球的环境映射转成某个表面实际接收的辐照度，需要该表面的法向；Multi-Illumination 不提供几何或深度真值。

## 3. Calibrated HDR 的独立结论

用同一 6 个场景的官方 JPG 与 EXR 逐像素对照，JPEG 截断量是被测量的而不是假设的：把 JPEG 最后一个未截断码值（253–254）对应的线性值作为 clip point，实测 clip point 平均为 1.14，且 “线性值超过 clip point 的比例” 与 “JPEG 至少一个通道达到 255 的比例” 高度一致（`state_smallbathroom3` 上为 0.4407 对 0.4500）。

- 每场景平均截断比例中位数 **5.8%**，跨场景范围 2.2%–45.0%；
- 最差单个光照方向达到 **69.4%**；
- 线性数据在 clip point 之上还延伸中位 **35 倍**。

所以 HDR 确实找回了 LDR 路线丢掉的真实信号，且截断集中在高光/明亮区域——正是材质区分最需要的地方。但要如实说明两点：其一，中位只有约 6% 的像素受影响，规模上不足以合理解释官方 test split 上 **-12.50 pp** 的差距；其二，线性 HDR 是同一观测量的去截断，不是新的物理观测量，不满足 `D-017` 对“改变可观测证据”的要求。

## 4. 判定

- **light-probe normalization：`No-Go`**。机制在训练前的 oracle 检验上即失败，且失败原因是可解释的测量学事实，不是调参不足。不进入描述符设计、不训练、不上服务器。
- **calibrated HDR：`Partially supported`，但不单独立项**。它是真实但幅度有限的改进，且不改变观测量类别。
- **polarization/flash：本数据集不可得**。Multi-Illumination 无偏振通道；其 25 个方向本身就是已被穷尽的 flash 观测。
- **几何 verifier：本数据集不可得**。无深度、法向或几何真值。

因此优先候选在其审计门禁处关闭，回退分支生效：**转向 SGNet/RGB-D-D 的 provenance、许可、checkpoint/hash 与单样本 smoke**。

## 5. 边界与限制

- 6 个场景是可行性审计规模，不是确认性实验规模；场景按房间类型多样性选取，非随机。
- `summary.json` 中的阈值是**看过数据之后**设定的，只作报告用途，不是预注册门禁。承载结论的是原始测量值本身。
- 本审计未消耗官方 30 个 `everett` test scenes；该 split 在 `material_photometric_external_confirmation_v0` 已使用一次，保留为将来最终一次性确认。
- 未在服务器执行任何下载；所有资产在本地取得并哈希后留在忽略目录。

## 6. 复现命令

```bash
python scripts/fetch_ranged_asset.py \
  --url https://data.csail.mit.edu/multilum/<scene>/<scene>_mip2_exr.zip \
  --output transfer_staging/hdr_probe_audit_v0/<scene>_mip2_exr.zip --parts 16

python scripts/audit_hdr_probe_radiometry.py \
  --scene-dir transfer_staging/hdr_probe_audit_v0/extracted/<scene> \
  --jpg-scene-dir transfer_staging/hdr_probe_audit_v0/extracted_jpg/<scene> \
  --output transfer_staging/hdr_probe_audit_v0/radiometry_<scene>.json

python scripts/summarize_hdr_probe_audit.py \
  --input-glob 'transfer_staging/hdr_probe_audit_v0/radiometry_*.json' \
  --output results/quantitative/hdr_light_probe_oracle_audit_v0/summary.json
```

聚合摘要 SHA-256：`14332b9f18fc6b251fefa13851b74a614e79113593a5d6ad65fd36fe53c1093c`。
