#!/usr/bin/env python3
"""Seed the labkit registry with this project's research map.

Idempotent: writes entities by fixed id, safe to re-run. Content mirrors
docs/semantic-physical-route-audit.md, docs/research-design-patterns.md and
experiments/plans/material_response_probe_v0.md — the source-of-truth docs.

Run:  python platform/labkit/seed.py
"""

from __future__ import annotations

import os
import sys

_PLATFORM_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PLATFORM_DIR not in sys.path:
    sys.path.insert(0, _PLATFORM_DIR)

from labkit import schema  # noqa: E402
from labkit.store import Store  # noqa: E402

MOTHER = "idea-identifiability-aware-division-of-labor"


def seed(store: Store) -> None:
    # ---- mother thesis --------------------------------------------------- #
    store.save(
        schema.Idea(
            id=MOTHER,
            title="识别度感知的语义—测量分工 (identifiability-aware division of labor)",
            slot="mainline",
            status="active",
            thesis=(
                "RGB/语义给出高分辨率但物理欠定的猜测；物理测量给出稀疏但可作真值的约束。"
                "真正的贡献单元是一张逐实例/逐位置的『信任地图』——判断哪里信语义、哪里让物理否决。"
            ),
            detail=(
                "统一 fork 的材质翻转率与 upstream 的 SGNet spatial reliability gate："
                "两者是同一对象——语义/外观引导的空间可信度场。项目全部 No-Go 的共因是"
                "做了全局无差别融合、缺这张地图。"
            ),
            design_patterns=["RP-07", "RP-08", "RP-09", "RP-10"],
        )
    )

    ideas = [
        schema.Idea(
            id="idea-identifiability-partition",
            title="① 欠定分区里语义才有用",
            slot="mainline",
            status="active",
            thesis="语义先验只在物理欠识别的分区（镜面/透明/暗光/小尺度）提升准确率，在可识别分区中性或有害。",
            detail="能把项目全部负结果翻译成一条正向分工法则。第一枪：按翻转率/材质大类切分区，比较 RGB-only 与 RGB+语义。",
            design_patterns=["RP-07", "RP-05"],
            links=[MOTHER],
        ),
        schema.Idea(
            id="idea-flip-as-uncertainty",
            title="② 翻转即不确定性（训练无关判别器）",
            slot="adjacent",
            status="active",
            thesis="冻结 VLM 在受控光照扰动下的答案分布本身是材质指纹与可靠性信号；漫反射稳定、镜面/透明剧烈翻转。",
            detail="模态无关原语：受控扰动下的输出方差当特征/不确定性。数据已落盘，0 训练可验证。",
            design_patterns=["RP-09", "RP-05"],
            links=[MOTHER],
        ),
        schema.Idea(
            id="idea-counterfactual-grounding-benchmark",
            title="③ VLM 物理接地反事实诊断基准",
            slot="adjacent",
            status="proposed",
            thesis="VLM 是看像素还是背物体—材质共现？造反常配对测它默认先验还是读测量。",
            detail="可独立发表的诊断/benchmark；多光照成对图能给出『同表面不同光被判不同材质』的铁证。",
            design_patterns=["RP-05", "RP-07"],
            links=[MOTHER],
        ),
        schema.Idea(
            id="idea-privileged-response-probe",
            title="④ 特权物理教师的可蒸馏性 / 响应探针",
            slot="mainline",
            status="active",
            thesis="多光响应相对不变均值是否含额外材质判别信息？哪些物理线索能蒸进单目 RGB 学生、哪些有信息论上限？",
            detail="material_response_probe_v0 是它的 frozen-feature gate；通过后才谈蒸馏。这是首个值得动 GPU 的实验。",
            design_patterns=["RP-06", "RP-08", "RP-02", "RP-03"],
            links=[MOTHER],
        ),
        schema.Idea(
            id="idea-unified-reliability-gate",
            title="⑤ 统一 reliability-gate 纲领",
            slot="pool",
            status="proposed",
            thesis="材质翻转率与 SGNet spatial reliability gate 用同一形式化，同时服务材质分工与深度超分。",
            detail="纲领级叙事，把 fork 与 upstream 拧成一个故事；一页统一形式化即可指导后续预注册。",
            design_patterns=["RP-09", "RP-10"],
            links=[MOTHER],
        ),
        schema.Idea(
            id="idea-active-measurement-agent",
            title="⑥ 主动测量 agent（高风险）",
            slot="high_risk",
            status="parked",
            thesis="欠定区域触发最省的下一次测量（换光/移视角/换传感器）最大化信息增益。",
            detail="信任地图的终点。需真值与强负对照；先真实选光显著优于随机再谈生成式干预。",
            design_patterns=["RP-11"],
            links=[MOTHER],
        ),
    ]
    for idea in ideas:
        store.save(idea)

    # ---- dataset --------------------------------------------------------- #
    store.save(
        schema.Dataset(
            id="ds-material-constancy-rgb-gate-v2",
            name="Material constancy RGB gate v2 (MIT Multi-Illumination-derived)",
            version="v2",
            manifest_hash="0651737375c61300bd60055e70e155c627a855e09bf1cfcf11ffcb13112f9828",
            license_status="needs_verification",
            path="data/processed/material_constancy_rgb_gate_v2/",
            independent_units=schema.IndependentUnits(scenes=30, regions=66, samples=330),
            notes="Source: https://data.csail.mit.edu/multilum . License/allowed-use pending record.",
        )
    )

    # ---- experiments ----------------------------------------------------- #
    store.save(
        schema.Experiment(
            id="exp-flip-identifiability-v0",
            title="Flip-as-uncertainty + identifiability partition (RGB-only)",
            idea_id="idea-flip-as-uncertainty",
            question="冻结 VLM 的光照翻转不稳定性能否训练无关地预测其错误，且欠定材质是否更不稳定更不准？",
            hypothesis="低翻转熵区域显著更准（AUROC>0.5，选择性拒答提升准确率）；under-identified 分区准确率更低、翻转更高。",
            track="exploratory",
            status="completed",
            conditions=[
                schema.Condition(name="entropy_ranked_selective", purpose="② 选择性预测", changed_var="按翻转熵拒答高熵区域"),
                schema.Condition(name="identifiability_partition", purpose="① 分区对照", changed_var="材质可识别性分层"),
            ],
            primary_metric="AUROC(-flip_entropy -> per-sample correct)",
            guardrail_metrics=["selective_gain_at_50pct", "partition accuracy gap"],
            go_threshold="每个模型 AUROC CI 下界 > 0.5 且选择性增益 @50% CI 下界 > 0",
            no_go_threshold="不稳定性不能超随机预测正确性（CI 跨 0.5）",
            statistical_unit="region",
            bootstrap_unit="scene",
        )
    )
    store.link_experiment_to_idea("exp-flip-identifiability-v0", "idea-flip-as-uncertainty")

    store.save(
        schema.Experiment(
            id="exp-material-response-probe-v0",
            title="material_response_probe_v0 — frozen-feature response gate",
            idea_id="idea-privileged-response-probe",
            question="对现有材质区域，受控光照响应是否比单 RGB 或不变均值提供额外材质判别信息？",
            hypothesis="多光响应浅层头相对最强单 RGB frozen-feature 基线提升区域准确率并降低翻转，而打乱/错区域控制不会。",
            track="confirmatory",
            status="planned",
            conditions=[
                schema.Condition(name="single_rgb_frozen", purpose="强简单基线", changed_var="单光 crop"),
                schema.Condition(name="multi_light_mean", purpose="不变均值", changed_var="同区多光特征均值"),
                schema.Condition(name="mean_plus_variance", purpose="简单响应", changed_var="加光致方差"),
                schema.Condition(name="pairwise_response", purpose="主干预", changed_var="同区多光有向差"),
                schema.Condition(name="rgb_plus_albedo", purpose="旧 No-Go 桥", changed_var="经浅层头重测"),
                schema.Condition(name="rgb_plus_residual", purpose="物理响应代理", changed_var="RGB/albedo 残差"),
            ],
            controls=schema.ControlSet(
                correct="同区多光响应 + 对齐 albedo/残差",
                wrong="错区域 albedo / 反向响应",
                shuffled="跨区域打乱光照配对",
                irrelevant="同维随机残差 / 无关区域特征",
                equal_param="等参数量 MLP 分支但无响应输入",
            ),
            primary_metric="mean region accuracy on held-out scenes",
            guardrail_metrics=["macro class accuracy", "region flip rate", "worst-light accuracy"],
            go_threshold="相对最强单 RGB 基线 +≥5pp（scene-aware CI 下界>0），翻转 −≥10pp（CI 上界<0），每个控制 +≥3pp",
            no_go_threshold="不超单 RGB 基线，或 CI 跨 0，或打乱/错控制追平增益，或 macro 掉 >2pp",
            statistical_unit="region",
            bootstrap_unit="scene",
            plan_md_path="experiments/plans/material_response_probe_v0.md",
            config_path="configs/material_response_probe_v0.json",
        )
    )
    store.link_experiment_to_idea("exp-material-response-probe-v0", "idea-privileged-response-probe")

    # ---- modules --------------------------------------------------------- #
    store.save(
        schema.Module(
            id="mod-flip-identifiability",
            name="flip_identifiability analysis",
            kind_="analysis",
            path="platform/labkit/analyses/flip_identifiability.py",
            notes="Reuses scripts/compare_material_conditions + analyze_material_gate for CI parity.",
        )
    )


def main() -> None:
    store = Store()
    seed(store)
    problems = store.validate_all()
    counts = {f: len(store.list_raw(f)) for f in store.export()}
    print("[seed] wrote:", ", ".join(f"{k}={v}" for k, v in counts.items()))
    if problems:
        print("[seed] VALIDATION PROBLEMS:")
        for p in problems:
            print("  -", p)
        raise SystemExit(1)
    print("[seed] registry valid.")


if __name__ == "__main__":
    main()
