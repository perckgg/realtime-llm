import type { AlertDetail, ContextEvent } from "@/api/types";
import { Card } from "@/components/ui";
import { cx, num } from "@/lib/util";
import { series } from "@/theme/tokens";

/**
 * "How C1 built this context" — giải thích cho hội đồng đồ thị service làm gì ở tầng C1.
 *
 * Trung thực với Phát hiện 7 (QĐ-026): đồ thị chỉ vạch *vùng tìm* (≤ 2 bước), còn Fusion
 * Score mới quyết định bằng chứng nào được chọn — thường là bằng chứng của chính service bị
 * cảnh báo. Không vẽ gì gợi ý "service lân cận cứu cảnh báo" khi dữ liệu không cho thấy vậy.
 * Mọi chữ hiển thị bằng tiếng Anh (quy ước giao diện).
 */

const PART_COLOR = {
  bm25: series[0],
  time: series[2],
  graph: "var(--color-ink-muted)",
} as const;
const CITED_COLOR = series[1];

type Scored = {
  e: ContextEvent;
  rank: number;
  d: number;
  bm25: number;
  time: number;
  graph: number;
  total: number;
  cited: boolean;
};

function numField(e: ContextEvent, key: string): number | null {
  const v = e.debug[key];
  if (v === undefined || v === null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function bandTitle(d: number): string {
  return d === 0 ? "Alerted service" : d === 1 ? "1 hop away" : `${d} hops away`;
}

export default function C1ContextExplainer({ alert }: { alert: AlertDetail }) {
  const w = alert.fusion_weights;
  if (!w || alert.search_scope.length === 0) return null;

  const cited = new Set(alert.evidence_event_ids);
  const scored: Scored[] = [];
  alert.context_events.forEach((e, i) => {
    const bm25 = numField(e, "bm25_norm");
    const time = numField(e, "time_sim");
    const graph = numField(e, "graph_sim");
    const d = numField(e, "graph_distance") ?? 0;
    if (bm25 === null || time === null || graph === null) return;
    scored.push({
      e,
      rank: i + 1,
      d,
      bm25: w.alpha * bm25,
      time: w.beta * time,
      graph: w.gamma * graph,
      total: w.alpha * bm25 + w.beta * time + w.gamma * graph,
      cited: cited.has(e.event_id),
    });
  });

  const maxD = w.graph_max_distance;
  const bands = Array.from({ length: maxD + 1 }, (_, d) => ({
    d,
    services: alert.search_scope.filter((s) => s.distance === d).map((s) => s.service),
    selected: scored.filter((s) => s.d === d).length,
  }));
  const selectedByService = new Map<string, number>();
  for (const s of scored) selectedByService.set(s.e.service, (selectedByService.get(s.e.service) ?? 0) + 1);

  const neighbors = alert.search_scope.filter((s) => s.distance > 0).length;
  const fromNeighbors = scored.filter((s) => s.d > 0);
  const graphPart = (d: number) => w.gamma / (1 + d);

  const takeaway =
    scored.length === 0
      ? "The score breakdown is not stored for this alert."
      : fromNeighbors.length === 0
        ? `All ${scored.length} selected events come from ${alert.service} itself (d = 0). The graph widened the search to ${neighbors} neighbor service${neighbors === 1 ? "" : "s"}, but none of their events reached the top ${scored.length}: on the graph part alone, an event 1 hop away starts ${num(graphPart(0) - graphPart(1), 2)} behind one from ${alert.service}.`
        : `${fromNeighbors.length} of ${scored.length} selected events come from neighbor services (${[...new Set(fromNeighbors.map((s) => `${s.e.service}, d = ${s.d}`))].join("; ")}).`;

  return (
    <Card
      title="How C1 built this context"
      subtitle="The service graph sets where C1 looks for evidence; the Fusion Score decides which events reach the LLM."
    >
      <div className="grid gap-5 xl:grid-cols-[1.05fr_1fr]">
        <section aria-label="Search scope">
          <h3 className="mb-2 text-[11.5px] font-semibold text-ink">
            1 · Search scope on the service graph (up to {maxD} hops)
          </h3>
          <div className="flex items-stretch gap-1.5">
            {bands.map((b, i) => (
              <div key={b.d} className="flex min-w-0 flex-1 items-stretch gap-1.5">
                {i > 0 && (
                  <span aria-hidden className="self-center text-[12px] text-ink-muted">
                    ›
                  </span>
                )}
                <div
                  className="flex min-w-0 flex-1 flex-col rounded-lg border px-2.5 py-2"
                  style={{
                    borderColor: b.d === 0 ? series[0] : "var(--color-hairline)",
                    background:
                      b.d === 0
                        ? `color-mix(in srgb, ${series[0]} 9%, var(--color-surface))`
                        : "var(--color-surface)",
                  }}
                >
                  <div className="text-[10.5px] font-semibold text-ink">d = {b.d}</div>
                  <div className="text-[10px] text-ink-muted">
                    {bandTitle(b.d)} · {b.services.length} service{b.services.length === 1 ? "" : "s"}
                  </div>
                  <div
                    className="mt-1 text-[10.5px] font-medium tabular-nums"
                    style={{ color: b.selected > 0 ? series[0] : "var(--color-ink-muted)" }}
                  >
                    {b.selected} of {scored.length} selected
                  </div>
                  <ul className="mt-2 flex flex-wrap gap-1">
                    {b.services.map((svc) => {
                      const n = selectedByService.get(svc) ?? 0;
                      return (
                        <li
                          key={svc}
                          title={svc}
                          className={cx(
                            "max-w-full truncate rounded border px-1.5 py-0.5 font-mono text-[10px]",
                            n > 0 ? "text-ink" : "text-ink-muted",
                          )}
                          style={{
                            borderColor: n > 0 ? series[0] : "var(--color-hairline)",
                            background:
                              n > 0
                                ? `color-mix(in srgb, ${series[0]} 12%, var(--color-surface))`
                                : undefined,
                          }}
                        >
                          {svc}
                          {n > 0 && <span className="ml-1 font-sans font-semibold">×{n}</span>}
                        </li>
                      );
                    })}
                    {b.services.length === 0 && <li className="text-[10px] text-ink-muted">none</li>}
                  </ul>
                </div>
              </div>
            ))}
          </div>
          <p className="mt-2 text-[10.5px] text-ink-muted">
            Distance d is counted on the undirected call graph built from Nezha traces. Graph part of the
            score by hop:{" "}
            {bands.map((b, i) => (
              <span key={b.d} className="tabular-nums">
                {i > 0 && " · "}d = {b.d} → {num(graphPart(b.d), 2)}
              </span>
            ))}
            .
          </p>
        </section>

        <section aria-label="Fusion Score">
          <h3 className="mb-2 text-[11.5px] font-semibold text-ink">
            2 · Fusion Score of the {scored.length} selected events
          </h3>
          <ol className="space-y-1.5">
            {scored.map((s) => {
              const dt = numField(s.e, "time_distance_sec");
              return (
                <li key={s.e.event_id} className="flex items-center gap-2">
                  <span className="w-5 shrink-0 text-right text-[10.5px] tabular-nums text-ink-muted">
                    #{s.rank}
                  </span>
                  <span
                    className="w-[92px] shrink-0 truncate text-[10.5px] text-ink-2"
                    title={s.e.content}
                  >
                    d = {s.d}
                    {dt !== null && ` · Δt ${Math.round(dt)} s`}
                  </span>
                  <div
                    className="relative flex h-[18px] flex-1 overflow-hidden rounded-sm"
                    style={{
                      background: "var(--color-plane)",
                      outline: s.cited ? `1.5px solid ${CITED_COLOR}` : undefined,
                      outlineOffset: 1,
                    }}
                    role="img"
                    aria-label={`BM25 ${num(s.bm25, 3)}, time ${num(s.time, 3)}, graph ${num(s.graph, 3)}, total ${num(s.total, 3)}${s.cited ? ", cited by the LLM" : ""}`}
                  >
                    <span style={{ width: `${s.bm25 * 100}%`, background: PART_COLOR.bm25 }} />
                    <span style={{ width: `${s.time * 100}%`, background: PART_COLOR.time }} />
                    <span style={{ width: `${s.graph * 100}%`, background: PART_COLOR.graph }} />
                  </div>
                  <span className="w-9 shrink-0 text-right text-[10.5px] tabular-nums text-ink">
                    {num(s.total, 2)}
                  </span>
                  <span
                    className="w-10 shrink-0 text-[10px] font-medium"
                    style={{ color: s.cited ? CITED_COLOR : "transparent" }}
                  >
                    cited
                  </span>
                </li>
              );
            })}
          </ol>
          <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[10.5px] text-ink-2">
            <li className="flex items-center gap-1.5">
              <span aria-hidden className="h-2.5 w-2.5 rounded-sm" style={{ background: PART_COLOR.bm25 }} />
              Text match (BM25) · weight {num(w.alpha, 2)}
            </li>
            <li className="flex items-center gap-1.5">
              <span aria-hidden className="h-2.5 w-2.5 rounded-sm" style={{ background: PART_COLOR.time }} />
              Closeness in time · weight {num(w.beta, 2)}
            </li>
            <li className="flex items-center gap-1.5">
              <span aria-hidden className="h-2.5 w-2.5 rounded-sm" style={{ background: PART_COLOR.graph }} />
              Graph proximity 1 / (1 + d) · weight {num(w.gamma, 2)}
            </li>
            <li className="flex items-center gap-1.5">
              <span
                aria-hidden
                className="h-2.5 w-3 rounded-sm"
                style={{ outline: `1.5px solid ${CITED_COLOR}` }}
              />
              Cited by the LLM
            </li>
          </ul>
        </section>
      </div>

      <p
        className="mt-4 border-t border-[color:var(--color-hairline)] pt-3 text-[12px] leading-relaxed text-ink-2"
        data-testid="c1-takeaway"
      >
        {takeaway}
      </p>
    </Card>
  );
}
