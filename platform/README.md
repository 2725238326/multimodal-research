# labkit — 研究实验平台

把本项目的研究方法论（`docs/research-design-patterns.md` 的 RP-01..RP-12、
`docs/semantic-physical-route-audit.md` 的"一主线/两邻接/一高风险"）固化成软件：
**idea → 实验（可证伪合同）→ run（可复现胶囊）→ Go/No-Go**，人和 agent 都能读写。

它不是通用 MLOps 面板：数据模型直接对应研究合同，而非泛化 run。

## 结构

```
platform/
  registry/        # git 跟踪的聚合真值（ideas/experiments/runs/datasets/modules）
  runs_local/      # gitignored：逐样本、日志、大 artifact
  labkit/          # Python 包（核心仅标准库；分析用 numpy；server 用 FastAPI）
    schema.py store.py cli.py server.py seed.py analyses/flip_identifiability.py
  web/             # TypeScript + React + Vite 前端（无图表库，手写 SVG）
  tests/
```

**为什么放 `platform/` 而不放 `results/`**：`.gitignore` 把整个 `results/` 树忽略，
新路径 `platform/registry/` 默认被跟踪——这正是让脱敏聚合摘要进 Git 的方式，
与 `reports/**/artifact.json` 的处理一致。`platform/` 目录**不是** Python 包，
避免遮蔽标准库 `platform` 模块；包名是 `labkit`。

## 快速开始

```bash
# 1) 播种研究地图（幂等）
python platform/labkit/seed.py

# 2) 跑首个真实实验（①② flip-identifiability，0 训练）
python platform/labkit/cli.py analyze flip-identifiability

# 3) 校验 registry
python platform/labkit/cli.py validate

# 4) 起可视化面板（可选依赖）
pip install -r platform/requirements-server.txt
python platform/labkit/server.py            # http://127.0.0.1:8000
#   前端开发模式（热更新，代理 /api 到 :8000）：
cd platform/web && npm install && npm run dev      # http://127.0.0.1:5173
#   或构建到 dist 由 FastAPI 一并托管：
cd platform/web && npm run build && python ../labkit/server.py
```

## Agent / 脚本如何写入（零依赖，仅标准库）

```bash
# 登记一个 idea / 实验
python platform/labkit/cli.py idea new "新想法" --slot adjacent --thesis "一句话可证伪核心"
python platform/labkit/cli.py exp  new "实验标题" --idea <idea-id> --track confirmatory \
    --primary-metric "mean region accuracy" --go "…" --no-go "…"

# GPU 训练脚本收尾时回填一个 run
python platform/labkit/cli.py run new --experiment <exp-id> --seed 20260722 --command "…"
python platform/labkit/cli.py run log <run-id> --metric acc=0.612 --ci 0.55 0.67 --unit accuracy
python platform/labkit/cli.py run verdict <run-id> go --reason "…"
```

Python 内直接用也行：
```python
import sys; sys.path.insert(0, "platform")
from labkit.store import Store; from labkit import schema
Store().save(schema.Run(id="run-x", experiment_id="exp-...", ...))
```

## 治理

- 聚合指标（进 Git）写 `registry/runs/<id>.json`；逐样本/大文件写 `runs_local/<id>/`（忽略）。
- `Run.validate` 强制：`tracked=false` 的 artifact 必须落在 `runs_local/`。
- 分析复用 `scripts/compare_material_conditions.py`、`scripts/analyze_material_gate.py`
  的 region 指标与 bootstrap（seed 20260719，统计单元=region），与项目其余部分数值一致。

## 测试

```bash
cd platform && python -m unittest discover -s tests -p "test_*.py"
```
（从 `platform/` 目录内运行，避免 `platform.tests` 与标准库 `platform` 冲突。）
