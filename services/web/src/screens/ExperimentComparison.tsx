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
import { series, status } from "@/theme/tokens";

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
  { key: "norag" as const, label: "LLM-no-RAG", color: METRIC_COLORS.fpr, glyph: "◆" },
  { key: "bm25" as const, label: "BM25", color: METRIC_COLORS.recall, glyph: "■" },
];

const METHOD_LABEL_EN: Record<string, string> = {
  bm25: "BM25",
  c1: "C1 (Topology)",
  norag: "LLM-no-RAG",
  ctav: "CTAV",
  detector_only: "Detector-only",
};

const HYPOTHESIS_META_EN: Record<string, { title: string; statusLabel: string }> = {
  H0: { title: "Uncalibrated Topology (C1) vs BM25", statusLabel: "Accepted (4/4 criteria)" },
  H1: {
    title: "Mechanism Experiment on Controlled Samples",
    statusLabel: "Partially retained (val, M5 — QD-028); not re-run on test",
  },
  H2: { title: "CTAV vs BM25 & C1 (Main Hypothesis)", statusLabel: "Rejected (1/3 criteria)" },
  H3: { title: "Component Ablation (C2, C3, C4, C5)", statusLabel: "Accepted (C3 contributes; C2 & C4 dropped)" },
  H4: { title: "Small Budget (120 LLM calls)", statusLabel: "Accepted (point estimate)" },
  H5: { title: "RCA Agent on CTAV-grouped Incidents", statusLabel: "Rejected (0/4 criteria)" },
};

const PHRASE_EN: [string, string][] = [
  ["Độ lợi C1 trên fault đến từ metric/span gần nhất theo thời gian:", "C1 fault gain comes from temporally closest metric/span evidence:"],
  ["Tham chiếu (không phải tiêu chí đăng ký): ARR mọi cảnh báo", "Reference (non-registered): ARR all alerts"],
  ["ARR cảnh báo trong lỗi", "ARR fault alerts"],
  ["lần tiêm lỗi là cascade", "fault injections are cascade"],
  ["Nhánh B chỉ đạt phần gom cảnh báo và sinh báo cáo đúng lược đồ (JSON hợp lệ", "Branch B succeeded only on alert grouping and schema-valid report synthesis (valid JSON"],
  ["Cận dưới CI95 của ΔHit@1 (RCA − baseline) > 0", "Lower CI95 bound of ΔHit@1 (RCA − baseline) > 0"],
  ["Alert Reduction ≥ 30% trên sự cố cascade", "Alert Reduction ≥ 30% on cascade incidents"],
  ["CI ΔRecall(C1 − BM25) có cận dưới > 0", "CI ΔRecall(C1 − BM25) lower bound > 0"],
  ["CI ΔFPR(C1 − BM25) có cận dưới > 0", "CI ΔFPR(C1 − BM25) lower bound > 0"],
  ["(i) CI ΔF1(CTAV − BM25) cận dưới > 0 và McNemar p < 0,05", "(i) CI ΔF1(CTAV − BM25) lower bound > 0 and McNemar p < 0.05"],
  ["(ii) CI ΔFPR(CTAV − BM25) không có cận dưới > 0", "(ii) CI ΔFPR(CTAV − BM25) lower bound ≤ 0"],
  ["(iii) ΔRecall(CTAV − C1) ≥ −0,05 (ước lượng điểm)", "(iii) ΔRecall(CTAV − C1) ≥ −0.05 (point estimate)"],
  ["bỏ C3 ⇒ CI ΔPrecision cận trên < 0 (C3 đóng góp)", "remove C3 ⇒ CI ΔPrecision upper bound < 0 (C3 contributes)"],
  ["thêm C2 (θ_topo 0,85): xác nhận bỏ nếu CI ΔFPR chứa 0 hoặc > 0", "add C2 (θ_topo 0.85): confirm removal if CI ΔFPR includes 0 or > 0"],
  ["thêm C4: xác nhận bỏ nếu chi phí tăng và CI ΔF1 không có cận dưới > 0", "add C4: confirm removal if cost rises and CI ΔF1 lower bound ≤ 0"],
  ["báo ΔF1, ΔFPR (không có tiêu chí đạt / không đạt)", "report ΔF1, ΔFPR (observational)"],
  ["báo ΔRecall, ΔFPR, +lần gọi (không có tiêu chí đạt / không đạt)", "report ΔRecall, ΔFPR, +calls (observational)"],
  ["F1(CTAV) ≥ F1(LLM-không-RAG) ở ngân sách 120 lần gọi (ước lượng điểm)", "F1(CTAV) ≥ F1(LLM-no-RAG) at 120 LLM call budget (point estimate)"],
  ["không tính được:", "N/A:"],
  ["cặp lệch", "discordant pairs"],
  ["lần gọi", "calls"],
  ["điểm", "point"],
  ["không-RAG", "no-RAG"],
  ["LLM-không-RAG", "LLM-no-RAG"],
  ["so với", "vs"],
  ["chi phí", "cost"],
  ["CTAV (baseline hiệu chỉnh)", "CTAV (calibrated baseline)"],
  ["with_c2 (bật θ_topo=0,85)", "with_c2 (enable θ_topo=0.85)"],
  ["no_c2 (bỏ C2 gating)", "no_c2 (disable C2 gating)"],
  ["no_c3 (bỏ neo bằng chứng)", "no_c3 (disable C3 anchoring)"],
  ["with_c4 (bật định tuyến C4)", "with_c4 (enable C4 routing)"],
  ["c3_rolling_baseline (C3-trượt)", "c3_rolling_baseline (C3-rolling)"],
  ["CTAV (test — H5 chính)", "CTAV (test — registered H5)"],
  ["C3-trượt (test — độ nhạy)", "C3-rolling (test — sensitivity)"],
  ["1 cascade (ARR=0,667); chạy lại ở M10-A bằng pipeline_val_v1", "1 cascade (ARR=0.667); replayed in M10-A/C.1 via pipeline_val_v1/_v2"],
  ["0 multi-service vì C3 ngưỡng dev lọc hết; ARR=0,513; JSON hợp lệ 38/38", "0 multi-service (filtered by frozen dev C3 threshold); ARR=0.513; valid JSON 38/38"],
  ["41 cascade / 39 multi-service; ARR cascade=0,704; Hit@1=0,208", "41 cascade / 39 multi-service; cascade ARR=0.704; Hit@1=0.208"],
  ["C3-trượt", "C3-rolling"],
  ["Đủ", "Full"],
];

function toEn(text: string): string {
  let out = text;
  for (const [vi, en] of PHRASE_EN) {
    out = out.split(vi).join(en);
  }
  return out.replace(/(\d),(\d)/g, "$1.$2").replace(/; /g, ", ");
}

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
  return `[${f(ci[0])}, ${f(ci[1])}]`;
}

function fmtP(p: number): string {
  if (p < 0.001) return "< 0.001";
  return num(p, 3);
}

function statusColor(st: string): string {
  if (st === "accepted") return status.good;
  if (st === "rejected") return status.critical;
  if (st === "partial") return status.warning;
  return "var(--color-ink-muted)";
}

export default function ExperimentComparison() {
  const [split, setSplit] = useState<SplitKey>("test");

  const hasData =
    Boolean(DATA?.verdicts?.length) &&
    Boolean(DATA?.methods?.[split]?.methods?.length) &&
    Boolean(DATA?.ablation?.[split]?.variants?.length);

  const methodBlock = DATA?.methods?.[split];
  const ablationBlock = DATA?.ablation?.[split];
  const budgetRows = useMemo(
    () => (DATA?.budget_curve?.[split] ?? []).map((b) => ({ ...b, budget: toEn(b.budget) })),
    [split],
  );
  const rcaRows = DATA?.rca ?? [];

  const barData = useMemo(() => {
    if (!methodBlock) return [];
    return methodBlock.methods.map((m) => ({
      name: METHOD_LABEL_EN[m.key] ?? toEn(m.label),
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
        Static experiment table not found (<code className="font-mono">src/data/experiment_table.json</code>).
        Run <code className="font-mono">py scripts/m10_experiment_table.py</code> to generate from{" "}
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
            CTAV &amp; RCA Experiment Comparison ({split === "test" ? "test split — G-test" : "val split"})
          </h1>
          <p className="text-[11.5px] text-ink-muted">
            Static verified table from <code className="font-mono">eval/results/m10_experiment_table_v2/experiment_table.json</code>{" "}
            (QD-037 · 0 fabricated numbers · bootstrap n=1,000, paired McNemar)
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
              {k === "test" ? "Test split (official)" : "Val split (reference)"}
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
          hint={bm25M ? `vs BM25 ${num(bm25M.fpr, 4)}` : undefined}
          accent={METRIC_COLORS.precision}
        />
        <StatTile
          label={`H4 @ 120 calls (${split})`}
          value={b120 ? num(b120.ctav, 3) : "—"}
          hint={b120 ? `vs LLM-no-RAG ${num(b120.norag, 3)}` : undefined}
        />
        <StatTile
          label={`RCA Hit@1 (${rcaPrimary?.split ?? split})`}
          value={rcaPrimary ? `${rcaPrimary.hit1_count}/${rcaPrimary.labelled} (${num(rcaPrimary.hit1, 3)})` : "—"}
          hint={
            rcaPrimary
              ? `ARR ${num(rcaPrimary.arr_all, 3)} · valid JSON ${num(rcaPrimary.json_valid_rate * 100, 0)}%`
              : undefined
          }
        />
      </div>

      <Card
        title="Hypothesis Verification Summary (H0–H5)"
        subtitle="Pre-registered G-test acceptance criteria (be2b985) and V45 honest H5 reporting (QD-045)."
      >
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[12px]">
            <thead>
              <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] text-ink-muted">
                <th className="py-2 pr-3 font-medium">Hypothesis</th>
                <th className="py-2 pr-3 font-medium">Split</th>
                <th className="py-2 pr-3 font-medium">Verdict</th>
                <th className="py-2 font-medium">Measured Evidence</th>
              </tr>
            </thead>
            <tbody>
              {DATA.verdicts.map((h) => {
                const meta = HYPOTHESIS_META_EN[h.id];
                return (
                  <tr key={h.id} className="border-b border-[color:var(--color-hairline)] last:border-0 align-top">
                    <td className="py-2 pr-3 font-medium text-ink">
                      <span className="font-mono">{h.id}</span> · {meta?.title ?? toEn(h.title)}
                    </td>
                    <td className="py-2 pr-3 font-mono text-[11px] text-ink-muted">{h.split}</td>
                    <td className="py-2 pr-3 whitespace-nowrap">
                      <span
                        className="inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium"
                        style={{ borderColor: statusColor(h.status), color: statusColor(h.status) }}
                      >
                        {meta?.statusLabel ?? toEn(h.status_label)}
                      </span>
                    </td>
                    <td className="py-2 text-[11.5px] text-ink-2">
                      <div>{toEn(h.summary)}</div>
                      {h.note && <div className="mt-1 text-[11px] italic text-ink-muted">{toEn(h.note)}</div>}
                      {h.clauses.length > 0 && (
                        <ul className="mt-1 space-y-0.5 text-[11px] text-ink-muted">
                          {h.clauses.map((c) => (
                            <li key={c.clause}>
                              <span className="font-mono">
                                {c.met === true ? "✓" : c.met === false ? "✗" : "•"}
                              </span>{" "}
                              {toEn(c.clause)}: <span className="text-ink-2">{toEn(c.detail)}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <Card
        title={`Five Alert Validation Methods (${split} — ${methodBlock.windows.toLocaleString("en-US")} telemetry windows, ${methodBlock.fault_windows} fault)`}
        subtitle="Error bars show 95% bootstrap confidence intervals (n=1,000). Full table below."
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
              <CartesianGrid vertical={false} stroke="var(--color-grid)" />
              <XAxis dataKey="name" {...axisProps} />
              <YAxis {...axisProps} domain={[0, "auto"]} width={44} />
              <Tooltip
                cursor={{ fill: "rgb(37 99 235 / 0.06)" }}
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
                <ErrorBar dataKey="precision_ci" stroke="var(--color-ink-2)" strokeWidth={1.1} width={4} />
              </Bar>
              <Bar dataKey="recall" name="Recall" fill={METRIC_COLORS.recall} radius={[2, 2, 0, 0]}>
                <ErrorBar dataKey="recall_ci" stroke="var(--color-ink-2)" strokeWidth={1.1} width={4} />
              </Bar>
              <Bar dataKey="f1" name="F1" fill={METRIC_COLORS.f1} radius={[2, 2, 0, 0]}>
                <ErrorBar dataKey="f1_ci" stroke="var(--color-ink-2)" strokeWidth={1.1} width={4} />
              </Bar>
              <Bar dataKey="fpr" name="FPR" fill={METRIC_COLORS.fpr} radius={[2, 2, 0, 0]}>
                <ErrorBar dataKey="fpr_ci" stroke="var(--color-ink-2)" strokeWidth={1.1} width={4} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full border-collapse text-[12px]">
            <thead>
              <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] text-ink-muted">
                <th className="py-2 pr-3 font-medium">Method</th>
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
                  <td className="py-1.5 pr-3 font-medium text-ink">
                    {METHOD_LABEL_EN[m.key] ?? toEn(m.label)}
                  </td>
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

        <h3 className="mt-5 mb-2 text-[12px] font-semibold text-ink">
          Paired Differences (paired bootstrap CI95 &amp; McNemar)
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[11.5px]">
            <thead>
              <tr className="border-b border-[color:var(--color-hairline)] text-left text-[10.5px] text-ink-muted">
                <th className="py-1.5 pr-3 font-medium">Comparison</th>
                <th className="py-1.5 pr-3 font-medium">ΔRecall [CI95]</th>
                <th className="py-1.5 pr-3 font-medium">ΔFPR [CI95]</th>
                <th className="py-1.5 pr-3 font-medium">ΔF1 [CI95]</th>
                <th className="py-1.5 pr-3 font-medium">ΔPrecision [CI95]</th>
                <th className="py-1.5 font-medium">McNemar p (all / fault / normal)</th>
              </tr>
            </thead>
            <tbody>
              {methodBlock.pairs.map((p) => (
                <tr key={p.label} className="border-b border-[color:var(--color-hairline)] last:border-0">
                  <td className="py-1.5 pr-3 font-medium text-ink">{toEn(p.label)}</td>
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
        title={`H3 — Component Ablation & C5 Rescue (${split})`}
        subtitle={`C5 Rescue sweeps below-threshold windows (${ablationBlock.rescue.judged_rescue_windows} windows, ${ablationBlock.rescue.judged_rescue_alerts} alerts judged; best point ${ablationBlock.rescue.best_point_name}, selected ${ablationBlock.rescue.selected_name}).`}
      >
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[12px]">
            <thead>
              <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] text-ink-muted">
                <th className="py-2 pr-3 font-medium">Variant</th>
                <th className="py-2 pr-3 text-right font-medium">TP</th>
                <th className="py-2 pr-3 text-right font-medium">FP</th>
                <th className="py-2 pr-3 text-right font-medium">Precision</th>
                <th className="py-2 pr-3 text-right font-medium">Recall</th>
                <th className="py-2 pr-3 font-medium">F1 [CI95]</th>
                <th className="py-2 pr-3 text-right font-medium">FPR</th>
                <th className="py-2 pr-3 text-right font-medium">LLM calls</th>
                <th className="py-2 text-right font-medium">USD</th>
              </tr>
            </thead>
            <tbody>
              {ablationBlock.variants.map((v) => (
                <tr key={v.key} className="border-b border-[color:var(--color-hairline)] last:border-0">
                  <td className="py-1.5 pr-3 font-medium text-ink">{toEn(v.label)}</td>
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
                    {v.llm_calls !== null ? v.llm_calls.toLocaleString("en-US") : "—"}
                  </td>
                  <td className="py-1.5 text-right tabular-nums">
                    {v.estimated_cost_usd !== null ? `$${num(v.estimated_cost_usd, 2)}` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className="mt-4 mb-2 text-[12px] font-semibold text-ink">Paired Differences vs CTAV</h3>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[11.5px]">
            <thead>
              <tr className="border-b border-[color:var(--color-hairline)] text-left text-[10.5px] text-ink-muted">
                <th className="py-1.5 pr-3 font-medium">Variant − CTAV</th>
                <th className="py-1.5 pr-3 font-medium">ΔRecall [CI95]</th>
                <th className="py-1.5 pr-3 font-medium">ΔFPR [CI95]</th>
                <th className="py-1.5 pr-3 font-medium">ΔF1 [CI95]</th>
                <th className="py-1.5 pr-3 font-medium">ΔPrecision [CI95]</th>
                <th className="py-1.5 font-medium">McNemar p (all / fault / normal)</th>
              </tr>
            </thead>
            <tbody>
              {ablationBlock.pairs.map((p) => (
                <tr key={p.label} className="border-b border-[color:var(--color-hairline)] last:border-0">
                  <td className="py-1.5 pr-3 font-medium text-ink">{toEn(p.label)}</td>
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
        title={`H4 — F1 Curve by LLM Call Budget (${split})`}
        subtitle="Candidates processed in chronological order; H4 is evaluated at the 120-call checkpoint."
        right={
          <Legend items={BUDGET_SERIES.map((s) => ({ key: s.key, label: s.label, color: s.color, glyph: s.glyph }))} />
        }
      >
        <div className="h-[240px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={budgetRows} margin={{ top: 8, right: 16, bottom: 0, left: -12 }}>
              <CartesianGrid vertical={false} stroke="var(--color-grid)" />
              <XAxis dataKey="budget" {...axisProps} />
              <YAxis {...axisProps} domain={[0, "auto"]} width={44} />
              <Tooltip
                content={({ active, payload, label }) =>
                  active && payload?.length ? (
                    <TooltipShell title={`Budget: ${label}`}>
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
                <th className="py-1.5 pr-3 font-medium">Method</th>
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
        title="H5 — RCA Agent Evaluation (Branch A: Root Cause Localization · Branch B: Grouping &amp; Summary) + C3-rolling Sensitivity"
        subtitle="Fails pre-registered test thresholds (Hit@1=0.471 < 0.60, Hit@3=0.471 < 0.80 because frozen dev C3 filters out multi-service incidents). Branch B achieves valid JSON across all splits."
      >
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[11.5px]">
            <thead>
              <tr className="border-b border-[color:var(--color-hairline)] text-left text-[10.5px] text-ink-muted">
                <th className="py-2 pr-3 font-medium">Configuration</th>
                <th className="py-2 pr-3 text-right font-medium">Alerts</th>
                <th className="py-2 pr-3 text-right font-medium">Incidents (labelled / multi)</th>
                <th className="py-2 pr-3 font-medium">Hit@1 [CI95]</th>
                <th className="py-2 pr-3 font-medium">Hit@3 [CI95]</th>
                <th className="py-2 pr-3 text-right font-medium">Baseline Hit@1</th>
                <th className="py-2 pr-3 text-right font-medium">Hit@1 / injection</th>
                <th className="py-2 pr-3 font-medium">ARR all alerts [CI95]</th>
                <th className="py-2 pr-3 text-right font-medium">ARR cascade</th>
                <th className="py-2 font-medium">Valid JSON</th>
              </tr>
            </thead>
            <tbody>
              {rcaRows.map((r) => (
                <tr key={r.run_id} className="border-b border-[color:var(--color-hairline)] last:border-0">
                  <td className="py-2 pr-3">
                    <div className="font-medium text-ink">{toEn(r.label)}</div>
                    <div className="text-[10.5px] text-ink-muted">{toEn(r.note)}</div>
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
