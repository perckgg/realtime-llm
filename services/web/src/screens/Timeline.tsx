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
import { clockUTC, cx, ms, num, pct, stampUTC, useAsync } from "@/lib/util";
import { ink, status, verdictColor, verdictGlyph, verdictLabel, VERDICT_ORDER } from "@/theme/tokens";
import { useRuns } from "@/lib/runContext";

const BUCKET_MINUTES = 10;

type VerdictFilter = Verdict | "ALL";

export default function Timeline() {
  const { runId } = useRuns();
  const [verdict, setVerdict] = useState<VerdictFilter>("ALL");
  const [service, setService] = useState("ALL");
  const [tab, setTab] = useState<"alerts" | "incidents">("alerts");

  const alertsQ = useAsync(() => api.listAlerts({ runId }), [runId]);
  const incidentsQ = useAsync(() => api.listIncidents(runId), [runId]);

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

  if (alertsQ.loading) return <Loading />;
  if (alertsQ.error) return <ErrorBox message={alertsQ.error} />;

  return (
    <div className="space-y-4">
      {/* Bộ lọc nằm trên một hàng, ngay phía trên biểu đồ nó điều khiển. */}
      <div className="flex flex-wrap items-end gap-3">
        <Segmented
          label="Verdict"
          value={verdict}
          onChange={(v) => setVerdict(v as VerdictFilter)}
          options={[
            { value: "ALL", label: "Tất cả" },
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
                {s === "ALL" ? "Tất cả service" : s}
              </option>
            ))}
          </select>
        </label>
        <div className="ml-auto text-[11px] text-ink-muted">
          {filtered.length} / {alerts.length} cảnh báo · gộp {BUCKET_MINUTES} phút
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Cảnh báo" value={String(filtered.length)} hint={`trên ${alerts.length} của run`} />
        <StatTile
          label="Đúng cảnh báo"
          value={String(stats.tp + stats.fp)}
          hint={`${stats.tp} khớp nhãn · ${stats.fp} sai`}
          accent={verdictColor.TRUE_ALERT}
        />
        <StatTile
          label="Precision"
          value={stats.tp + stats.fp ? num(stats.tp / (stats.tp + stats.fp), 3) : "—"}
          hint="TRUE_ALERT khớp nhãn Nezha"
        />
        <StatTile
          label="Từ Rescue Score"
          value={String(stats.rescue)}
          hint="cảnh báo được promote dù dưới ngưỡng"
          accent={status.warning}
        />
      </div>

      <Card
        title="Cảnh báo theo thời gian, tách theo verdict"
        subtitle={`Cột xếp chồng: số cảnh báo mỗi ${BUCKET_MINUTES} phút. Đường liền: số cửa sổ thực sự là lỗi theo nhãn Nezha. Cùng một đơn vị — số cửa sổ — nên dùng chung một trục.`}
        right={
          <Legend
            items={[
              ...VERDICT_ORDER.map((v) => ({
                key: v,
                label: verdictLabel[v],
                color: verdictColor[v],
                glyph: verdictGlyph[v],
              })),
              { key: "gt", label: "Lỗi theo nhãn", color: ink.secondary, glyph: "▬" },
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
                          label="Lỗi theo nhãn"
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
                  // Viền màu bề mặt tạo khe 2px giữa các đoạn xếp chồng.
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
        title={tab === "alerts" ? "Danh sách cảnh báo" : "Sự cố đã gom nhóm"}
        subtitle={
          tab === "alerts"
            ? "Bảng số liệu đi kèm biểu đồ ở trên. Bấm một dòng để mở màn hình chi tiết."
            : "Alert được gom theo cửa sổ thời gian và cạnh đồ thị phụ thuộc. Bấm để xem đồ thị lan truyền."
        }
        right={
          <Segmented
            value={tab}
            onChange={(v) => setTab(v as "alerts" | "incidents")}
            options={[
              { value: "alerts", label: `Cảnh báo (${filtered.length})` },
              { value: "incidents", label: `Sự cố (${incidentsQ.data?.length ?? 0})` },
            ]}
          />
        }
        className="overflow-hidden"
      >
        {tab === "alerts" ? (
          <AlertTable alerts={filtered} />
        ) : incidentsQ.loading ? (
          <Loading />
        ) : (
          <IncidentTable incidents={incidentsQ.data ?? []} />
        )}
      </Card>
    </div>
  );
}

function AlertTable({ alerts }: { alerts: Alert[] }) {
  if (!alerts.length) return <Empty>Không có cảnh báo nào khớp bộ lọc.</Empty>;
  return (
    <div className="max-h-[460px] overflow-auto">
      <table className="w-full border-collapse text-[12px]">
        <thead className="sticky top-0 bg-surface">
          <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] text-ink-muted">
            <th className="py-2 pr-3 font-medium">Thời điểm (UTC)</th>
            <th className="py-2 pr-3 font-medium">Service</th>
            <th className="py-2 pr-3 font-medium">Verdict</th>
            <th className="py-2 pr-3 text-right font-medium">Anomaly</th>
            <th className="py-2 pr-3 text-right font-medium">Confidence</th>
            <th className="py-2 pr-3 font-medium">Nhãn</th>
            <th className="py-2 pr-3 text-right font-medium">Retrieval</th>
            <th className="py-2 pr-3 text-right font-medium">LLM</th>
            <th className="py-2 font-medium">Nguồn</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((a) => (
            <tr
              key={a.alert_id}
              className="border-b border-[color:var(--color-hairline)] last:border-0 hover:bg-[color:var(--color-plane)]"
            >
              <td className="py-1.5 pr-3 tabular-nums whitespace-nowrap">
                <Link to={`/alerts/${a.alert_id}`} className="hover:underline">
                  {stampUTC(a.ts)}
                </Link>
              </td>
              <td className="py-1.5 pr-3 font-mono text-[11px]">{a.service}</td>
              <td className="py-1.5 pr-3">
                <VerdictBadge verdict={a.verdict} />
              </td>
              <td className="py-1.5 pr-3 text-right tabular-nums">{num(a.anomaly_score, 2)}</td>
              <td className="py-1.5 pr-3 text-right tabular-nums">{num(a.confidence, 2)}</td>
              <td className="py-1.5 pr-3">
                {a.label.is_fault ? (
                  <span className="text-[11px]" style={{ color: status.critical }}>
                    ✱ {a.label.fault_type}
                  </span>
                ) : (
                  <span className="text-[11px] text-ink-muted">bình thường</span>
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
          ))}
        </tbody>
      </table>
    </div>
  );
}

function IncidentTable({ incidents }: { incidents: Incident[] }) {
  if (!incidents.length) return <Empty>Run này chưa gom được sự cố nào.</Empty>;
  return (
    <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {incidents.map((i) => {
        const correct = i.root_cause_service === i.ground_truth_service;
        return (
          <li key={i.incident_id}>
            <Link
              to={`/incidents/${i.incident_id}`}
              className="block rounded-lg border border-[color:var(--color-hairline)] p-3 transition-colors hover:bg-[color:var(--color-plane)]"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-[11px] text-ink-muted">{i.incident_id}</span>
                <span
                  className="text-[11px] font-medium"
                  style={{ color: i.root_cause_service ? (correct ? status.good : status.critical) : status.warning }}
                >
                  {i.root_cause_service ? (correct ? "✓ đúng gốc" : "✗ sai gốc") : "⚠ bị từ chối"}
                </span>
              </div>
              <div className="mt-2 text-[13px] font-semibold text-ink">
                {i.root_cause_service ?? "—"}
                <span className="ml-2 text-[11px] font-normal text-ink-muted">
                  nhãn: {i.ground_truth_service}
                </span>
              </div>
              <div className="mt-1.5 text-[11px] text-ink-2">
                {i.services.join("  →  ")}
              </div>
              <dl className="mt-2 border-t border-[color:var(--color-hairline)] pt-1.5">
                <KV k="Loại lỗi" v={i.fault_type ?? "—"} />
                <KV k="Khoảng" v={`${clockUTC(i.start_ts)} – ${clockUTC(i.end_ts)}`} />
                <KV k="Số alert" v={i.alert_ids.length} />
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
  return [...map.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([ts, row]) => ({ label: clockUTC(new Date(ts).toISOString()).slice(0, 5), ...row }));
}

function summarise(alerts: Alert[]) {
  let tp = 0;
  let fp = 0;
  let rescue = 0;
  for (const a of alerts) {
    if (a.verdict === "TRUE_ALERT") (a.label.is_fault ? tp++ : fp++);
    if (a.candidate_source === "rescue") rescue++;
  }
  return { tp, fp, rescue, coverage: alerts.length ? pct(tp / alerts.length) : "—" };
}
