import { useState } from "react";
import type { IncidentDetail } from "@/api/types";
import { Card } from "@/components/ui";
import { clockUTC, cx, num } from "@/lib/util";
import { ink, status } from "@/theme/tokens";

/**
 * "How the RCA agent localized the root cause" — ba bước của RCA mức 1 (QĐ-040..043) kể cho hội đồng:
 * 1. gom cảnh báo trong cửa sổ T_group; 2. nối các service bằng cạnh gọi trong trace;
 * 3. lùi một bước ngược chiều gọi: mỗi service có cảnh báo "đổ lỗi" cho callee trực tiếp cũng có
 * cảnh báo, không có thì đổ cho chính nó (services/rca_agent/propagation.py::backward_one_hop,
 * dấu hiệu `alert`). Bảng phiếu tính lại từ cạnh API trả về và đối chiếu với báo cáo đã lưu.
 * Mọi chữ hiển thị bằng tiếng Anh (quy ước giao diện).
 */

const ROOT = status.critical;
const AFFECTED = status.serious;
const HEALTHY = ink.muted;
const CALL = ink.axis;

type Vote = { from: string; blames: string[]; reason: string };

function computeVotes(alerted: string[], edges: IncidentDetail["edges"]): Vote[] {
  const set = new Set(alerted);
  return alerted.map((s) => {
    const callees = [...new Set(edges.filter((e) => e.source === s && e.target !== s && set.has(e.target)).map((e) => e.target))].sort();
    return callees.length
      ? { from: s, blames: callees, reason: `calls alerted ${callees.join(", ")}` }
      : { from: s, blames: [s], reason: "has no alerted callee" };
  });
}

function columns(alerted: string[], edges: IncidentDetail["edges"]): Map<string, number> {
  // Callers on the left, callees on the right: col(callee) >= col(caller) + 1 (capped for cycles).
  const set = new Set(alerted);
  const inner = edges.filter((e) => set.has(e.source) && set.has(e.target) && e.source !== e.target);
  const col = new Map(alerted.map((s) => [s, 0]));
  for (let i = 0; i < alerted.length; i++) {
    for (const e of inner) {
      const next = (col.get(e.source) ?? 0) + 1;
      if (next > (col.get(e.target) ?? 0) && next < alerted.length) col.set(e.target, next);
    }
  }
  return col;
}

export default function RcaPropagationStory({ data }: { data: IncidentDetail }) {
  const [step, setStep] = useState<0 | 1 | 2 | 3>(0);

  const alerts = [...data.alerts].sort((a, b) => a.ts.localeCompare(b.ts));
  const alerted = [...new Set([...data.services, ...alerts.map((a) => a.service)])];
  const maxScore = new Map<string, number>();
  for (const a of alerts) maxScore.set(a.service, Math.max(maxScore.get(a.service) ?? 0, a.anomaly_score));

  const votes = computeVotes(alerted, data.edges);
  const score = new Map(alerted.map((s) => [s, 0]));
  for (const v of votes) for (const b of v.blames) score.set(b, (score.get(b) ?? 0) + 1 / v.blames.length / alerted.length);
  const storedRoot = data.root_cause_service;
  const EPS = 1e-9;
  // Ties: the agent breaks them by each service's highest anomaly score over the whole incident
  // span (detector windows included), which the page does not have — so the stored root goes first.
  const ranking = [...score.entries()].sort(
    (a, b) =>
      (Math.abs(b[1] - a[1]) > EPS ? b[1] - a[1] : 0) ||
      Number(b[0] === storedRoot) - Number(a[0] === storedRoot) ||
      (maxScore.get(b[0]) ?? 0) - (maxScore.get(a[0]) ?? 0) ||
      a[0].localeCompare(b[0]),
  );
  const topScore = ranking[0]?.[1] ?? 0;
  const tied = ranking.filter(([, sc]) => Math.abs(sc - topScore) <= EPS).map(([svc]) => svc);
  const recomputedRoot = ranking[0]?.[0] ?? null;
  const root = storedRoot ?? recomputedRoot;
  const gt = data.ground_truth_service;

  const dim = (n: 1 | 2 | 3) => (step !== 0 && step !== n ? "opacity-30" : "opacity-100");

  return (
    <Card
      title="How the RCA agent localized the root cause"
      subtitle="Three steps, no LLM involved: group alerts in time, link them by trace calls, then step back one hop against the call direction."
      right={
        <div className="flex items-center gap-1" role="group" aria-label="Step through">
          {(["All", "1", "2", "3"] as const).map((label, i) => (
            <button
              key={label}
              type="button"
              onClick={() => setStep(i as 0 | 1 | 2 | 3)}
              aria-pressed={step === i}
              className={cx(
                "rounded border px-2 py-0.5 text-[11px]",
                step === i
                  ? "border-[color:var(--color-ink-2)] bg-[color:var(--color-plane)] font-medium text-ink"
                  : "border-[color:var(--color-hairline)] text-ink-muted hover:text-ink-2",
              )}
            >
              {i === 0 ? "All steps" : `Step ${label}`}
            </button>
          ))}
        </div>
      }
    >
      <div className="grid gap-5 xl:grid-cols-[1fr_1.5fr_1fr]">
        <section className={cx("transition-opacity", dim(1))} aria-label="Step 1">
          <StepTitle n={1} text={`Cluster alerts in time (gap ≤ ${data.grouping_reason.temporal_window_sec} s)`} />
          <AlertTimeline data={data} alerted={alerted} alerts={alerts} root={root} />
          <p className="mt-2 text-[11px] text-ink-2">
            {alerts.length === 1
              ? "A single alert: its time cluster holds nothing else."
              : `${alerts.length} alerts on ${alerted.length} service${alerted.length === 1 ? "" : "s"}, each at most ${data.grouping_reason.temporal_window_sec} s after the previous one, so they share one time cluster.`}
          </p>
        </section>

        <section className={cx("transition-opacity", dim(2))} aria-label="Step 2">
          <StepTitle n={2} text="Link services by trace calls" />
          <CallDiagram data={data} alerted={alerted} root={root} />
          <p className="mt-2 text-[11px] text-ink-2">
            {alerted.length === 1
              ? "Only one service raised an alert, so it forms the incident on its own and there is no call to follow."
              : "Alerted services joined by a call (either direction) form one incident. Grey arrows: who calls whom in the traces. Red dashed arrows: the direction a failure spreads (against the call)."}
          </p>
        </section>

        <section className={cx("transition-opacity", dim(3))} aria-label="Step 3">
          <StepTitle n={3} text="Step back one hop against the call direction" />
          <ul className="space-y-1">
            {votes.map((v) => (
              <li key={v.from} className="text-[11px] leading-snug text-ink-2">
                <span className="font-mono text-ink">{v.from}</span> {v.reason} →{" "}
                {v.blames[0] === v.from && v.blames.length === 1 ? "blames itself" : `blames ${v.blames.join(", ")}`}
              </li>
            ))}
          </ul>
          <ol className="mt-2 space-y-1">
            {ranking.slice(0, 3).map(([svc, sc], i) => (
              <li key={svc} className="flex items-center gap-2">
                <span className="w-4 text-right text-[10.5px] tabular-nums text-ink-muted">{i + 1}</span>
                <span className="w-[150px] truncate font-mono text-[10.5px] text-ink" title={svc}>
                  {svc}
                </span>
                <span className="h-2 flex-1 rounded-full" style={{ background: ink.grid }}>
                  <span
                    className="block h-2 rounded-full"
                    style={{ width: `${sc * 100}%`, background: svc === root ? ROOT : AFFECTED }}
                  />
                </span>
                <span className="w-8 text-right text-[10.5px] tabular-nums text-ink-2">{num(sc, 2)}</span>
              </li>
            ))}
          </ol>
          <div className="mt-3 space-y-1 rounded-md border border-[color:var(--color-hairline)] px-2.5 py-2 text-[11px]">
            <div className="flex justify-between gap-2">
              <span className="text-ink-muted">Predicted root cause</span>
              <span className="font-mono font-medium" style={{ color: ROOT }}>
                {root ?? "inconclusive"}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-ink-muted">Nezha label</span>
              <span className="font-mono">
                {gt ? `${data.fault_type ?? "fault"} @ ${gt}` : "unlabelled"}
              </span>
            </div>
            {gt && root && (
              <div className="text-right font-medium" style={{ color: gt === root ? status.good : status.critical }}>
                {gt === root ? "✓ Match" : "✗ Mismatch"}
              </div>
            )}
            {tied.length > 1 && (
              <div className="text-[10.5px] text-ink-muted">
                Tie at {num(topScore, 2)} between {tied.join(" and ")}; the agent breaks ties by the highest
                anomaly score over the incident span.
              </div>
            )}
            {storedRoot && !tied.includes(storedRoot) && (
              <div className="text-[10.5px] text-ink-muted">
                The stored report names {storedRoot}, which differs from the recomputed vote; the report is shown.
              </div>
            )}
          </div>
        </section>
      </div>
    </Card>
  );
}

function StepTitle({ n, text }: { n: number; text: string }) {
  return (
    <h3 className="mb-2 flex items-center gap-2 text-[11.5px] font-semibold text-ink">
      <span
        aria-hidden
        className="inline-flex h-4 w-4 items-center justify-center rounded-full border text-[10px]"
        style={{ borderColor: ink.axis }}
      >
        {n}
      </span>
      {text}
    </h3>
  );
}

function AlertTimeline({
  data,
  alerted,
  alerts,
  root,
}: {
  data: IncidentDetail;
  alerted: string[];
  alerts: IncidentDetail["alerts"];
  root: string | null;
}) {
  const W = 320;
  const labelW = 0;
  const rowH = 22;
  const top = 6;
  const t = (iso: string) => Date.parse(iso);
  const t0 = t(data.start_ts);
  const t1 = Math.max(t(data.end_ts), t0 + 1000);
  const pad = Math.max((t1 - t0) * 0.08, 5000);
  const x = (ms: number) => labelW + 8 + ((ms - (t0 - pad)) / (t1 - t0 + 2 * pad)) * (W - labelW - 16);
  const H = top + alerted.length * rowH + 30;
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxWidth: W * 1.25 }} role="img" aria-label="Alerts over time, one row per service">
        <rect
          x={x(t0)}
          y={top - 2}
          width={Math.max(x(t1) - x(t0), 2)}
          height={alerted.length * rowH}
          fill={ink.plane}
          stroke={ink.grid}
        />
        {alerted.map((svc, i) => {
          const y = top + i * rowH + rowH / 2;
          return (
            <g key={svc}>
              <line x1={8} x2={W - 8} y1={y} y2={y} stroke={ink.grid} strokeDasharray="2 4" />
              <text x={10} y={y - 6} fontSize={9.5} fill={ink.secondary} fontFamily="ui-monospace, monospace">
                {svc}
              </text>
              {alerts
                .filter((a) => a.service === svc)
                .map((a) => (
                  <circle
                    key={a.alert_id}
                    cx={x(t(a.ts))}
                    cy={y + 3}
                    r={4.5}
                    fill={svc === root ? ROOT : AFFECTED}
                    stroke={ink.surface}
                    strokeWidth={1.5}
                  >
                    <title>{`${svc} · ${clockUTC(a.ts)} UTC · score ${num(a.anomaly_score, 2)}`}</title>
                  </circle>
                ))}
            </g>
          );
        })}
        {x(t1) - x(t0) > 90 ? (
          <>
            <text x={x(t0)} y={H - 8} fontSize={9.5} fill={ink.muted} textAnchor="start">
              {clockUTC(data.start_ts)}
            </text>
            <text x={x(t1)} y={H - 8} fontSize={9.5} fill={ink.muted} textAnchor="end">
              {clockUTC(data.end_ts)}
            </text>
          </>
        ) : (
          <text x={(x(t0) + x(t1)) / 2} y={H - 8} fontSize={9.5} fill={ink.muted} textAnchor="middle">
            {clockUTC(data.start_ts) === clockUTC(data.end_ts)
              ? clockUTC(data.start_ts)
              : `${clockUTC(data.start_ts)} – ${clockUTC(data.end_ts)}`}
          </text>
        )}
      </svg>
    </div>
  );
}

function CallDiagram({ data, alerted, root }: { data: IncidentDetail; alerted: string[]; root: string | null }) {
  const col = columns(alerted, data.edges);
  const nCols = Math.max(...[...col.values()], 0) + 1;
  const byCol: string[][] = Array.from({ length: nCols }, () => []);
  for (const s of alerted) byCol[col.get(s) ?? 0]!.push(s);
  byCol.forEach((c) => c.sort());

  const set = new Set(alerted);
  const healthyCallees = root
    ? [...new Set(data.edges.filter((e) => e.source === root && !set.has(e.target)).map((e) => e.target))].sort().slice(0, 3)
    : [];
  const moreHealthy = root
    ? new Set(data.edges.filter((e) => e.source === root && !set.has(e.target)).map((e) => e.target)).size - healthyCallees.length
    : 0;

  const BW = 150;
  const BH = 40;
  const GAP_X = 56;
  const GAP_Y = 14;
  const PW = 112;
  const PH = 20;
  const pad = 6;
  const rows = Math.max(...byCol.map((c) => c.length), 1);
  const blockH = rows * BH + (rows - 1) * GAP_Y;
  const healthyH = healthyCallees.length ? healthyCallees.length * PH + (healthyCallees.length - 1) * 8 + (moreHealthy > 0 ? 16 : 0) : 0;
  const H = Math.max(blockH, healthyH) + pad * 2 + 4;
  const healthyX = pad + nCols * BW + (nCols - 1) * GAP_X + (healthyCallees.length ? 40 : 0);
  const W = healthyCallees.length ? healthyX + PW + pad : pad * 2 + nCols * BW + (nCols - 1) * GAP_X;

  const pos = new Map<string, { x: number; y: number }>();
  byCol.forEach((c, ci) => {
    const colH = c.length * BH + (c.length - 1) * GAP_Y;
    const y0 = pad + (H - pad * 2 - colH) / 2;
    c.forEach((s, ri) => pos.set(s, { x: pad + ci * (BW + GAP_X), y: y0 + ri * (BH + GAP_Y) }));
  });

  const inner = data.edges.filter((e) => set.has(e.source) && set.has(e.target) && e.source !== e.target);
  const rootPos = root ? pos.get(root) : undefined;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxWidth: W * 1.25 }} role="img" aria-label="Alerted services linked by trace calls">
      <defs>
        <marker id="rca-call" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M1 1L9 5L1 9" fill="none" stroke={CALL} strokeWidth={1.5} />
        </marker>
        <marker id="rca-blame" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M1 1L9 5L1 9" fill="none" stroke={ROOT} strokeWidth={1.5} />
        </marker>
      </defs>
      {inner.map((e) => {
        const a = pos.get(e.source)!;
        const b = pos.get(e.target)!;
        const forward = b.x > a.x;
        const x1 = forward ? a.x + BW : a.x + BW / 2;
        const x2 = forward ? b.x : b.x + BW / 2;
        const y1 = forward ? a.y + BH / 2 - 7 : a.y + BH;
        const y2 = forward ? b.y + BH / 2 - 7 : b.y;
        return (
          <g key={`${e.source}->${e.target}`}>
            <line x1={x1} y1={y1} x2={x2 - 2} y2={y2} stroke={CALL} strokeWidth={1.2} markerEnd="url(#rca-call)" />
            <text x={(x1 + x2) / 2} y={Math.min(y1, y2) - 4} fontSize={9} fill={ink.muted} textAnchor="middle">
              calls ×{e.call_count.toLocaleString("en-US")}
            </text>
            {forward && (
              <line
                x1={x2}
                y1={y2 + 14}
                x2={x1 + 2}
                y2={y1 + 14}
                stroke={ROOT}
                strokeWidth={1.5}
                strokeDasharray="5 3"
                markerEnd="url(#rca-blame)"
              />
            )}
          </g>
        );
      })}
      {rootPos &&
        healthyCallees.map((svc, i) => {
          const y = pad + (H - pad * 2 - healthyH) / 2 + i * (PH + 8);
          return (
            <g key={svc}>
              <line x1={rootPos.x + BW} y1={rootPos.y + BH / 2} x2={healthyX} y2={y + PH / 2} stroke={ink.grid} />
              <rect x={healthyX} y={y} width={PW} height={PH} rx={4} fill={ink.surface} stroke={ink.grid} />
              <text x={healthyX + PW / 2} y={y + PH / 2 + 3.5} fontSize={9} fill={HEALTHY} textAnchor="middle" fontFamily="ui-monospace, monospace">
                {svc.length > 20 ? `${svc.slice(0, 19)}…` : svc}
              </text>
            </g>
          );
        })}
      {rootPos && moreHealthy > 0 && (
        <text x={healthyX + PW / 2} y={pad + (H - pad * 2 - healthyH) / 2 + healthyH - 2} fontSize={9} fill={HEALTHY} textAnchor="middle">
          +{moreHealthy} more, no alert
        </text>
      )}
      {alerted.map((s) => {
        const p = pos.get(s)!;
        const isRoot = s === root;
        const color = isRoot ? ROOT : AFFECTED;
        const n = data.alerts.filter((a) => a.service === s).length;
        return (
          <g key={s}>
            <rect
              x={p.x}
              y={p.y}
              width={BW}
              height={BH}
              rx={6}
              style={{ fill: `color-mix(in srgb, ${color} ${isRoot ? 12 : 7}%, ${ink.surface})` }}
              stroke={color}
              strokeWidth={isRoot ? 2 : 1}
            />
            <text x={p.x + BW / 2} y={p.y + 16} fontSize={10} fontWeight={600} fill={ink.primary} textAnchor="middle" fontFamily="ui-monospace, monospace">
              {s.length > 22 ? `${s.slice(0, 21)}…` : s}
            </text>
            <text x={p.x + BW / 2} y={p.y + 30} fontSize={9} fill={color} textAnchor="middle">
              {n} alert{n === 1 ? "" : "s"} · {isRoot ? "predicted root" : "affected"}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
