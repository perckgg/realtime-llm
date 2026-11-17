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
import { api } from "@/api/client";
import type { Alert, Incident, Verdict } from "@/api/types";
import { Legend, TooltipRow, TooltipShell, axisProps } from "@/components/charts";
import { Card, Empty, ErrorBox, KV, Loading, Pill, StatTile, VerdictBadge } from "@/components/ui";
import { clockUTC, cx, dayUTC, ms, num, pct, policySteps, stampUTC, useAsync } from "@/lib/util";
import { ink, status, verdictColor, verdictGlyph, verdictLabel, VERDICT_ORDER } from "@/theme/tokens";
import { useRuns } from "@/lib/runContext";

const BUCKET_MINUTES = 10;

type VerdictFilter = Verdict | "ALL";

export default function Timeline() {
  const { runs, runId, setRunId, runsLoading, runsError } = useRuns();
  const [verdict, setVerdict] = useState<VerdictFilter>("ALL");
  const [service, setService] = useState("ALL");
  const [tab, setTab] = useState<"alerts" | "incidents">("alerts");

  const activeRun = runs.find((r) => r.run_id === runId);
  const rcaOnlyRun = Boolean(activeRun && activeRun.alert_count === 0);
  const defaultPipelineRun = runs.find((r) => r.alert_count > 0);

  const alertsQ = useAsync(
    () => (runId && !rcaOnlyRun ? api.listAlerts({ runId }) : Promise.resolve<Alert[]>([])),
    [runId, rcaOnlyRun],
  );
  const incidentsQ = useAsync(
    () => (runId ? api.listIncidents(runId) : Promise.resolve<Incident[]>([])),
    [runId],
  );

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

  const buckets = useMemo(() => bucketise(filtered), [filtered]);
  const stats = useMemo(() => summarise(filtered), [filtered]);

  if (runsLoading) return <Loading label="Loading runs…" />;
  if (runsError) return <ErrorBox message={runsError} />;
  if (!runId) return <Empty>No runs have been ingested into the database yet.</Empty>;
  if (alertsQ.loading) return <Loading label={`Loading alerts for ${runId}…`} />;
  if (alertsQ.error) return <ErrorBox message={alertsQ.error} />;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <Segmented
          label="Verdict"
          value={verdict}
          onChange={(v) => setVerdict(v as VerdictFilter)}
          options={[
            { value: "ALL", label: "All" },
            ...VERDICT_ORDER.map((v) => ({
              value: v,
              label: verdictLabel[v],
              glyph: verdictGlyph[v],
              color: verdictColor[v],
            })),
          ]}
        />
        <label className="flex flex-col gap-1 text-[11px] text-ink-muted">
          Service
          <select
            value={service}
            onChange={(e) => setService(e.target.value)}
            className="rounded-md border border-[color:var(--color-hairline)] bg-surface px-2 py-1.5 text-[12px] text-ink"
          >
            {services.map((s) => (
              <option key={s} value={s}>
                {s === "ALL" ? "All services" : s}
              </option>
            ))}
          </select>
        </label>
        <div className="ml-auto text-[11px] text-ink-muted">
          {filtered.length} / {alerts.length} alerts · {BUCKET_MINUTES}m buckets
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Alerts" value={String(filtered.length)} hint={`of ${alerts.length} in run`} />
        <StatTile
          label="Confirmed Alerts"
          value={String(stats.tp + stats.fp)}
          hint={`${stats.tp} matched label · ${stats.fp} FP`}
          accent={verdictColor.TRUE_ALERT}
        />
        <StatTile
          label="Precision"
          value={stats.tp + stats.fp ? num(stats.tp / (stats.tp + stats.fp), 3) : "—"}
          hint="TRUE_ALERT matching Nezha fault label"
        />
        <StatTile
          label="Downgraded by CTAV (C3)"
          value={String(stats.anchored)}
          hint={`total policy downgrades ${stats.policyDowngraded} · Rescue ${stats.rescue}`}
          accent={status.warning}
        />
      </div>

      <Card
        title="Alerts over time by verdict"
        subtitle={`Stacked bars: alerts per ${BUCKET_MINUTES}-minute bucket. Solid line: ground-truth fault windows in Nezha (same unit — window count — shared axis).`}
        right={
          <Legend
            items={[
              ...VERDICT_ORDER.map((v) => ({
                key: v,
                label: verdictLabel[v],
                color: verdictColor[v],
                glyph: verdictGlyph[v],
              })),
              { key: "gt", label: "Ground-truth faults", color: ink.secondary, glyph: "▬" },
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
                cursor={{ fill: "rgb(11 11 11 / 0.04)" }}
                content={({ active, payload, label }) => {
                  const fullLabel = (
                    payload?.[0]?.payload as { fullLabel?: string } | undefined
                  )?.fullLabel;
                  return active && payload?.length ? (
                    <TooltipShell title={fullLabel ?? `${label} UTC`}>
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
                          label="Ground-truth faults"
                          value={String(
                            (payload.find((p) => p.dataKey === "ground_truth_faults")
                              ?.value as number) ?? 0,
                          )}
                        />
                      </div>
                    </TooltipShell>
                  ) : null;
                }}
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
        title={tab === "alerts" ? "Alert list" : "Grouped incidents"}
        subtitle={
          tab === "alerts"
            ? "Alert-level table backing the chart above. Click a timestamp to inspect Alert Detail."
            : "Alerts grouped by temporal window and trace dependency edges. Click to open Incident Detail."
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
          rcaOnlyRun ? (
            <div className="space-y-3 rounded-lg border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)] p-4 text-[12.5px] text-ink-2">
              <p>
                Run <span className="font-mono font-medium text-ink">{runId}</span> is an M9 RCA-only
                run (0 alerts in ClickHouse; {incidentsQ.data?.length ?? 0} incidents in PostgreSQL).
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setTab("incidents")}
                  className="rounded border border-[color:var(--color-hairline)] bg-surface px-3 py-1 text-[11.5px] font-medium text-ink hover:bg-[color:var(--color-plane)]"
                >
                  View Incidents tab ({incidentsQ.data?.length ?? 0})
                </button>
                {defaultPipelineRun && (
                  <button
                    type="button"
                    onClick={() => setRunId(defaultPipelineRun.run_id)}
                    className="rounded border border-[color:var(--color-hairline)] bg-surface px-3 py-1 text-[11.5px] text-ink-2 hover:text-ink"
                  >
                    Switch to {defaultPipelineRun.run_id}
                  </button>
                )}
              </div>
            </div>
          ) : (
            <AlertTable
              key={`${runId}-${verdict}-${service}-${filtered.length}`}
              alerts={filtered}
              runId={runId}
            />
          )
        ) : incidentsQ.loading ? (
          <Loading />
        ) : incidentsQ.error ? (
          <ErrorBox message={incidentsQ.error} />
        ) : (
          <IncidentTable incidents={incidentsQ.data ?? []} />
        )}
      </Card>
    </div>
  );
}

const ALERT_PAGE_SIZE = 200;

function AlertTable({ alerts, runId }: { alerts: Alert[]; runId: string }) {
  const [page, setPage] = useState(0);
  if (!alerts.length) return <Empty>No alerts match the current filter.</Empty>;
  const totalPages = Math.max(1, Math.ceil(alerts.length / ALERT_PAGE_SIZE));
  const safePage = Math.min(page, totalPages - 1);
  const start = safePage * ALERT_PAGE_SIZE;
  const visible = alerts.slice(start, start + ALERT_PAGE_SIZE);

  return (
    <div>
      {totalPages > 1 && (
        <div className="mb-2 flex items-center justify-between text-[11px] text-ink-muted">
          <span>
            Showing {start + 1}–{Math.min(start + ALERT_PAGE_SIZE, alerts.length)} of{" "}
            {alerts.length} alerts
          </span>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              disabled={safePage === 0}
              onClick={() => setPage(Math.max(0, safePage - 1))}
              className="rounded border border-[color:var(--color-hairline)] px-2 py-0.5 text-ink disabled:opacity-40"
            >
              Prev
            </button>
            <span className="tabular-nums">
              Page {safePage + 1}/{totalPages}
            </span>
            <button
              type="button"
              disabled={safePage >= totalPages - 1}
              onClick={() => setPage(Math.min(totalPages - 1, safePage + 1))}
              className="rounded border border-[color:var(--color-hairline)] px-2 py-0.5 text-ink disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
      <div className="max-h-[460px] overflow-auto">
        <table className="w-full border-collapse text-[12px]">
          <thead className="sticky top-0 bg-surface">
            <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] text-ink-muted">
              <th className="py-2 pr-3 font-medium">Timestamp (UTC)</th>
              <th className="py-2 pr-3 font-medium">Service</th>
              <th className="py-2 pr-3 font-medium">Verdict</th>
              <th className="py-2 pr-3 font-medium">CTAV (tier · origin)</th>
              <th className="py-2 pr-3 text-right font-medium">Anomaly</th>
              <th className="py-2 pr-3 text-right font-medium">Confidence</th>
              <th className="py-2 pr-3 font-medium">Label</th>
              <th className="py-2 pr-3 text-right font-medium">Retrieval</th>
              <th className="py-2 pr-3 text-right font-medium">LLM</th>
              <th className="py-2 font-medium">Source</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((a) => {
              const steps = policySteps(a);
              const targetRunId = a.run_id || runId;
              return (
                <tr
                  key={a.alert_id}
                  className="border-b border-[color:var(--color-hairline)] last:border-0 hover:bg-[color:var(--color-plane)]"
                >
                  <td className="py-1.5 pr-3 tabular-nums whitespace-nowrap">
                    <Link
                      to={`/alerts/${a.alert_id}?run_id=${encodeURIComponent(targetRunId)}`}
                      className="hover:underline"
                    >
                      {stampUTC(a.ts)}
                    </Link>
                  </td>
                  <td className="py-1.5 pr-3 font-mono text-[11px]">{a.service}</td>
                  <td className="py-1.5 pr-3">
                    <VerdictBadge verdict={a.verdict} />
                    {a.raw_verdict && a.raw_verdict !== a.verdict && (
                      <div className="mt-0.5 text-[10px] text-ink-muted">
                        raw: {verdictLabel[a.raw_verdict] ?? a.raw_verdict}
                      </div>
                    )}
                  </td>
                  <td className="py-1.5 pr-3 text-[11px] text-ink-2">
                    <div>
                      T{a.routing_tier ?? "—"} · {a.evidence_origin ?? "—"}
                    </div>
                    {steps.shortReason && <Pill tone="warn">{steps.shortReason}</Pill>}
                  </td>
                  <td className="py-1.5 pr-3 text-right tabular-nums">
                    {num(a.anomaly_score, 2)}
                  </td>
                  <td className="py-1.5 pr-3 text-right tabular-nums">
                    {num(a.confidence, 2)}
                  </td>
                  <td className="py-1.5 pr-3">
                    {a.label.is_fault ? (
                      <span className="text-[11px]" style={{ color: status.critical }}>
                        ✱ {a.label.fault_type}
                      </span>
                    ) : (
                      <span className="text-[11px] text-ink-muted">normal</span>
                    )}
                  </td>
                  <td className="py-1.5 pr-3 text-right tabular-nums text-ink-2">
                    {ms(a.retrieval_latency_ms)}
                  </td>
                  <td className="py-1.5 pr-3 text-right tabular-nums text-ink-2">
                    {ms(a.llm_latency_ms)}
                    {a.cache_hit && <span className="ml-1 text-ink-muted">·cache</span>}
                  </td>
                  <td className="py-1.5">
                    <Pill tone={a.candidate_source === "rescue" ? "warn" : "neutral"}>
                      {a.candidate_source}
                    </Pill>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function IncidentTable({ incidents }: { incidents: Incident[] }) {
  if (!incidents.length) return <Empty>No grouped incidents in this run.</Empty>;
  return (
    <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {incidents.map((i) => {
        const hasGt =
          i.ground_truth_service !== null && i.ground_truth_service !== undefined;
        const correct = hasGt && i.root_cause_service === i.ground_truth_service;
        const badgeColor = !hasGt
          ? ink.muted
          : i.root_cause_service
            ? correct
              ? status.good
              : status.critical
            : status.warning;
        const badgeLabel = !hasGt
          ? "— unlabelled"
          : i.root_cause_service
            ? correct
              ? "✓ root match"
              : "✗ wrong root"
            : "⚠ rejected";
        return (
          <li key={i.incident_id}>
            <Link
              to={`/incidents/${i.incident_id}`}
              className="block rounded-lg border border-[color:var(--color-hairline)] p-3 transition-colors hover:bg-[color:var(--color-plane)]"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-[11px] text-ink-muted">{i.incident_id}</span>
                <span className="text-[11px] font-medium" style={{ color: badgeColor }}>
                  {badgeLabel}
                </span>
              </div>
              <div className="mt-2 text-[13px] font-semibold text-ink">
                {i.root_cause_service ?? "—"}
                <span className="ml-2 text-[11px] font-normal text-ink-muted">
                  label: {i.ground_truth_service ?? "none (no_fault / ambiguous)"}
                </span>
              </div>
              <div className="mt-1.5 text-[11px] text-ink-2">
                {i.services.join("  →  ")}
              </div>
              <dl className="mt-2 border-t border-[color:var(--color-hairline)] pt-1.5">
                <KV k="Fault type" v={i.fault_type ?? "—"} />
                <KV k="Window" v={`${clockUTC(i.start_ts)} – ${clockUTC(i.end_ts)}`} />
                <KV k="Alerts" v={i.alert_ids.length} />
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
      {label && <span className="text-[11px] text-ink-muted">{label}</span>}
      <div className="flex rounded-md border border-[color:var(--color-hairline)] bg-surface p-0.5">
        {options.map((o) => (
          <button
            key={o.value}
            type="button"
            onClick={() => onChange(o.value)}
            className={cx(
              "flex items-center gap-1.5 rounded px-2.5 py-1 text-[11.5px] transition-colors",
              value === o.value
                ? "bg-[color:var(--color-plane)] font-medium text-ink"
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

function bucketise(alerts: Alert[]) {
  const size = BUCKET_MINUTES * 60_000;
  const map = new Map<
    number,
    { TRUE_ALERT: number; FALSE_POSITIVE: number; UNCERTAIN: number; ground_truth_faults: number }
  >();
  for (const a of alerts) {
    const key = Math.floor(Date.parse(a.ts) / size) * size;
    const row =
      map.get(key) ??
      { TRUE_ALERT: 0, FALSE_POSITIVE: 0, UNCERTAIN: 0, ground_truth_faults: 0 };
    row[a.verdict] += 1;
    if (a.label.is_fault) row.ground_truth_faults += 1;
    map.set(key, row);
  }
  const sorted = [...map.entries()].sort((a, b) => a[0] - b[0]);
  let prevDay = "";
  return sorted.map(([ts, row]) => {
    const iso = new Date(ts).toISOString();
    const day = dayUTC(iso);
    const ddmm = `${day.slice(8, 10)}/${day.slice(5, 7)}`;
    const hhmm = clockUTC(iso).slice(0, 5);
    const showDate = day !== prevDay;
    prevDay = day;
    return {
      label: showDate ? `${ddmm} ${hhmm}` : hhmm,
      fullLabel: `${ddmm} ${hhmm} UTC`,
      ...row,
    };
  });
}

function summarise(alerts: Alert[]) {
  let tp = 0;
  let fp = 0;
  let rescue = 0;
  let anchored = 0;
  let policyDowngraded = 0;
  for (const a of alerts) {
    if (a.verdict === "TRUE_ALERT") (a.label.is_fault ? tp++ : fp++);
    if (a.candidate_source === "rescue") rescue++;
    const steps = policySteps(a);
    if (steps.anchoring.status === "downgraded") anchored++;
    if (steps.shortReason !== null) policyDowngraded++;
  }
  return {
    tp,
    fp,
    rescue,
    anchored,
    policyDowngraded,
    coverage: alerts.length ? pct(tp / alerts.length) : "—",
  };
}
