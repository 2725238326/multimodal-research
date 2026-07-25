// Minimal dependency-free SVG charts. Restrained, colorblind-reasonable palette
// that reads in light and dark. Series encode models; partitions get a fixed hue.

import { useState } from "react";

export const SERIES_COLORS = ["#2563eb", "#d97706", "#7c3aed", "#0891b2"];
export const PARTITION_COLORS: Record<string, string> = {
  identifiable: "#059669",
  mixed: "#6b7280",
  under_identified: "#dc2626",
};

const AXIS = "var(--muted)";
const GRID = "var(--grid)";

function pct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

interface Row {
  [k: string]: any;
}

// --------------------------------------------------------------------------
// Grouped bar with CI whiskers (partition accuracy by model)
// --------------------------------------------------------------------------
export function GroupedBarCI({
  rows,
  categoryField,
  seriesField,
  valueField,
  ciLoField,
  ciHiField,
}: {
  rows: Row[];
  categoryField: string;
  seriesField: string;
  valueField: string;
  ciLoField?: string;
  ciHiField?: string;
}) {
  const W = 640;
  const H = 320;
  const pad = { l: 46, r: 16, t: 16, b: 54 };
  const cats = [...new Set(rows.map((r) => r[categoryField]))];
  const series = [...new Set(rows.map((r) => r[seriesField]))];
  const innerW = W - pad.l - pad.r;
  const innerH = H - pad.t - pad.b;
  const maxV = Math.max(
    0.001,
    ...rows.map((r) => (ciHiField ? r[ciHiField] ?? r[valueField] : r[valueField]))
  );
  const yTop = Math.min(1, Math.ceil(maxV * 10) / 10);
  const x = (i: number) => pad.l + (i + 0.5) * (innerW / cats.length);
  const y = (v: number) => pad.t + innerH - (v / yTop) * innerH;
  const groupW = innerW / cats.length;
  const barW = Math.min(46, (groupW * 0.7) / series.length);

  const ticks = Array.from({ length: 6 }, (_, i) => (yTop * i) / 5);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img">
      {ticks.map((t, i) => (
        <g key={i}>
          <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} stroke={GRID} />
          <text x={pad.l - 6} y={y(t) + 4} textAnchor="end" fontSize="11" fill={AXIS}>
            {pct(t)}
          </text>
        </g>
      ))}
      {cats.map((cat, ci) => {
        const cx = x(ci);
        return (
          <g key={String(cat)}>
            {series.map((s, si) => {
              const row = rows.find((r) => r[categoryField] === cat && r[seriesField] === s);
              if (!row) return null;
              const v = row[valueField];
              const bx = cx - (series.length * barW) / 2 + si * barW;
              return (
                <g key={String(s)}>
                  <rect
                    x={bx}
                    y={y(v)}
                    width={barW - 3}
                    height={pad.t + innerH - y(v)}
                    fill={SERIES_COLORS[si % SERIES_COLORS.length]}
                    rx={2}
                  >
                    <title>{`${cat} · ${s}: ${pct(v)}`}</title>
                  </rect>
                  {ciLoField && ciHiField && row[ciLoField] != null && (
                    <line
                      x1={bx + (barW - 3) / 2}
                      x2={bx + (barW - 3) / 2}
                      y1={y(row[ciLoField])}
                      y2={y(row[ciHiField])}
                      stroke="var(--fg)"
                      strokeWidth={1.4}
                      opacity={0.7}
                    />
                  )}
                </g>
              );
            })}
            <text x={cx} y={H - pad.b + 18} textAnchor="middle" fontSize="12" fill="var(--fg)">
              {String(cat)}
            </text>
          </g>
        );
      })}
      <Legend items={series.map((s, i) => ({ label: String(s), color: SERIES_COLORS[i % SERIES_COLORS.length] }))} y={H - 12} x={pad.l} />
    </svg>
  );
}

// --------------------------------------------------------------------------
// Scatter (region entropy vs accuracy), colored by partition, marker by model
// --------------------------------------------------------------------------
export function Scatter({
  rows,
  xField,
  yField,
  colorField,
  seriesField,
}: {
  rows: Row[];
  xField: string;
  yField: string;
  colorField: string;
  seriesField: string;
}) {
  const W = 640;
  const H = 340;
  const pad = { l: 46, r: 16, t: 16, b: 52 };
  const innerW = W - pad.l - pad.r;
  const innerH = H - pad.t - pad.b;
  const xMax = Math.max(0.001, ...rows.map((r) => r[xField]));
  const xTop = Math.ceil(xMax * 2) / 2;
  const x = (v: number) => pad.l + (v / xTop) * innerW;
  const y = (v: number) => pad.t + innerH - v * innerH;
  const series = [...new Set(rows.map((r) => r[seriesField]))];
  const [active, setActive] = useState<string | null>(null);

  const xticks = Array.from({ length: 6 }, (_, i) => (xTop * i) / 5);
  const yticks = Array.from({ length: 6 }, (_, i) => i / 5);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img">
      {yticks.map((t, i) => (
        <g key={`y${i}`}>
          <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} stroke={GRID} />
          <text x={pad.l - 6} y={y(t) + 4} textAnchor="end" fontSize="11" fill={AXIS}>
            {pct(t)}
          </text>
        </g>
      ))}
      {xticks.map((t, i) => (
        <text key={`x${i}`} x={x(t)} y={H - pad.b + 18} textAnchor="middle" fontSize="11" fill={AXIS}>
          {t.toFixed(1)}
        </text>
      ))}
      <text x={(pad.l + W - pad.r) / 2} y={H - 20} textAnchor="middle" fontSize="12" fill="var(--fg)">
        flip entropy (bits) →
      </text>
      {rows.map((r, i) => {
        const s = r[seriesField];
        const dim = active && s !== active;
        const isFirst = s === series[0];
        return (
          <circle
            key={i}
            cx={x(r[xField])}
            cy={y(r[yField])}
            r={isFirst ? 4.5 : 3.5}
            fill={isFirst ? PARTITION_COLORS[r[colorField]] ?? "#888" : "none"}
            stroke={PARTITION_COLORS[r[colorField]] ?? "#888"}
            strokeWidth={isFirst ? 0 : 1.6}
            opacity={dim ? 0.12 : 0.78}
          >
            <title>{`${r.region_id} · ${r[seriesField]} · ${r.material_label}\nentropy ${r[xField]} · acc ${pct(r[yField])}`}</title>
          </circle>
        );
      })}
      <g>
        {["identifiable", "mixed", "under_identified"].map((p, i) => (
          <g key={p} transform={`translate(${pad.l + i * 150}, ${12})`}>
            <circle cx={6} cy={-4} r={5} fill={PARTITION_COLORS[p]} />
            <text x={16} y={0} fontSize="11" fill="var(--fg)">
              {p}
            </text>
          </g>
        ))}
      </g>
      <g>
        {series.map((s, i) => (
          <text
            key={String(s)}
            x={W - pad.r - 8}
            y={pad.t + 14 + i * 16}
            textAnchor="end"
            fontSize="11"
            fill="var(--muted)"
            style={{ cursor: "pointer", fontWeight: active === s ? 700 : 400 }}
            onClick={() => setActive(active === s ? null : String(s))}
          >
            {i === 0 ? "●" : "○"} {String(s)}
          </text>
        ))}
      </g>
    </svg>
  );
}

// --------------------------------------------------------------------------
// Line (selective prediction: coverage vs accuracy)
// --------------------------------------------------------------------------
export function LineChart({
  rows,
  xField,
  yField,
  seriesField,
}: {
  rows: Row[];
  xField: string;
  yField: string;
  seriesField: string;
}) {
  const W = 640;
  const H = 320;
  const pad = { l: 46, r: 16, t: 16, b: 52 };
  const innerW = W - pad.l - pad.r;
  const innerH = H - pad.t - pad.b;
  const series = [...new Set(rows.map((r) => r[seriesField]))];
  const ys = rows.map((r) => r[yField]);
  const yMin = Math.max(0, Math.floor(Math.min(...ys) * 10) / 10);
  const yMax = Math.min(1, Math.ceil(Math.max(...ys) * 10) / 10);
  const x = (v: number) => pad.l + v * innerW;
  const y = (v: number) => pad.t + innerH - ((v - yMin) / (yMax - yMin || 1)) * innerH;
  const yticks = Array.from({ length: 6 }, (_, i) => yMin + ((yMax - yMin) * i) / 5);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img">
      {yticks.map((t, i) => (
        <g key={i}>
          <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} stroke={GRID} />
          <text x={pad.l - 6} y={y(t) + 4} textAnchor="end" fontSize="11" fill={AXIS}>
            {pct(t)}
          </text>
        </g>
      ))}
      {[0, 0.25, 0.5, 0.75, 1].map((t) => (
        <text key={t} x={x(t)} y={H - pad.b + 18} textAnchor="middle" fontSize="11" fill={AXIS}>
          {pct(t)}
        </text>
      ))}
      <text x={(pad.l + W - pad.r) / 2} y={H - 20} textAnchor="middle" fontSize="12" fill="var(--fg)">
        coverage (低翻转熵优先纳入) →
      </text>
      {series.map((s, si) => {
        const pts = rows
          .filter((r) => r[seriesField] === s)
          .sort((a, b) => a[xField] - b[xField]);
        const d = pts.map((p, i) => `${i ? "L" : "M"}${x(p[xField]).toFixed(1)},${y(p[yField]).toFixed(1)}`).join(" ");
        return (
          <path key={String(s)} d={d} fill="none" stroke={SERIES_COLORS[si % SERIES_COLORS.length]} strokeWidth={2} />
        );
      })}
      <Legend
        items={series.map((s, i) => ({ label: String(s), color: SERIES_COLORS[i % SERIES_COLORS.length] }))}
        y={H - 2}
        x={pad.l}
      />
    </svg>
  );
}

function Legend({ items, x, y }: { items: { label: string; color: string }[]; x: number; y: number }) {
  let offset = x;
  return (
    <g>
      {items.map((it) => {
        const el = (
          <g key={it.label} transform={`translate(${offset}, ${y})`}>
            <rect x={0} y={-9} width={11} height={11} rx={2} fill={it.color} />
            <text x={16} y={0} fontSize="11" fill="var(--fg)">
              {it.label}
            </text>
          </g>
        );
        offset += 26 + it.label.length * 7.2;
        return el;
      })}
    </g>
  );
}
