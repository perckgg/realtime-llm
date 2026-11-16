import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  CartesianGrid,
  ErrorBar,
  LabelList,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, USING_FIXTURES } from "@/api/client";
import type { MetricWithCI, RetrievalStrategy, RunMetrics } from "@/api/types";
import { Legend, TooltipRow, TooltipShell, axisProps } from "@/components/charts";
import { Card, ErrorBox, Loading, Pill, StatTile } from "@/components/ui";
import { cx, num, pct, useAsync } from "@/lib/util";
import {
  ablationRows,
  budgetCurve,
  h0TestComparison,
  snapshotMeta,
} from "@/mock/fixtures";
import {
  ink,
  status,
  strategyColor,
  strategyLabel,
  strategyShortLabel,
  STRATEGY_ORDER,
} from "@/theme/tokens";
import { useRuns } from "@/lib/runContext";

const BASELINE: RetrievalStrategy = "bm25_hybrid";

/** Bốn chỉ số chất lượng chính trên tập cửa sổ có telemetry của `val`. */
const QUALITY: { key: keyof RunMetrics; label: string; note: string; higherIsBetter: boolean }[] = [
  { key: "precision", label: "Precision", note: "TRUE_ALERT đúng / TRUE_ALERT", higherIsBetter: true },
  { key: "recall", label: "Recall", note: "cửa sổ lỗi bắt được (/ 209 fault)", higherIsBetter: true },
  { key: "f1", label: "F1", note: "trung bình điều hoà", higherIsBetter: true },
  { key: "fpr", label: "FPR", note: "báo động giả trên normal — thấp là tốt", higherIsBetter: false },
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
  const ctavRow = rows.find((r) => r.retrieval_strategy === "ctav");

  if (loading) return <Loading label="Đang tải chỉ số của các run…" />;
  if (error) return <ErrorBox message={error} />;

  const best = shown.reduce<RunMetrics | null>(
    (acc, r) => (!acc || r.f1.value > acc.f1.value ? r : acc),
    null,
  );
  const validRates = shown
    .map((r) => r.json_valid_rate)
    .filter((v): v is number => typeof v === "number");

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
            So sánh thực nghiệm CTAV vs Baseline (dữ liệu thật)
          </h1>
          <p className="mt-1 text-[11.5px] text-ink-muted">
            Split <code className="font-mono">val</code> · {rows[0]?.n_windows.toLocaleString("vi-VN") ?? 0} cửa sổ có
            telemetry ({snapshotMeta.val_fault_windows} fault) · seed 42 · judge{" "}
            <code className="font-mono">{snapshotMeta.judge_model}</code> (QĐ-026, QĐ-031).
          </p>
        </div>
        <Legend
          items={STRATEGY_ORDER.map((s) => ({
            key: s,
            label: strategyShortLabel[s],
            color: strategyColor[s],
          }))}
          active={visible}
          onToggle={toggle}
        />
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile
          label="CTAV F1 (val)"
          value={ctavRow ? num(ctavRow.f1.value, 3) : "—"}
          hint={
            baseline
              ? `vs BM25 ${num(baseline.f1.value, 3)} (Δ=+${num((ctavRow?.f1.value ?? 0) - baseline.f1.value, 3)})`
              : ""
          }
          accent={strategyColor.ctav}
        />
        <StatTile
          label="FPR CTAV (val)"
          value={ctavRow ? num(ctavRow.fpr.value, 4) : "—"}
          hint={baseline ? `giảm ${(baseline.fpr.value / Math.max(0.0001, ctavRow?.fpr.value ?? 1)).toFixed(1)}× so với BM25` : ""}
          accent={status.good}
        />
        <StatTile
          label="F1 tốt nhất (đang chọn)"
          value={best ? num(best.f1.value, 3) : "—"}
          hint={best ? strategyShortLabel[best.retrieval_strategy] : ""}
          accent={best ? strategyColor[best.retrieval_strategy] : undefined}
        />
        <StatTile
          label="JSON valid rate"
          value={validRates.length ? pct(Math.min(...validRates), 2) : "—"}
          hint="trên các phương pháp dùng LLM (M9 bổ sung Hit@k)"
          accent={status.good}
        />
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {QUALITY.map((m) => (
          <MetricPanel key={String(m.key)} metric={m} rows={shown} baseline={baseline} />
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card
          title="Đường cong F1 theo ngân sách gọi LLM (H4, val)"
          subtitle="Thứ tự thời gian: 120 → 250 → 500 → 1.000 → 2.000 → 4.000 → đủ 5.677 lần gọi (QĐ-031)."
          right={
            <Legend
              items={[
                { key: "ctav", label: "CTAV", color: strategyColor.ctav, glyph: "▬" },
                { key: "c1", label: "C1 topo", color: strategyColor.hybrid_bm25_graph, glyph: "▬" },
                { key: "bm25", label: "BM25", color: strategyColor.bm25_hybrid, glyph: "▬" },
                { key: "norag", label: "Không RAG", color: strategyColor.no_rag, glyph: "▬" },
              ]}
            />
          }
        >
          <BudgetCurvePanel />
        </Card>

        <Card
          title="Độ trễ p95 (tách thang đo ms)"
          subtitle="Retrieval p95 và LLM judge p95 tính bằng mili-giây; BM25 val trúng cache từ _v1/_v2 nên LLM p95 thấp (5,6 ms)."
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
      </div>

      <Card
        title="Bảng chỉ số đầy đủ trên val (cửa sổ có telemetry)"
        subtitle="Kèm khoảng tin cậy bootstrap 95% (1.000 mẫu, seed 42). Hit@1/Hit@3 sẽ bổ sung ở M9 và Context precision ở V35."
      >
        <MetricsTable rows={rows} visible={visible} baseline={baseline} />
      </Card>

      {USING_FIXTURES && (
        <>
          <Card
            title="Bảng Ablation H3 & C5 Rescue trên val (QĐ-031, QĐ-033)"
            subtitle="Một-thay-đổi-một-lần quanh CTAV chốt (C1 + θ 0,80 + C3 dev p90). Các thành phần C2, C4 và C5 không đóng góp có ý nghĩa nên được tách làm ablation."
          >
            <AblationTable />
          </Card>

          <Card
            title={`Kết quả G-test H0 trên tập test (${h0TestComparison.windows.toLocaleString("vi-VN")} cửa sổ telemetry, ${h0TestComparison.fault_windows} fault — QĐ-037)`}
            subtitle={`Kết luận đăng ký trước (commit be2b985): ${h0TestComparison.conclusion}. Các phương pháp CTAV, Không-RAG, H3, H4 trên test đang chạy tiếp ở M8.`}
          >
            <H0TestTable />
          </Card>
        </>
      )}
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
      short: strategyShortLabel[r.retrieval_strategy],
      value: m.value,
      err: [round(Math.max(0, m.value - m.ci_low)), round(Math.max(0, m.ci_high - m.value))] as [
        number,
        number,
      ],
      ci: m,
    };
  });

  const baseValue = baseline ? (baseline[metric.key] as MetricWithCI).value : null;
  const domainMax = Math.min(1, Math.max(0.15, ...data.map((d) => d.ci.ci_high)) * 1.25);

  return (
    <Card title={metric.label} subtitle={metric.note}>
      <div style={{ height: 30 + rows.length * 30 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 2, right: 48, bottom: 2, left: 4 }}
            barCategoryGap="28%"
          >
            <CartesianGrid horizontal={false} stroke={ink.grid} />
            <XAxis type="number" domain={[0, domainMax]} {...axisProps} tickCount={5} />
            <YAxis
              type="category"
              dataKey="short"
              width={82}
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
                      value={num(p.value, metric.key === "fpr" ? 4 : 3)}
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
                  stroke={ink.surface}
                  strokeWidth={2}
                />
              ))}
              <ErrorBar dataKey="err" width={5} strokeWidth={1.5} stroke={ink.secondary} direction="x" />
              <LabelList
                dataKey="value"
                position="right"
                formatter={(v) => num(Number(v), metric.key === "fpr" ? 4 : 3)}
                style={{ fill: ink.primary, fontSize: 10.5 }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

function BudgetCurvePanel() {
  const data = budgetCurve.map((p) => ({ ...p, label: String(p.budget) }));
  return (
    <div className="h-[220px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: -12 }}>
          <CartesianGrid vertical={false} stroke={ink.grid} />
          <XAxis dataKey="label" {...axisProps} />
          <YAxis {...axisProps} domain={[0, 0.25]} width={44} />
          <Tooltip
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              const p = payload[0]?.payload as (typeof data)[number];
              return (
                <TooltipShell title={`Ngân sách ${label} lần gọi`}>
                  <TooltipRow color={strategyColor.ctav} label="CTAV" value={`${num(p.ctav, 3)} (${p.ctav_tp}/${p.ctav_fp})`} />
                  <TooltipRow color={strategyColor.hybrid_bm25_graph} label="C1 topo" value={`${num(p.c1, 3)} (${p.c1_tp}/${p.c1_fp})`} />
                  <TooltipRow color={strategyColor.bm25_hybrid} label="BM25" value={`${num(p.bm25, 3)} (${p.bm25_tp}/${p.bm25_fp})`} />
                  <TooltipRow color={strategyColor.no_rag} label="Không RAG" value={`${num(p.norag, 3)} (${p.norag_tp}/${p.norag_fp})`} />
                </TooltipShell>
              );
            }}
          />
          <Line type="monotone" dataKey="ctav" stroke={strategyColor.ctav} strokeWidth={2.5} dot={{ r: 3 }} isAnimationActive={false} />
          <Line type="monotone" dataKey="c1" stroke={strategyColor.hybrid_bm25_graph} strokeWidth={1.8} dot={{ r: 2.5 }} isAnimationActive={false} />
          <Line type="monotone" dataKey="bm25" stroke={strategyColor.bm25_hybrid} strokeWidth={1.8} dot={{ r: 2.5 }} isAnimationActive={false} />
          <Line type="monotone" dataKey="norag" stroke={strategyColor.no_rag} strokeWidth={1.8} strokeDasharray="4 3" dot={{ r: 2.5 }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function LatencyPanel({ rows }: { rows: RunMetrics[] }) {
  const data = rows.map((r) => ({
    short: strategyShortLabel[r.retrieval_strategy],
    strategy: r.retrieval_strategy,
    retrieval: Math.round(r.retrieval_latency_p95_ms),
    llm: Math.round(r.llm_latency_p95_ms),
  }));

  return (
    <div style={{ height: Math.max(220, 30 + rows.length * 40) }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 2, right: 64, bottom: 2, left: 4 }}
          barCategoryGap="24%"
        >
          <CartesianGrid horizontal={false} stroke={ink.grid} />
          <XAxis type="number" {...axisProps} unit=" ms" />
          <YAxis type="category" dataKey="short" width={88} {...axisProps} tick={{ fill: ink.secondary, fontSize: 11 }} />
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
          <Bar dataKey="retrieval" fill={ink.secondary} barSize={10} radius={[0, 4, 4, 0]} isAnimationActive={false}>
            <LabelList dataKey="retrieval" position="right" formatter={(v) => `${Number(v)} ms`} style={{ fill: ink.primary, fontSize: 10 }} />
          </Bar>
          <Bar dataKey="llm" fill={ink.grid} stroke={ink.axis} barSize={10} radius={[0, 4, 4, 0]} isAnimationActive={false}>
            <LabelList dataKey="llm" position="right" formatter={(v) => `${Number(v)} ms`} style={{ fill: ink.secondary, fontSize: 10 }} />
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
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-[12px]">
        <thead>
          <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] text-ink-muted">
            <th className="py-2 pr-4 font-medium">Phương pháp</th>
            <th className="py-2 pr-3 text-right font-medium">TP/FP/FN</th>
            {QUALITY.map((c) => (
              <th key={String(c.key)} className="py-2 pr-3 text-right font-medium">
                {c.label}
              </th>
            ))}
            <th className="py-2 pr-3 text-right font-medium">JSON valid</th>
            <th className="py-2 text-right font-medium">Chi phí (token)</th>
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
                    <span className={cx("text-ink", (isBaseline || r.retrieval_strategy === "ctav") && "font-semibold")}>
                      {strategyLabel[r.retrieval_strategy]}
                    </span>
                  </span>
                </td>
                <td className="py-2 pr-3 text-right tabular-nums text-ink-2">
                  {r.tp}/{r.fp}/{r.fn}
                </td>
                {QUALITY.map((c) => {
                  const m = r[c.key] as MetricWithCI;
                  const base = baseline ? (baseline[c.key] as MetricWithCI).value : null;
                  const delta = base === null || isBaseline ? null : m.value - base;
                  const better = delta === null ? null : c.higherIsBetter ? delta > 0 : delta < 0;
                  const digits = c.key === "fpr" ? 4 : 3;
                  return (
                    <td key={String(c.key)} className="py-2 pr-3 text-right tabular-nums">
                      <span className="text-ink">{num(m.value, digits)}</span>
                      <span className="ml-1 text-[10px] text-ink-muted">
                        [{num(m.ci_low, digits)}–{num(m.ci_high, digits)}]
                      </span>
                      {delta !== null && (
                        <span
                          className="ml-1 text-[10px]"
                          style={{ color: better ? "#006300" : status.critical }}
                        >
                          {better ? "▲" : "▼"}
                          {Math.abs(delta).toFixed(digits)}
                        </span>
                      )}
                    </td>
                  );
                })}
                <td className="py-2 pr-3 text-right tabular-nums text-ink-2">
                  {typeof r.json_valid_rate === "number" ? pct(r.json_valid_rate, 2) : "—"}
                </td>
                <td className="py-2 text-right tabular-nums text-ink-2">
                  {typeof r.estimated_cost_usd === "number" ? `$${r.estimated_cost_usd.toFixed(2)}` : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-3 text-[11px] text-ink-muted">
        Trong ngoặc vuông là khoảng tin cậy bootstrap 95% (1.000 mẫu, seed 42). Mũi tên so sánh với baseline{" "}
        <span className="font-mono">bm25_hybrid</span>. Hit@1/Hit@3 thuộc M9; Context precision 50 cửa sổ thuộc V35.
      </p>
    </div>
  );
}

function AblationTable() {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-[12px]">
        <thead>
          <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] text-ink-muted">
            <th className="py-2 pr-3 font-medium">Biến thể</th>
            <th className="py-2 pr-3 text-right font-medium">TP / FP</th>
            <th className="py-2 pr-3 text-right font-medium">Precision</th>
            <th className="py-2 pr-3 text-right font-medium">Recall</th>
            <th className="py-2 pr-3 text-right font-medium">F1 [CI95]</th>
            <th className="py-2 pr-3 text-right font-medium">FPR</th>
            <th className="py-2 pr-3 text-right font-medium">ΔF1 [CI95]</th>
            <th className="py-2 pr-3 text-right font-medium">Lần gọi / USD</th>
            <th className="py-2 font-medium">Kết luận H3</th>
          </tr>
        </thead>
        <tbody>
          {ablationRows.map((r) => (
            <tr
              key={r.key}
              className={cx(
                "border-b border-[color:var(--color-hairline)] last:border-0",
                r.key === "ctav" && "bg-[color:var(--color-plane)] font-medium",
              )}
            >
              <td className="py-2 pr-3 text-ink">{r.label}</td>
              <td className="py-2 pr-3 text-right tabular-nums text-ink-2">
                {r.tp} / {r.fp}
              </td>
              <td className="py-2 pr-3 text-right tabular-nums">{num(r.precision, 3)}</td>
              <td className="py-2 pr-3 text-right tabular-nums">{num(r.recall, 3)}</td>
              <td className="py-2 pr-3 text-right tabular-nums">
                {num(r.f1, 3)}{" "}
                <span className="text-[10px] text-ink-muted">
                  [{num(r.f1_ci95[0], 3)}; {num(r.f1_ci95[1], 3)}]
                </span>
              </td>
              <td className="py-2 pr-3 text-right tabular-nums">{num(r.fpr, 4)}</td>
              <td className="py-2 pr-3 text-right tabular-nums">
                {r.delta_f1 !== null && r.delta_f1_ci95 ? (
                  <>
                    {r.delta_f1 >= 0 ? "+" : ""}
                    {num(r.delta_f1, 3)}{" "}
                    <span className="text-[10px] text-ink-muted">
                      [{num(r.delta_f1_ci95[0], 3)}; {num(r.delta_f1_ci95[1], 3)}]
                    </span>
                  </>
                ) : (
                  "—"
                )}
              </td>
              <td className="py-2 pr-3 text-right tabular-nums text-ink-2">
                {r.llm_calls.toLocaleString("vi-VN")} / ${r.estimated_cost_usd.toFixed(2)}
              </td>
              <td className="py-2 text-[11px] text-ink-2">{r.note}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function H0TestTable() {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[12px]">
          <thead>
            <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] text-ink-muted">
              <th className="py-2 pr-3 font-medium">Phương pháp (test)</th>
              <th className="py-2 pr-3 text-right font-medium">TP / FP</th>
              <th className="py-2 pr-3 text-right font-medium">Precision</th>
              <th className="py-2 pr-3 text-right font-medium">Recall</th>
              <th className="py-2 pr-3 text-right font-medium">F1</th>
              <th className="py-2 text-right font-medium">FPR</th>
            </tr>
          </thead>
          <tbody>
            {h0TestComparison.methods.map((m) => (
              <tr key={m.key} className="border-b border-[color:var(--color-hairline)] last:border-0">
                <td className="py-2 pr-3 font-medium text-ink">{m.label}</td>
                <td className="py-2 pr-3 text-right tabular-nums text-ink-2">
                  {m.tp} / {m.fp}
                </td>
                <td className="py-2 pr-3 text-right tabular-nums">{num(m.precision, 3)}</td>
                <td className="py-2 pr-3 text-right tabular-nums">{num(m.recall, 3)}</td>
                <td className="py-2 pr-3 text-right tabular-nums">{num(m.f1, 3)}</td>
                <td className="py-2 text-right tabular-nums">{num(m.fpr, 4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div>
        <table className="w-full border-collapse text-[12px]">
          <thead>
            <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] text-ink-muted">
              <th className="py-2 pr-3 font-medium">Vế tiêu chí H0 đã đăng ký</th>
              <th className="py-2 pr-3 font-medium">Giá trị trên test</th>
              <th className="py-2 text-right font-medium">Đạt</th>
            </tr>
          </thead>
          <tbody>
            {h0TestComparison.criteria.map((c) => (
              <tr key={c.criterion} className="border-b border-[color:var(--color-hairline)] last:border-0">
                <td className="py-2 pr-3 text-ink-2">{c.criterion}</td>
                <td className="py-2 pr-3 font-mono text-[11px] text-ink">{c.test_value}</td>
                <td className="py-2 text-right">
                  <Pill tone={c.passed ? "good" : "warn"}>{c.passed ? "✓ Đạt" : "✗ Không đạt"}</Pill>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function round(x: number): number {
  return Math.round(x * 1000) / 1000;
}
