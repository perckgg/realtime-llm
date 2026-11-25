import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Handle,
  MarkerType,
  Position,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import { api } from "@/api/client";
import type { GraphNode } from "@/api/types";
import RcaPropagationStory from "@/components/RcaPropagationStory";
import TopologyCanvas from "@/components/TopologyCanvas";
import { Card, Empty, ErrorBox, KV, Loading, Pill, StatTile, VerdictBadge } from "@/components/ui";
import {
  computeNeighborhoodFocus,
  edgeWidthFromCalls,
  formatCallCount,
  layoutIncidentNeighborhood,
} from "@/lib/graphLayout";
import { useRuns } from "@/lib/runContext";
import { clockUTC, cx, num, stampUTC, useAsync } from "@/lib/util";
import { ink, series, status } from "@/theme/tokens";

const ROLE: Record<GraphNode["role"], { color: string; glyph: string; label: string }> = {
  root_cause: { color: status.critical, glyph: "◉", label: "Predicted root cause" },
  ground_truth: { color: status.good, glyph: "✓", label: "Ground truth" },
  affected: { color: status.serious, glyph: "◐", label: "Affected" },
  healthy: { color: ink.muted, glyph: "○", label: "Healthy neighbor" },
};

const UPSTREAM_COLOR = "#2563eb";
const DOWNSTREAM_COLOR = "#ea580c";

type FocusState = "none" | "selected" | "related" | "dimmed";

type ServiceNodeData = {
  node: GraphNode;
  pathIndex: number | null;
  focusState: FocusState;
  onSelect: (service: string) => void;
  onHover: (service: string | null) => void;
};

function ServiceNode({ data }: NodeProps<Node<ServiceNodeData>>) {
  const { node, pathIndex, focusState, onSelect, onHover } = data;
  const role = ROLE[node.role];
  const emphasised = node.role === "root_cause" || node.role === "ground_truth" || node.role === "affected";

  const glow =
    focusState === "selected"
      ? "0 0 0 2px var(--color-accent), 0 8px 18px rgb(37 99 235 / 0.18)"
      : node.role === "root_cause" && focusState !== "dimmed"
        ? `0 0 0 1px ${role.color}, 0 6px 16px color-mix(in srgb, ${role.color} 22%, transparent)`
        : undefined;

  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onSelect(node.service);
      }}
      onMouseEnter={() => onHover(node.service)}
      onMouseLeave={() => onHover(null)}
      className={cx(
        "min-w-[186px] rounded-xl border bg-surface px-3 py-2.5 text-left transition-all duration-150",
        emphasised && "shadow-xs",
      )}
      style={{
        borderColor: focusState === "selected" ? "var(--color-accent)" : emphasised ? role.color : "var(--color-hairline)",
        borderWidth: emphasised || focusState === "selected" ? 1.8 : 1,
        opacity: focusState === "dimmed" ? 0.16 : 1,
        boxShadow: glow,
        background:
          node.role === "healthy"
            ? "var(--color-surface)"
            : `color-mix(in srgb, ${role.color} 10%, var(--color-surface))`,
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: "var(--color-axis)", width: 6, height: 6 }}
      />
      <div className="flex items-center gap-1.5">
        <span aria-hidden style={{ color: role.color }} className="text-[12px]">
          {role.glyph}
        </span>
        <span className="font-mono text-[12px] font-semibold text-ink">{node.service}</span>
        {pathIndex !== null && (
          <span className="ml-auto rounded bg-[color:var(--color-plane)] px-1.5 py-0.5 font-mono text-[10px] tabular-nums text-ink-muted">
            #{pathIndex + 1}
          </span>
        )}
      </div>
      <div className="mt-0.5 text-[10.5px] font-medium" style={{ color: role.color }}>
        {role.label}
      </div>
      {node.alert_count > 0 && (
        <div className="mt-1.5 flex items-center gap-2">
          <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-[color:var(--color-grid)]">
            <span
              className="block h-1.5 rounded-full"
              style={{ width: `${Math.min(100, node.max_anomaly_score * 100)}%`, background: series[0] }}
            />
          </span>
          <span className="font-mono text-[10px] tabular-nums text-ink-2">
            {node.alert_count} alert · {num(node.max_anomaly_score, 2)}
          </span>
        </div>
      )}
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: "var(--color-axis)", width: 6, height: 6 }}
      />
    </button>
  );
}

const nodeTypes = { service: ServiceNode };

export default function IncidentDetail() {
  const { incidentId = "" } = useParams();
  const { groundTruthOverlay } = useRuns();
  const { data, loading, error } = useAsync(() => api.getIncident(incidentId), [incidentId]);
  const [rawJson, setRawJson] = useState(false);
  const [graphMode, setGraphMode] = useState<"focus" | "full">("focus");
  const [selectedService, setSelectedService] = useState<string | null>(null);
  const [hoveredService, setHoveredService] = useState<string | null>(null);

  const fanLayout = useMemo(
    () => (data ? layoutIncidentNeighborhood(data, graphMode) : null),
    [data, graphMode],
  );

  const activeFocusId = hoveredService ?? selectedService;
  const focus = useMemo(
    () => (fanLayout ? computeNeighborhoodFocus(activeFocusId, fanLayout.edges) : null),
    [fanLayout, activeFocusId],
  );

  const graph = useMemo(() => {
    if (!fanLayout) return null;

    const nodes: Node<ServiceNodeData>[] = fanLayout.nodes.map(({ node, pathIndex, x, y }) => {
      let focusState: FocusState = "none";
      if (focus) {
        if (node.service === focus.focused) focusState = "selected";
        else if (focus.relatedNodes.has(node.service)) focusState = "related";
        else focusState = "dimmed";
      }
      return {
        id: node.service,
        type: "service",
        position: { x, y },
        data: {
          node,
          pathIndex,
          focusState,
          onSelect: (svc) => setSelectedService((cur) => (cur === svc ? null : svc)),
          onHover: setHoveredService,
        },
        draggable: true,
      };
    });

    const edges: Edge[] = fanLayout.edges.map((e) => {
      const rawId = `${e.source}->${e.target}`;
      const isRelated = focus ? focus.relatedEdges.has(rawId) : false;
      const isDimmed = Boolean(focus && !isRelated && !e.on_path);
      const isUpstreamEdge = focus ? e.target === focus.focused : false;
      const isDownstreamEdge = focus ? e.source === focus.focused : false;

      const baseWidth = edgeWidthFromCalls(e.call_count, fanLayout.minCalls, fanLayout.maxCalls);
      const stroke = e.on_path
        ? status.critical
        : isUpstreamEdge
          ? UPSTREAM_COLOR
          : isDownstreamEdge
            ? DOWNSTREAM_COLOR
            : "var(--color-axis)";

      const label = e.on_path
        ? e.error_rate > 0
          ? `${(e.error_rate * 100).toFixed(0)}% error`
          : "fault propagation"
        : isRelated
          ? `${formatCallCount(e.call_count)} calls`
          : undefined;

      return {
        // Call edges go caller -> callee; fault propagation reverses direction.
        id: rawId,
        type: "smoothstep",
        source: e.on_path ? e.target : e.source,
        target: e.on_path ? e.source : e.target,
        animated: Boolean(e.on_path || isDownstreamEdge),
        style: {
          stroke,
          strokeWidth: e.on_path ? 2.6 : isRelated ? Math.max(2, baseWidth) : baseWidth,
          strokeDasharray: !e.on_path && !isRelated ? "4 4" : undefined,
          opacity: isDimmed ? 0.12 : e.on_path || isRelated ? 0.95 : 0.48,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: stroke,
          width: 14,
          height: 14,
        },
        label,
        labelStyle: { fill: stroke, fontSize: 10, fontWeight: 600 },
        labelBgStyle: { fill: "var(--color-surface)", fillOpacity: 0.92 },
        labelBgPadding: [4, 2] as [number, number],
        labelBgBorderRadius: 4,
      };
    });

    return { nodes, edges };
  }, [fanLayout, focus]);

  if (loading) return <Loading />;
  if (error || !data || !graph || !fanLayout) return <ErrorBox message={error ?? "Incident not found"} />;

  const hasGt =
    data.ground_truth_service !== null && data.ground_truth_service !== undefined;
  const correct = hasGt && data.root_cause_service === data.ground_truth_service;
  const report = data.report;
  const isCascade = data.services.length > 1;
  const badgeColor = !report
    ? status.warning
    : !hasGt
      ? ink.muted
      : correct
        ? status.good
        : status.critical;
  const badgeLabel = !report
    ? "Report rejected"
    : !hasGt
      ? "Unlabelled in ground truth"
      : correct
        ? "Matches ground truth"
        : `Mismatch — ground truth: ${data.ground_truth_service}`;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 text-[11.5px] text-ink-muted">
        <Link to="/incidents" className="hover:text-ink">
          ← Incident Queue
        </Link>
        <span>·</span>
        <Link to="/timeline" className="hover:text-ink">
          Alert Stream
        </Link>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="font-mono text-[19px] font-semibold tracking-tight text-ink">
              {data.root_cause_service ?? "Inconclusive"}
            </h1>
            {isCascade ? (
              <Pill tone="critical">Multi-service cascade · {data.services.length} services</Pill>
            ) : (
              <Pill tone="accent">Single-service incident</Pill>
            )}
            {groundTruthOverlay && (
              <span
                className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium"
                style={{ borderColor: badgeColor, color: badgeColor }}
              >
                <span aria-hidden>{!report ? "!" : !hasGt ? "—" : correct ? "✓" : "✗"}</span>
                {badgeLabel}
              </span>
            )}
          </div>
          <p className="mt-1 font-mono text-[11px] text-ink-muted">
            {data.incident_id} · {stampUTC(data.start_ts)} → {clockUTC(data.end_ts)} UTC
          </p>
        </div>
      </div>

      {(data.run_id.includes("sens") || data.run_id.includes("c3rolling")) && (
        <div
          className="rounded-xl border px-3.5 py-2.5 text-[11.5px]"
          style={{
            borderColor: "var(--color-hairline)",
            background: "color-mix(in srgb, var(--color-warning) 14%, var(--color-surface))",
            color: "var(--color-ink-2)",
          }}
        >
          <strong className="text-ink">High-Recall Mode (Rolling Baseline):</strong> This
          multi-service cascade incident comes from the rolling-baseline sensitivity stream for
          cascade localization walkthroughs; primary registered benchmark results remain under the
          default CTAV stream.
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile
          label="Fault classification"
          value={report?.fault_type ?? data.fault_type ?? "—"}
          hint={
            groundTruthOverlay && data.fault_type
              ? `Ground truth: ${data.fault_type}`
              : "Diagnostic report classification"
          }
        />
        <StatTile
          label="Diagnostic confidence"
          value={report ? num(report.confidence, 2) : "—"}
          hint={report?.llm_backend ?? "no report"}
        />
        <StatTile
          label="Correlated alerts"
          value={String(data.alert_ids.length)}
          hint={`grouping window ${data.grouping_reason.temporal_window_sec}s`}
        />
        <StatTile
          label="Graph edges used"
          value={String(data.grouping_reason.graph_edges_used)}
          hint="trace edges linking grouped alerts"
        />
      </div>

      <RcaPropagationStory data={data} />

      <div className="grid gap-4 xl:grid-cols-[1.7fr_1fr]">
        <Card
          title="Service Neighborhood Graph"
          subtitle="Horizontal fault propagation spine (solid animated red arrows) with upstream callers above and downstream callees below (dashed background call edges)."
          right={
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex rounded-lg border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)] p-0.5">
                <button
                  type="button"
                  onClick={() => setGraphMode("focus")}
                  className={cx(
                    "rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors",
                    graphMode === "focus"
                      ? "bg-surface text-ink shadow-xs"
                      : "text-ink-muted hover:text-ink",
                  )}
                >
                  Propagation Focus
                </button>
                <button
                  type="button"
                  onClick={() => setGraphMode("full")}
                  className={cx(
                    "rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors",
                    graphMode === "full"
                      ? "bg-surface text-ink shadow-xs"
                      : "text-ink-muted hover:text-ink",
                  )}
                >
                  Full 1-Hop
                  {graphMode === "focus" && fanLayout.hiddenHealthyCount > 0
                    ? ` (+${fanLayout.hiddenHealthyCount})`
                    : ` (${data.nodes.length})`}
                </button>
              </div>
            </div>
          }
        >
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-[11px]">
            <ul className="flex flex-wrap gap-x-3.5 gap-y-1">
              {(Object.keys(ROLE) as GraphNode["role"][]).map((r) => (
                <li key={r} className="flex items-center gap-1.5 text-ink-2">
                  <span aria-hidden style={{ color: ROLE[r].color }}>
                    {ROLE[r].glyph}
                  </span>
                  {ROLE[r].label}
                </li>
              ))}
            </ul>
            <span className="font-mono text-[10.5px] text-ink-muted">
              {graph.nodes.length} / {data.nodes.length} nodes · {graph.edges.length} edges
            </span>
          </div>

          {graph.nodes.length === 0 ? (
            <Empty>No graph nodes available.</Empty>
          ) : (
            <TopologyCanvas
              flowKey={`${data.incident_id}-${graphMode}`}
              nodes={graph.nodes}
              edges={graph.edges}
              nodeTypes={nodeTypes}
              heightClass="h-[430px]"
              title={`Service Neighborhood — ${data.root_cause_service ?? data.incident_id}`}
              hint="Hover or click a service to inspect calls · Red solid arrows show fault propagation"
              onPaneClick={() => {
                setSelectedService(null);
                setHoveredService(null);
              }}
              minimapColor={(n) => {
                const d = n.data as unknown as ServiceNodeData | undefined;
                return d ? ROLE[d.node.role].color : "#94a3b8";
              }}
            />
          )}

          <details className="mt-3">
            <summary className="cursor-pointer text-[11px] text-ink-muted hover:text-ink-2">
              View as table
            </summary>
            <table className="mt-2 w-full border-collapse text-[11.5px]">
              <thead>
                <tr className="border-b border-[color:var(--color-hairline)] text-left text-[10.5px] text-ink-muted">
                  <th className="py-1 pr-3 font-medium">From</th>
                  <th className="py-1 pr-3 font-medium">To</th>
                  <th className="py-1 pr-3 text-right font-medium">Calls</th>
                  <th className="py-1 pr-3 text-right font-medium">Error rate</th>
                  <th className="py-1 font-medium">On path</th>
                </tr>
              </thead>
              <tbody>
                {data.edges.map((e) => (
                  <tr
                    key={`${e.source}-${e.target}`}
                    className="border-b border-[color:var(--color-hairline)] last:border-0"
                  >
                    <td className="py-1 pr-3 font-mono">{e.source}</td>
                    <td className="py-1 pr-3 font-mono">{e.target}</td>
                    <td className="py-1 pr-3 text-right font-mono tabular-nums">{e.call_count}</td>
                    <td className="py-1 pr-3 text-right font-mono tabular-nums">
                      {(e.error_rate * 100).toFixed(1)}%
                    </td>
                    <td className="py-1">{e.on_path ? "yes" : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </Card>

        <div className="space-y-4">
          {report ? (
            <Card
              title="Diagnostic Report"
              subtitle={`schema ${report.schema_version} · ${report.llm_backend} · ${stampUTC(report.generated_at)}`}
              right={
                <button
                  type="button"
                  onClick={() => setRawJson((v) => !v)}
                  className="rounded border border-[color:var(--color-hairline)] px-2 py-1 text-[11px] text-ink-muted hover:text-ink-2"
                >
                  {rawJson ? "Readable" : "Raw JSON"}
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
                    <KV
                      k="root_cause_service"
                      v={<span className="font-mono">{report.root_cause_service}</span>}
                    />
                    <KV k="fault_type" v={<span className="font-mono">{report.fault_type}</span>} />
                    <KV k="confidence" v={num(report.confidence, 2)} />
                  </dl>

                  <div>
                    <div className="mb-1.5 text-[11px] text-ink-muted">Propagation path</div>
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
                      Evidence ({report.evidence.length}) — ≥ 1 required
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
                      Suggested actions (advisory remediation steps)
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
                                    : "var(--color-ink-muted)"
                              } 16%, var(--color-surface))`,
                              color:
                                s.priority === "high"
                                  ? status.critical
                                  : s.priority === "medium"
                                    ? "var(--color-warning)"
                                    : "var(--color-ink-2)",
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
          ) : (
            <Card
              title="Report Rejected"
              subtitle="Recorded in diagnostic audit log when evidence grounding fails."
            >
              <p className="text-[12.5px] text-ink-2">{data.rejected_reason}</p>
            </Card>
          )}

          <Card title={`Alerts in Incident (${data.alerts.length})`}>
            {data.alerts.length === 0 ? (
              <Empty>No alerts in this incident.</Empty>
            ) : (
              <ul className="divide-y divide-[color:var(--color-hairline)]">
                {data.alerts.map((a) => (
                  <li key={a.alert_id} className="flex items-center justify-between gap-2 py-2">
                    <div className="min-w-0">
                      <Link
                        to={`/alerts/${a.alert_id}?run_id=${encodeURIComponent(data.run_id)}`}
                        className="font-mono text-[11.5px] text-ink hover:text-[color:var(--color-accent)] hover:underline"
                      >
                        {a.service}
                      </Link>
                      <div className="font-mono text-[10.5px] text-ink-muted">
                        {clockUTC(a.ts)} UTC · score {num(a.anomaly_score, 2)}
                      </div>
                    </div>
                    <VerdictBadge verdict={a.verdict} compact />
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
