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
import { Card, ErrorBox, KV, Loading, Pill, StatTile, VerdictBadge } from "@/components/ui";
import { clockUTC, cx, num, stampUTC, useAsync } from "@/lib/util";
import { formatFaultType, ink, series, status } from "@/theme/tokens";

const ROLE: Record<GraphNode["role"], { color: string; glyph: string; label: string }> = {
  root_cause: { color: status.critical, glyph: "◉", label: "Predicted Root Cause" },
  ground_truth: { color: status.good, glyph: "✓", label: "Ground-Truth Service" },
  affected: { color: status.serious, glyph: "◐", label: "Affected Upstream Service" },
  healthy: { color: ink.muted, glyph: "○", label: "Healthy Neighbor" },
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
        "min-w-[178px] rounded-xl border bg-surface px-3.5 py-2.5 shadow-sm",
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
        <span className="font-mono text-[11.5px] font-semibold text-ink">{node.service}</span>
        {pathIndex !== null && (
          <span className="ml-auto font-mono text-[10px] tabular-nums text-ink-muted">
            #{pathIndex + 1}
          </span>
        )}
      </div>
      <div className="mt-0.5 text-[10.5px] font-medium" style={{ color: role.color }}>
        {role.label}
      </div>
      {node.alert_count > 0 && (
        <div className="mt-2 flex items-center gap-2">
          <span className="h-1.5 flex-1 rounded-full" style={{ background: ink.grid }}>
            <span
              className="block h-1.5 rounded-full"
              style={{ width: `${node.max_anomaly_score * 100}%`, background: series[0] }}
            />
          </span>
          <span className="text-[10px] tabular-nums text-ink-2">
            {node.alert_count} {node.alert_count === 1 ? "alert" : "alerts"} · {num(node.max_anomaly_score, 2)}
          </span>
        </div>
      )}
      <Handle type="source" position={Position.Right} style={{ background: ink.axis, width: 6, height: 6 }} />
    </div>
  );
}

const nodeTypes = { service: ServiceNode };

function layout(detail: IncidentDetailT): { nodes: Node<ServiceNodeData>[]; edges: Edge[] } {
  const path = detail.services;
  const X = 260;
  const Y = 115;

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
    // Call graph direction is caller → callee; fault propagation flows callee → caller.
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
    label: e.on_path
      ? e.error_rate != null
        ? `${(e.error_rate * 100).toFixed(0)}% errors`
        : `${e.call_count.toLocaleString("en-US")} spans`
      : undefined,
    labelStyle: { fill: status.critical, fontSize: 10, fontWeight: 600 },
    labelBgStyle: { fill: ink.surface },
  }));

  return { nodes, edges };
}

export default function IncidentDetail() {
  const { incidentId = "" } = useParams();
  const { data, loading, error } = useAsync(() => api.getIncident(incidentId), [incidentId]);
  const [rawJson, setRawJson] = useState(false);

  const graph = useMemo(() => (data ? layout(data) : null), [data]);

  if (loading) return <Loading label="Loading incident topology…" />;
  if (error || !data || !graph) return <ErrorBox message={error ?? `Incident '${incidentId}' not found`} />;

  const hasGt = data.ground_truth_service !== null;
  const correct = hasGt && data.root_cause_service === data.ground_truth_service;
  const report = data.report;

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
            <h1 className="text-[20px] font-semibold tracking-tight text-ink">
              {data.root_cause_service ?? "Unresolved Root Cause"}
            </h1>
            <span
              className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium"
              style={{
                borderColor: !report
                  ? status.warning
                  : !hasGt
                    ? ink.muted
                    : correct
                      ? status.good
                      : status.critical,
                color: !report
                  ? status.warning
                  : !hasGt
                    ? ink.secondary
                    : correct
                      ? status.good
                      : status.critical,
                background: !report
                  ? `${status.warning}12`
                  : !hasGt
                    ? `${ink.muted}10`
                    : correct
                      ? `${status.good}10`
                      : `${status.critical}10`,
              }}
            >
              <span aria-hidden>{!report ? "⚠" : !hasGt ? "○" : correct ? "✓" : "✗"}</span>
              {!report
                ? "Report Rejected"
                : !hasGt
                  ? "Normal Traffic Cluster (False Positive)"
                  : correct
                    ? "Matches Ground-Truth Root Cause"
                    : `Mismatched — Ground Truth: ${data.ground_truth_service}`}
            </span>
          </div>
          <p className="mt-1 font-mono text-[11px] text-ink-muted">
            {data.incident_id} · {stampUTC(data.start_ts)} → {clockUTC(data.end_ts)} UTC
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3.5 md:grid-cols-4">
        <StatTile
          label="Fault Category"
          value={formatFaultType(data.fault_type)}
          hint="Benchmark ground truth"
        />
        <StatTile
          label="Report Confidence"
          value={report ? num(report.confidence, 2) : "—"}
          hint={report?.llm_backend ?? "No diagnostic report generated"}
        />
        <StatTile
          label="Clustered Alerts"
          value={String(data.alert_ids.length)}
          hint={`Correlation window: ${data.grouping_reason.temporal_window_sec}s`}
        />
        <StatTile
          label="Topology Edges Used"
          value={String(data.grouping_reason.graph_edges_used)}
          hint="Call-graph edges connecting alerts"
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.65fr_1fr]">
        <Card
          title="Service Dependency & Fault Propagation Graph"
          subtitle="Animated red edges show backward fault propagation (callee → caller). Gray nodes display healthy adjacent neighbors for blast-radius context."
          right={
            <ul className="flex flex-wrap gap-x-3.5 gap-y-1">
              {(Object.keys(ROLE) as GraphNode["role"][]).map((r) => (
                <li key={r} className="flex items-center gap-1 text-[10.5px] font-medium text-ink-2">
                  <span aria-hidden style={{ color: ROLE[r].color }}>
                    {ROLE[r].glyph}
                  </span>
                  {ROLE[r].label}
                </li>
              ))}
            </ul>
          }
        >
          <div className="h-[430px] rounded-xl border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)]/40">
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

          <details className="mt-3">
            <summary className="cursor-pointer text-[11.5px] font-medium text-ink-muted hover:text-ink">
              View Call-Graph Edge Table
            </summary>
            <table className="mt-2.5 w-full border-collapse text-[11.5px]">
              <thead>
                <tr className="border-b border-[color:var(--color-hairline)] text-left text-[10.5px] font-semibold tracking-wide text-ink-muted uppercase">
                  <th className="py-1.5 pr-3">Caller Service</th>
                  <th className="py-1.5 pr-3">Callee Service</th>
                  <th className="py-1.5 pr-3 text-right">Observed Spans</th>
                  <th className="py-1.5 pr-3 text-right">Mean Latency</th>
                  <th className="py-1.5">On Fault Path</th>
                </tr>
              </thead>
              <tbody>
                {data.edges.map((e) => (
                  <tr key={`${e.source}-${e.target}`} className="border-b border-[color:var(--color-hairline)] last:border-0">
                    <td className="py-1.5 pr-3 font-mono">{e.source}</td>
                    <td className="py-1.5 pr-3 font-mono">{e.target}</td>
                    <td className="py-1.5 pr-3 text-right tabular-nums">
                      {e.call_count.toLocaleString("en-US")}
                    </td>
                    <td className="py-1.5 pr-3 text-right tabular-nums">
                      {e.avg_duration_ms != null ? `${num(e.avg_duration_ms, 1)} ms` : "—"}
                    </td>
                    <td className="py-1.5">{e.on_path ? "Yes" : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </Card>

        <div className="space-y-4">
          {report ? (
            <Card
              title="Automated Diagnostic Report"
              subtitle={`Schema v${report.schema_version} · ${report.llm_backend} · ${stampUTC(report.generated_at)}`}
              right={
                <button
                  type="button"
                  onClick={() => setRawJson((v) => !v)}
                  className="rounded-md border border-[color:var(--color-hairline)] bg-surface px-2.5 py-1 text-[11px] font-medium text-ink-2 hover:text-ink"
                >
                  {rawJson ? "Formatted View" : "Raw JSON"}
                </button>
              }
            >
              {rawJson ? (
                <pre className="max-h-[420px] overflow-auto rounded-lg bg-[color:var(--color-plane)] p-3 font-mono text-[11px] leading-relaxed text-ink-2">
                  {JSON.stringify(report, null, 2)}
                </pre>
              ) : (
                <div className="space-y-4">
                  <dl className="divide-y divide-[color:var(--color-hairline)]">
                    <KV
                      k="Predicted Root Cause"
                      v={<span className="font-mono font-semibold">{report.root_cause_service}</span>}
                    />
                    <KV
                      k="Fault Category"
                      v={<span className="font-mono">{formatFaultType(report.fault_type)}</span>}
                    />
                    <KV k="Confidence" v={num(report.confidence, 2)} />
                  </dl>

                  <div>
                    <div className="mb-1.5 text-[11px] font-semibold tracking-wide text-ink-muted uppercase">
                      Fault Propagation Chain
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      {report.propagation_path.map((s, i) => (
                        <span key={s} className="flex items-center gap-1.5">
                          {i > 0 && <span className="text-ink-muted">→</span>}
                          <span
                            className="rounded-md border px-2 py-0.5 font-mono text-[11px] font-medium"
                            style={{
                              borderColor: i === 0 ? status.critical : "var(--color-hairline)",
                              color: i === 0 ? status.critical : "var(--color-ink-2)",
                              background: i === 0 ? `${status.critical}0d` : "var(--color-plane)",
                            }}
                          >
                            {s}
                          </span>
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <div className="mb-1.5 text-[11px] font-semibold tracking-wide text-ink-muted uppercase">
                      Supporting Evidence ({report.evidence.length})
                    </div>
                    <ul className="space-y-2">
                      {report.evidence.length ? (
                        report.evidence.map((ev) => (
                          <li
                            key={ev.event_id}
                            className="rounded-lg border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)]/60 p-2.5"
                          >
                            <div className="flex items-center gap-2 text-[10.5px] text-ink-muted">
                              <Pill>{ev.modality}</Pill>
                              <span className="font-mono font-medium text-ink">{ev.service}</span>
                              <span className="tabular-nums">{clockUTC(ev.ts)} UTC</span>
                            </div>
                            <p className="mt-1 font-mono text-[11px] leading-relaxed break-words text-ink-2">
                              {ev.excerpt}
                            </p>
                          </li>
                        ))
                      ) : (
                        <li className="text-[11.5px] text-ink-muted">
                          No telemetry evidence excerpts attached to this cluster.
                        </li>
                      )}
                    </ul>
                  </div>

                  <div>
                    <div className="mb-1.5 text-[11px] font-semibold tracking-wide text-ink-muted uppercase">
                      Recommended Remediation Actions
                    </div>
                    <ul className="space-y-2">
                      {report.suggested_actions.map((s) => (
                        <li key={s.description} className="flex items-start gap-2 text-[12px] leading-relaxed text-ink-2">
                          <span
                            className="mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase"
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
                          <span>{s.description}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </Card>
          ) : (
            <Card
              title="Diagnostic Report Rejected"
              subtitle="Schema validation failure recorded to reject store without silent suppression."
            >
              <p className="text-[12.5px] text-ink-2">{data.rejected_reason}</p>
            </Card>
          )}

          <Card title={`Correlated Alerts (${data.alerts.length})`}>
            <ul className="space-y-1.5">
              {data.alerts.map((a) => (
                <li key={a.alert_id}>
                  <Link
                    to={`/alerts/${a.alert_id}`}
                    className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-[11.5px] transition-colors hover:bg-[color:var(--color-plane)]"
                  >
                    <span className="tabular-nums text-ink-muted">{clockUTC(a.ts)}</span>
                    <span className="font-mono font-medium text-ink-2">{a.service}</span>
                    <span className="ml-auto">
                      <VerdictBadge verdict={a.verdict} compact />
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </div>
  );
}
