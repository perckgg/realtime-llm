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
import type { ContextEvent } from "@/api/types";
import { TooltipRow, TooltipShell, axisProps } from "@/components/charts";
import { Card, ErrorBox, KV, Loading, Pill, StatTile, VerdictBadge } from "@/components/ui";
import { clockUTC, cx, ms, num, stampUTC, useAsync } from "@/lib/util";
import { ink, sequential, series, status, strategyLabel } from "@/theme/tokens";

const MODALITY_GLYPH: Record<ContextEvent["modality"], string> = {
  log: "▤",
  trace: "⟶",
  metric: "∿",
};

export default function AlertDetail() {
  const { alertId = "" } = useParams();
  const { data: a, loading, error } = useAsync(() => api.getAlert(alertId), [alertId]);

  if (loading) return <Loading />;
  if (error || !a) return <ErrorBox message={error ?? "Không tìm thấy cảnh báo"} />;

  const evidence = new Set(a.evidence_event_ids);
  const alertTime = clockUTC(a.ts).slice(0, 5);

  return (
    <div className="space-y-4">
      <Link to="/timeline" className="inline-block text-[11.5px] text-ink-muted hover:text-ink-2">
        ← Timeline
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-[19px] font-semibold tracking-tight text-ink">{a.service}</h1>
            <VerdictBadge verdict={a.verdict} />
            {a.downgraded_by_anchoring && (
              <Pill tone="warn">
                ⚠ C3 hạ cấp: {a.raw_verdict} → {a.verdict} (thiếu bằng chứng vượt dev p90)
              </Pill>
            )}
            {!a.downgraded_by_anchoring && a.anchor_ids && a.anchor_ids.length > 0 && (
              <Pill tone="good">
                ⚓ Neo C3 hợp lệ ({a.anchor_ids.length} span vượt dev p90)
              </Pill>
            )}
            {a.downgraded_by_evidence_rule && (
              <Pill tone="warn">⚠ hạ cấp do quy tắc thiếu bằng chứng</Pill>
            )}
          </div>
          <p className="mt-1 font-mono text-[11px] text-ink-muted">
            {a.alert_id} · window {a.window_id} · {stampUTC(a.ts)}
          </p>
        </div>
        <div className="text-right text-[11px] text-ink-muted">
          <div>{strategyLabel[a.retrieval_strategy]}</div>
          <div className="font-mono">{a.run_id}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Anomaly score" value={num(a.anomaly_score, 2)} hint={`ngưỡng ${a.detector_threshold}`} />
        <StatTile
          label="Confidence"
          value={num(a.confidence, 2)}
          hint={`${a.judge_backend}${a.threshold_applied ? ` · θ=${num(a.threshold_applied, 2)}` : ""}`}
        />
        <StatTile
          label="Ngữ cảnh"
          value={`${a.context_event_count}`}
          hint={`${a.context_tokens.toLocaleString("vi-VN")} token · origin=${a.evidence_origin ?? "none"}`}
        />
        <StatTile
          label="Nhãn Nezha"
          value={a.label.is_fault ? "Lỗi" : "Bình thường"}
          hint={a.label.is_fault ? `${a.label.fault_type} @ ${a.label.root_cause_service}` : "không có tiêm lỗi"}
          accent={a.label.is_fault ? status.critical : undefined}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
        <Card
          title={a.metric_name}
          subtitle="Chuỗi anomaly_score thật của cùng pod quanh cửa sổ cảnh báo. Đường ngang đỏ là ngưỡng detector 0,85; đường dọc xanh là cửa sổ hiện tại."
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
                <ReferenceLine x={alertTime} stroke={series[0]} strokeWidth={2} strokeDasharray="3 3" />
                <ReferenceLine
                  y={a.detector_threshold}
                  stroke={status.critical}
                  strokeDasharray="4 4"
                  label={{
                    value: `ngưỡng ${a.detector_threshold}`,
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
          <Card title="Lý do LLM ra verdict" subtitle={`${a.judge_backend} · ${ms(a.llm_latency_ms)}${a.cache_hit ? " · lấy từ cache" : ""}`}>
            <p className="text-[12.5px] leading-relaxed text-ink-2">{a.reasoning}</p>
            <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-[color:var(--color-hairline)] pt-2 text-[11px] text-ink-muted">
              <span>Bằng chứng LLM viện dẫn:</span>
              {a.evidence_event_ids.length
                ? a.evidence_event_ids.map((id) => <Pill key={id}>{id}</Pill>)
                : "không có — quy tắc bằng chứng sẽ hạ verdict xuống UNCERTAIN"}
            </div>
          </Card>

          <Card title="Siêu dữ liệu & Chính sách CTAV">
            <dl className="divide-y divide-[color:var(--color-hairline)]">
              <KV k="candidate_id" v={<span className="font-mono">{a.candidate_id}</span>} />
              <KV k="Raw verdict (LLM)" v={a.raw_verdict ?? a.verdict} />
              <KV k="Final verdict" v={a.verdict} />
              <KV k="Nguồn bằng chứng" v={a.evidence_origin ?? "none"} />
              <KV k="Hạ bởi C3 (dev p90)" v={a.downgraded_by_anchoring ? "có" : "không"} />
              <KV k="Độ trễ retrieval" v={ms(a.retrieval_latency_ms)} />
              <KV k="Độ trễ LLM" v={ms(a.llm_latency_ms)} />
              <KV k="Cache" v={a.cache_hit ? "hit" : "miss"} />
            </dl>
          </Card>
        </div>
      </div>

      <Card
        title={`Bằng chứng RAG đã truy xuất (${a.context_events.length})`}
        subtitle="Sắp theo điểm retrieval giảm dần. C3 chỉ giữ TRUE_ALERT khi có log ERROR/WARN hoặc span tại s₀ có duration_ms vượt ngưỡng nền dev p90."
      >
        <ol className="space-y-2">
          {a.context_events.length ? (
            a.context_events.map((e, i) => (
              <EventRow key={e.event_id} e={e} rank={i + 1} cited={evidence.has(e.event_id)} />
            ))
          ) : (
            <p className="text-[12px] text-ink-muted">Không truy xuất được sự kiện telemetry nào trong ±8 phút.</p>
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
        "rounded-lg border p-3",
        cited ? "bg-[color:var(--color-plane)]" : "",
      )}
      style={{ borderColor: e.is_c3_anchor ? status.good : cited ? series[0] : "var(--color-hairline)" }}
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
        {e.origin && (
          <Pill>{e.origin === "graph" ? `graph d=${e.graph_distance ?? "?"}` : "local"}</Pill>
        )}
        {e.is_c3_anchor && <Pill tone="good">⚓ Neo C3 (&gt; dev p90)</Pill>}
        {cited && (
          <span className="text-[11px] font-medium" style={{ color: series[0] }}>
            ● LLM viện dẫn
          </span>
        )}
        {dur !== null && (
          <span className="font-mono text-[10.5px] text-ink-2">
            dur={num(dur, 1)}ms {dev90 !== null ? `(dev p90=${num(dev90, 1)}ms)` : "(thiếu dev p90)"}
          </span>
        )}
        <span className="ml-auto flex items-center gap-2">
          <span className="h-1.5 w-24 rounded-full" style={{ background: ink.grid }}>
            <span
              className="block h-1.5 rounded-full"
              style={{ width: `${Math.min(1, e.score) * 100}%`, background: sequential[1] }}
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
