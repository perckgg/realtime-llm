import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, USING_FIXTURES } from "@/api/client";
import type { Alert, Incident, Verdict } from "@/api/types";
import { Legend, TooltipRow, TooltipShell, axisProps } from "@/components/charts";
import { Card, Empty, ErrorBox, KV, Loading, Pill, StatTile, VerdictBadge } from "@/components/ui";
import { clockUTC, cx, ms, num, stampUTC, useAsync } from "@/lib/util";
import { groundTruthBuckets } from "@/mock/fixtures";
import {
  formatFaultType,
  ink,
  status,
  verdictColor,
  verdictGlyph,
  verdictLabel,
  verdictShortLabel,
  VERDICT_ORDER,
} from "@/theme/tokens";
import { useRuns } from "@/lib/runContext";

const BUCKET_MINUTES = 10;

type VerdictFilter = Verdict | "ALL";

const PIPELINE_STAGES = [
  {
    step: "1",
    title: "Anomaly Detection",
    detail: "Isolation Forest scores pod telemetry windows (threshold 0.85).",
  },
  {
    step: "2",
    title: "Topology Retrieval",
    detail: "Fuses local service logs/traces with 1-hop dependency context.",
  },
  {
    step: "3",
    title: "Baseline Evidence Gate",
    detail: "Confirms alerts only with local ERROR/WARN logs or >p90 latency spans.",
  },
  {
    step: "4",
    title: "Root Cause Localization",
    detail: "Clusters confirmed alerts (300s graph window) to isolate fault origin.",
  },
];

export default function Timeline() {
  const { runId } = useRuns();
  const [verdict, setVerdict] = useState<VerdictFilter>("ALL");
  const [service, setService] = useState("ALL");
  const [tab, setTab] = useState<"alerts" | "incidents">("alerts");

  const alertsQ = useAsync(() => api.listAlerts({ runId }), [runId]);
  const incidentsQ = useAsync(() => api.listIncidents(runId), [runId]);
  const metricsQ = useAsync(() => api.runMetrics(runId), [runId]);

  const alerts = alertsQ.data ?? [];

  const services = useMemo(
    () => ["ALL", ...Array.from(new Set(alerts.map((a) => a.service))).sort()],
    [alerts],
  );

  const filtered = useMemo(
    () =>
      alerts.filter(
        (a) =>
          (verdict === "ALL" || a.verdict === verdict) &&
          (service === "ALL" || a.service === service),
      ),
    [alerts, verdict, service],
  );

  const useFullGt = USING_FIXTURES && service === "ALL" && verdict === "ALL";
  const buckets = useMemo(() => bucketise(filtered, useFullGt), [filtered, useFullGt]);
  const stats = useMemo(() => summarise(filtered), [filtered]);
  const fullMetrics = metricsQ.data;
  const unfiltered = verdict === "ALL" && service === "ALL";

  if (alertsQ.loading) return <Loading label="Loading alert timeline…" />;
  if (alertsQ.error) return <ErrorBox message={alertsQ.error} />;

  const trueAlertCount = unfiltered && fullMetrics ? fullMetrics.tp + fullMetrics.fp : stats.tp + stats.fp;
  const trueAlertHint =
    unfiltered && fullMetrics
      ? `${fullMetrics.tp} true faults · ${fullMetrics.fp} false positives (validation split)`
      : `${stats.tp} true faults · ${stats.fp} false positives (filtered view)`;
  const precisionValue =
    unfiltered && fullMetrics
      ? num(fullMetrics.precision.value, 3)
      : stats.tp + stats.fp
        ? num(stats.tp / (stats.tp + stats.fp), 3)
        : "—";

  return (
    <div className="space-y-5">
      <section
        aria-label="CTAV Validation Pipeline Architecture"
        className="grid gap-2.5 rounded-xl border border-[color:var(--color-hairline)] bg-surface p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.03)] sm:grid-cols-2 lg:grid-cols-4"
      >
        {PIPELINE_STAGES.map((st) => (
          <div
            key={st.step}
            className="flex items-start gap-2.5 rounded-lg bg-[color:var(--color-plane)]/70 px-3 py-2"
          >
            <span
              className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full font-mono text-[10.5px] font-semibold text-white"
              style={{ background: "var(--color-seq-550)" }}
            >
              {st.step}
            </span>
            <div className="min-w-0">
              <div className="text-[11.5px] font-semibold text-ink">{st.title}</div>
              <p className="mt-0.5 text-[11px] leading-snug text-ink-muted">{st.detail}</p>
            </div>
          </div>
        ))}
      </section>

      <div className="flex flex-wrap items-end gap-3">
        <Segmented
          label="Verdict Filter"
          value={verdict}
          onChange={(v) => setVerdict(v as VerdictFilter)}
          options={[
            { value: "ALL", label: "All Verdicts" },
            ...VERDICT_ORDER.map((v) => ({
              value: v,
              label: verdictLabel[v],
              glyph: verdictGlyph[v],
              color: verdictColor[v],
            })),
          ]}
        />
        <label className="flex flex-col gap-1 text-[11px] font-medium text-ink-muted">
          Target Service
          <select
            value={service}
            onChange={(e) => setService(e.target.value)}
            className="rounded-lg border border-[color:var(--color-hairline)] bg-surface px-2.5 py-1.5 text-[12px] text-ink shadow-[0_1px_2px_rgba(15,23,42,0.02)]"
          >
            {services.map((s) => (
              <option key={s} value={s}>
                {s === "ALL" ? "All Services" : s}
              </option>
            ))}
          </select>
        </label>
        <div className="ml-auto text-[11.5px] text-ink-muted">
          Showing <strong className="font-semibold text-ink">{filtered.length}</strong> of{" "}
          {alerts.length} sampled candidates · {BUCKET_MINUTES}-min bins
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3.5 md:grid-cols-4">
        <StatTile
          label="Sampled Candidates"
          value={String(filtered.length)}
          hint={
            fullMetrics
              ? `Across ${(fullMetrics.tp + fullMetrics.fp + fullMetrics.fn + fullMetrics.tn).toLocaleString("en-US")} telemetry windows`
              : `Out of ${alerts.length} alerts in run`
          }
        />
        <StatTile
          label="Confirmed Alerts"
          value={String(trueAlertCount)}
          hint={trueAlertHint}
          accent={verdictColor.TRUE_ALERT}
        />
        <StatTile
          label="Validation Precision"
          value={precisionValue}
          hint="Confirmed alerts matching fault labels"
        />
        <StatTile
          label="Suppressed by Gate"
          value={String(stats.anchoredDown)}
          hint={`${stats.anchoredConfirmed} verified with >p90 anchors`}
          accent={status.warning}
        />
      </div>

      <Card
        title="Alert Verdicts Over Time"
        subtitle={`Stacked bars show sampled candidate verdicts aggregated into ${BUCKET_MINUTES}-minute UTC intervals. Dark line tracks ground-truth injected faults${useFullGt ? " across the full validation split" : ""}.`}
        right={
          <Legend
            items={[
              ...VERDICT_ORDER.map((v) => ({
                key: v,
                label: verdictLabel[v],
                color: verdictColor[v],
                glyph: verdictGlyph[v],
              })),
              { key: "gt", label: "Ground-Truth Faults", color: ink.secondary, glyph: "▬" },
            ]}
          />
        }
      >
        <div className="h-[260px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={buckets} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
              <CartesianGrid vertical={false} stroke={ink.grid} />
              <XAxis dataKey="label" {...axisProps} interval="preserveStartEnd" minTickGap={28} />
              <YAxis {...axisProps} allowDecimals={false} width={40} />
              <Tooltip
                cursor={{ fill: "rgb(15 23 42 / 0.04)" }}
                content={({ active, payload, label }) =>
                  active && payload?.length ? (
                    <TooltipShell title={`${label} UTC`}>
                      {VERDICT_ORDER.map((v) => (
                        <TooltipRow
                          key={v}
                          color={verdictColor[v]}
                          glyph={verdictGlyph[v]}
                          label={verdictLabel[v]}
                          value={String(
                            (payload.find((p) => p.dataKey === v)?.value as number) ?? 0,
                          )}
                        />
                      ))}
                      <div className="mt-1 border-t border-[color:var(--color-hairline)] pt-1">
                        <TooltipRow
                          color={ink.secondary}
                          glyph="▬"
                          label="Ground-Truth Faults"
                          value={String(
                            (payload.find((p) => p.dataKey === "ground_truth_faults")
                              ?.value as number) ?? 0,
                          )}
                        />
                      </div>
                    </TooltipShell>
                  ) : null
                }
              />
              {VERDICT_ORDER.map((v, i) => (
                <Bar
                  key={v}
                  dataKey={v}
                  stackId="verdict"
                  fill={verdictColor[v]}
                  stroke={ink.surface}
                  strokeWidth={2}
                  maxBarSize={18}
                  radius={i === VERDICT_ORDER.length - 1 ? [3, 3, 0, 0] : undefined}
                />
              ))}
              <Line
                type="monotone"
                dataKey="ground_truth_faults"
                stroke={ink.secondary}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, stroke: ink.surface, strokeWidth: 2 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card
        title={tab === "alerts" ? "Evaluated Alert Candidates" : "Clustered Service Incidents"}
        subtitle={
          tab === "alerts"
            ? "Select any alert row to inspect the LLM judge rationale, top-6 retrieved telemetry events, and Baseline Evidence Gate verification."
            : "Confirmed alerts grouped by 300s call-graph correlation. Select an incident card to explore its propagation topology and remediation report."
        }
        right={
          <Segmented
            value={tab}
            onChange={(v) => setTab(v as "alerts" | "incidents")}
            options={[
              { value: "alerts", label: `Alerts (${filtered.length})` },
              { value: "incidents", label: `Incidents (${incidentsQ.data?.length ?? 0})` },
            ]}
          />
        }
        className="overflow-hidden"
      >
        {tab === "alerts" ? (
          <AlertTable alerts={filtered} />
        ) : incidentsQ.loading ? (
          <Loading label="Loading grouped incidents…" />
        ) : (
          <IncidentTable incidents={incidentsQ.data ?? []} />
        )}
      </Card>
    </div>
  );
}

function originPillLabel(origin: Alert["evidence_origin"]): string {
  switch (origin) {
    case "graph":
      return "Neighbor Graph";
    case "local":
      return "Local Service";
    case "mixed":
      return "Local + Graph";
    default:
      return "No Telemetry";
  }
}

function AlertTable({ alerts }: { alerts: Alert[] }) {
  if (!alerts.length) return <Empty>No alert candidates match the current filters.</Empty>;
  return (
    <div className="max-h-[460px] overflow-auto">
      <table className="w-full border-collapse text-[12px]">
        <thead className="sticky top-0 z-10 bg-surface">
          <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] font-semibold tracking-wide text-ink-muted uppercase">
            <th className="py-2.5 pr-3">Timestamp (UTC)</th>
            <th className="py-2.5 pr-3">Service</th>
            <th className="py-2.5 pr-3">Verdict</th>
            <th className="py-2.5 pr-3 text-right">Anomaly</th>
            <th className="py-2.5 pr-3 text-right">Confidence</th>
            <th className="py-2.5 pr-3">Ground Truth</th>
            <th className="py-2.5 pr-3">Baseline Gate &amp; Provenance</th>
            <th className="py-2.5 text-right">Judge Latency</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((a) => (
            <tr
              key={a.alert_id}
              className="border-b border-[color:var(--color-hairline)] last:border-0 hover:bg-[color:var(--color-plane)]/80"
            >
              <td className="py-2 pr-3 tabular-nums whitespace-nowrap">
                <Link
                  to={`/alerts/${a.alert_id}`}
                  className="font-medium text-[color:var(--color-seq-550)] hover:underline"
                >
                  {stampUTC(a.ts)}
                </Link>
              </td>
              <td className="py-2 pr-3 font-mono text-[11px] text-ink">{a.service}</td>
              <td className="py-2 pr-3">
                <VerdictBadge verdict={a.verdict} />
              </td>
              <td className="py-2 pr-3 text-right tabular-nums text-ink-2">
                {num(a.anomaly_score, 2)}
              </td>
              <td className="py-2 pr-3 text-right tabular-nums text-ink-2">
                {num(a.confidence, 2)}
              </td>
              <td className="py-2 pr-3">
                {a.label.is_fault ? (
                  <span className="text-[11px] font-medium" style={{ color: status.critical }}>
                    ✱ {formatFaultType(a.label.fault_type)}
                  </span>
                ) : (
                  <span className="text-[11px] text-ink-muted">Normal Traffic</span>
                )}
              </td>
              <td className="py-2 pr-3">
                <div className="flex flex-wrap items-center gap-1">
                  {a.downgraded_by_anchoring ? (
                    <Pill tone="warn">
                      ↓ Suppressed ({a.raw_verdict ? verdictShortLabel[a.raw_verdict] : "Uncertain"})
                    </Pill>
                  ) : a.anchor_ids && a.anchor_ids.length > 0 ? (
                    <Pill tone="good">✓ p90 Anchor ({a.anchor_ids.length})</Pill>
                  ) : a.downgraded_by_evidence_rule ? (
                    <Pill tone="warn">Insufficient Evidence</Pill>
                  ) : (
                    <Pill>{originPillLabel(a.evidence_origin)}</Pill>
                  )}
                </div>
              </td>
              <td className="py-2 text-right tabular-nums whitespace-nowrap text-ink-2">
                {ms(a.llm_latency_ms)}
                {a.cache_hit && <span className="ml-1 text-[10.5px] text-ink-muted">· cache</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function IncidentTable({ incidents }: { incidents: Incident[] }) {
  if (!incidents.length) return <Empty>No grouped incidents recorded in this run.</Empty>;
  return (
    <ul className="grid gap-3.5 md:grid-cols-2 xl:grid-cols-3">
      {incidents.map((i) => {
        const hasGt = i.ground_truth_service !== null;
        const correct = hasGt && i.root_cause_service === i.ground_truth_service;
        return (
          <li key={i.incident_id}>
            <Link
              to={`/incidents/${i.incident_id}`}
              className="block rounded-xl border border-[color:var(--color-hairline)] bg-surface p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.02)] transition-all hover:border-[color:var(--color-seq-550)] hover:bg-[color:var(--color-plane)]/50"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-[11px] text-ink-muted">{i.incident_id}</span>
                <span
                  className="text-[11px] font-semibold"
                  style={{
                    color: !i.root_cause_service
                      ? status.warning
                      : !hasGt
                        ? ink.muted
                        : correct
                          ? status.good
                          : status.critical,
                  }}
                >
                  {!i.root_cause_service
                    ? "⚠ Unresolved"
                    : !hasGt
                      ? "○ Normal Cluster (FP)"
                      : correct
                        ? "✓ Exact Root Cause"
                        : "✗ Mismatched Root"}
                </span>
              </div>
              <div className="mt-2 text-[13.5px] font-semibold text-ink">
                {i.root_cause_service ?? "—"}
                <span className="ml-2 text-[11px] font-normal text-ink-muted">
                  ground truth: {i.ground_truth_service ?? "normal"}
                </span>
              </div>
              <div className="mt-1.5 font-mono text-[11px] text-ink-2">
                {i.services.join("  →  ")}
              </div>
              <dl className="mt-2.5 border-t border-[color:var(--color-hairline)] pt-2">
                <KV k="Fault Category" v={formatFaultType(i.fault_type)} />
                <KV k="Time Window" v={`${clockUTC(i.start_ts)} – ${clockUTC(i.end_ts)} UTC`} />
                <KV k="Member Alerts" v={i.alert_ids.length} />
              </dl>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

function Segmented({
  label,
  value,
  onChange,
  options,
}: {
  label?: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string; glyph?: string; color?: string }[];
}) {
  return (
    <div className="flex flex-col gap-1">
      {label && <span className="text-[11px] font-medium text-ink-muted">{label}</span>}
      <div className="flex flex-wrap rounded-lg border border-[color:var(--color-hairline)] bg-surface p-0.5 shadow-[0_1px_2px_rgba(15,23,42,0.02)]">
        {options.map((o) => (
          <button
            key={o.value}
            type="button"
            onClick={() => onChange(o.value)}
            className={cx(
              "flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11.5px] transition-colors",
              value === o.value
                ? "bg-[color:var(--color-plane)] font-semibold text-ink"
                : "text-ink-muted hover:text-ink-2",
            )}
          >
            {o.glyph && (
              <span aria-hidden style={{ color: o.color }}>
                {o.glyph}
              </span>
            )}
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function bucketise(alerts: Alert[], useFullGt: boolean) {
  const size = BUCKET_MINUTES * 60_000;
  const map = new Map<
    number,
    { TRUE_ALERT: number; FALSE_POSITIVE: number; UNCERTAIN: number; ground_truth_faults: number }
  >();
  if (useFullGt) {
    for (const g of groundTruthBuckets) {
      map.set(g.ts_ms, {
        TRUE_ALERT: 0,
        FALSE_POSITIVE: 0,
        UNCERTAIN: 0,
        ground_truth_faults: g.faults,
      });
    }
  }
  for (const a of alerts) {
    const key = Math.floor(Date.parse(a.ts) / size) * size;
    const row =
      map.get(key) ??
      { TRUE_ALERT: 0, FALSE_POSITIVE: 0, UNCERTAIN: 0, ground_truth_faults: 0 };
    row[a.verdict] += 1;
    if (!useFullGt && a.label.is_fault) row.ground_truth_faults += 1;
    map.set(key, row);
  }
  return [...map.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([ts, row]) => ({
      label: stampUTC(new Date(ts).toISOString()).slice(5, 16),
      ...row,
    }));
}

function summarise(alerts: Alert[]) {
  let tp = 0;
  let fp = 0;
  let anchoredDown = 0;
  let anchoredConfirmed = 0;
  for (const a of alerts) {
    if (a.verdict === "TRUE_ALERT") a.label.is_fault ? tp++ : fp++;
    if (a.downgraded_by_anchoring) anchoredDown++;
    if (a.anchor_ids && a.anchor_ids.length > 0) anchoredConfirmed++;
  }
  return { tp, fp, anchoredDown, anchoredConfirmed };
}
