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

const QUALITY: { key: keyof RunMetrics; label: string; note: string; higherIsBetter: boolean }[] = [
  { key: "precision", label: "Precision", note: "Confirmed faults / total confirmed alerts", higherIsBetter: true },
  { key: "recall", label: "Recall", note: "Detected faults / 209 injected windows", higherIsBetter: true },
  { key: "f1", label: "F1 Score", note: "Harmonic mean of Precision and Recall", higherIsBetter: true },
  { key: "fpr", label: "False Positive Rate", note: "False alarm rate on normal traffic (lower is better)", higherIsBetter: false },
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

  if (loading) return <Loading label="Loading benchmark metrics…" />;
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
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[20px] font-semibold tracking-tight text-ink">
            Benchmark Performance &amp; Component Ablation
          </h1>
          <p className="mt-1 text-[11.5px] text-ink-muted">
            Validation split ·{" "}
            <strong className="font-semibold text-ink-2">
              {rows[0]?.n_windows.toLocaleString("en-US") ?? 0}
            </strong>{" "}
            telemetry windows ({snapshotMeta.val_fault_windows} injected faults) · Seed 42 · Judge:{" "}
            <code className="font-mono">{snapshotMeta.judge_model}</code>
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

      <div className="grid grid-cols-2 gap-3.5 md:grid-cols-4">
        <StatTile
          label="CTAV F1 Score (Validation)"
          value={ctavRow ? num(ctavRow.f1.value, 3) : "—"}
          hint={
            baseline
              ? `vs. BM25 Baseline ${num(baseline.f1.value, 3)} (Δ=+${num((ctavRow?.f1.value ?? 0) - baseline.f1.value, 3)})`
              : ""
          }
          accent={strategyColor.ctav}
        />
        <StatTile
          label="CTAV False Positive Rate"
          value={ctavRow ? num(ctavRow.fpr.value, 4) : "—"}
          hint={
            baseline
              ? `Reduces false alarms by ${(baseline.fpr.value / Math.max(0.0001, ctavRow?.fpr.value ?? 1)).toFixed(1)}× vs. BM25 Baseline`
              : ""
          }
          accent={status.good}
        />
        <StatTile
          label="Top F1 (Visible Methods)"
          value={best ? num(best.f1.value, 3) : "—"}
          hint={best ? strategyShortLabel[best.retrieval_strategy] : ""}
          accent={best ? strategyColor[best.retrieval_strategy] : undefined}
        />
        <StatTile
          label="Valid JSON Rate"
          value={validRates.length ? pct(Math.min(...validRates), 2) : "—"}
          hint="Structured output adherence across LLM runs"
          accent={status.good}
        />
      </div>

      <div className="grid gap-3.5 md:grid-cols-2 xl:grid-cols-4">
        {QUALITY.map((m) => (
          <MetricPanel key={String(m.key)} metric={m} rows={shown} baseline={baseline} />
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card
          title="F1 Score vs. LLM Call Budget (Validation Split)"
          subtitle="Chronological candidate budget sweep: 120 → 250 → 500 → 1,000 → 2,000 → 4,000 → 5,677 evaluated windows."
          right={
            <Legend
              items={[
                { key: "ctav", label: "CTAV (Proposed)", color: strategyColor.ctav, glyph: "▬" },
                { key: "c1", label: "Topology RAG", color: strategyColor.hybrid_bm25_graph, glyph: "▬" },
                { key: "bm25", label: "BM25 Baseline", color: strategyColor.bm25_hybrid, glyph: "▬" },
                { key: "norag", label: "LLM (No RAG)", color: strategyColor.no_rag, glyph: "▬" },
              ]}
            />
          }
        >
          <BudgetCurvePanel />
        </Card>

        <Card
          title="95th-Percentile Stage Latency (ms)"
          subtitle="Retrieval and LLM judge p95 latency in milliseconds; cached BM25 validation lookups replay in ~6 ms."
          right={
            <Legend
              items={[
                { key: "r", label: "Retrieval p95", color: ink.secondary, glyph: "■" },
                { key: "l", label: "LLM Judge p95", color: ink.muted, glyph: "□" },
              ]}
            />
          }
        >
          <LatencyPanel rows={shown} />
        </Card>
      </div>

      <Card
        title="Validation Split Benchmark Summary (Telemetry Windows)"
        subtitle="Point estimates with 95% bootstrap confidence intervals (1,000 resamples, seed 42). Delta arrows show change relative to BM25 Lexical RAG (Baseline)."
      >
        <MetricsTable rows={rows} visible={visible} baseline={baseline} />
      </Card>

      {USING_FIXTURES && (
        <>
          <Card
            title="Component Ablation Study (Validation Split)"
            subtitle="Single-factor modifications around the calibrated CTAV pipeline. Components without statistically significant F1 or FPR improvement are isolated here."
          >
            <AblationTable />
          </Card>

          <Card
            title={`Holdout Test Split Verification (${h0TestComparison.windows.toLocaleString("en-US")} telemetry windows, ${h0TestComparison.fault_windows} faults)`}
            subtitle={`Hypothesis outcome: ${h0TestComparison.conclusion}. Demonstrates that topology retrieval boosts fault recall while increasing uncalibrated false alarms.`}
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
      <div style={{ height: 34 + rows.length * 32 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 4, right: 48, bottom: 2, left: 4 }}
            barCategoryGap="28%"
          >
            <CartesianGrid horizontal={false} stroke={ink.grid} />
            <XAxis type="number" domain={[0, domainMax]} {...axisProps} tickCount={5} />
            <YAxis
              type="category"
              dataKey="short"
              width={96}
              {...axisProps}
              tick={{ fill: ink.secondary, fontSize: 10.5 }}
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
              cursor={{ fill: "rgb(15 23 42 / 0.04)" }}
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
                      label="95% CI"
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
    <div className="h-[230px]">
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
                <TooltipShell title={`Budget: ${Number(label).toLocaleString("en-US")} calls`}>
                  <TooltipRow color={strategyColor.ctav} label="CTAV (Proposed)" value={`${num(p.ctav, 3)} (${p.ctav_tp} TP / ${p.ctav_fp} FP)`} />
                  <TooltipRow color={strategyColor.hybrid_bm25_graph} label="Topology RAG" value={`${num(p.c1, 3)} (${p.c1_tp} TP / ${p.c1_fp} FP)`} />
                  <TooltipRow color={strategyColor.bm25_hybrid} label="BM25 Baseline" value={`${num(p.bm25, 3)} (${p.bm25_tp} TP / ${p.bm25_fp} FP)`} />
                  <TooltipRow color={strategyColor.no_rag} label="LLM (No RAG)" value={`${num(p.norag, 3)} (${p.norag_tp} TP / ${p.norag_fp} FP)`} />
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
    <div style={{ height: Math.max(230, 32 + rows.length * 42) }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 2, right: 64, bottom: 2, left: 4 }}
          barCategoryGap="24%"
        >
          <CartesianGrid horizontal={false} stroke={ink.grid} />
          <XAxis type="number" {...axisProps} unit=" ms" />
          <YAxis type="category" dataKey="short" width={98} {...axisProps} tick={{ fill: ink.secondary, fontSize: 10.5 }} />
          <Tooltip
            cursor={{ fill: "rgb(15 23 42 / 0.04)" }}
            content={({ active, payload }) => {
              const p = payload?.[0]?.payload as (typeof data)[number] | undefined;
              if (!active || !p) return null;
              return (
                <TooltipShell title={strategyLabel[p.strategy]}>
                  <TooltipRow color={ink.secondary} label="Retrieval p95" value={`${p.retrieval} ms`} />
                  <TooltipRow color={ink.muted} glyph="□" label="LLM Judge p95" value={`${p.llm} ms`} />
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
          <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] font-semibold tracking-wide text-ink-muted uppercase">
            <th className="py-2.5 pr-4">Method</th>
            <th className="py-2.5 pr-3 text-right">TP / FP / FN</th>
            {QUALITY.map((c) => (
              <th key={String(c.key)} className="py-2.5 pr-3 text-right">
                {c.label}
              </th>
            ))}
            <th className="py-2.5 pr-3 text-right">JSON Valid</th>
            <th className="py-2.5 text-right">Est. Cost (USD)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const isBaseline = r.retrieval_strategy === BASELINE;
            const isCtav = r.retrieval_strategy === "ctav";
            return (
              <tr
                key={r.run_id}
                className={cx(
                  "border-b border-[color:var(--color-hairline)] last:border-0",
                  isCtav && "bg-[color:var(--color-plane)]/60",
                  !visible.has(r.retrieval_strategy) && "opacity-40",
                )}
              >
                <td className="py-2.5 pr-4">
                  <span className="flex items-center gap-2">
                    <span aria-hidden style={{ color: strategyColor[r.retrieval_strategy] }}>
                      ■
                    </span>
                    <span className={cx("text-ink", (isBaseline || isCtav) && "font-semibold")}>
                      {strategyLabel[r.retrieval_strategy]}
                    </span>
                  </span>
                </td>
                <td className="py-2.5 pr-3 text-right tabular-nums text-ink-2">
                  {r.tp} / {r.fp} / {r.fn}
                </td>
                {QUALITY.map((c) => {
                  const m = r[c.key] as MetricWithCI;
                  const base = baseline ? (baseline[c.key] as MetricWithCI).value : null;
                  const delta = base === null || isBaseline ? null : m.value - base;
                  const better = delta === null ? null : c.higherIsBetter ? delta > 0 : delta < 0;
                  const digits = c.key === "fpr" ? 4 : 3;
                  return (
                    <td key={String(c.key)} className="py-2.5 pr-3 text-right tabular-nums whitespace-nowrap">
                      <span className="font-medium text-ink">{num(m.value, digits)}</span>
                      <span className="ml-1 text-[10px] text-ink-muted">
                        [{num(m.ci_low, digits)}–{num(m.ci_high, digits)}]
                      </span>
                      {delta !== null && (
                        <span
                          className="ml-1 text-[10px] font-medium"
                          style={{ color: better ? "#065f46" : status.critical }}
                        >
                          {better ? "▲" : "▼"}
                          {Math.abs(delta).toFixed(digits)}
                        </span>
                      )}
                    </td>
                  );
                })}
                <td className="py-2.5 pr-3 text-right tabular-nums text-ink-2">
                  {typeof r.json_valid_rate === "number" ? pct(r.json_valid_rate, 2) : "—"}
                </td>
                <td className="py-2.5 text-right tabular-nums text-ink-2">
                  {typeof r.estimated_cost_usd === "number" ? `$${r.estimated_cost_usd.toFixed(2)}` : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-3 text-[11px] text-ink-muted">
        Bracketed intervals report 95% bootstrap confidence bounds (1,000 resamples, seed 42). Delta arrows indicate performance shifts relative to{" "}
        <span className="font-mono">BM25 Lexical RAG (Baseline)</span>.
      </p>
    </div>
  );
}

function AblationTable() {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-[12px]">
        <thead>
          <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] font-semibold tracking-wide text-ink-muted uppercase">
            <th className="py-2.5 pr-3">Configuration Variant</th>
            <th className="py-2.5 pr-3 text-right">TP / FP</th>
            <th className="py-2.5 pr-3 text-right">Precision</th>
            <th className="py-2.5 pr-3 text-right">Recall</th>
            <th className="py-2.5 pr-3 text-right">F1 [95% CI]</th>
            <th className="py-2.5 pr-3 text-right">FPR</th>
            <th className="py-2.5 pr-3 text-right">ΔF1 [95% CI]</th>
            <th className="py-2.5 pr-3 text-right">Calls / Cost</th>
            <th className="py-2.5">Ablation Finding</th>
          </tr>
        </thead>
        <tbody>
          {ablationRows.map((r) => (
            <tr
              key={r.key}
              className={cx(
                "border-b border-[color:var(--color-hairline)] last:border-0",
                r.key === "ctav" && "bg-[color:var(--color-plane)]/80 font-medium",
              )}
            >
              <td className="py-2.5 pr-3 text-ink">{r.label}</td>
              <td className="py-2.5 pr-3 text-right tabular-nums text-ink-2">
                {r.tp} / {r.fp}
              </td>
              <td className="py-2.5 pr-3 text-right tabular-nums">{num(r.precision, 3)}</td>
              <td className="py-2.5 pr-3 text-right tabular-nums">{num(r.recall, 3)}</td>
              <td className="py-2.5 pr-3 text-right tabular-nums whitespace-nowrap">
                {num(r.f1, 3)}{" "}
                <span className="text-[10px] text-ink-muted">
                  [{num(r.f1_ci95[0], 3)}; {num(r.f1_ci95[1], 3)}]
                </span>
              </td>
              <td className="py-2.5 pr-3 text-right tabular-nums">{num(r.fpr, 4)}</td>
              <td className="py-2.5 pr-3 text-right tabular-nums whitespace-nowrap">
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
              <td className="py-2.5 pr-3 text-right tabular-nums whitespace-nowrap text-ink-2">
                {r.llm_calls.toLocaleString("en-US")} / ${r.estimated_cost_usd.toFixed(2)}
              </td>
              <td className="py-2.5 text-[11px] leading-snug text-ink-2">{r.note}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function H0TestTable() {
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[12px]">
          <thead>
            <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] font-semibold tracking-wide text-ink-muted uppercase">
              <th className="py-2.5 pr-3">Method (Holdout Test)</th>
              <th className="py-2.5 pr-3 text-right">TP / FP</th>
              <th className="py-2.5 pr-3 text-right">Precision</th>
              <th className="py-2.5 pr-3 text-right">Recall</th>
              <th className="py-2.5 pr-3 text-right">F1</th>
              <th className="py-2.5 text-right">FPR</th>
            </tr>
          </thead>
          <tbody>
            {h0TestComparison.methods.map((m) => (
              <tr key={m.key} className="border-b border-[color:var(--color-hairline)] last:border-0">
                <td className="py-2.5 pr-3 font-medium text-ink">{m.label}</td>
                <td className="py-2.5 pr-3 text-right tabular-nums text-ink-2">
                  {m.tp} / {m.fp}
                </td>
                <td className="py-2.5 pr-3 text-right tabular-nums">{num(m.precision, 3)}</td>
                <td className="py-2.5 pr-3 text-right tabular-nums">{num(m.recall, 3)}</td>
                <td className="py-2.5 pr-3 text-right tabular-nums">{num(m.f1, 3)}</td>
                <td className="py-2.5 text-right tabular-nums">{num(m.fpr, 4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div>
        <table className="w-full border-collapse text-[12px]">
          <thead>
            <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] font-semibold tracking-wide text-ink-muted uppercase">
              <th className="py-2.5 pr-3">Statistical Criterion</th>
              <th className="py-2.5 pr-3">Observed Test Result</th>
              <th className="py-2.5 text-right">Status</th>
            </tr>
          </thead>
          <tbody>
            {h0TestComparison.criteria.map((c) => (
              <tr key={c.criterion} className="border-b border-[color:var(--color-hairline)] last:border-0">
                <td className="py-2.5 pr-3 text-ink-2">{c.criterion}</td>
                <td className="py-2.5 pr-3 font-mono text-[11px] text-ink">{c.test_value}</td>
                <td className="py-2.5 text-right">
                  <Pill tone={c.passed ? "good" : "warn"}>{c.passed ? "✓ Passed" : "✗ Failed"}</Pill>
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
