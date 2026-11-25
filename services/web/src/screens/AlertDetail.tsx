import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/api/client";
import type { ContextEvent } from "@/api/types";
import { TooltipRow, TooltipShell, axisProps } from "@/components/charts";
import C1ContextExplainer from "@/components/C1ContextExplainer";
import { Card, Empty, ErrorBox, KV, Loading, Pill, StatTile, VerdictBadge } from "@/components/ui";
import { clockUTC, cx, ms, num, policySteps, stampUTC, useAsync } from "@/lib/util";
import { useRuns } from "@/lib/runContext";
import { ink, sequential, series, status, strategyLabel, verdictLabel } from "@/theme/tokens";

const MODALITY_GLYPH: Record<ContextEvent["modality"], string> = {
  log: "▤",
  trace: "⟶",
  metric: "∿",
};

export default function AlertDetail() {
  const { alertId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const { runId: contextRunId, groundTruthOverlay } = useRuns();
  const requestedRunId = searchParams.get("run_id") ?? (contextRunId || undefined);
  const { data: a, loading, error } = useAsync(
    () => api.getAlert(alertId, requestedRunId),
    [alertId, requestedRunId],
  );

  if (loading) return <Loading />;
  if (error || !a) return <ErrorBox message={error ?? "Alert not found"} />;

  const evidence = new Set(a.evidence_event_ids);
  const alertTime = clockUTC(a.ts).slice(0, 5);
  const steps = policySteps(a);
  const llmSubtitle = `${a.judge_backend} · ${ms(a.llm_latency_ms)} · ${
    a.cache_hit ? "cached inference" : "live inference"
  }`;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 text-[11.5px] text-ink-muted">
        <Link to="/timeline" className="hover:text-ink">
          ← Alert Stream
        </Link>
        <span>·</span>
        <Link to="/overview" className="hover:text-ink">
          Operations
        </Link>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="font-mono text-[19px] font-semibold tracking-tight text-ink">{a.service}</h1>
            <VerdictBadge verdict={a.verdict} />
            {a.downgraded_by_anchoring && (
              <Pill tone="warn">Downgraded by C3 anchoring</Pill>
            )}
            {a.downgraded_by_gating && (
              <Pill tone="warn">Downgraded by C2 gating</Pill>
            )}
            {a.downgraded_by_evidence_rule && (
              <Pill tone="critical">Downgraded by evidence rule</Pill>
            )}
          </div>
          <p className="mt-1 font-mono text-[11px] text-ink-muted">
            {a.alert_id} · window {a.window_id} · {stampUTC(a.ts)} UTC
          </p>
        </div>
        <div className="text-right text-[11px] text-ink-muted">
          <div className="font-medium text-ink-2">{strategyLabel[a.retrieval_strategy]}</div>
          <div className="font-mono">{a.run_id}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Anomaly score" value={num(a.anomaly_score, 2)} hint={`threshold ${a.detector_threshold}`} />
        <StatTile label="Judge confidence" value={num(a.confidence, 2)} hint={a.judge_backend} />
        <StatTile label="Context events" value={`${a.context_event_count}`} hint={`${a.context_tokens.toLocaleString("en-US")} tokens${a.retrieval_truncated ? " · truncated" : ""}`} />
        {groundTruthOverlay ? (
          <StatTile
            label="Ground-Truth Label"
            value={a.label.is_fault ? "Fault" : "Normal"}
            hint={a.label.is_fault ? `${a.label.fault_type} @ ${a.label.root_cause_service}` : "no fault injection"}
            accent={a.label.is_fault ? status.critical : status.good}
          />
        ) : (
          <StatTile
            label="Evidence Origin"
            value={a.evidence_origin ?? "—"}
            hint={a.routing_tier === 2 ? "Tier 2 · Topology Graph" : "Tier 1 · Local BM25"}
            accent={a.downgraded_by_anchoring ? status.warning : "var(--color-accent)"}
          />
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
        <Card
          title={a.metric_name}
          subtitle="Anomaly score series around the alert window. Horizontal dashed line shows detector threshold; highlighted region marks the alerted window."
        >
          <div className="h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={a.metric_series.map((p) => ({ ...p, t: clockUTC(p.ts).slice(0, 5) }))}
                margin={{ top: 6, right: 10, bottom: 0, left: -20 }}
              >
                <defs>
                  <linearGradient id="alertFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={series[0]} stopOpacity={0.22} />
                    <stop offset="100%" stopColor={series[0]} stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke={ink.grid} />
                <XAxis dataKey="t" {...axisProps} minTickGap={24} />
                <YAxis {...axisProps} domain={[0, 1]} width={40} />
                <ReferenceArea x1={alertTime} x2={alertTime} fill={series[0]} fillOpacity={0.12} />
                <ReferenceLine
                  y={a.detector_threshold}
                  stroke={status.critical}
                  strokeDasharray="4 4"
                  label={{
                    value: `threshold ${a.detector_threshold}`,
                    position: "insideTopRight",
                    fill: status.critical,
                    fontSize: 10,
                  }}
                />
                <Tooltip
                  cursor={{ stroke: ink.axis, strokeWidth: 1 }}
                  content={({ active, payload, label }) =>
                    active && payload?.length ? (
                      <TooltipShell title={`${label} UTC`}>
                        <TooltipRow
                          color={series[0]}
                          label={a.metric_name}
                          value={num(payload[0]?.value as number, 3)}
                        />
                      </TooltipShell>
                    ) : null
                  }
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke={series[0]}
                  strokeWidth={2}
                  fill="url(#alertFill)"
                  activeDot={{ r: 4, stroke: ink.surface, strokeWidth: 2 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <div className="space-y-4">
          <Card title="LLM Verdict Reasoning" subtitle={llmSubtitle}>
            <p className="text-[12.5px] leading-relaxed text-ink-2">{a.reasoning}</p>
            <div className="mt-3 border-t border-[color:var(--color-hairline)] pt-2 text-[11px] text-ink-muted">
              Cited evidence:{" "}
              {a.evidence_event_ids.length
                ? a.evidence_event_ids.map((id) => <Pill key={id}>{id}</Pill>)
                : "none — evidence rule downgrades verdict to UNCERTAIN"}
            </div>
          </Card>

          {a.candidate_source === "rescue" && a.rescue_components && (
            <Card
              title="Rescue Score"
              subtitle={`Below detector threshold; promoted by Rescue Score ${num(a.rescue_score ?? 0, 2)}.`}
            >
              <div className="space-y-2">
                {(
                  [
                    ["λ log", a.rescue_components.lambda_log],
                    ["φ topo", a.rescue_components.phi_topo],
                    ["Δ time", a.rescue_components.delta_time],
                  ] as const
                ).map(([label, v]) => (
                  <div key={label} className="flex items-center gap-3">
                    <span className="w-14 shrink-0 text-[11px] text-ink-2">{label}</span>
                    <div className="h-2 flex-1 rounded-full" style={{ background: ink.grid }}>
                      <div
                        className="h-2 rounded-full"
                        style={{ width: `${v * 100}%`, background: series[0] }}
                      />
                    </div>
                    <span className="w-10 text-right text-[11px] tabular-nums text-ink">
                      {num(v, 2)}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <Card title="CTAV Decision Policy & Evidence Origin">
            <dl className="divide-y divide-[color:var(--color-hairline)]">
              <KV
                k="Raw → Final verdict"
                v={
                  <span className="font-mono">
                    {a.raw_verdict ? (verdictLabel[a.raw_verdict] ?? a.raw_verdict) : "—"} →{" "}
                    {verdictLabel[a.verdict] ?? a.verdict}
                  </span>
                }
              />
              <KV
                k="Routing tier"
                v={
                  a.routing_tier === 1
                    ? "Tier 1 (Local BM25)"
                    : a.routing_tier === 2
                      ? "Tier 2 (C1 Topology Graph)"
                      : "—"
                }
              />
              <KV
                k="Evidence origin"
                v={<Pill>{a.evidence_origin ?? "—"}</Pill>}
              />
              <KV
                k="Applied threshold"
                v={
                  a.threshold_applied !== null && a.threshold_applied !== undefined
                    ? num(a.threshold_applied, 2)
                    : "—"
                }
              />
              <KV
                k="C3 evidence anchoring"
                v={
                  <Pill tone={steps.anchoring.status === "downgraded" ? "warn" : "neutral"}>
                    {steps.anchoring.label}
                  </Pill>
                }
              />
              <KV
                k="C2 confidence gating"
                v={
                  <Pill tone={steps.gating.status === "downgraded" ? "warn" : "neutral"}>
                    {steps.gating.label}
                  </Pill>
                }
              />
              <KV
                k="Require-evidence rule"
                v={
                  <Pill tone={steps.evidenceRule.status === "downgraded" ? "warn" : "neutral"}>
                    {steps.evidenceRule.label}
                  </Pill>
                }
              />
            </dl>
          </Card>

          <Card title="Execution Metadata">
            <dl className="divide-y divide-[color:var(--color-hairline)]">
              <KV k="Candidate ID" v={<span className="font-mono">{a.candidate_id}</span>} />
              <KV k="Trigger source" v={a.candidate_source} />
              <KV k="Retrieval latency" v={ms(a.retrieval_latency_ms)} />
              <KV k="Judge latency" v={ms(a.llm_latency_ms)} />
              <KV
                k="Inference cache"
                v={a.cache_hit ? "cache hit" : "direct inference"}
              />
              <KV k="Context truncated" v={a.retrieval_truncated ? "yes" : "no"} />
            </dl>
          </Card>
        </div>
      </div>

      <C1ContextExplainer alert={a} />

      <Card
        title={`Retrieved RAG Evidence (${a.context_events.length})`}
        subtitle="Sorted by descending fusion score. Expand debug fields to inspect graph distance, time proximity, and provenance."
      >
        {a.context_events.length === 0 ? (
          <Empty>No context events retrieved in this window.</Empty>
        ) : (
          <ol className="space-y-2">
            {a.context_events.map((e, i) => (
              <EventRow key={e.event_id} e={e} rank={i + 1} cited={evidence.has(e.event_id)} />
            ))}
          </ol>
        )}
      </Card>
    </div>
  );
}

function EventRow({ e, rank, cited }: { e: ContextEvent; rank: number; cited: boolean }) {
  const [open, setOpen] = useState(false);
  const origin = e.debug.origin ? String(e.debug.origin) : null;
  const graphDist =
    e.debug.graph_distance !== undefined && e.debug.graph_distance !== null
      ? Number(e.debug.graph_distance)
      : null;
  const timeDistSec =
    e.debug.time_distance_sec !== undefined && e.debug.time_distance_sec !== null
      ? Number(e.debug.time_distance_sec)
      : null;
  const durationMs =
    e.debug.duration_ms !== undefined && e.debug.duration_ms !== null
      ? Number(e.debug.duration_ms)
      : null;

  return (
    <li
      className={cx(
        "rounded-lg border p-3",
        cited ? "bg-[color:var(--color-plane)]" : "",
      )}
      style={{ borderColor: cited ? series[0] : "var(--color-hairline)" }}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="w-5 text-[11px] tabular-nums text-ink-muted">#{rank}</span>
        <Pill>
          <span aria-hidden className="mr-1">
            {MODALITY_GLYPH[e.modality]}
          </span>
          {e.modality}
        </Pill>
        <span className="font-mono text-[11px] text-ink-2">{e.service}</span>
        <span className="text-[11px] text-ink-muted">{clockUTC(e.ts)}</span>
        {origin && (
          <Pill tone={origin === "graph" ? "warn" : "neutral"}>
            origin: {origin}
          </Pill>
        )}
        {graphDist !== null && !Number.isNaN(graphDist) && (
          <span className="font-mono text-[10.5px] text-ink-muted">d_G={graphDist}</span>
        )}
        {timeDistSec !== null && !Number.isNaN(timeDistSec) && (
          <span className="font-mono text-[10.5px] text-ink-muted">
            Δt={num(timeDistSec, 1)}s
          </span>
        )}
        {durationMs !== null && !Number.isNaN(durationMs) && (
          <span className="font-mono text-[10.5px] text-ink-muted">{ms(durationMs)}</span>
        )}
        {cited && (
          <span className="text-[11px] font-medium" style={{ color: series[0] }}>
            ● cited by LLM
          </span>
        )}
        <span className="ml-auto flex items-center gap-2">
          {/* Thanh điểm dùng sắc độ tuần tự của cùng một màu — độ lớn, không phải danh tính. */}
          <span className="h-1.5 w-24 rounded-full" style={{ background: ink.grid }}>
            <span
              className="block h-1.5 rounded-full"
              style={{ width: `${e.score * 100}%`, background: sequential[1] }}
            />
          </span>
          <span className="w-9 text-right text-[11px] tabular-nums text-ink">{num(e.score, 2)}</span>
        </span>
      </div>
      <p className="mt-2 font-mono text-[11.5px] leading-relaxed break-words text-ink-2">
        {e.content}
      </p>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="mt-1.5 text-[11px] text-ink-muted hover:text-ink-2"
      >
        {open ? "▾" : "▸"} debug
      </button>
      {open && (
        <dl className="mt-1 grid grid-cols-2 gap-x-6 rounded bg-[color:var(--color-plane)] p-2 md:grid-cols-3">
          {Object.entries(e.debug).map(([k, v]) => (
            <KV key={k} k={k} v={<span className="font-mono">{String(v)}</span>} />
          ))}
        </dl>
      )}
    </li>
  );
}
