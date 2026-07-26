# 2026-07-19 深度物理关系实验与 RGB-D 路线总结

## 一、今天主要解决了什么问题

今天围绕一个核心问题持续推进：

> 能否借用 DOP 的对象对查询思路，把深度图提供的物理证据接入 VLM，用于判断物体之间的支撑或依赖关系？

实际工作没有停留在提示词讨论，而是依次完成了数据真值、模型推理、反事实生成、深度特征编码、RGB-D 融合、结构化关系头和文献查新。每个模块都用同一批物理干预数据做小规模 gate；有效的保留，无效的停止。

最终结论是：**AI2-THOR 物理干预数据可靠，但当前单帧 RGB-D 支撑关系学习模块没有超过简单深度规则，且外部论文已经覆盖宽泛的 RGB-D 关系推理接口。因此停止继续堆关系模块，下一步转向 RGB 引导深度图超分辨率。**

## 二、数据与实验基础

### 1. AI2-THOR 物理干预真值

在 RTX 5090 节点补齐 EGL/GLVND 后，AI2-THOR 已能正常输出 RGB、metric depth、实例分割并执行物理动作。

- 扫描场景：120 个 iTHOR 场景。
- 初始 receptacle 候选：3,478 个。
- 可移动/可拾取父物体候选：886 个。
- 最终实验：5 个场景、35 对物体。
- 标签分布：23 对 `child_depends_on_parent`，12 对 `no_observed_dependency`。
- 双向验证：35 对、70 个方向均完成；没有动作失败、反向依赖或互相依赖。
- 控制实验：正例父物体干预 46/46 出现下落，负例 0/24，下落无关物体 0/35。

这些结果说明：今天最可靠的资产不是某个关系模型，而是**具有真实物理干预验证的对象对标签和可复现生成流程**。

## 三、今天验证过的模型与模块

### 1. DOP 式短提示 + Qwen2.5-VL

在相同 35 对数据上比较 RGB-only、正确几何、错误几何、无关几何和 text-only。

Qwen2.5-VL-7B 的 balanced accuracy：

| 条件 | Balanced accuracy |
| --- | ---: |
| RGB-only | 65.2% |
| 正确几何证据 | 58.7% |
| 错误几何证据 | 50.0% |
| 无关几何证据 | 56.5% |
| Text-only | 50.0% |
| 简单几何规则 | 约 93.5% |

结论：正确几何提示没有提高 7B，反而低于 RGB-only；3B 也存在明显类别偏置。因此停止“DOP 短提示 + 直接支撑二分类”，不再靠改 prompt 扩大实验。

### 2. 深度事实编译器与重力树文字先验

将对象深度、位置和对象对关系整理成结构化事实，再转成文字输入 7B。

- 深度事实：探索性 balanced accuracy 75.0%。
- 同协议 RGB-only：52.0%。
- REST3D 风格重力树文字先验：50.0%。
- Text-only：58.3%。

深度事实在这个小 gate 中有信号，但规则仍然更强，而且文字事实容易接近直接答案。它只保留为诊断基线；重力树文字接口停止。

### 3. Visual Jenga 反事实 inpainting

借用 Visual Jenga 的思想：分别移除 parent/child，通过多次 inpainting 后的生成多样性判断依赖方向。深度只用于约束 mask，不把标签写进生成 prompt。

完成的工作：

- 部署 Stable Diffusion Inpainting，并核验模型文件完整性。
- 生成 rectangle、correct-depth、wrong-depth 等 mask。
- 每个条件固定 4 个 seed。
- 使用冻结 CLIP ViT-L/14 对固定对象区域计算跨 seed 语义多样性。
- 增加严格面积匹配控制，三类 mask 均固定为 1,400 像素。

面积匹配后的 parent-child 多样性差：

| Mask | 差值 |
| --- | ---: |
| Correct-depth | 0.0355 |
| Random-location | 0.0213 |
| Wrong-depth | 0.0721 |

正确深度没有优于错误深度，说明信号更可能来自 mask 位置/内容，而不是正确的深度物理关系。该分支触发 No-Go，不扩展到 35 对。

### 4. SD-VLM Depth Positional Encoding

按 SD-VLM 公开公式实现了深度位置编码：

- 整图 DPE：`24 x 24 x 128`。
- 按对象框做 ROI pooling。
- 拼接 A、B、绝对差、带符号差和深度统计。
- 每个有序对象对得到 516 维特征。

这部分通过了结构和维度 smoke，说明编码接口可运行；但接口可运行不等于关系预测有效。

### 5. DPE、RGB 和关系头消融

使用 35 对数据进行场景级 leave-one-scene-out：

| 模块 | Balanced accuracy | 决策 |
| --- | ---: | --- |
| 深度差规则 | 60.9% | 保留为最低基线 |
| DPE + 普通关系头 | 52.5% | 淘汰 |
| RGB(CLIP) + DPE + 普通关系头 | 43.1% | 淘汰 |
| DPE 双向交换关系头 | 50.2% | 淘汰 |
| RGB+DPE 双向交换关系头 | 50.0% | 淘汰 |
| 显式节点 + 有向边分类器 | 39.9% | 淘汰 |

结果表明：当前小样本下，DPE 编码本身没有转化成可靠的支撑关系预测；直接加入 RGB 还会恶化结果；继续增加图网络或训练轮数缺乏依据。

## 四、模块保留和停止清单

### 保留

1. DOP 对象对查询：保留为任务接口，不作为创新点。
2. AI2-THOR 双向物理干预：保留为真值生成和离线评估。
3. DPE 编码：保留为可复用深度特征接口。
4. 对象级 ROI pooling：保留为工程组件。
5. 深度事实编译器：仅保留为诊断基线。

### 停止

1. DOP 短提示直接支撑二分类。
2. REST3D 重力树文字先验。
3. Visual Jenga 深度 mask inpainting。
4. DPE 普通 MLP 关系头。
5. RGB 与 DPE 直接拼接。
6. 双向交换关系头。
7. 显式图节点/有向边分类器。

## 五、今天的文献查新结论

进一步核验了与 RGB-D 关系推理最接近的公开工作：

1. [Prompt-Guided Spatial Understanding with RGB-D Transformers](https://openaccess.thecvf.com/content/ICCV2025W/AICity/papers/Muturi_Prompt-Guided_Spatial_Understanding_with_RGB-D_Transformers_for_Fine-Grained_Object_Relation_ICCVW_2025_paper.pdf)：已经覆盖 RGB、Depth、对象 mask、空间关系问答和深度增强 VLM。
2. [PhysGraph](https://arxiv.org/abs/2606.08655)：由 RGB-D observation 重建对象级几何，并推断材料、关节和 physics-aware scene graph。
3. [FunFact](https://arxiv.org/abs/2604.03696)：由 posed RGB-D 构建功能关系图，结合 foundation model、factor graph 和几何/常识先验，并包含 AI2-THOR 数据。

因此，“RGB-D + 对象关系 + 场景图/VLM”本身已经不是干净空白。继续缝合图结构、因子图或更大 VLM，创新风险和实验风险都很高。

## 六、最终路线切换

下一步转向：

> **RGB 引导深度图超分辨率：输入低分辨率 Depth 和高分辨率 RGB，恢复高分辨率 Depth。**

这条路线具备明确的像素级真值、公开数据、标准指标和可复现代码，也符合原多模态图像复原项目主线。

第一轮计划：

1. 在 RGB-D-D 上复现 SGNet baseline。
2. 在相同 backbone、数据和训练预算下加入 C2PD 连续性约束。
3. 比较 depth-only、RGB-only、SGNet、SGNet+C2PD。
4. 增加 RGB-Depth 轻微错位和 RGB 纹理扰动测试。
5. 只有常规指标和错位鲁棒性同时提高，才继续加入 DORNet 的真实退化建模。

拟研究问题：

> 在真实深度退化和 RGB-Depth 轻微错位下，连续性约束能否抑制 RGB 纹理错误传播到深度边界？

## 七、今天形成的 finding

1. 物理干预数据比人工框关系更可靠，AI2-THOR 双向标签可以继续复用。
2. 对冻结 VLM，加入正确深度/几何信息不保证性能提高；证据接口可能比证据本身更关键。
3. 生成模型产生的方向差异不等于深度物理关系；错误深度控制是必要反证。
4. DPE 的工程接口可用，但在 35 对数据上没有转化为关系预测收益。
5. RGB 与深度简单拼接可能产生负迁移，而不是自然互补。
6. 当可解释规则明显强于学习模块时，应停止继续堆模型。
7. 当前更值得投入的是具有明确真值和指标的 RGB-D 图像复原，而不是继续寻找新的单图物理关系名称。

## 八、结果边界与复现记录

- 所有 35 对结果均为小规模 pilot/gate，不是正式 benchmark。
- 数据、模型权重、逐样本输出和生成图片保留在本地或服务器研究目录，不上传 Git。
- 公开仓库只保存自有代码、汇总指标、方法来源和复现入口。
- 深度关系代码与详细实验记录位于 [aspera11011/Summer](https://github.com/aspera11011/Summer)，本轮路线审计对应 commit `0d24ba9`。
- 下一步正式结果必须补齐任务、数据集、倍率、指标、权重来源、环境、命令和完成程度。
