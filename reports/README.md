# 本地阶段汇报

- `2026-07-19_depth_physics_and_rgbd_route_summary.md`：深度物理关系当天完整实验总结，包含 AI2-THOR 干预真值、Qwen gate、Visual Jenga、DPE/RGB/结构化关系头消融、查新结论和转向 RGB-D 图像复原的下一步。
- `material_response_probe_v0.md`：SigLIP2 frozen-feature 多光照响应 gate 的 330 样本、三 seed、负对照和 No-Go 结论。
- `material_response_selective_gate_v0.md`：在固定 RGB 预测下对跨光照响应拒判信号进行 nested scene 评估；固定覆盖率、AURC 和 shuffled control 均未过门槛，结论为 No-Go。
- `material_photometric_trajectory_external_confirmation_v0.md`：曝光审查的像素光度轨迹在开发集有方向性收益，但在官方零重叠 test split 显著反转；关闭当前多光照 response 路线。
- `2026-07-18_19_nightly_research_summary.docx`：面向学姐的通俗版今晚工作与 finding 总结。
- `material_constancy_region_alignment_v1.md`：共同区域标记的两模型、330 样本诊断结果与 No-Go 判断。
- `project-task-guide/artifact.json`：完整项目任务技术报告的可审计源数据与阅读结构。
- `project-task-guide/report.html`：面向新协作者的自包含项目说明；为本地生成物，不进入 Git。
- 实验事实来源：`experiments/manifests/`、`results/quantitative/`、`experiments/logs/` 与本地脚本。
- 该目录受根目录 `.gitignore` 保护，只用于本地汇报与交接。
