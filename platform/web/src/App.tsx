import { useEffect, useState } from "react";
import {
  Registry,
  RegistryResponse,
  fetchRegistry,
  Idea,
  ChartSpec,
} from "./types";
import { GroupedBarCI, Scatter, LineChart } from "./charts";

// ------------------------------------------------------------------ routing
function useHash(): string {
  const [hash, setHash] = useState(window.location.hash || "#/");
  useEffect(() => {
    const on = () => setHash(window.location.hash || "#/");
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return hash;
}
const go = (h: string) => (window.location.hash = h);

const SLOTS: { key: Idea["slot"]; label: string }[] = [
  { key: "mainline", label: "主线 Mainline" },
  { key: "adjacent", label: "邻接 Adjacent" },
  { key: "high_risk", label: "高风险 High-risk" },
  { key: "pool", label: "候选池 Pool" },
];

// ------------------------------------------------------------------ app
export default function App() {
  const [reg, setReg] = useState<RegistryResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const hash = useHash();

  useEffect(() => {
    fetchRegistry().then(setReg).catch((e) => setErr(String(e)));
  }, []);

  if (err) return <div className="main"><h2>无法连接后端</h2><p className="lede">{err}</p><p className="muted">先启动：<span className="pill">python platform/labkit/server.py</span></p></div>;
  if (!reg) return <div className="main muted">加载中…</div>;

  const data = reg.data;
  const [, path, id] = hash.replace(/^#/, "").split("/");

  let view;
  if (path === "ideas") view = <IdeaBoard data={data} />;
  else if (path === "experiment") view = <ExperimentDetail data={data} id={id} />;
  else if (path === "run") view = <RunDetail data={data} id={id} />;
  else if (path === "datasets") view = <DatasetList data={data} />;
  else view = <Home data={data} problems={reg.problems} />;

  return (
    <div className="app">
      <Sidebar data={data} hash={hash} />
      <div className="main">{view}</div>
    </div>
  );
}

function Sidebar({ data, hash }: { data: Registry; hash: string }) {
  const is = (p: string) => (hash === p ? "active" : "");
  return (
    <div className="sidebar">
      <h1>labkit</h1>
      <div className="tag">研究实验平台 · v0.1</div>
      <div className="nav">
        <a className={is("#/")} onClick={() => go("#/")}>概览 Home</a>
        <a className={is("#/ideas")} onClick={() => go("#/ideas")}>Idea 看板</a>
        <a className={is("#/datasets")} onClick={() => go("#/datasets")}>数据集</a>
        <div className="section">实验 Experiments</div>
        {data.experiments.map((e) => (
          <a key={e.id} className={hash === `#/experiment/${e.id}` ? "active" : ""} onClick={() => go(`#/experiment/${e.id}`)}>
            {e.title}
          </a>
        ))}
        <div className="section">Runs</div>
        {data.runs.map((r) => (
          <a key={r.id} className={hash === `#/run/${r.id}` ? "active" : ""} onClick={() => go(`#/run/${r.id}`)}>
            <span className={`badge ${r.verdict}`}>{r.verdict}</span> {r.id.replace(/^run-/, "")}
          </a>
        ))}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ home
function Home({ data, problems }: { data: Registry; problems: string[] }) {
  const mother = data.ideas.find((i) => i.slot === "mainline" && i.links.length === 0);
  const counts = SLOTS.map((s) => ({ ...s, n: data.ideas.filter((i) => i.slot === s.key).length }));
  return (
    <>
      <div className="crumbs">概览</div>
      <h2>识别度感知的语义—测量分工</h2>
      {mother && <p className="lede">{mother.thesis}</p>}
      <div className="grid cols-4">
        {counts.map((c) => (
          <div className="card stat" key={c.key}>
            <div className="n">{c.n}</div>
            <div className="l">{c.label}</div>
          </div>
        ))}
      </div>
      <div className="grid cols-4">
        <Stat n={data.experiments.length} l="实验" />
        <Stat n={data.runs.length} l="Runs" />
        <Stat n={data.runs.filter((r) => r.verdict === "go").length} l="Go 结论" />
        <Stat n={data.datasets.length} l="数据集" />
      </div>
      {problems.length > 0 && (
        <div className="card">
          <h3>Registry 校验问题</h3>
          {problems.map((p, i) => <div className="problem" key={i}>{p}</div>)}
        </div>
      )}
      <h3>最新 Run</h3>
      {data.runs.map((r) => (
        <div className="card" key={r.id}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div><span className={`badge ${r.verdict}`}>{r.verdict.toUpperCase()}</span> <b>{r.title}</b></div>
            <a onClick={() => go(`#/run/${r.id}`)}>查看 →</a>
          </div>
          {r.verdict_reason && <p className="muted" style={{ marginBottom: 0 }}>{r.verdict_reason}</p>}
        </div>
      ))}
    </>
  );
}
const Stat = ({ n, l }: { n: number; l: string }) => (
  <div className="card stat"><div className="n">{n}</div><div className="l">{l}</div></div>
);

// ------------------------------------------------------------------ idea board
function IdeaBoard({ data }: { data: Registry }) {
  return (
    <>
      <div className="crumbs">Idea 看板</div>
      <h2>研究 idea 看板</h2>
      <p className="lede">按 WIP 槽位分列（一主线 / 两邻接 / 一高风险 / 候选池）。卡片色条=状态。</p>
      <div className="board">
        {SLOTS.map((slot) => (
          <div className="col" key={slot.key}>
            <h4>{slot.label}</h4>
            {data.ideas
              .filter((i) => i.slot === slot.key)
              .map((idea) => (
                <IdeaCard key={idea.id} idea={idea} data={data} />
              ))}
          </div>
        ))}
      </div>
    </>
  );
}

const STATUS_COLOR: Record<string, string> = {
  active: "#2563eb", proposed: "#6b7280", blocked: "#d97706", parked: "#d97706", done: "#059669",
};
function IdeaCard({ idea, data }: { idea: Idea; data: Registry }) {
  const exps = data.experiments.filter((e) => e.idea_id === idea.id || idea.experiment_ids.includes(e.id));
  return (
    <div className="card idea-card" style={{ borderLeftColor: STATUS_COLOR[idea.status] ?? "#888" }}>
      <div className="title">{idea.title}</div>
      <div className="thesis">{idea.thesis}</div>
      <div style={{ marginTop: 8, display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <span className={`badge ${idea.status}`}>{idea.status}</span>
        {idea.design_patterns.map((p) => <span className="pill" key={p}>{p}</span>)}
      </div>
      {exps.map((e) => (
        <div key={e.id} style={{ marginTop: 8 }}>
          <a onClick={() => go(`#/experiment/${e.id}`)}>→ {e.title}</a>
        </div>
      ))}
    </div>
  );
}

// ------------------------------------------------------------------ experiment
function ExperimentDetail({ data, id }: { data: Registry; id: string }) {
  const exp = data.experiments.find((e) => e.id === id);
  if (!exp) return <p>未找到实验 {id}</p>;
  const runs = data.runs.filter((r) => r.experiment_id === exp.id);
  const idea = data.ideas.find((i) => i.id === exp.idea_id);
  return (
    <>
      <div className="crumbs">
        <a onClick={() => go("#/ideas")}>Idea 看板</a> / 实验
      </div>
      <h2>{exp.title}</h2>
      <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
        <span className={`badge ${exp.track}`}>{exp.track}</span>
        <span className={`badge ${exp.status}`}>{exp.status}</span>
        {idea && <a onClick={() => go("#/ideas")} className="muted">← {idea.title}</a>}
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>可证伪合同 (RP-01)</h3>
        <div className="kv">
          <div className="k">研究问题</div><div>{exp.question}</div>
          <div className="k">可证伪假设</div><div>{exp.hypothesis}</div>
          <div className="k">主指标</div><div>{exp.primary_metric || "—"}</div>
          <div className="k">保护指标</div><div>{exp.guardrail_metrics.join("; ") || "—"}</div>
          <div className="k">统计单元 / bootstrap</div><div>{exp.statistical_unit} / {exp.bootstrap_unit}</div>
          <div className="k" style={{ color: "#059669" }}>Go 阈值</div><div>{exp.go_threshold}</div>
          <div className="k" style={{ color: "#dc2626" }}>No-Go 阈值</div><div>{exp.no_go_threshold}</div>
          {exp.plan_md_path && <><div className="k">计划</div><div className="mono">{exp.plan_md_path}</div></>}
          {exp.config_path && <><div className="k">配置</div><div className="mono">{exp.config_path}</div></>}
        </div>
      </div>

      {exp.conditions.length > 0 && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>条件 (RP-04 单机制增量)</h3>
          <table>
            <thead><tr><th>条件</th><th>目的</th><th>改变的变量</th></tr></thead>
            <tbody>
              {exp.conditions.map((c) => (
                <tr key={c.name}><td className="mono">{c.name}</td><td>{c.purpose}</td><td>{c.changed_var}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(exp.controls.correct || exp.controls.shuffled) && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>反事实控制四件套 (RP-05)</h3>
          <div className="kv">
            <div className="k">正确相关</div><div>{exp.controls.correct || "—"}</div>
            <div className="k">错误/反向</div><div>{exp.controls.wrong || "—"}</div>
            <div className="k">打乱</div><div>{exp.controls.shuffled || "—"}</div>
            <div className="k">等信息无关</div><div>{exp.controls.irrelevant || "—"}</div>
            <div className="k">等参数/等算力</div><div>{exp.controls.equal_param || "—"}</div>
          </div>
        </div>
      )}

      <h3>Runs</h3>
      {runs.length === 0 && <p className="muted">尚无 run。</p>}
      {runs.map((r) => (
        <div className="card" key={r.id}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <div><span className={`badge ${r.verdict}`}>{r.verdict.toUpperCase()}</span> <b>{r.title}</b></div>
            <a onClick={() => go(`#/run/${r.id}`)}>查看 →</a>
          </div>
        </div>
      ))}
    </>
  );
}

// ------------------------------------------------------------------ run
function RunDetail({ data, id }: { data: Registry; id: string }) {
  const run = data.runs.find((r) => r.id === id);
  if (!run) return <p>未找到 run {id}</p>;
  const exp = data.experiments.find((e) => e.id === run.experiment_id);
  return (
    <>
      <div className="crumbs">
        {exp && <><a onClick={() => go(`#/experiment/${exp.id}`)}>{exp.title}</a> / </>}Run
      </div>
      <h2>{run.title || run.id}</h2>
      <div style={{ marginBottom: 14 }}>
        <span className={`badge ${run.verdict}`}>{run.verdict.toUpperCase()}</span>
      </div>
      {run.verdict_reason && <div className="reason">{run.verdict_reason}</div>}

      <h3>指标</h3>
      <div className="card">
        <table>
          <thead><tr><th>指标</th><th className="num">值</th><th className="num">95% CI</th><th>单位</th></tr></thead>
          <tbody>
            {Object.entries(run.metrics).map(([k, m]) => (
              <tr key={k}>
                <td className="mono">{k}</td>
                <td className="num">{fmt(m.value, m.unit)}</td>
                <td className="num">{m.ci95 ? `[${fmt(m.ci95[0], m.unit)}, ${fmt(m.ci95[1], m.unit)}]` : "—"}</td>
                <td className="muted">{m.unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {run.charts.map((c) => (
        <ChartBlock key={c.id} spec={c} rows={run.datasets[c.dataset] || []} />
      ))}

      <h3>可复现胶囊 (RP-12)</h3>
      <div className="card">
        <div className="kv">
          <div className="k">命令</div><div className="mono">{run.command || "—"}</div>
          <div className="k">seed</div><div className="mono">{run.seed ?? "—"}</div>
          <div className="k">commit</div><div className="mono">{run.commit || "—"}</div>
          <div className="k">device</div><div>{run.device || "—"}</div>
        </div>
        {run.artifacts.length > 0 && (
          <>
            <h4 className="muted" style={{ marginBottom: 6 }}>Artifacts</h4>
            {run.artifacts.map((a) => (
              <div key={a.name} className="mono">
                {a.tracked ? "📦" : "🔒"} {a.path} <span className="muted">{a.tracked ? "(tracked)" : "(runs_local, ignored)"}</span>
              </div>
            ))}
          </>
        )}
        {run.notes && <p className="muted" style={{ marginTop: 12, marginBottom: 0 }}>{run.notes}</p>}
      </div>
    </>
  );
}

function ChartBlock({ spec, rows }: { spec: ChartSpec; rows: any[] }) {
  if (rows.length === 0) return null;
  let chart;
  if (spec.type === "grouped_bar")
    chart = <GroupedBarCI rows={rows} categoryField={spec.encodings.x.field} seriesField={spec.encodings.series.field} valueField={spec.encodings.y.field} ciLoField={spec.encodings.ciLo?.field} ciHiField={spec.encodings.ciHi?.field} />;
  else if (spec.type === "scatter")
    chart = <Scatter rows={rows} xField={spec.encodings.x.field} yField={spec.encodings.y.field} colorField={spec.encodings.color.field} seriesField={spec.encodings.series.field} />;
  else if (spec.type === "line")
    chart = <LineChart rows={rows} xField={spec.encodings.x.field} yField={spec.encodings.y.field} seriesField={spec.encodings.series.field} />;
  else chart = <div className="muted">unsupported chart: {spec.type}</div>;
  return (
    <div className="card">
      <div className="chart-title">{spec.title}</div>
      {spec.subtitle && <div className="chart-sub">{spec.subtitle}</div>}
      {chart}
    </div>
  );
}

// ------------------------------------------------------------------ datasets
function DatasetList({ data }: { data: Registry }) {
  return (
    <>
      <div className="crumbs">数据集</div>
      <h2>数据集</h2>
      {data.datasets.map((d) => (
        <div className="card" key={d.id}>
          <b>{d.name}</b> <span className="pill">{d.version}</span>
          <div className="kv" style={{ marginTop: 10 }}>
            <div className="k">许可状态</div><div><span className={`badge ${d.license_status === "needs_verification" ? "blocked" : "go"}`}>{d.license_status}</span></div>
            <div className="k">独立单元</div><div>{d.independent_units.scenes} 场景 / {d.independent_units.regions} 区域 / {d.independent_units.samples} 样本</div>
            <div className="k">manifest hash</div><div className="mono" style={{ wordBreak: "break-all" }}>{d.manifest_hash}</div>
            <div className="k">路径</div><div className="mono">{d.path}</div>
          </div>
          {d.notes && <p className="muted" style={{ marginBottom: 0 }}>{d.notes}</p>}
        </div>
      ))}
    </>
  );
}

// ------------------------------------------------------------------ util
function fmt(v: number, unit: string): string {
  if (unit === "accuracy" || unit === "accuracy_delta") return `${(v * 100).toFixed(1)}%`;
  return v.toFixed(3);
}
