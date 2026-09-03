import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  CartesianGrid,
  ErrorBar,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/api/client";
import type { MetricWithCI, RetrievalStrategy, RunMetrics } from "@/api/types";
import { Legend, TooltipRow, TooltipShell, axisProps } from "@/components/charts";
import { Card, ErrorBox, Loading, StatTile } from "@/components/ui";
import { cx, num, pct, useAsync } from "@/lib/util";
import { ink, status, strategyColor, strategyLabel, STRATEGY_ORDER } from "@/theme/tokens";
import { useRuns } from "@/lib/runContext";

const BASELINE: RetrievalStrategy = "bm25_hybrid";

/** Sáu chỉ số chất lượng, tất cả trong [0, 1] nên mỗi panel dùng chung một trục. */
const QUALITY: { key: keyof RunMetrics; label: string; note: string; higherIsBetter: boolean }[] = [
  { key: "precision", label: "Precision", note: "TRUE_ALERT đúng / TRUE_ALERT", higherIsBetter: true },
  { key: "recall", label: "Recall", note: "cửa sổ lỗi bắt được", higherIsBetter: true },
  { key: "f1", label: "F1", note: "trung bình điều hoà", higherIsBetter: true },
  { key: "fpr", label: "FPR", note: "báo động giả trên cửa sổ bình thường — thấp là tốt", higherIsBetter: false },
  { key: "hit_at_1", label: "Hit@1", note: "đoán đúng service gốc ở vị trí 1", higherIsBetter: true },
  { key: "hit_at_3", label: "Hit@3", note: "service gốc nằm trong 3 gợi ý đầu", higherIsBetter: true },
];

export default function ExperimentComparison() {
  const { runs } = useRuns();
  const [visible, setVisible] = useState<Set<string>>(new Set(STRATEGY_ORDER));

  const { data, loading, error } = useAsync(
    () => Promise.all(runs.map((r) => api.runMetrics(r.run_id))),
    [runs.map((r) => r.run_id).join(",")],
  );

  const rows = useMemo(
    () =>
      (data ?? [])
        .slice()
        .sort(
          (a, b) =>
            STRATEGY_ORDER.indexOf(a.retrieval_strategy) -
            STRATEGY_ORDER.indexOf(b.retrieval_strategy),
        ),
    [data],
  );

  const shown = rows.filter((r) => visible.has(r.retrieval_strategy));
  const baseline = rows.find((r) => r.retrieval_strategy === BASELINE);

  if (loading) return <Loading label="Đang tải chỉ số của các run…" />;
  if (error) return <ErrorBox message={error} />;

  const best = shown.reduce<RunMetrics | null>(
    (acc, r) => (!acc || r.f1.value > acc.f1.value ? r : acc),
    null,
  );

  function toggle(key: string) {
    setVisible((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        if (next.size > 1) next.delete(key);
      } else next.add(key);
      return next;
    });
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[19px] font-semibold tracking-tight text-ink">
            So sánh năm biến thể retrieval
          </h1>
          <p className="mt-1 text-[11.5px] text-ink-muted">
            Cùng split <code className="font-mono">dev</code>, cùng seed 42, cùng {rows[0]?.n_windows ?? 0} cửa
            sổ. Chỉ đổi chiến lược truy xuất — đó là điều kiện để phép so sánh có nghĩa
            (<code className="font-mono">02-data-and-experiment-protocol.md</code> §3).
          </p>
        </div>
        {/* Bấm để ẩn/hiện biến thể. Màu đi theo biến thể nên ẩn bớt không sơn lại phần còn lại. */}
        <Legend
          items={STRATEGY_ORDER.map((s) => ({
            key: s,
            label: strategyLabel[s],
            color: strategyColor[s],
          }))}
          active={visible}
          onToggle={toggle}
        />
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile
          label="Baseline (Giai đoạn 1)"
          value={baseline ? num(baseline.precision.value, 2) : "—"}
          hint="Precision của bm25_hybrid"
          accent={strategyColor[BASELINE]}
        />
        <StatTile
          label="F1 tốt nhất"
          value={best ? num(best.f1.value, 2) : "—"}
          hint={best ? strategyLabel[best.retrieval_strategy] : ""}
          accent={best ? strategyColor[best.retrieval_strategy] : undefined}
        />
        <StatTile
          label="Hit@1 tốt nhất"
          value={
            shown.length ? num(Math.max(...shown.map((r) => r.hit_at_1.value)), 2) : "—"
          }
          hint="tỉ lệ đoán đúng service gốc ngay lần đầu"
        />
        <StatTile
          label="JSON valid rate"
          value={shown.length ? pct(Math.min(...shown.map((r) => r.json_valid_rate)), 1) : "—"}
          hint="thấp nhất trong các biến thể · mục tiêu ≥ 95%"
          accent={status.good}
        />
      </div>

      {/* Small multiples: mỗi chỉ số một panel, mỗi panel một trục. Không bao giờ
          ghép hai thang đo khác nhau lên cùng một biểu đồ. */}
      <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
        {QUALITY.map((m) => (
          <MetricPanel key={String(m.key)} metric={m} rows={shown} baseline={baseline} />
        ))}
      </div>

      <Card
        title="Độ trễ p95"
        subtitle="Đơn vị mili-giây, khác thang với các chỉ số chất lượng ở trên, nên nó có biểu đồ riêng."
        right={
          <Legend
            items={[
              { key: "r", label: "Retrieval", color: ink.secondary, glyph: "■" },
              { key: "l", label: "LLM judge", color: ink.muted, glyph: "□" },
            ]}
          />
        }
      >
        <LatencyPanel rows={shown} />
      </Card>

      <Card
        title="Bảng chỉ số đầy đủ"
        subtitle="Kèm khoảng tin cậy bootstrap 95%. Đây là bảng dán thẳng vào chương kết quả của luận văn."
      >
        <MetricsTable rows={rows} visible={visible} baseline={baseline} />
      </Card>
    </div>
  );
}

function MetricPanel({
  metric,
  rows,
  baseline,
}: {
  metric: (typeof QUALITY)[number];
  rows: RunMetrics[];
  baseline: RunMetrics | undefined;
}) {
  const data = rows.map((r) => {
    const m = r[metric.key] as MetricWithCI;
    return {
      strategy: r.retrieval_strategy,
      short: shortName(r.retrieval_strategy),
      value: m.value,
      err: [round(m.value - m.ci_low), round(m.ci_high - m.value)] as [number, number],
      ci: m,
    };
  });

  const baseValue = baseline ? (baseline[metric.key] as MetricWithCI).value : null;
  const domainMax = Math.min(1, Math.max(0.2, ...data.map((d) => d.ci.ci_high)) * 1.25);

  return (
    <Card title={metric.label} subtitle={metric.note}>
      <div style={{ height: 30 + rows.length * 30 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 2, right: 46, bottom: 2, left: 4 }}
            barCategoryGap="28%"
          >
            <CartesianGrid horizontal={false} stroke={ink.grid} />
            <XAxis type="number" domain={[0, domainMax]} {...axisProps} tickCount={5} />
            <YAxis
              type="category"
              dataKey="short"
              width={84}
              {...axisProps}
              tick={{ fill: ink.secondary, fontSize: 11 }}
            />
            {baseValue !== null && (
              <ReferenceLine
                x={baseValue}
                stroke={ink.axis}
                strokeDasharray="3 3"
                label={{ value: "baseline", position: "top", fill: ink.muted, fontSize: 9 }}
              />
            )}
            <Tooltip
              cursor={{ fill: "rgb(11 11 11 / 0.04)" }}
              content={({ active, payload }) => {
                const p = payload?.[0]?.payload as (typeof data)[number] | undefined;
                if (!active || !p) return null;
                return (
                  <TooltipShell title={strategyLabel[p.strategy]}>
                    <TooltipRow
                      color={strategyColor[p.strategy]}
                      label={metric.label}
                      value={num(p.value, 3)}
                    />
                    <TooltipRow
                      label="CI 95%"
                      value={`${num(p.ci.ci_low, 3)} – ${num(p.ci.ci_high, 3)}`}
                    />
                  </TooltipShell>
                );
              }}
            />
            <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={14} isAnimationActive={false}>
              {data.map((d) => (
                <Cell
                  key={d.strategy}
                  fill={strategyColor[d.strategy]}
                  // Vòng 2px màu bề mặt giữ khe giữa các thanh sát nhau.
                  stroke={ink.surface}
                  strokeWidth={2}
                />
              ))}
              <ErrorBar dataKey="err" width={5} strokeWidth={1.5} stroke={ink.secondary} direction="x" />
              <LabelList
                dataKey="value"
                position="right"
                formatter={(v) => num(Number(v), 2)}
                style={{ fill: ink.primary, fontSize: 10.5 }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

function LatencyPanel({ rows }: { rows: RunMetrics[] }) {
  const data = rows.map((r) => ({
    short: shortName(r.retrieval_strategy),
    strategy: r.retrieval_strategy,
    retrieval: r.retrieval_latency_p95_ms,
    llm: r.llm_latency_p95_ms,
  }));

  return (
    <div style={{ height: 40 + rows.length * 44 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 2, right: 60, bottom: 2, left: 4 }}
          barCategoryGap="24%"
        >
          <CartesianGrid horizontal={false} stroke={ink.grid} />
          <XAxis type="number" {...axisProps} unit=" ms" />
          <YAxis type="category" dataKey="short" width={96} {...axisProps} tick={{ fill: ink.secondary, fontSize: 11 }} />
          <Tooltip
            cursor={{ fill: "rgb(11 11 11 / 0.04)" }}
            content={({ active, payload }) => {
              const p = payload?.[0]?.payload as (typeof data)[number] | undefined;
              if (!active || !p) return null;
              return (
                <TooltipShell title={strategyLabel[p.strategy]}>
                  <TooltipRow color={ink.secondary} label="Retrieval p95" value={`${p.retrieval} ms`} />
                  <TooltipRow color={ink.muted} glyph="□" label="LLM judge p95" value={`${p.llm} ms`} />
                </TooltipShell>
              );
            }}
          />
          {/* Hai thanh cạnh nhau, cùng đơn vị ms — vẫn chỉ một trục. */}
          <Bar dataKey="retrieval" fill={ink.secondary} barSize={11} radius={[0, 4, 4, 0]} isAnimationActive={false}>
            <LabelList dataKey="retrieval" position="right" formatter={(v) => `${Number(v)} ms`} style={{ fill: ink.primary, fontSize: 10.5 }} />
          </Bar>
          <Bar dataKey="llm" fill={ink.grid} stroke={ink.axis} barSize={11} radius={[0, 4, 4, 0]} isAnimationActive={false}>
            <LabelList dataKey="llm" position="right" formatter={(v) => `${Number(v)} ms`} style={{ fill: ink.secondary, fontSize: 10.5 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function MetricsTable({
  rows,
  visible,
  baseline,
}: {
  rows: RunMetrics[];
  visible: Set<string>;
  baseline: RunMetrics | undefined;
}) {
  const cols = [...QUALITY, { key: "context_precision" as const, label: "Ctx precision", note: "", higherIsBetter: true }];
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-[12px]">
        <thead>
          <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] text-ink-muted">
            <th className="py-2 pr-4 font-medium">Biến thể</th>
            <th className="py-2 pr-3 text-right font-medium">TP/FP/FN</th>
            {cols.map((c) => (
              <th key={String(c.key)} className="py-2 pr-3 text-right font-medium">
                {c.label}
              </th>
            ))}
            <th className="py-2 pr-3 text-right font-medium">Cache</th>
            <th className="py-2 text-right font-medium">JSON valid</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const isBaseline = r.retrieval_strategy === BASELINE;
            return (
              <tr
                key={r.run_id}
                className={cx(
                  "border-b border-[color:var(--color-hairline)] last:border-0",
                  !visible.has(r.retrieval_strategy) && "opacity-40",
                )}
              >
                <td className="py-2 pr-4">
                  <span className="flex items-center gap-2">
                    <span aria-hidden style={{ color: strategyColor[r.retrieval_strategy] }}>
                      ■
                    </span>
                    <span className={cx("text-ink", isBaseline && "font-semibold")}>
                      {strategyLabel[r.retrieval_strategy]}
                    </span>
                  </span>
                </td>
                <td className="py-2 pr-3 text-right tabular-nums text-ink-2">
                  {r.tp}/{r.fp}/{r.fn}
                </td>
                {cols.map((c) => {
                  const m = r[c.key] as MetricWithCI;
                  const base = baseline ? (baseline[c.key] as MetricWithCI).value : null;
                  const delta = base === null || isBaseline ? null : m.value - base;
                  const better = delta === null ? null : c.higherIsBetter ? delta > 0 : delta < 0;
                  return (
                    <td key={String(c.key)} className="py-2 pr-3 text-right tabular-nums">
                      <span className="text-ink">{num(m.value, 3)}</span>
                      <span className="ml-1 text-[10px] text-ink-muted">
                        [{num(m.ci_low, 2)}–{num(m.ci_high, 2)}]
                      </span>
                      {delta !== null && (
                        <span
                          className="ml-1 text-[10px]"
                          style={{ color: better ? "#006300" : status.critical }}
                        >
                          {better ? "▲" : "▼"}
                          {Math.abs(delta).toFixed(2)}
                        </span>
                      )}
                    </td>
                  );
                })}
                <td className="py-2 pr-3 text-right tabular-nums text-ink-2">{pct(r.cache_hit_rate, 0)}</td>
                <td className="py-2 text-right tabular-nums text-ink-2">{pct(r.json_valid_rate, 1)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-3 text-[11px] text-ink-muted">
        Trong ngoặc vuông là khoảng tin cậy bootstrap 95%. Mũi tên là chênh lệch so với baseline
        <span className="mx-1 font-mono">bm25_hybrid</span>; khoảng tin cậy chồng nhau nghĩa là
        chênh lệch chưa có ý nghĩa thống kê, dù mũi tên chỉ hướng nào.
      </p>
    </div>
  );
}

function shortName(s: RetrievalStrategy): string {
  return s === "hybrid_bm25_graph" ? "hybrid" : s === "bm25_hybrid" ? "bm25 (base)" : s;
}

function round(x: number): number {
  return Math.round(x * 1000) / 1000;
}
