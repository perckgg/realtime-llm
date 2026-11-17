import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ErrorBar,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import rawExperimentTable from "@/data/experiment_table.json";
import { Legend, TooltipRow, TooltipShell, axisProps } from "@/components/charts";
import { Card, Empty, StatTile } from "@/components/ui";
import { cx, num } from "@/lib/util";
import { ink, series, status } from "@/theme/tokens";

type SplitKey = "test" | "val";
type CiPair = [number, number];

interface MethodRow {
  key: string;
  label: string;
  tp: number;
  fp: number;
  fn: number;
  tn: number;
  precision: number;
  precision_ci95: CiPair;
  recall: number;
  recall_ci95: CiPair;
  f1: number;
  f1_ci95: CiPair;
  fpr: number;
  fpr_ci95: CiPair;
  llm_calls: number | null;
  estimated_cost_usd: number | null;
}

interface PairRow {
  label: string;
  d_precision: number;
  d_precision_ci95: CiPair;
  d_recall: number;
  d_recall_ci95: CiPair;
  d_f1: number;
  d_f1_ci95: CiPair;
  d_fpr: number;
  d_fpr_ci95: CiPair;
  mcnemar_all_p: number;
  mcnemar_fault_p: number;
  mcnemar_normal_p: number;
}

interface HypothesisClause {
  clause: string;
  met: boolean | null;
  detail: string;
}

interface HypothesisRow {
  id: string;
  title: string;
  split: string;
  status: string;
  status_label: string;
  summary: string;
  note?: string;
  clauses: HypothesisClause[];
}

interface BudgetRow {
  budget: string;
  budget_calls: number | null;
  ctav: number;
  ctav_ci95: CiPair;
  bm25: number;
  bm25_ci95: CiPair;
  c1: number;
  c1_ci95: CiPair;
  norag: number;
  norag_ci95: CiPair;
}

interface RcaRow {
  run_id: string;
  label: string;
  split: string;
  alerts: number;
  alerts_in_fault: number;
  cascade_injections: number;
  incidents: number;
  labelled: number;
  ambiguous: number;
  no_fault: number;
  multi_service: number;
  hit1: number;
  hit1_count: number;
  hit1_ci95: CiPair;
  hit3: number;
  hit3_count: number;
  hit3_ci95: CiPair;
  baseline_hit1: number;
  per_injection_hit1: number;
  per_injection_hit1_ci95: CiPair;
  arr_all: number;
  arr_all_ci95: CiPair;
  arr_cascade: number | null;
  arr_cascade_ci95: CiPair | null;
  summary_valid: number;
  summary_incidents: number;
  json_valid_rate: number;
  note: string;
}

interface ExperimentTablePayload {
  schema_version: string;
  generated_at: string;
  sources: string[];
  verdicts: HypothesisRow[];
  methods: Record<SplitKey, { windows: number; fault_windows: number; methods: MethodRow[]; pairs: PairRow[] }>;
  ablation: Record<
    SplitKey,
    {
      windows: number;
      fault_windows: number;
      variants: MethodRow[];
      pairs: PairRow[];
      rescue: {
        selected_name: string;
        best_point_name: string;
        judged_rescue_windows: number;
        judged_rescue_alerts: number;
        added_calls: number;
        rescued_alerts_in_subset: number;
      };
    }
  >;
  budget_curve: Record<SplitKey, BudgetRow[]>;
  rca: RcaRow[];
}

const DATA = rawExperimentTable as ExperimentTablePayload;

const METRIC_COLORS = {
  precision: series[0] ?? "#2b59c3",
  recall: series[1] ?? "#0f766e",
  f1: series[2] ?? "#b45309",
  fpr: series[3] ?? "#7c3aed",
};

const BUDGET_SERIES = [
  { key: "ctav" as const, label: "CTAV", color: METRIC_COLORS.precision, glyph: "●" },
  { key: "c1" as const, label: "C1 (Topology)", color: METRIC_COLORS.f1, glyph: "▲" },
  { key: "norag" as const, label: "LLM-không-RAG", color: METRIC_COLORS.fpr, glyph: "◆" },
  { key: "bm25" as const, label: "BM25", color: METRIC_COLORS.recall, glyph: "■" },
];

function ciSpan(val: number, ci: CiPair): [number, number] {
  return [Math.max(0, val - ci[0]), Math.max(0, ci[1] - val)];
}

function fmtSigned(v: number, decimals = 3): string {
  const s = num(Math.abs(v), decimals);
  if (v > 0) return `+${s}`;
  if (v < 0) return `−${s}`;
  return `+${s}`;
}

function fmtCi(ci: CiPair, decimals = 3, signed = false): string {
  const f = signed ? (x: number) => fmtSigned(x, decimals) : (x: number) => num(x, decimals);
  return `[${f(ci[0])}; ${f(ci[1])}]`;
}

function fmtP(p: number): string {
  if (p < 0.001) return "< 0,001";
  return num(p, 3);
}

function statusColor(st: string): string {
  if (st === "accepted") return status.good;
  if (st === "rejected") return status.critical;
  if (st === "partial") return status.warning;
  return ink.muted;
}

export default function ExperimentComparison() {
  const [split, setSplit] = useState<SplitKey>("test");

  const hasData =
    Boolean(DATA?.verdicts?.length) &&
    Boolean(DATA?.methods?.[split]?.methods?.length) &&
    Boolean(DATA?.ablation?.[split]?.variants?.length);

  const methodBlock = DATA?.methods?.[split];
  const ablationBlock = DATA?.ablation?.[split];
  const budgetRows = DATA?.budget_curve?.[split] ?? [];
  const rcaRows = DATA?.rca ?? [];

  const barData = useMemo(() => {
    if (!methodBlock) return [];
    return methodBlock.methods.map((m) => ({
      name: m.label,
      precision: m.precision,
      precision_ci: ciSpan(m.precision, m.precision_ci95),
      recall: m.recall,
      recall_ci: ciSpan(m.recall, m.recall_ci95),
      f1: m.f1,
      f1_ci: ciSpan(m.f1, m.f1_ci95),
      fpr: m.fpr,
      fpr_ci: ciSpan(m.fpr, m.fpr_ci95),
    }));
  }, [methodBlock]);

  if (!hasData || !methodBlock || !ablationBlock) {
    return (
      <Empty>
        Chưa có bảng thực nghiệm tĩnh (<code className="font-mono">src/data/experiment_table.json</code>).
        Chạy <code className="font-mono">py scripts/m10_experiment_table.py</code> để sinh từ{" "}
        <code className="font-mono">eval/results/</code>.
      </Empty>
    );
  }

  const ctavM = methodBlock.methods.find((m) => m.key === "ctav");
  const bm25M = methodBlock.methods.find((m) => m.key === "bm25");
  const b120 = budgetRows[0];
  const rcaPrimary = rcaRows.find((r) => (split === "test" ? r.split === "test" : r.split === "val"));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-[18px] font-semibold tracking-tight text-ink">
            So sánh thực nghiệm CTAV &amp; RCA ({split === "test" ? "split test — G-test" : "split val"})
          </h1>
          <p className="text-[11.5px] text-ink-muted">
            Bảng tĩnh trích từ <code className="font-mono">eval/results/m10_experiment_table_v2/experiment_table.json</code>{" "}
            (QĐ-037 · 0 số giả lập · bootstrap n=1.000, McNemar ghép cặp)
          </p>
        </div>
        <div className="flex items-center gap-1 rounded-md border border-[color:var(--color-hairline)] bg-surface p-0.5 text-[11.5px]">
          {(["test", "val"] as const).map((k) => (
            <button
              key={k}
              type="button"
              onClick={() => setSplit(k)}
              className={cx(
                "rounded px-3 py-1 transition-colors",
                split === k ? "bg-[color:var(--color-plane)] font-medium text-ink" : "text-ink-muted hover:text-ink-2",
              )}
            >
              {k === "test" ? "Split test (chính thức)" : "Split val (tham chiếu)"}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile
          label={`CTAV F1 (${split})`}
          value={ctavM ? num(ctavM.f1, 3) : "—"}
          hint={ctavM ? `TP ${ctavM.tp} · FP ${ctavM.fp} · CI ${fmtCi(ctavM.f1_ci95)}` : undefined}
          accent={METRIC_COLORS.f1}
        />
        <StatTile
          label={`CTAV FPR (${split})`}
          value={ctavM ? num(ctavM.fpr, 4) : "—"}
          hint={bm25M ? `so với BM25 ${num(bm25M.fpr, 4)}` : undefined}
          accent={METRIC_COLORS.precision}
        />
        <StatTile
          label={`H4 @ 120 lần gọi (${split})`}
          value={b120 ? num(b120.ctav, 3) : "—"}
          hint={b120 ? `so với không-RAG ${num(b120.norag, 3)}` : undefined}
        />
        <StatTile
          label={`RCA Hit@1 (${rcaPrimary?.split ?? split})`}
          value={rcaPrimary ? `${rcaPrimary.hit1_count}/${rcaPrimary.labelled} (${num(rcaPrimary.hit1, 3)})` : "—"}
          hint={
            rcaPrimary
              ? `ARR ${num(rcaPrimary.arr_all, 3)} · JSON ${num(rcaPrimary.json_valid_rate * 100, 0)}%`
              : undefined
          }
        />
      </div>

      <Card
        title="Tổng hợp kiểm định giả thuyết H0–H5"
        subtitle="Theo tiêu chí đăng ký trước G-test (be2b985) và quyết định báo cáo H5 (V45 / QĐ-045)."
      >
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[12px]">
            <thead>
              <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] text-ink-muted">
                <th className="py-2 pr-3 font-medium">Giả thuyết</th>
                <th className="py-2 pr-3 font-medium">Split</th>
                <th className="py-2 pr-3 font-medium">Kết luận</th>
                <th className="py-2 font-medium">Số đo kiểm định</th>
              </tr>
            </thead>
            <tbody>
              {DATA.verdicts.map((h) => (
                <tr key={h.id} className="border-b border-[color:var(--color-hairline)] last:border-0 align-top">
                  <td className="py-2 pr-3 font-medium text-ink">
                    <span className="font-mono">{h.id}</span> · {h.title}
                  </td>
                  <td className="py-2 pr-3 font-mono text-[11px] text-ink-muted">{h.split}</td>
                  <td className="py-2 pr-3 whitespace-nowrap">
                    <span
                      className="inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium"
                      style={{ borderColor: statusColor(h.status), color: statusColor(h.status) }}
                    >
                      {h.status_label}
                    </span>
                  </td>
                  <td className="py-2 text-[11.5px] text-ink-2">
                    <div>{h.summary}</div>
                    {h.note && <div className="mt-1 text-[11px] italic text-ink-muted">{h.note}</div>}
                    {h.clauses.length > 0 && (
                      <ul className="mt-1 space-y-0.5 text-[11px] text-ink-muted">
                        {h.clauses.map((c) => (
                          <li key={c.clause}>
                            <span className="font-mono">
                              {c.met === true ? "✓" : c.met === false ? "✗" : "•"}
                            </span>{" "}
                            {c.clause}: <span className="text-ink-2">{c.detail}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card
        title={`Năm phương pháp phân loại cảnh báo (${split} — ${methodBlock.windows.toLocaleString("vi-VN")} cửa sổ telemetry, ${methodBlock.fault_windows} fault)`}
        subtitle="Râu biểu đồ là khoảng tin cậy bootstrap 95% (n=1.000). Chỉ số đầy đủ nằm ở bảng bên dưới."
        right={
          <Legend
            items={[
              { key: "p", label: "Precision", color: METRIC_COLORS.precision },
              { key: "r", label: "Recall", color: METRIC_COLORS.recall },
              { key: "f1", label: "F1", color: METRIC_COLORS.f1 },
              { key: "fpr", label: "FPR", color: METRIC_COLORS.fpr },
            ]}
          />
        }
      >
        <div className="h-[280px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={barData} margin={{ top: 8, right: 12, bottom: 0, left: -10 }}>
              <CartesianGrid vertical={false} stroke={ink.grid} />
              <XAxis dataKey="name" {...axisProps} />
              <YAxis {...axisProps} domain={[0, "auto"]} width={44} />
              <Tooltip
                cursor={{ fill: "rgb(11 11 11 / 0.04)" }}
                content={({ active, payload, label }) =>
                  active && payload?.length ? (
                    <TooltipShell title={String(label)}>
                      {payload.map((entry) => (
                        <TooltipRow
                          key={String(entry.dataKey)}
                          color={entry.color}
                          label={String(entry.name)}
                          value={num(Number(entry.value), 3)}
                        />
                      ))}
                    </TooltipShell>
                  ) : null
                }
              />
              <Bar dataKey="precision" name="Precision" fill={METRIC_COLORS.precision} radius={[2, 2, 0, 0]}>
                <ErrorBar dataKey="precision_ci" stroke={ink.secondary} strokeWidth={1.1} width={4} />
              </Bar>
              <Bar dataKey="recall" name="Recall" fill={METRIC_COLORS.recall} radius={[2, 2, 0, 0]}>
                <ErrorBar dataKey="recall_ci" stroke={ink.secondary} strokeWidth={1.1} width={4} />
              </Bar>
              <Bar dataKey="f1" name="F1" fill={METRIC_COLORS.f1} radius={[2, 2, 0, 0]}>
                <ErrorBar dataKey="f1_ci" stroke={ink.secondary} strokeWidth={1.1} width={4} />
              </Bar>
              <Bar dataKey="fpr" name="FPR" fill={METRIC_COLORS.fpr} radius={[2, 2, 0, 0]}>
                <ErrorBar dataKey="fpr_ci" stroke={ink.secondary} strokeWidth={1.1} width={4} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full border-collapse text-[12px]">
            <thead>
              <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] text-ink-muted">
                <th className="py-2 pr-3 font-medium">Phương pháp</th>
                <th className="py-2 pr-3 text-right font-medium">TP</th>
                <th className="py-2 pr-3 text-right font-medium">FP</th>
                <th className="py-2 pr-3 text-right font-medium">Precision</th>
                <th className="py-2 pr-3 font-medium">Recall [CI95]</th>
                <th className="py-2 pr-3 font-medium">F1 [CI95]</th>
                <th className="py-2 font-medium">FPR [CI95]</th>
              </tr>
            </thead>
            <tbody>
              {methodBlock.methods.map((m) => (
                <tr key={m.key} className="border-b border-[color:var(--color-hairline)] last:border-0">
                  <td className="py-1.5 pr-3 font-medium text-ink">{m.label}</td>
                  <td className="py-1.5 pr-3 text-right tabular-nums">{m.tp}</td>
                  <td className="py-1.5 pr-3 text-right tabular-nums">{m.fp}</td>
                  <td className="py-1.5 pr-3 text-right tabular-nums">{num(m.precision, 3)}</td>
                  <td className="py-1.5 pr-3 tabular-nums text-ink-2">
                    <span className="font-medium text-ink">{num(m.recall, 3)}</span>{" "}
                    <span className="text-[11px] text-ink-muted">{fmtCi(m.recall_ci95)}</span>
                  </td>
                  <td className="py-1.5 pr-3 tabular-nums text-ink-2">
                    <span className="font-medium text-ink">{num(m.f1, 3)}</span>{" "}
                    <span className="text-[11px] text-ink-muted">{fmtCi(m.f1_ci95)}</span>
                  </td>
                  <td className="py-1.5 tabular-nums text-ink-2">
                    <span className="font-medium text-ink">{num(m.fpr, 4)}</span>{" "}
                    <span className="text-[11px] text-ink-muted">{fmtCi(m.fpr_ci95, 4)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className="mt-5 mb-2 text-[12px] font-semibold text-ink">Hiệu ghép cặp (paired bootstrap CI95 &amp; McNemar)</h3>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[11.5px]">
            <thead>
              <tr className="border-b border-[color:var(--color-hairline)] text-left text-[10.5px] text-ink-muted">
                <th className="py-1.5 pr-3 font-medium">Hiệu</th>
                <th className="py-1.5 pr-3 font-medium">ΔRecall [CI95]</th>
                <th className="py-1.5 pr-3 font-medium">ΔFPR [CI95]</th>
                <th className="py-1.5 pr-3 font-medium">ΔF1 [CI95]</th>
                <th className="py-1.5 pr-3 font-medium">ΔPrecision [CI95]</th>
                <th className="py-1.5 font-medium">McNemar p (mọi / fault / normal)</th>
              </tr>
            </thead>
            <tbody>
              {methodBlock.pairs.map((p) => (
                <tr key={p.label} className="border-b border-[color:var(--color-hairline)] last:border-0">
                  <td className="py-1.5 pr-3 font-medium text-ink">{p.label}</td>
                  <td className="py-1.5 pr-3 tabular-nums">
                    {fmtSigned(p.d_recall)} <span className="text-ink-muted">{fmtCi(p.d_recall_ci95, 3, true)}</span>
                  </td>
                  <td className="py-1.5 pr-3 tabular-nums">
                    {fmtSigned(p.d_fpr, 4)} <span className="text-ink-muted">{fmtCi(p.d_fpr_ci95, 4, true)}</span>
                  </td>
                  <td className="py-1.5 pr-3 tabular-nums">
                    {fmtSigned(p.d_f1)} <span className="text-ink-muted">{fmtCi(p.d_f1_ci95, 3, true)}</span>
                  </td>
                  <td className="py-1.5 pr-3 tabular-nums">
                    {fmtSigned(p.d_precision)} <span className="text-ink-muted">{fmtCi(p.d_precision_ci95, 3, true)}</span>
                  </td>
                  <td className="py-1.5 tabular-nums text-ink-2">
                    {fmtP(p.mcnemar_all_p)} / {fmtP(p.mcnemar_fault_p)} / {fmtP(p.mcnemar_normal_p)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card
        title={`H3 — Ablation thành phần CTAV & C5 Rescue (${split})`}
        subtitle={`C5 Rescue quét vùng dưới ngưỡng (${ablationBlock.rescue.judged_rescue_windows} cửa sổ, ${ablationBlock.rescue.judged_rescue_alerts} alert được judge; best point ${ablationBlock.rescue.best_point_name}, chọn ${ablationBlock.rescue.selected_name}).`}
      >
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[12px]">
            <thead>
              <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] text-ink-muted">
                <th className="py-2 pr-3 font-medium">Biến thể</th>
                <th className="py-2 pr-3 text-right font-medium">TP</th>
                <th className="py-2 pr-3 text-right font-medium">FP</th>
                <th className="py-2 pr-3 text-right font-medium">Precision</th>
                <th className="py-2 pr-3 text-right font-medium">Recall</th>
                <th className="py-2 pr-3 font-medium">F1 [CI95]</th>
                <th className="py-2 pr-3 text-right font-medium">FPR</th>
                <th className="py-2 pr-3 text-right font-medium">Lần gọi LLM</th>
                <th className="py-2 text-right font-medium">USD</th>
              </tr>
            </thead>
            <tbody>
              {ablationBlock.variants.map((v) => (
                <tr key={v.key} className="border-b border-[color:var(--color-hairline)] last:border-0">
                  <td className="py-1.5 pr-3 font-medium text-ink">{v.label}</td>
                  <td className="py-1.5 pr-3 text-right tabular-nums">{v.tp}</td>
                  <td className="py-1.5 pr-3 text-right tabular-nums">{v.fp}</td>
                  <td className="py-1.5 pr-3 text-right tabular-nums">{num(v.precision, 3)}</td>
                  <td className="py-1.5 pr-3 text-right tabular-nums">{num(v.recall, 3)}</td>
                  <td className="py-1.5 pr-3 tabular-nums">
                    <span className="font-medium">{num(v.f1, 3)}</span>{" "}
                    <span className="text-[11px] text-ink-muted">{fmtCi(v.f1_ci95)}</span>
                  </td>
                  <td className="py-1.5 pr-3 text-right tabular-nums">{num(v.fpr, 4)}</td>
                  <td className="py-1.5 pr-3 text-right tabular-nums">
                    {v.llm_calls !== null ? v.llm_calls.toLocaleString("vi-VN") : "—"}
                  </td>
                  <td className="py-1.5 text-right tabular-nums">
                    {v.estimated_cost_usd !== null ? `$${num(v.estimated_cost_usd, 2)}` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className="mt-4 mb-2 text-[12px] font-semibold text-ink">Hiệu ghép cặp so với CTAV</h3>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[11.5px]">
            <thead>
              <tr className="border-b border-[color:var(--color-hairline)] text-left text-[10.5px] text-ink-muted">
                <th className="py-1.5 pr-3 font-medium">Biến thể − CTAV</th>
                <th className="py-1.5 pr-3 font-medium">ΔRecall [CI95]</th>
                <th className="py-1.5 pr-3 font-medium">ΔFPR [CI95]</th>
                <th className="py-1.5 pr-3 font-medium">ΔF1 [CI95]</th>
                <th className="py-1.5 pr-3 font-medium">ΔPrecision [CI95]</th>
                <th className="py-1.5 font-medium">McNemar p (mọi / fault / normal)</th>
              </tr>
            </thead>
            <tbody>
              {ablationBlock.pairs.map((p) => (
                <tr key={p.label} className="border-b border-[color:var(--color-hairline)] last:border-0">
                  <td className="py-1.5 pr-3 font-medium text-ink">{p.label}</td>
                  <td className="py-1.5 pr-3 tabular-nums">
                    {fmtSigned(p.d_recall)} <span className="text-ink-muted">{fmtCi(p.d_recall_ci95, 3, true)}</span>
                  </td>
                  <td className="py-1.5 pr-3 tabular-nums">
                    {fmtSigned(p.d_fpr, 4)} <span className="text-ink-muted">{fmtCi(p.d_fpr_ci95, 4, true)}</span>
                  </td>
                  <td className="py-1.5 pr-3 tabular-nums">
                    {fmtSigned(p.d_f1)} <span className="text-ink-muted">{fmtCi(p.d_f1_ci95, 3, true)}</span>
                  </td>
                  <td className="py-1.5 pr-3 tabular-nums">
                    {fmtSigned(p.d_precision)} <span className="text-ink-muted">{fmtCi(p.d_precision_ci95, 3, true)}</span>
                  </td>
                  <td className="py-1.5 tabular-nums text-ink-2">
                    {fmtP(p.mcnemar_all_p)} / {fmtP(p.mcnemar_fault_p)} / {fmtP(p.mcnemar_normal_p)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card
        title={`H4 — Đường cong F1 theo ngân sách lần gọi LLM (${split})`}
        subtitle="Candidate xếp theo thứ tự thời gian; H4 kiểm định ở mốc đầu 120 lần gọi."
        right={
          <Legend items={BUDGET_SERIES.map((s) => ({ key: s.key, label: s.label, color: s.color, glyph: s.glyph }))} />
        }
      >
        <div className="h-[240px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={budgetRows} margin={{ top: 8, right: 16, bottom: 0, left: -12 }}>
              <CartesianGrid vertical={false} stroke={ink.grid} />
              <XAxis dataKey="budget" {...axisProps} />
              <YAxis {...axisProps} domain={[0, "auto"]} width={44} />
              <Tooltip
                content={({ active, payload, label }) =>
                  active && payload?.length ? (
                    <TooltipShell title={`Ngân sách: ${label}`}>
                      {payload.map((entry) => (
                        <TooltipRow
                          key={String(entry.dataKey)}
                          color={entry.color}
                          label={String(entry.name)}
                          value={num(Number(entry.value), 3)}
                        />
                      ))}
                    </TooltipShell>
                  ) : null
                }
              />
              {BUDGET_SERIES.map((s) => (
                <Line
                  key={s.key}
                  type="monotone"
                  dataKey={s.key}
                  name={s.label}
                  stroke={s.color}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="mt-3 overflow-x-auto">
          <table className="w-full border-collapse text-[12px]">
            <thead>
              <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] text-ink-muted">
                <th className="py-1.5 pr-3 font-medium">Phương pháp</th>
                {budgetRows.map((b) => (
                  <th key={b.budget} className="py-1.5 px-2 text-right font-medium tabular-nums">
                    {b.budget}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {BUDGET_SERIES.map((s) => (
                <tr key={s.key} className="border-b border-[color:var(--color-hairline)] last:border-0">
                  <td className="py-1.5 pr-3 font-medium text-ink">{s.label}</td>
                  {budgetRows.map((b) => (
                    <td key={b.budget} className="py-1.5 px-2 text-right tabular-nums">
                      {num(b[s.key], 3)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card
        title="H5 — Đánh giá tác tử RCA (Nhánh A: định vị gốc · Nhánh B: gom &amp; tóm tắt) + Độ nhạy C3-trượt"
        subtitle="Không đạt ngưỡng đăng ký trước trên test (Hit@1=0,471 < 0,60; Hit@3=0,471 < 0,80 vì C3 ngưỡng dev lọc hết ca đa dịch vụ). Nhánh B đạt trên cả 2 split."
      >
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[11.5px]">
            <thead>
              <tr className="border-b border-[color:var(--color-hairline)] text-left text-[10.5px] text-ink-muted">
                <th className="py-2 pr-3 font-medium">Cấu hình</th>
                <th className="py-2 pr-3 text-right font-medium">Alert</th>
                <th className="py-2 pr-3 text-right font-medium">Sự cố (có nhãn / multi)</th>
                <th className="py-2 pr-3 font-medium">Hit@1 [CI95]</th>
                <th className="py-2 pr-3 font-medium">Hit@3 [CI95]</th>
                <th className="py-2 pr-3 text-right font-medium">Baseline Hit@1</th>
                <th className="py-2 pr-3 text-right font-medium">Hit@1 / tiêm lỗi</th>
                <th className="py-2 pr-3 font-medium">ARR mọi cảnh báo [CI95]</th>
                <th className="py-2 pr-3 text-right font-medium">ARR cascade</th>
                <th className="py-2 font-medium">JSON hợp lệ</th>
              </tr>
            </thead>
            <tbody>
              {rcaRows.map((r) => (
                <tr key={r.run_id} className="border-b border-[color:var(--color-hairline)] last:border-0">
                  <td className="py-2 pr-3">
                    <div className="font-medium text-ink">{r.label}</div>
                    <div className="text-[10.5px] text-ink-muted">{r.note}</div>
                  </td>
                  <td className="py-2 pr-3 text-right tabular-nums">{r.alerts}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">
                    {r.incidents} ({r.labelled} / {r.multi_service})
                  </td>
                  <td className="py-2 pr-3 tabular-nums">
                    <span className="font-medium text-ink">{num(r.hit1, 3)}</span>{" "}
                    <span className="text-ink-muted">{fmtCi(r.hit1_ci95)}</span>
                  </td>
                  <td className="py-2 pr-3 tabular-nums">
                    <span className="font-medium text-ink">{num(r.hit3, 3)}</span>{" "}
                    <span className="text-ink-muted">{fmtCi(r.hit3_ci95)}</span>
                  </td>
                  <td className="py-2 pr-3 text-right tabular-nums">{num(r.baseline_hit1, 3)}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{num(r.per_injection_hit1, 3)}</td>
                  <td className="py-2 pr-3 tabular-nums">
                    <span className="font-medium text-ink">{num(r.arr_all, 3)}</span>{" "}
                    <span className="text-ink-muted">{fmtCi(r.arr_all_ci95)}</span>
                  </td>
                  <td className="py-2 pr-3 text-right tabular-nums">
                    {r.arr_cascade !== null ? `${num(r.arr_cascade, 3)} (${r.cascade_injections})` : `— (${r.cascade_injections})`}
                  </td>
                  <td className="py-2 tabular-nums">
                    {r.summary_valid}/{r.summary_incidents} ({num(r.json_valid_rate * 100, 0)}%)
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
