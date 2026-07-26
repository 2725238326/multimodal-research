# SGNet/RGB-D-D provenance

**核验日期：2026-07-25**

此清单记录可从官方来源确认的第三方身份和使用边界，不代表已经确认 upstream 实验实际使用了下列仓库的当前 HEAD。

| 资产 | 官方来源 | 2026-07-25 核验 revision | 许可证/允许用途 | 本 fork 状态 |
| --- | --- | --- | --- | --- |
| SGNet | `https://github.com/yanzq95/SGNet` | `a0935c1d0176f8240fed2619e1247de418f082a8` (`main` HEAD) | GitHub 官方仓库声明 Apache-2.0 | 来源已核验；upstream 实际运行 commit 未记录，Needs verification |
| C2PD | `https://github.com/amhamster/C2PD` | `28690461430555c1bb0b544b1cd3a458400fb361` (`master` HEAD) | GitHub 官方仓库声明 Apache-2.0 | 来源已核验；upstream 实际运行 commit 未记录，Needs verification |
| RGB-D-D | `https://github.com/lingzhi96/RGB-D-D-Dataset` | `4397c1833e3c6e306db888b260f5ce21da67351f` (`main` HEAD) | 官方 README：仅学术、非商业使用，要求署名和同许可衍生；下载需由正式员工签署 Release Agreement 并使用机构邮箱登记 | 数据未进入 Git；本 fork 尚未确认登记授权、split 文件哈希或本地数据哈希，Blocked for execution |
| NYU Depth v2 | `https://cs.nyu.edu/~silberman/datasets/nyu_depth_v2.html` | 官方数据页，无代码 revision | 官方页面要求引用论文，但本轮未在页面找到明确许可证文本 | 数据未进入 Git；许可、下载来源、split 和哈希均 Needs verification |

## Checkpoint records already present

迁移的聚合摘要记录了以下 SHA-256，但不包含 checkpoint 文件：

- SGNet baseline: `ceda2db815c9c001a6ee92c4b794f119f7f082c36c1fe552ebb1d7bb3041a340`
- C2PD: `e1de04e88e32d208fcbcaaae60837ae5033a14b042838df47cabd295d92c1385`
- SGNet adapter v1: `0706c1cf997196fbe64861f58542c6eef3fbc95a3156f218cb915b57d7c58f9d`
- SGNet adapter v2: `77c94cf35ffc137f37cf8a7cd739099721bbc63cd8d5a338ed5a5fbf8084dc26`
- Spatial reliability gate pilot: `98a96d03eee4b7b3ca649bf5b2f1dcc4eda9f299c0e66f17796caadadab14e06`
- Runtime benchmark gate: `a5e4c516be4af7cce5d26c9e5fe21f86eb6c31719ff827a2a5743992338e95bf`

这些哈希只能在取得合法来源的本地 checkpoint 后用于一致性核验，不能证明 checkpoint 的许可或来源。

## 2026-07-26 复核

### 代码 revision 已稳定

| 仓库 | 2026-07-26 API 复核 | 最后 push | 许可 |
| --- | --- | --- | --- |
| `yanzq95/SGNet` | `a0935c1d0176f8240fed2619e1247de418f082a8`（`main` HEAD） | 2024-04-05 | Apache-2.0（API `spdx_id`） |
| `amhamster/C2PD` | `28690461430555c1bb0b544b1cd3a458400fb361`（`master` HEAD） | 2025-01-13 | Apache-2.0（API `spdx_id`） |

两个 revision 与 2026-07-25 记录一致。由于两仓库分别自 2024-04-05 和 2025-01-13 起没有新 push，**upstream 在 2026-07 期间做的任何 clone 都只能落在上述 commit 上**。这把 execution gate 第 1 项从"完全未知"收窄为高置信推断，但仍不等于记录：需要 upstream 执行者确认其未使用 fork、patch 或更早的 checkout。

### Checkpoint 托管方式已查清，但获取路径断开

- 官方 SGNet README 明确：`All pretrained models can be found <Google Drive folder>`，URL 为 `https://drive.google.com/drive/folders/17mCRfsNj0f_BNY3viHcR6M1camCVoAb8`。
- README 同时说明：初版 `.pth` 的变量名与最新代码不一致，因此作者**重新上传了命名为 `xxx_R.pth` 的文件**。这与 upstream 脚本中的 `${sgnet_dir}/cpts/SGNet_X16_R.pth` 完全对应，可确认 upstream 使用的是官方重传版权重，而非自训练权重。
- **checkpoint 不在 Git 仓库内**，`cpts/` 目录在该 commit 下不存在（API 返回 `Not Found`）。因此仓库许可 Apache-2.0 覆盖代码，不自动覆盖 Google Drive 上的权重文件；作者亦未发布权重的官方哈希。
- **阻塞：本机无法访问 Google**。实测 `drive.google.com` 与 `www.google.com` 均连接超时（21 s 后失败），而 `raw.githubusercontent.com` 与 `data.csail.mit.edu` 正常。这是网络层阻断，不是临时故障。

后果：项目规定的获取路径是"本地下载 → 哈希校验 → 上传服务器，服务器不得下载"。由于官方 checkpoint 与 SGNet 版 NYU-v2 都只在 Google Drive 上，**该路径对这两类资产当前不可执行**。这一项需要用户决策，不能由执行者自行绕过。

### NYU v2 许可：官方页面无授权文本

对官方页面 `https://cs.nyu.edu/~silberman/datasets/nyu_depth_v2.html` 做了全文扫描（7,593 字符）。页面只声明引用要求——"If you use the dataset, please cite the following work"（Silberman et al., ECCV 2012）——**没有出现 license、copyright、terms、permission 或 commercial 相关的授权文本**。

另需注意：SGNet README 给出的 NYU-v2 下载指向作者自建的 Google Drive 文件 `1osYRaDfMYuyiTkJwDbKl3kHwyevDLsZf`，即本任务实际使用的是**SGNet 作者预处理并再分发的 NYU-v2 副本**，不是 NYU 官方分发。因此需要分别确认原始数据集条款与该再分发行为的授权依据，不能只引用 NYU 页面。

## Execution gate

在执行任何 SGNet/RGB-D-D 训练或评估前必须补齐：

| # | 项目 | 2026-07-26 状态 |
| --- | --- | --- |
| 1 | upstream 实际使用的 SGNet/C2PD commit | `Needs verification`（已收窄为 `a0935c1d` / `28690461`，待执行者确认） |
| 2 | checkpoint 官方下载 URL、许可和 SHA-256 对照 | `Blocked`：URL 已定位且文件名已对应，但 Google Drive 本机不可达，且作者未发布官方哈希 |
| 3 | RGB-D-D Release Agreement/登记授权确认及 split 哈希 | `Blocked`：需正式员工签署并用机构邮箱登记，授权状态待核查 |
| 4 | NYU v2 的明确允许用途、下载来源和 split 哈希 | `Needs verification`：官方页面只有引用要求、无授权文本；实际来源为 SGNet 作者的再分发副本 |
| 5 | 锁定的 Python/PyTorch/CUDA 环境 | `Not started`：远端 `summer` 环境为材质路线所建，未含 SGNet 依赖 |

五项中没有一项已闭合；其中第 2、3 项是外部依赖阻塞，需要用户决策或对外沟通，不能由执行者在本机解决。
