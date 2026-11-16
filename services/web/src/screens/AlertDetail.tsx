import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/api/client";
import type { Alert, ContextEvent } from "@/api/types";
import { TooltipRow, TooltipShell, axisProps } from "@/components/charts";
import { Card, ErrorBox, KV, Loading, Pill, StatTile, VerdictBadge } from "@/components/ui";
import { clockUTC, cx, ms, num, stampUTC, useAsync } from "@/lib/util";
import {
  formatFaultType,
  ink,
  modalityLabel,
  sequential,
  series,
  status,
  strategyLabel,
  verdictLabel,
} from "@/theme/tokens";

const MODALITY_GLYPH: Record<ContextEvent["modality"], string> = {
  log: "▤",
  trace: "⟶",
  metric: "∿",
};

function formatOrigin(origin: Alert["evidence_origin"]): string {
  switch (origin) {
    case "graph":
      return "Neighbor Graph";
    case "local":
      return "Local Service";
    case "mixed":
      return "Local + Neighbor";
    default:
      return "None";
  }
}

export default function AlertDetail() {
  const { alertId = "" } = useParams();
  const { data: a, loading, error } = useAsync(() => api.getAlert(alertId), [alertId]);

  if (loading) return <Loading label="Loading alert inspection…" />;
  if (error || !a) return <ErrorBox message={error ?? `Alert '${alertId}' not found`} />;

  const evidence = new Set(a.evidence_event_ids);
  const alertTime = clockUTC(a.ts).slice(0, 5);
  const anchorCount = a.anchor_ids?.length ?? 0;

  return (
    <div className="space-y-5">
      <Link
        to="/timeline"
        className="inline-flex items-center gap-1 text-[12px] font-medium text-ink-muted hover:text-ink"
      >
        ← Back to Timeline
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-[20px] font-semibold tracking-tight text-ink">{a.service}</h1>
            <VerdictBadge verdict={a.verdict} />
            {a.downgraded_by_anchoring && (
              <Pill tone="warn">
                ↓ Suppressed by Baseline Gate ({a.raw_verdict} → {a.verdict})
              </Pill>
            )}
            {!a.downgraded_by_anchoring && anchorCount > 0 && (
              <Pill tone="good">
                ✓ Baseline Anchor Verified ({anchorCount} {anchorCount === 1 ? "span" : "spans"} &gt; p90)
              </Pill>
            )}
            {a.downgraded_by_evidence_rule && (
              <Pill tone="warn">⚠ Downgraded: Missing Evidence Citations</Pill>
            )}
          </div>
          <p className="mt-1 font-mono text-[11px] text-ink-muted">
            {a.alert_id} · Window {a.window_id} · {stampUTC(a.ts)}
          </p>
        </div>
        <div className="rounded-lg border border-[color:var(--color-hairline)] bg-surface px-3 py-2 text-right text-[11px] text-ink-muted">
          <div className="font-semibold text-ink">{strategyLabel[a.retrieval_strategy]}</div>
          <div className="font-mono">{a.run_id}</div>
        </div>
      </div>

      {a.downgraded_by_anchoring && (
        <div
          className="rounded-xl border px-4 py-3 text-[12px]"
          style={{
            borderColor: `${status.serious}88`,
            background: `color-mix(in srgb, ${status.serious} 10%, ${ink.surface})`,
            color: ink.primary,
          }}
        >
          <span className="font-semibold text-[#9a3412]">
            Baseline Evidence Gate Triggered ({a.raw_verdict} → {a.verdict}):{" "}
          </span>
          <span className="text-ink-2">
            The LLM judge initially flagged this window from correlated neighbor signals, but local spans at{" "}
            <code className="font-mono font-medium text-ink">{a.service}</code> remained within the historical p90 latency baseline and exhibited no local ERROR/WARN logs.
          </span>
        </div>
      )}

      {!a.downgraded_by_anchoring && anchorCount > 0 && (
        <div
          className="rounded-xl border px-4 py-3 text-[12px]"
          style={{
            borderColor: `${status.good}77`,
            background: `color-mix(in srgb, ${status.good} 8%, ${ink.surface})`,
            color: ink.primary,
          }}
        >
          <span className="font-semibold text-[#065f46]">
            Baseline Evidence Gate Passed ({anchorCount} anchored {anchorCount === 1 ? "event" : "events"}):{" "}
          </span>
          <span className="text-ink-2">
            Positive confirmation is corroborated by local telemetry evidence exceeding historical p90 baseline latency at{" "}
            <code className="font-mono font-medium text-ink">{a.service}</code>.
          </span>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3.5 md:grid-cols-4">
        <StatTile
          label="Anomaly Score"
          value={num(a.anomaly_score, 2)}
          hint={`Detector threshold: ${a.detector_threshold}`}
        />
        <StatTile
          label="Judge Confidence"
          value={num(a.confidence, 2)}
          hint={`${a.judge_backend}${a.threshold_applied ? ` · Confidence Threshold: ${num(a.threshold_applied, 2)}` : ""}`}
        />
        <StatTile
          label="Retrieved Context"
          value={`${a.context_event_count} events`}
          hint={`${a.context_tokens.toLocaleString("en-US")} tokens · Provenance: ${formatOrigin(a.evidence_origin)}`}
        />
        <StatTile
          label="Ground Truth Label"
          value={a.label.is_fault ? "Injected Fault" : "Normal Traffic"}
          hint={
            a.label.is_fault
              ? `${formatFaultType(a.label.fault_type)} @ ${a.label.root_cause_service}`
              : "No fault injected in window"
          }
          accent={a.label.is_fault ? status.critical : undefined}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
        <Card
          title={`Pod Anomaly Score Profile — ${a.pod ?? a.service}`}
          subtitle="Recorded Isolation Forest anomaly trajectory around the target window. Dashed red line indicates detector threshold (0.85); dashed blue vertical marker denotes this window."
        >
          <div className="h-[230px]">
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
                <ReferenceLine x={alertTime} stroke={series[0]} strokeWidth={2} strokeDasharray="3 3" />
                <ReferenceLine
                  y={a.detector_threshold}
                  stroke={status.critical}
                  strokeDasharray="4 4"
                  label={{
                    value: `Threshold ${a.detector_threshold}`,
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
          <Card
            title="LLM Judge Assessment"
            subtitle={`${a.judge_backend} · ${ms(a.llm_latency_ms)}${a.cache_hit ? " · Cache Hit" : ""}`}
          >
            <p className="text-[12.5px] leading-relaxed text-ink-2">{a.reasoning}</p>
            <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-[color:var(--color-hairline)] pt-2.5 text-[11px] text-ink-muted">
              <span>Cited Event IDs:</span>
              {a.evidence_event_ids.length
                ? a.evidence_event_ids.map((id) => <Pill key={id}>{id}</Pill>)
                : "None — automatically downgraded to Uncertain"}
            </div>
          </Card>

          <Card title="Validation Pipeline Metadata">
            <dl className="divide-y divide-[color:var(--color-hairline)]">
              <KV k="Candidate ID" v={<span className="font-mono">{a.candidate_id}</span>} />
              <KV
                k="Initial LLM Verdict"
                v={verdictLabel[a.raw_verdict ?? a.verdict]}
              />
              <KV k="Final Calibrated Verdict" v={verdictLabel[a.verdict]} />
              <KV k="Evidence Provenance" v={formatOrigin(a.evidence_origin)} />
              <KV
                k="Baseline Evidence Gate"
                v={a.downgraded_by_anchoring ? "Suppressed (No >p90 Anchor)" : anchorCount > 0 ? `Anchored (${anchorCount})` : "Passed"}
              />
              <KV k="Retrieval Latency" v={ms(a.retrieval_latency_ms)} />
              <KV k="Judge Latency" v={ms(a.llm_latency_ms)} />
              <KV k="Prompt Cache" v={a.cache_hit ? "Hit" : "Miss"} />
            </dl>
          </Card>
        </div>
      </div>

      <Card
        title={`Retrieved Multi-Modal Evidence (${a.context_events.length} events)`}
        subtitle="Ranked by retrieval fusion score. Confirmed alerts require corroboration from local ERROR/WARN logs or trace spans exceeding the historical p90 latency baseline."
      >
        <ol className="space-y-2.5">
          {a.context_events.length ? (
            a.context_events.map((e, i) => (
              <EventRow key={e.event_id} e={e} rank={i + 1} cited={evidence.has(e.event_id)} />
            ))
          ) : (
            <p className="text-[12px] text-ink-muted">
              No supporting telemetry events were retrieved within the ±8 minute search window.
            </p>
          )}
        </ol>
      </Card>
    </div>
  );
}

function EventRow({ e, rank, cited }: { e: ContextEvent; rank: number; cited: boolean }) {
  const [open, setOpen] = useState(false);
  const dur = typeof e.debug.duration_ms === "number" ? e.debug.duration_ms : null;
  const dev90 = typeof e.debug.dev_p90_ms === "number" ? e.debug.dev_p90_ms : null;

  return (
    <li
      className={cx(
        "rounded-xl border p-3.5 transition-colors",
        cited ? "bg-[color:var(--color-plane)]/70" : "bg-surface",
      )}
      style={{ borderColor: e.is_c3_anchor ? status.good : cited ? series[0] : "var(--color-hairline)" }}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="w-5 font-mono text-[11px] font-medium tabular-nums text-ink-muted">
          #{rank}
        </span>
        <Pill>
          <span aria-hidden className="mr-0.5">
            {MODALITY_GLYPH[e.modality]}
          </span>
          {modalityLabel[e.modality]}
        </Pill>
        <span className="font-mono text-[11.5px] font-semibold text-ink">{e.service}</span>
        <span className="text-[11px] tabular-nums text-ink-muted">{clockUTC(e.ts)} UTC</span>
        {e.origin && (
          <Pill tone={e.origin === "graph" ? "info" : "neutral"}>
            {e.origin === "graph" ? `Neighbor (hop=${e.graph_distance ?? 1})` : "Local Service"}
          </Pill>
        )}
        {e.is_c3_anchor && <Pill tone="good">✓ Baseline Anchor (&gt; p90)</Pill>}
        {cited && (
          <span className="text-[11px] font-semibold" style={{ color: series[0] }}>
            ● Cited by Judge
          </span>
        )}
        {dur !== null && (
          <span className="font-mono text-[10.5px] text-ink-2">
            Span: {num(dur, 1)} ms{" "}
            {dev90 !== null ? `(p90 baseline: ${num(dev90, 1)} ms)` : "(no p90 baseline)"}
          </span>
        )}
        <span className="ml-auto flex items-center gap-2">
          <span className="h-1.5 w-24 rounded-full" style={{ background: ink.grid }}>
            <span
              className="block h-1.5 rounded-full"
              style={{ width: `${Math.min(1, e.score) * 100}%`, background: sequential[1] }}
            />
          </span>
          <span className="w-9 text-right text-[11px] tabular-nums font-medium text-ink">
            {num(e.score, 2)}
          </span>
        </span>
      </div>
      <p className="mt-2 font-mono text-[11.5px] leading-relaxed break-words text-ink-2">
        {e.content}
      </p>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="mt-2 text-[11px] font-medium text-ink-muted hover:text-ink"
      >
        {open ? "▾" : "▸"} telemetry metadata
      </button>
      {open && (
        <dl className="mt-2 grid grid-cols-2 gap-x-6 rounded-lg bg-[color:var(--color-plane)] p-3 md:grid-cols-3">
          {Object.entries(e.debug).map(([k, v]) => (
            <KV key={k} k={k} v={<span className="font-mono">{String(v)}</span>} />
          ))}
        </dl>
      )}
    </li>
  );
}
