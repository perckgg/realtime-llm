import { useEffect, useMemo, useState } from "react";
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
import type { GraphEdge, GraphNode, IncidentDetail as IncidentDetailT } from "@/api/types";
import { Card, ErrorBox, KV, Loading, Pill, StatTile, VerdictBadge } from "@/components/ui";
import { clockUTC, cx, num, stampUTC, useAsync } from "@/lib/util";
import { formatFaultType, ink, series, status } from "@/theme/tokens";

type ViewMode = "ctav" | "diff";
type StepFilter = "all" | "origin" | "cascade" | "suppressed";
type Selection = { kind: "node"; id: string } | { kind: "edge"; id: string };

const ROLE: Record<GraphNode["role"], { color: string; glyph: string; label: string }> = {
  root_cause: { color: status.critical, glyph: "◉", label: "Predicted Root Cause" },
  ground_truth: { color: status.good, glyph: "✓", label: "Ground-Truth Service" },
  affected: { color: status.serious, glyph: "◐", label: "Affected Upstream Service" },
  healthy: { color: ink.muted, glyph: "○", label: "Healthy Neighbor" },
};

type ServiceNodeData = {
  node: GraphNode;
  pathIndex: number | null;
  viewMode: ViewMode;
  selected: boolean;
  dimmed: boolean;
};

function ServiceNode({ data }: NodeProps<Node<ServiceNodeData>>) {
  const { node, pathIndex, viewMode, selected, dimmed } = data;
  const role = ROLE[node.role];
  const supCount = node.suppressed_count ?? 0;
  const diffBlocked = viewMode === "diff" && node.role === "healthy" && supCount > 0;
  const emphasised = node.role === "root_cause" || node.role === "ground_truth" || diffBlocked;
  const hasRatio = node.sample_span_ms != null && node.baseline_p90_ms != null;
  const ratio =
    hasRatio && node.baseline_p90_ms! > 0 ? node.sample_span_ms! / node.baseline_p90_ms! : null;

  return (
    <div
      className={cx(
        "min-w-[192px] cursor-pointer rounded-xl border bg-surface px-3.5 py-2.5 shadow-sm transition-all",
        emphasised && "shadow-md",
        selected && "ring-2 ring-[color:var(--color-seq-550)] ring-offset-1",
      )}
      style={{
        opacity: dimmed ? 0.3 : 1,
        borderColor: diffBlocked ? status.warning : role.color,
        borderStyle: diffBlocked ? "dashed" : "solid",
        borderWidth: emphasised ? 2 : 1,
        background: diffBlocked
          ? `color-mix(in srgb, ${status.warning} 10%, ${ink.surface})`
          : node.role === "healthy"
            ? ink.surface
            : `color-mix(in srgb, ${role.color} 8%, ${ink.surface})`,
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: ink.axis, width: 6, height: 6 }} />
      <div className="flex items-center gap-1.5">
        <span aria-hidden style={{ color: diffBlocked ? "#b45309" : role.color }} className="text-[12px]">
          {diffBlocked ? "🛡" : role.glyph}
        </span>
        <span className="font-mono text-[11.5px] font-semibold text-ink">{node.service}</span>
        {pathIndex !== null && (
          <span className="ml-auto font-mono text-[10px] tabular-nums text-ink-muted">
            #{pathIndex + 1}
          </span>
        )}
      </div>
      <div
        className="mt-0.5 text-[10.5px] font-medium"
        style={{ color: diffBlocked ? "#92400e" : role.color }}
      >
        {diffBlocked ? "Neighbor Noise Blocked by CTAV" : role.label}
      </div>

      {node.alert_count > 0 && (
        <div className="mt-2 flex items-center gap-2">
          <span className="h-1.5 flex-1 rounded-full" style={{ background: ink.grid }}>
            <span
              className="block h-1.5 rounded-full"
              style={{ width: `${Math.min(1, node.max_anomaly_score) * 100}%`, background: series[0] }}
            />
          </span>
          <span className="text-[10px] tabular-nums text-ink-2">
            {node.alert_count} confirmed · {num(node.max_anomaly_score, 2)}
          </span>
        </div>
      )}

      {supCount > 0 && (
        <div className="mt-1.5 flex items-center justify-between gap-2 rounded bg-[#fffbeb] px-1.5 py-0.5 text-[10px] font-medium text-[#92400e]">
          <span>Blocked by p90 gate</span>
          <span className="font-mono font-semibold">{supCount} suppressed</span>
        </div>
      )}

      {hasRatio && (
        <div className="mt-1.5 font-mono text-[9.5px] text-ink-muted">
          Span {num(node.sample_span_ms!, 1)}ms vs p90 {num(node.baseline_p90_ms!, 1)}ms
          {ratio !== null && ` (${ratio.toFixed(1)}×)`}
        </div>
      )}

      <Handle type="source" position={Position.Right} style={{ background: ink.axis, width: 6, height: 6 }} />
    </div>
  );
}

const nodeTypes = { service: ServiceNode };

function isNodeVisibleInStep(node: GraphNode, step: StepFilter): boolean {
  if (step === "all") return true;
  if (step === "origin") return node.role === "root_cause" || node.role === "ground_truth";
  if (step === "cascade") return node.role !== "healthy";
  if (step === "suppressed") return (node.suppressed_count ?? 0) > 0 || node.role === "root_cause";
  return true;
}

function layout(
  detail: IncidentDetailT,
  viewMode: ViewMode,
  step: StepFilter,
  selection: Selection | null,
): { nodes: Node<ServiceNodeData>[]; edges: Edge[] } {
  const path = detail.services;
  const X = 280;
  const Y = 140;

  const placed = new Map<string, { x: number; y: number }>();
  path.forEach((s, i) => placed.set(s, { x: i * X, y: 0 }));

  const suppressedNeighbors: GraphNode[] = [];
  const otherNeighbors: GraphNode[] = [];
  for (const n of detail.nodes) {
    if (placed.has(n.service)) continue;
    if ((n.suppressed_count ?? 0) > 0) suppressedNeighbors.push(n);
    else otherNeighbors.push(n);
  }

  suppressedNeighbors.forEach((n, idx) => {
    const colWidth = Math.max(225, (path.length * X) / Math.max(1, suppressedNeighbors.length));
    placed.set(n.service, { x: idx * colWidth + 20, y: Y });
  });

  otherNeighbors.forEach((n, idx) => {
    const colWidth = Math.max(225, (path.length * X) / Math.max(1, otherNeighbors.length));
    placed.set(n.service, { x: idx * colWidth + 20, y: -Y });
  });

  const nodeByService = new Map(detail.nodes.map((n) => [n.service, n]));

  const nodes: Node<ServiceNodeData>[] = detail.nodes.map((n) => ({
    id: n.service,
    type: "service",
    position: placed.get(n.service) ?? { x: 0, y: 0 },
    data: {
      node: n,
      pathIndex: path.includes(n.service) ? path.indexOf(n.service) : null,
      viewMode,
      selected: selection?.kind === "node" && selection.id === n.service,
      dimmed: !isNodeVisibleInStep(n, step),
    },
    draggable: true,
  }));

  const edges: Edge[] = detail.edges.map((e) => {
    const edgeId = `${e.source}->${e.target}`;
    const srcNode = nodeByService.get(e.source);
    const dstNode = nodeByService.get(e.target);
    const touchesSuppressed =
      (srcNode?.suppressed_count ?? 0) > 0 || (dstNode?.suppressed_count ?? 0) > 0;
    const isSelected = selection?.kind === "edge" && selection.id === edgeId;
    const diffNoise = viewMode === "diff" && !e.on_path && touchesSuppressed;

    const dimmed =
      step === "origin"
        ? true
        : step === "cascade"
          ? !e.on_path
          : step === "suppressed"
            ? !touchesSuppressed
            : false;

    const stroke = e.on_path
      ? status.critical
      : diffNoise
        ? status.warning
        : isSelected
          ? series[0]
          : ink.grid;

    return {
      // Call graph direction is caller → callee; fault propagation flows callee → caller.
      id: edgeId,
      source: e.on_path ? e.target : e.source,
      target: e.on_path ? e.source : e.target,
      animated: e.on_path || diffNoise,
      style: {
        stroke,
        strokeWidth: isSelected ? 3 : e.on_path ? 2.5 : diffNoise ? 2 : 1.25,
        strokeDasharray: diffNoise ? "5 4" : undefined,
        opacity: dimmed ? 0.2 : 1,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: e.on_path ? status.critical : diffNoise ? status.warning : ink.axis,
        width: 14,
        height: 14,
      },
      label: e.on_path
        ? e.error_rate != null
          ? `${(e.error_rate * 100).toFixed(0)}% errors`
          : `${e.call_count.toLocaleString("en-US")} spans`
        : diffNoise
          ? "noise gated"
          : undefined,
      labelStyle: {
        fill: e.on_path ? status.critical : "#b45309",
        fontSize: 10,
        fontWeight: 600,
      },
      labelBgStyle: { fill: ink.surface },
    };
  });

  return { nodes, edges };
}

export default function IncidentDetail() {
  const { incidentId = "" } = useParams();
  const { data, loading, error } = useAsync(() => api.getIncident(incidentId), [incidentId]);
  const [rawJson, setRawJson] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>("ctav");
  const [step, setStep] = useState<StepFilter>("all");
  const [selection, setSelection] = useState<Selection | null>(null);

  useEffect(() => {
    if (data) {
      const def = data.root_cause_service ?? data.nodes[0]?.service;
      setSelection(def ? { kind: "node", id: def } : null);
      setStep("all");
    }
  }, [data]);

  const graph = useMemo(
    () => (data ? layout(data, viewMode, step, selection) : null),
    [data, viewMode, step, selection],
  );

  if (loading) return <Loading label="Loading incident topology…" />;
  if (error || !data || !graph) return <ErrorBox message={error ?? `Incident '${incidentId}' not found`} />;

  const hasGt = data.ground_truth_service !== null;
  const correct = hasGt && data.root_cause_service === data.ground_truth_service;
  const report = data.report;

  const totalConfirmedInGraph = data.nodes.reduce((acc, n) => acc + n.alert_count, 0);
  const totalSuppressedInGraph = data.nodes.reduce((acc, n) => acc + (n.suppressed_count ?? 0), 0);

  const selectedNode: GraphNode | null =
    selection?.kind === "node"
      ? (data.nodes.find((n) => n.service === selection.id) ?? null)
      : null;
  const selectedEdge: GraphEdge | null =
    selection?.kind === "edge"
      ? (data.edges.find((e) => `${e.source}->${e.target}` === selection.id) ?? null)
      : null;

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
          hint={`${totalSuppressedInGraph} neighbor alerts blocked nearby (±300s)`}
        />
        <StatTile
          label="Topology Edges Used"
          value={String(data.grouping_reason.graph_edges_used)}
          hint="Call-graph edges connecting alerts"
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.65fr_1fr]">
        <div className="space-y-4">
          <Card
            title="Interactive Service Dependency & Fault Propagation Graph"
            subtitle="Click any service node or call edge to inspect local latency vs. p90 baselines, confirmed alerts, and false alarms blocked by CTAV."
            right={
              <div className="flex flex-wrap items-center gap-1 rounded-lg border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)] p-0.5">
                <button
                  type="button"
                  onClick={() => setViewMode("ctav")}
                  className={cx(
                    "rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors",
                    viewMode === "ctav" ? "bg-surface text-ink shadow-xs" : "text-ink-muted hover:text-ink",
                  )}
                >
                  Calibrated CTAV View
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode("diff")}
                  className={cx(
                    "rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors",
                    viewMode === "diff" ? "bg-surface text-[#92400e] shadow-xs" : "text-ink-muted hover:text-ink",
                  )}
                >
                  Before vs. After CTAV Gate (Diff)
                </button>
              </div>
            }
          >
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)]/60 px-3 py-2">
              <div className="flex flex-wrap items-center gap-1">
                <span className="mr-1 text-[10.5px] font-semibold tracking-wide text-ink-muted uppercase">
                  Cascade Step:
                </span>
                {(
                  [
                    ["all", "All Layers"],
                    ["origin", "1. Root Origin"],
                    ["cascade", "2. Upstream Cascade"],
                    ["suppressed", "3. Neighbor Noise Blocked"],
                  ] as const
                ).map(([k, lbl]) => (
                  <button
                    key={k}
                    type="button"
                    onClick={() => {
                      setStep(k);
                      if (k === "suppressed") setViewMode("diff");
                    }}
                    className={cx(
                      "rounded border px-2 py-0.5 text-[11px] font-medium transition-colors",
                      step === k
                        ? "border-[color:var(--color-seq-550)] bg-surface text-ink"
                        : "border-transparent text-ink-muted hover:text-ink",
                    )}
                  >
                    {lbl}
                  </button>
                ))}
              </div>
              <div className="text-[11px] text-ink-2">
                Blast radius:{" "}
                <strong className="font-semibold text-ink">{totalConfirmedInGraph} confirmed</strong>
                {totalSuppressedInGraph > 0 && (
                  <>
                    {" "}
                    ·{" "}
                    <strong className="font-semibold text-[#92400e]">
                      {totalSuppressedInGraph} neighbor noise blocked
                    </strong>
                  </>
                )}
              </div>
            </div>

            <div className="mb-2 flex flex-wrap gap-x-3.5 gap-y-1">
              {(Object.keys(ROLE) as GraphNode["role"][]).map((r) => (
                <span key={r} className="flex items-center gap-1 text-[10.5px] font-medium text-ink-2">
                  <span aria-hidden style={{ color: ROLE[r].color }}>
                    {ROLE[r].glyph}
                  </span>
                  {ROLE[r].label}
                </span>
              ))}
              {viewMode === "diff" && (
                <span className="flex items-center gap-1 text-[10.5px] font-semibold text-[#92400e]">
                  <span aria-hidden>🛡</span>Neighbor False Alarm Blocked by p90 Gate
                </span>
              )}
            </div>

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
                onNodeClick={(_, n) => setSelection({ kind: "node", id: n.id })}
                onEdgeClick={(_, e) => setSelection({ kind: "edge", id: e.id })}
              >
                <Background variant={BackgroundVariant.Dots} gap={18} size={1} color={ink.grid} />
                <Controls showInteractive={false} />
              </ReactFlow>
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-1.5">
              <span className="text-[10.5px] font-semibold tracking-wide text-ink-muted uppercase">
                Inspect Node:
              </span>
              {data.nodes.map((n) => {
                const active = selection?.kind === "node" && selection.id === n.service;
                return (
                  <button
                    key={n.service}
                    type="button"
                    onClick={() => setSelection({ kind: "node", id: n.service })}
                    className={cx(
                      "rounded-md border px-2 py-0.5 font-mono text-[10.5px] transition-colors",
                      active
                        ? "border-[color:var(--color-seq-550)] bg-[color:var(--color-plane)] font-semibold text-ink"
                        : "border-[color:var(--color-hairline)] bg-surface text-ink-2 hover:text-ink",
                    )}
                  >
                    {n.service}
                    {(n.suppressed_count ?? 0) > 0 && ` (🛡${n.suppressed_count})`}
                  </button>
                );
              })}
            </div>

            {selectedNode && <NodeInspector node={selectedNode} />}
            {selectedEdge && <EdgeInspector edge={selectedEdge} />}

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
                    <tr
                      key={`${e.source}-${e.target}`}
                      onClick={() => setSelection({ kind: "edge", id: `${e.source}->${e.target}` })}
                      className="cursor-pointer border-b border-[color:var(--color-hairline)] last:border-0 hover:bg-[color:var(--color-plane)]/60"
                    >
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
        </div>

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

function NodeInspector({ node }: { node: GraphNode }) {
  const role = ROLE[node.role];
  const supCount = node.suppressed_count ?? 0;
  const confirmedIds = node.confirmed_alert_ids ?? [];
  const suppressedIds = node.suppressed_alert_ids ?? [];
  const hasLatency = node.sample_span_ms != null && node.baseline_p90_ms != null;
  const maxMs = hasLatency ? Math.max(node.sample_span_ms!, node.baseline_p90_ms!, 1) : 1;

  return (
    <div
      className="mt-3 rounded-xl border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)]/70 p-4"
      aria-label="Node Telemetry Inspector"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-semibold tracking-wide text-ink-muted uppercase">
            Node Inspector
          </span>
          <span className="font-mono text-[13px] font-semibold text-ink">{node.service}</span>
          <Pill tone={node.role === "healthy" ? "neutral" : "warn"}>
            {role.glyph} {role.label}
          </Pill>
        </div>
        {node.first_alert_ts && (
          <span className="font-mono text-[11px] text-ink-muted">
            First signal: {stampUTC(node.first_alert_ts)}
          </span>
        )}
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg border border-[color:var(--color-hairline)] bg-surface p-2.5">
          <div className="text-[10.5px] text-ink-muted">Confirmed Alerts</div>
          <div className="mt-0.5 text-[16px] font-semibold tabular-nums text-ink">{node.alert_count}</div>
        </div>
        <div className="rounded-lg border border-[color:var(--color-hairline)] bg-surface p-2.5">
          <div className="text-[10.5px] text-ink-muted">Blocked by p90 Gate (±300s)</div>
          <div className="mt-0.5 text-[16px] font-semibold tabular-nums text-[#92400e]">{supCount}</div>
        </div>
        <div className="rounded-lg border border-[color:var(--color-hairline)] bg-surface p-2.5">
          <div className="text-[10.5px] text-ink-muted">Peak Anomaly Score</div>
          <div className="mt-0.5 text-[16px] font-semibold tabular-nums text-ink">
            {node.max_anomaly_score > 0 ? num(node.max_anomaly_score, 3) : "—"}
          </div>
        </div>
      </div>

      {hasLatency ? (
        <div className="mt-3 rounded-lg border border-[color:var(--color-hairline)] bg-surface p-3">
          <div className="flex items-center justify-between text-[11px]">
            <span className="font-medium text-ink">
              Peak Observed Span Latency vs. Historical p90 Baseline
            </span>
            <span className="font-mono text-ink-2">
              {num(node.sample_span_ms!, 1)} ms vs {num(node.baseline_p90_ms!, 1)} ms (
              {node.baseline_p90_ms! > 0
                ? `${(node.sample_span_ms! / node.baseline_p90_ms!).toFixed(1)}×`
                : "n/a"}
              )
            </span>
          </div>
          <div className="mt-2 space-y-1.5 text-[10.5px]">
            <div className="flex items-center gap-2">
              <span className="w-24 text-ink-muted">Observed Span</span>
              <span className="h-2 flex-1 rounded-full bg-[color:var(--color-grid)]">
                <span
                  className="block h-2 rounded-full"
                  style={{
                    width: `${(node.sample_span_ms! / maxMs) * 100}%`,
                    background:
                      node.sample_span_ms! > node.baseline_p90_ms! ? status.critical : series[0],
                  }}
                />
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-24 text-ink-muted">Historical p90</span>
              <span className="h-2 flex-1 rounded-full bg-[color:var(--color-grid)]">
                <span
                  className="block h-2 rounded-full"
                  style={{
                    width: `${(node.baseline_p90_ms! / maxMs) * 100}%`,
                    background: ink.muted,
                  }}
                />
              </span>
            </div>
          </div>
        </div>
      ) : supCount > 0 ? (
        <p className="mt-3 rounded-lg border border-[color:var(--color-hairline)] bg-surface p-3 text-[11.5px] text-ink-2">
          In uncalibrated Topology RAG, neighbor fault signals would have triggered{" "}
          <strong>{supCount}</strong> false alarms on <code className="font-mono">{node.service}</code>.
          CTAV suppressed them because local trace spans remained within historical p90 thresholds and no local ERROR/WARN logs were present.
        </p>
      ) : null}

      {(confirmedIds.length > 0 || suppressedIds.length > 0) && (
        <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px]">
          {confirmedIds.map((aid) => (
            <Link
              key={aid}
              to={`/alerts/${aid}`}
              className="rounded-md border border-[color:var(--color-series-1)]/50 bg-surface px-2 py-0.5 font-mono text-[10.5px] text-[#1e40af] hover:underline"
            >
              Inspect Confirmed: {aid} →
            </Link>
          ))}
          {suppressedIds.map((aid) => (
            <Link
              key={aid}
              to={`/alerts/${aid}`}
              className="rounded-md border border-[color:var(--color-serious)]/60 bg-[#fffbeb] px-2 py-0.5 font-mono text-[10.5px] text-[#92400e] hover:underline"
            >
              Inspect Blocked FP: {aid} →
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function EdgeInspector({ edge }: { edge: GraphEdge }) {
  return (
    <div
      className="mt-3 rounded-xl border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)]/70 p-4"
      aria-label="Edge Dependency Inspector"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[11px] font-semibold tracking-wide text-ink-muted uppercase">
          Edge Inspector
        </span>
        <span className="font-mono text-[12.5px] font-semibold text-ink">
          {edge.source} (Caller) → {edge.target} (Callee)
        </span>
        <Pill tone={edge.on_path ? "warn" : "neutral"}>
          {edge.on_path ? "Active Fault Propagation Edge" : "Adjacent Context Edge"}
        </Pill>
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg border border-[color:var(--color-hairline)] bg-surface p-2.5">
          <div className="text-[10.5px] text-ink-muted">Observed Span Count</div>
          <div className="mt-0.5 text-[16px] font-semibold tabular-nums text-ink">
            {edge.call_count.toLocaleString("en-US")}
          </div>
        </div>
        <div className="rounded-lg border border-[color:var(--color-hairline)] bg-surface p-2.5">
          <div className="text-[10.5px] text-ink-muted">Historical Mean Duration</div>
          <div className="mt-0.5 text-[16px] font-semibold tabular-nums text-ink">
            {edge.avg_duration_ms != null ? `${num(edge.avg_duration_ms, 1)} ms` : "—"}
          </div>
        </div>
        <div className="rounded-lg border border-[color:var(--color-hairline)] bg-surface p-2.5">
          <div className="text-[10.5px] text-ink-muted">Propagation Direction</div>
          <div className="mt-0.5 font-mono text-[11.5px] font-semibold text-ink">
            {edge.target} ⟶ {edge.source}
          </div>
        </div>
      </div>
    </div>
  );
}
