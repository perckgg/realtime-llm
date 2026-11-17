import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import { api } from "@/api/client";
import type { GraphNode, IncidentDetail as IncidentDetailT } from "@/api/types";
import { Card, Empty, ErrorBox, KV, Loading, Pill, StatTile, VerdictBadge } from "@/components/ui";
import { clockUTC, cx, num, stampUTC, useAsync } from "@/lib/util";
import { ink, series, status } from "@/theme/tokens";

/**
 * Vai trò của node là *trạng thái*, nên nó dùng bảng status chứ không mượn màu
 * series. Mỗi vai trò luôn đi kèm ký hiệu và nhãn chữ — màu không bao giờ là
 * kênh thông tin duy nhất.
 */
const ROLE: Record<GraphNode["role"], { color: string; glyph: string; label: string }> = {
  root_cause: { color: status.critical, glyph: "◉", label: "Nguyên nhân gốc (dự đoán)" },
  ground_truth: { color: status.good, glyph: "✓", label: "Nhãn Nezha" },
  affected: { color: status.serious, glyph: "◐", label: "Bị ảnh hưởng" },
  healthy: { color: ink.muted, glyph: "○", label: "Bình thường" },
};

type ServiceNodeData = {
  node: GraphNode;
  pathIndex: number | null;
};

function ServiceNode({ data }: NodeProps<Node<ServiceNodeData>>) {
  const { node, pathIndex } = data;
  const role = ROLE[node.role];
  const emphasised = node.role === "root_cause" || node.role === "ground_truth";
  return (
    <div
      className={cx(
        "min-w-[168px] rounded-lg border bg-surface px-3 py-2 shadow-sm",
        emphasised && "shadow-md",
      )}
      style={{
        borderColor: role.color,
        borderWidth: emphasised ? 2 : 1,
        background:
          node.role === "healthy" ? ink.surface : `color-mix(in srgb, ${role.color} 8%, ${ink.surface})`,
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: ink.axis, width: 6, height: 6 }} />
      <div className="flex items-center gap-1.5">
        <span aria-hidden style={{ color: role.color }} className="text-[12px]">
          {role.glyph}
        </span>
        <span className="text-[12px] font-semibold text-ink">{node.service}</span>
        {pathIndex !== null && (
          <span className="ml-auto text-[10px] tabular-nums text-ink-muted">#{pathIndex + 1}</span>
        )}
      </div>
      <div className="mt-0.5 text-[10px]" style={{ color: role.color }}>
        {role.label}
      </div>
      {node.alert_count > 0 && (
        <div className="mt-1.5 flex items-center gap-2">
          <span className="h-1.5 flex-1 rounded-full" style={{ background: ink.grid }}>
            <span
              className="block h-1.5 rounded-full"
              style={{ width: `${node.max_anomaly_score * 100}%`, background: series[0] }}
            />
          </span>
          <span className="text-[10px] tabular-nums text-ink-2">
            {node.alert_count} alert · {num(node.max_anomaly_score, 2)}
          </span>
        </div>
      )}
      <Handle type="source" position={Position.Right} style={{ background: ink.axis, width: 6, height: 6 }} />
    </div>
  );
}

const nodeTypes = { service: ServiceNode };

/**
 * Bố cục phân lớp thủ công thay vì thư viện auto-layout: đồ thị chỉ có chục
 * node và trục ngang phải kể đúng chiều lan truyền (gốc bên trái → frontend bên
 * phải). Một thư viện layout sẽ làm mờ đúng cái thông điệp đó.
 */
function layout(detail: IncidentDetailT): { nodes: Node<ServiceNodeData>[]; edges: Edge[] } {
  const path = detail.services;
  const X = 250;
  const Y = 110;

  const placed = new Map<string, { x: number; y: number }>();
  path.forEach((s, i) => placed.set(s, { x: i * X, y: 0 }));

  let side = 0;
  for (const n of detail.nodes) {
    if (placed.has(n.service)) continue;
    const neighbour = detail.edges.find(
      (e) =>
        (e.source === n.service && path.includes(e.target)) ||
        (e.target === n.service && path.includes(e.source)),
    );
    const anchor = neighbour
      ? path.indexOf(neighbour.source === n.service ? neighbour.target : neighbour.source)
      : path.length - 1;
    side += 1;
    placed.set(n.service, {
      x: Math.max(0, anchor) * X + 40,
      y: side % 2 === 0 ? Y * Math.ceil(side / 2) : -Y * Math.ceil(side / 2),
    });
  }

  const nodes: Node<ServiceNodeData>[] = detail.nodes.map((n) => ({
    id: n.service,
    type: "service",
    position: placed.get(n.service) ?? { x: 0, y: 0 },
    data: { node: n, pathIndex: path.includes(n.service) ? path.indexOf(n.service) : null },
    draggable: true,
  }));

  const edges: Edge[] = detail.edges.map((e) => ({
    // Cạnh gọi đi theo chiều caller → callee; lỗi lan theo chiều ngược lại, nên
    // đường lan truyền được vẽ đảo chiều để mũi tên chỉ đúng hướng lan.
    id: `${e.source}->${e.target}`,
    source: e.on_path ? e.target : e.source,
    target: e.on_path ? e.source : e.target,
    animated: e.on_path,
    style: {
      stroke: e.on_path ? status.critical : ink.grid,
      strokeWidth: e.on_path ? 2.5 : 1,
    },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: e.on_path ? status.critical : ink.axis,
      width: 14,
      height: 14,
    },
    label: e.on_path ? `${(e.error_rate * 100).toFixed(0)}% lỗi` : undefined,
    labelStyle: { fill: status.critical, fontSize: 10 },
    labelBgStyle: { fill: ink.surface },
  }));

  return { nodes, edges };
}

export default function IncidentDetail() {
  const { incidentId = "" } = useParams();
  const { data, loading, error } = useAsync(() => api.getIncident(incidentId), [incidentId]);
  const [rawJson, setRawJson] = useState(false);

  const graph = useMemo(() => (data ? layout(data) : null), [data]);

  if (loading) return <Loading />;
  if (error || !data || !graph) return <ErrorBox message={error ?? "Không tìm thấy sự cố"} />;

  const hasGt =
    data.ground_truth_service !== null && data.ground_truth_service !== undefined;
  const correct = hasGt && data.root_cause_service === data.ground_truth_service;
  const report = data.report;
  const badgeColor = !report
    ? status.warning
    : !hasGt
      ? ink.muted
      : correct
        ? status.good
        : status.critical;
  const badgeLabel = !report
    ? "Báo cáo bị từ chối"
    : !hasGt
      ? "Không có nhãn Nezha (ngoài lỗi / mơ hồ)"
      : correct
        ? "Khớp nhãn Nezha"
        : `Sai — nhãn là ${data.ground_truth_service}`;

  return (
    <div className="space-y-4">
      <Link to="/timeline" className="inline-block text-[11.5px] text-ink-muted hover:text-ink-2">
        ← Timeline
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[19px] font-semibold tracking-tight text-ink">
              {data.root_cause_service ?? "Không kết luận được"}
            </h1>
            <span
              className="inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium"
              style={{ borderColor: badgeColor, color: badgeColor }}
            >
              <span aria-hidden>{!report ? "⚠" : !hasGt ? "—" : correct ? "✓" : "✗"}</span>
              {badgeLabel}
            </span>
          </div>
          <p className="mt-1 font-mono text-[11px] text-ink-muted">
            {data.incident_id} · {stampUTC(data.start_ts)} → {clockUTC(data.end_ts)}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Loại lỗi" value={data.fault_type ?? "—"} hint="theo nhãn Nezha" />
        <StatTile
          label="Confidence"
          value={report ? num(report.confidence, 2) : "—"}
          hint={report?.llm_backend ?? "không có báo cáo"}
        />
        <StatTile label="Alert gom vào" value={String(data.alert_ids.length)} hint={`cửa sổ gom ${data.grouping_reason.temporal_window_sec}s`} />
        <StatTile
          label="Cạnh đồ thị dùng"
          value={String(data.grouping_reason.graph_edges_used)}
          hint="cạnh trace nối các alert trong nhóm"
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.7fr_1fr]">
        <Card
          title="Đồ thị lan truyền"
          subtitle="Mũi tên đỏ chỉ chiều lỗi lan đi (ngược chiều lời gọi). Node xám là hàng xóm không bị ảnh hưởng, giữ lại để thấy lỗi đã KHÔNG lan tới đâu. Kéo để sắp lại, cuộn để phóng to."
          right={
            <ul className="flex flex-wrap gap-x-3 gap-y-1">
              {(Object.keys(ROLE) as GraphNode["role"][]).map((r) => (
                <li key={r} className="flex items-center gap-1 text-[10.5px] text-ink-2">
                  <span aria-hidden style={{ color: ROLE[r].color }}>
                    {ROLE[r].glyph}
                  </span>
                  {ROLE[r].label}
                </li>
              ))}
            </ul>
          }
        >
          {graph.nodes.length === 0 ? (
            <Empty>Không có node đồ thị nào.</Empty>
          ) : (
            <div className="h-[420px] rounded-md border border-[color:var(--color-hairline)]">
              <ReactFlow
                nodes={graph.nodes}
                edges={graph.edges}
                nodeTypes={nodeTypes}
                fitView
                fitViewOptions={{ padding: 0.18 }}
                proOptions={{ hideAttribution: true }}
                minZoom={0.4}
                maxZoom={1.6}
                nodesConnectable={false}
                elementsSelectable={false}
              >
                <Background variant={BackgroundVariant.Dots} gap={18} size={1} color={ink.grid} />
                <Controls showInteractive={false} />
              </ReactFlow>
            </div>
          )}

          {/* Bảng thay thế cho đồ thị — bắt buộc, để thông tin không chỉ nằm ở hình. */}
          <details className="mt-3">
            <summary className="cursor-pointer text-[11px] text-ink-muted hover:text-ink-2">
              Xem dạng bảng
            </summary>
            <table className="mt-2 w-full border-collapse text-[11.5px]">
              <thead>
                <tr className="border-b border-[color:var(--color-hairline)] text-left text-[10.5px] text-ink-muted">
                  <th className="py-1 pr-3 font-medium">Từ</th>
                  <th className="py-1 pr-3 font-medium">Tới</th>
                  <th className="py-1 pr-3 text-right font-medium">Lời gọi</th>
                  <th className="py-1 pr-3 text-right font-medium">Tỉ lệ lỗi</th>
                  <th className="py-1 font-medium">Trên đường lan</th>
                </tr>
              </thead>
              <tbody>
                {data.edges.map((e) => (
                  <tr key={`${e.source}-${e.target}`} className="border-b border-[color:var(--color-hairline)] last:border-0">
                    <td className="py-1 pr-3 font-mono">{e.source}</td>
                    <td className="py-1 pr-3 font-mono">{e.target}</td>
                    <td className="py-1 pr-3 text-right tabular-nums">{e.call_count}</td>
                    <td className="py-1 pr-3 text-right tabular-nums">{(e.error_rate * 100).toFixed(1)}%</td>
                    <td className="py-1">{e.on_path ? "có" : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </Card>

        <div className="space-y-4">
          {report ? (
            <>
              <Card
                title="Báo cáo chẩn đoán"
                subtitle={`schema ${report.schema_version} · ${report.llm_backend} · ${stampUTC(report.generated_at)}`}
                right={
                  <button
                    type="button"
                    onClick={() => setRawJson((v) => !v)}
                    className="rounded border border-[color:var(--color-hairline)] px-2 py-1 text-[11px] text-ink-muted hover:text-ink-2"
                  >
                    {rawJson ? "Dạng đọc" : "JSON thô"}
                  </button>
                }
              >
                {rawJson ? (
                  <pre className="max-h-[420px] overflow-auto rounded bg-[color:var(--color-plane)] p-3 font-mono text-[11px] leading-relaxed text-ink-2">
                    {JSON.stringify(report, null, 2)}
                  </pre>
                ) : (
                  <div className="space-y-3">
                    <dl className="divide-y divide-[color:var(--color-hairline)]">
                      <KV k="root_cause_service" v={<span className="font-mono">{report.root_cause_service}</span>} />
                      <KV k="fault_type" v={<span className="font-mono">{report.fault_type}</span>} />
                      <KV k="confidence" v={num(report.confidence, 2)} />
                    </dl>

                    <div>
                      <div className="mb-1.5 text-[11px] text-ink-muted">Đường lan truyền</div>
                      <div className="flex flex-wrap items-center gap-1.5">
                        {report.propagation_path.map((s, i) => (
                          <span key={s} className="flex items-center gap-1.5">
                            {i > 0 && <span className="text-ink-muted">→</span>}
                            <span
                              className="rounded border px-1.5 py-0.5 font-mono text-[11px]"
                              style={{
                                borderColor: i === 0 ? status.critical : "var(--color-hairline)",
                                color: i === 0 ? status.critical : "var(--color-ink-2)",
                              }}
                            >
                              {s}
                            </span>
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <div className="mb-1.5 text-[11px] text-ink-muted">
                        Bằng chứng ({report.evidence.length}) — bắt buộc ≥ 1
                      </div>
                      <ul className="space-y-1.5">
                        {report.evidence.map((ev) => (
                          <li
                            key={ev.event_id}
                            className="rounded border border-[color:var(--color-hairline)] p-2"
                          >
                            <div className="flex items-center gap-2 text-[10.5px] text-ink-muted">
                              <Pill>{ev.modality}</Pill>
                              <span className="font-mono">{ev.service}</span>
                              <span>{clockUTC(ev.ts)}</span>
                            </div>
                            <p className="mt-1 font-mono text-[11px] break-words text-ink-2">
                              {ev.excerpt}
                            </p>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <div className="mb-1.5 text-[11px] text-ink-muted">
                        Hành động gợi ý — chỉ mô tả, không sinh câu lệnh (03 §2.1)
                      </div>
                      <ul className="space-y-1.5">
                        {report.suggested_actions.map((s) => (
                          <li key={s.description} className="flex items-start gap-2 text-[12px] text-ink-2">
                            <span
                              className="mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium"
                              style={{
                                background: `color-mix(in srgb, ${
                                  s.priority === "high"
                                    ? status.critical
                                    : s.priority === "medium"
                                      ? status.warning
                                      : ink.muted
                                } 14%, ${ink.surface})`,
                                color:
                                  s.priority === "high"
                                    ? status.critical
                                    : s.priority === "medium"
                                      ? "#8a6000"
                                      : ink.secondary,
                              }}
                            >
                              {s.priority}
                            </span>
                            {s.description}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </Card>
            </>
          ) : (
            <Card title="Báo cáo bị từ chối" subtitle="Ghi vào bảng diagnostic_rejected, không nuốt lỗi im lặng (03 §4).">
              <p className="text-[12.5px] text-ink-2">{data.rejected_reason}</p>
            </Card>
          )}

          <Card title={`Alert trong sự cố (${data.alerts.length})`}>
            {data.alerts.length === 0 ? (
              <Empty>Không có cảnh báo trong sự cố này.</Empty>
            ) : (
              <ul className="space-y-1.5">
                {data.alerts.map((a) => (
                  <li key={a.alert_id}>
                    <Link
                      to={`/alerts/${a.alert_id}`}
                      className="flex items-center gap-2 rounded px-1.5 py-1 text-[11.5px] hover:bg-[color:var(--color-plane)]"
                    >
                      <span className="tabular-nums text-ink-muted">{clockUTC(a.ts)}</span>
                      <span className="font-mono text-ink-2">{a.service}</span>
                      <span className="ml-auto">
                        <VerdictBadge verdict={a.verdict} compact />
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
