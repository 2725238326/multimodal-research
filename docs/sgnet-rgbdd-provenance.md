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

## Execution gate

在执行任何 SGNet/RGB-D-D 训练或评估前必须补齐：

1. upstream 实际使用的 SGNet/C2PD commit；
2. checkpoint 官方下载 URL、许可和 SHA-256 对照；
3. RGB-D-D Release Agreement/登记授权确认及 split 哈希；
4. NYU v2 的明确允许用途、下载来源和 split 哈希；
5. 锁定的 Python/PyTorch/CUDA 环境。
