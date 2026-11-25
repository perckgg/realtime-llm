import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Handle,
  MarkerType,
  Position,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import { api } from "@/api/client";
import type { Alert, Incident, TopologyData, TopologyNode, TopologyStatus } from "@/api/types";
import {
  ActivityIcon,
  AlertTriangleIcon,
  ArrowRightIcon,
  FlameIcon,
  LayersIcon,
  NetworkIcon,
  PlayIcon,
  ShieldCheckIcon,
} from "@/components/icons";
import TopologyCanvas from "@/components/TopologyCanvas";
import { Card, Empty, ErrorBox, KV, Loading, Pill, StatTile } from "@/components/ui";
import {
  computeNeighborhoodFocus,
  edgeWidthFromCalls,
  formatCallCount,
  layoutServiceTopology,
  type TopologyScope,
} from "@/lib/graphLayout";
import { useRuns } from "@/lib/runContext";
import { clockUTC, cx, num, pct, policySteps, useAsync } from "@/lib/util";
import { status as statusPalette } from "@/theme/tokens";

const STATUS_META: Record<
  TopologyStatus,
  { color: string; glyph: string; label: string }
> = {
  critical: { color: statusPalette.critical, glyph: "◉", label: "Root cause" },
  degraded: { color: statusPalette.serious, glyph: "◐", label: "Alerted" },
  suppressed: { color: statusPalette.warning, glyph: "◇", label: "Filtered noise" },
  healthy: { color: statusPalette.good, glyph: "○", label: "Healthy" },
};

const UPSTREAM_COLOR = "#2563eb";
const DOWNSTREAM_COLOR = "#ea580c";

type FocusRole = "none" | "selected" | "upstream" | "downstream" | "dimmed";

type TopoNodeData = {
  node: TopologyNode;
  focusRole: FocusRole;
  onSelect: (service: string) => void;
  onHover: (service: string | null) => void;
};

function TopologyServiceNode({ data }: NodeProps<Node<TopoNodeData>>) {
  const { node, focusRole, onSelect, onHover } = data;
  const meta = STATUS_META[node.status];
  const emphasised = node.status === "critical" || node.status === "degraded";
  const subTag = node.subsystem === "online_boutique" ? "OB" : node.subsystem === "train_ticket" ? "TT" : "SYS";

  const borderColor =
    focusRole === "selected"
      ? "var(--color-accent)"
      : focusRole === "upstream"
        ? UPSTREAM_COLOR
        : focusRole === "downstream"
          ? DOWNSTREAM_COLOR
          : emphasised
            ? meta.color
            : "var(--color-hairline)";

  const glow =
    focusRole === "selected"
      ? "0 0 0 2px var(--color-accent), 0 8px 18px rgb(37 99 235 / 0.18)"
      : node.status === "critical" && focusRole !== "dimmed"
        ? `0 0 0 1px ${meta.color}, 0 6px 16px color-mix(in srgb, ${meta.color} 22%, transparent)`
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
      className="w-[204px] rounded-xl border bg-surface px-3 py-2.5 text-left transition-all duration-150"
      style={{
        borderColor,
        borderWidth: emphasised || focusRole === "selected" || focusRole === "upstream" || focusRole === "downstream" ? 1.8 : 1,
        opacity: focusRole === "dimmed" ? 0.16 : 1,
        boxShadow: glow,
        background:
          node.status === "healthy"
            ? "var(--color-surface)"
            : `color-mix(in srgb, ${meta.color} 8%, var(--color-surface))`,
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: "var(--color-axis)", width: 6, height: 6 }}
      />

      {/* Row 1: Identity + Subsystem */}
      <div className="flex items-center justify-between gap-1.5">
        <div className="flex min-w-0 items-center gap-1.5">
          <span aria-hidden style={{ color: meta.color }} className="shrink-0 text-[11px]">
            {meta.glyph}
          </span>
          <span className="truncate font-mono text-[11.5px] font-semibold text-ink">
            {node.service}
          </span>
        </div>
        <span className="shrink-0 rounded bg-[color:var(--color-plane)] px-1 py-0.5 font-mono text-[9px] font-medium text-ink-muted">
          {subTag}
        </span>
      </div>

      {/* Row 2: Status + Anomaly Score Mini Bar */}
      <div className="mt-1.5 flex items-center gap-2">
        <span className="shrink-0 text-[10px] font-medium" style={{ color: meta.color }}>
          {focusRole === "upstream"
            ? "↑ Caller"
            : focusRole === "downstream"
              ? "↓ Callee"
              : meta.label}
        </span>
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[color:var(--color-grid)]">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${Math.min(100, Math.round(node.max_anomaly_score * 100))}%`,
              background: node.max_anomaly_score >= 0.85 ? meta.color : "var(--color-axis)",
            }}
          />
        </div>
        <span className="font-mono text-[9.5px] tabular-nums text-ink-muted">
          {node.max_anomaly_score > 0 ? num(node.max_anomaly_score, 2) : "—"}
        </span>
      </div>

      {/* Row 3: Compact Operational Counters */}
      <div className="mt-1.5 flex items-center justify-between border-t border-[color:var(--color-hairline)] pt-1.5 font-mono text-[9.5px] tabular-nums text-ink-muted">
        <span>
          <strong className="text-ink">{node.incident_count}</strong> inc
        </span>
        <span>
          <strong className="text-ink">{node.confirmed_alerts}</strong> alert
        </span>
        <span>
          <strong className="text-ink">{node.suppressed_alerts}</strong> filt
        </span>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        style={{ background: "var(--color-axis)", width: 6, height: 6 }}
      />
    </button>
  );
}

const topoNodeTypes = { topologyService: TopologyServiceNode };

export default function Overview() {
  const navigate = useNavigate();
  const { runs, runId, runsLoading, runsError, groundTruthOverlay } = useRuns();
  const [scope, setScope] = useState<TopologyScope>("active_faults");
  const [includeFilteredNoise, setIncludeFilteredNoise] = useState(false);
  const [includeHealthyNeighbors, setIncludeHealthyNeighbors] = useState(true);
  const [selectedService, setSelectedService] = useState<string | null>(null);
  const [hoveredService, setHoveredService] = useState<string | null>(null);

  const activeRun = runs.find((r) => r.run_id === runId);
  const rcaOnlyRun = Boolean(activeRun && activeRun.alert_count === 0);

  const topologyQ = useAsync(
    () => (runId ? api.getTopology(runId) : Promise.resolve<TopologyData | null>(null)),
    [runId],
  );
  const incidentsQ = useAsync(
    () => (runId ? api.listIncidents(runId) : Promise.resolve<Incident[]>([])),
    [runId],
  );
  const alertsQ = useAsync(
    () => (runId && !rcaOnlyRun ? api.listAlerts({ runId }) : Promise.resolve<Alert[]>([])),
    [runId, rcaOnlyRun],
  );

  const topology = topologyQ.data;
  const incidents = incidentsQ.data ?? [];
  const alerts = alertsQ.data ?? [];

  const summary = useMemo(() => {
    const confirmed = alerts.filter((a) => a.verdict === "TRUE_ALERT").length;
    let c3Suppressed = 0;
    let totalPolicySuppressed = 0;
    for (const a of alerts) {
      const steps = policySteps(a);
      if (steps.anchoring.status === "downgraded") c3Suppressed += 1;
      if (steps.shortReason !== null) totalPolicySuppressed += 1;
    }
    const rawConfirmed = confirmed + totalPolicySuppressed;
    const suppressionRate = rawConfirmed > 0 ? totalPolicySuppressed / rawConfirmed : 0;
    const arr = confirmed > 0 ? Math.max(0, 1 - incidents.length / confirmed) : 0;
    const impactedServices =
      topology?.nodes.filter((n) => n.status === "critical" || n.status === "degraded").length ?? 0;
    const totalServices = topology?.nodes.length ?? 0;
    const multiServiceIncidents = incidents.filter((i) => i.services.length > 1).length;
    return {
      confirmed,
      c3Suppressed,
      totalPolicySuppressed,
      suppressionRate,
      arr,
      impactedServices,
      totalServices,
      multiServiceIncidents,
    };
  }, [alerts, incidents, topology]);

  const layout = useMemo(
    () =>
      topology
        ? layoutServiceTopology(topology, {
            scope,
            includeFilteredNoise,
            includeHealthyNeighbors,
          })
        : null,
    [topology, scope, includeFilteredNoise, includeHealthyNeighbors],
  );

  const activeFocusId = hoveredService ?? selectedService;
  const focus = useMemo(
    () => (layout ? computeNeighborhoodFocus(activeFocusId, layout.edges) : null),
    [layout, activeFocusId],
  );

  const rfGraph = useMemo(() => {
    if (!layout) return null;
    const byName = new Map(layout.nodes.map((p) => [p.node.service, p.node]));

    const nodes: Node<TopoNodeData>[] = layout.nodes.map(({ node, x, y }) => {
      let focusRole: FocusRole = "none";
      if (focus) {
        if (node.service === focus.focused) focusRole = "selected";
        else if (focus.upstream.has(node.service)) focusRole = "upstream";
        else if (focus.downstream.has(node.service)) focusRole = "downstream";
        else focusRole = "dimmed";
      }
      return {
        id: node.service,
        type: "topologyService",
        position: { x, y },
        data: {
          node,
          focusRole,
          onSelect: (svc) => setSelectedService((cur) => (cur === svc ? null : svc)),
          onHover: setHoveredService,
        },
        draggable: true,
      };
    });

    const edges: Edge[] = layout.edges.map((e) => {
      const id = `${e.source}->${e.target}`;
      const src = byName.get(e.source);
      const dst = byName.get(e.target);
      const faultPair =
        (src && (src.status === "critical" || src.status === "degraded")) &&
        (dst && (dst.status === "critical" || dst.status === "degraded"));

      const isRelated = focus ? focus.relatedEdges.has(id) : false;
      const isUpstreamEdge = focus ? e.target === focus.focused : false;
      const isDownstreamEdge = focus ? e.source === focus.focused : false;
      const isDimmed = Boolean(focus && !isRelated);

      const baseWidth = edgeWidthFromCalls(e.call_count, layout.minCalls, layout.maxCalls);
      const stroke = isUpstreamEdge
        ? UPSTREAM_COLOR
        : isDownstreamEdge
          ? DOWNSTREAM_COLOR
          : faultPair
            ? statusPalette.critical
            : "var(--color-axis)";

      return {
        id,
        type: "smoothstep",
        source: e.source,
        target: e.target,
        animated: Boolean(faultPair || isDownstreamEdge),
        style: {
          stroke,
          strokeWidth: isRelated ? Math.max(2.2, baseWidth) : faultPair ? 2.2 : baseWidth,
          strokeDasharray: !faultPair && !isRelated ? "4 3" : undefined,
          opacity: isDimmed ? 0.1 : isRelated || faultPair ? 0.95 : 0.45,
          transition: "opacity 150ms ease, stroke 150ms ease",
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: stroke,
          width: 14,
          height: 14,
        },
        label: isRelated ? `${formatCallCount(e.call_count)} calls` : undefined,
        labelStyle: { fill: stroke, fontSize: 10, fontWeight: 600 },
        labelBgStyle: { fill: "var(--color-surface)", fillOpacity: 0.92 },
        labelBgPadding: [4, 2] as [number, number],
        labelBgBorderRadius: 4,
      };
    });

    return { nodes, edges };
  }, [layout, focus]);

  const inspectedNode = useMemo(() => {
    if (!topology || !selectedService) return null;
    return topology.nodes.find((n) => n.service === selectedService) ?? null;
  }, [topology, selectedService]);

  const inspectedNeighbors = useMemo(() => {
    if (!topology || !selectedService) return { upstream: [] as string[], downstream: [] as string[] };
    const f = computeNeighborhoodFocus(selectedService, topology.edges);
    return {
      upstream: f ? [...f.upstream].sort() : [],
      downstream: f ? [...f.downstream].sort() : [],
    };
  }, [topology, selectedService]);

  const priorityIncidents = useMemo(() => {
    return [...incidents]
      .sort(
        (a, b) =>
          b.services.length - a.services.length ||
          b.alert_ids.length - a.alert_ids.length ||
          b.start_ts.localeCompare(a.start_ts),
      )
      .slice(0, 8);
  }, [incidents]);

  if (runsLoading) return <Loading label="Connecting to telemetry store…" />;
  if (runsError) return <ErrorBox message={runsError} />;
  if (!runId) return <Empty>No telemetry streams available in storage.</Empty>;

  const flowKey = `${runId}-${scope}-${includeFilteredNoise ? 1 : 0}-${includeHealthyNeighbors ? 1 : 0}`;

  return (
    <div className="space-y-5">
      {/* Operational header banner */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-[19px] font-semibold tracking-tight text-ink">
            Operations Command Center
          </h1>
          <p className="mt-0.5 text-[12px] text-ink-muted">
            Topology-aware alert validation (CTAV) and automated microservice root cause analysis
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => navigate(`/timeline?run_id=${encodeURIComponent(runId)}&replay=1`)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-[color:var(--color-accent)] px-3.5 py-2 text-[12px] font-medium text-white shadow-xs transition-opacity hover:opacity-90"
          >
            <PlayIcon size={13} />
            Simulate Live Replay
          </button>
          <Link
            to={`/incidents?run_id=${encodeURIComponent(runId)}`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[color:var(--color-hairline)] bg-surface px-3 py-2 text-[12px] font-medium text-ink transition-colors hover:bg-[color:var(--color-plane)]"
          >
            Incident Queue ({incidents.length})
            <ArrowRightIcon size={13} />
          </Link>
        </div>
      </div>

      {/* KPI Strip */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile
          label="Active Incidents"
          value={String(incidents.length)}
          hint={
            summary.confirmed > 0
              ? `${pct(summary.arr)} alert reduction (${summary.confirmed} → ${incidents.length})`
              : `${summary.multiServiceIncidents} multi-service cascades`
          }
          accent={incidents.length > 0 ? statusPalette.critical : statusPalette.good}
          icon={<FlameIcon size={16} />}
        />
        <StatTile
          label="Confirmed Alerts"
          value={rcaOnlyRun ? "—" : String(summary.confirmed)}
          hint={
            rcaOnlyRun
              ? "Archived RCA-only session"
              : `from ${alerts.length.toLocaleString("en-US")} anomaly candidates`
          }
          accent="var(--color-accent)"
          icon={<ActivityIcon size={16} />}
        />
        <StatTile
          label="Noise Suppressed (CTAV)"
          value={rcaOnlyRun ? "—" : summary.totalPolicySuppressed.toLocaleString("en-US")}
          hint={
            rcaOnlyRun
              ? "Switch to full stream for alert telemetry"
              : `${summary.c3Suppressed.toLocaleString("en-US")} by C3 anchoring · ${pct(summary.suppressionRate)} raw noise blocked`
          }
          accent={statusPalette.good}
          icon={<ShieldCheckIcon size={16} />}
        />
        <StatTile
          label="Impacted Services"
          value={`${summary.impactedServices} / ${summary.totalServices}`}
          hint={`${topology?.edges.length ?? 0} traced call dependencies monitored`}
          accent={summary.impactedServices > 0 ? statusPalette.warning : statusPalette.good}
          icon={<NetworkIcon size={16} />}
        />
      </div>

      {/* Main Operations Grid: Topology Map + Priority Incidents */}
      <div className="grid gap-4 xl:grid-cols-[1.7fr_1fr]">
        <Card
          title="Service Dependency Topology"
          subtitle="Subsystem-grouped service map with log-weighted call volume. Hover or click any service to trace callers and callees."
          right={
            <div className="flex flex-wrap items-center gap-1 rounded-lg border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)] p-0.5">
              {(
                [
                  ["active_faults", "Active Faults"],
                  ["online_boutique", "Online Boutique"],
                  ["train_ticket", "Train Ticket"],
                  ["all", `All (${summary.totalServices || 56})`],
                ] as const
              ).map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => {
                    setScope(key);
                    setSelectedService(null);
                    setHoveredService(null);
                  }}
                  className={cx(
                    "rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors",
                    scope === key
                      ? "bg-surface text-ink shadow-xs"
                      : "text-ink-muted hover:text-ink",
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          }
        >
          {/* Legend + Context Layer Toggles */}
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-[11px]">
            <ul className="flex flex-wrap items-center gap-x-3.5 gap-y-1">
              {(Object.keys(STATUS_META) as TopologyStatus[]).map((key) => (
                <li key={key} className="flex items-center gap-1.5 text-ink-2">
                  <span aria-hidden style={{ color: STATUS_META[key].color }}>
                    {STATUS_META[key].glyph}
                  </span>
                  {STATUS_META[key].label}
                </li>
              ))}
            </ul>

            <div className="flex flex-wrap items-center gap-2">
              {scope === "active_faults" && (
                <>
                  <button
                    type="button"
                    aria-pressed={includeFilteredNoise}
                    onClick={() => setIncludeFilteredNoise((v) => !v)}
                    className={cx(
                      "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[10.5px] font-medium transition-colors",
                      includeFilteredNoise
                        ? "border-[color:var(--color-warning)] bg-[color:var(--color-warning)]/12 text-ink"
                        : "border-[color:var(--color-hairline)] bg-surface text-ink-muted hover:text-ink",
                    )}
                  >
                    <LayersIcon size={11} />+ Filtered noise
                  </button>
                  <button
                    type="button"
                    aria-pressed={includeHealthyNeighbors}
                    onClick={() => setIncludeHealthyNeighbors((v) => !v)}
                    className={cx(
                      "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[10.5px] font-medium transition-colors",
                      includeHealthyNeighbors
                        ? "border-[color:var(--color-accent)] bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent)]"
                        : "border-[color:var(--color-hairline)] bg-surface text-ink-muted hover:text-ink",
                    )}
                  >
                    + Healthy 1-hop
                  </button>
                </>
              )}
              <span className="font-mono text-[10.5px] text-ink-muted">
                {rfGraph?.nodes.length ?? 0} nodes · {rfGraph?.edges.length ?? 0} edges
              </span>
            </div>
          </div>

          {topologyQ.loading ? (
            <Loading label="Building service dependency graph…" />
          ) : topologyQ.error ? (
            <ErrorBox message={topologyQ.error} />
          ) : !rfGraph || rfGraph.nodes.length === 0 ? (
            <Empty>No service nodes available for this filter.</Empty>
          ) : (
            <TopologyCanvas
              flowKey={flowKey}
              nodes={rfGraph.nodes}
              edges={rfGraph.edges}
              nodeTypes={topoNodeTypes}
              heightClass="h-[460px]"
              title="Service Dependency Topology — Fullscreen View"
              onPaneClick={() => {
                setSelectedService(null);
                setHoveredService(null);
              }}
              minimapColor={(n) => {
                const d = n.data as unknown as TopoNodeData | undefined;
                return d ? STATUS_META[d.node.status].color : "#94a3b8";
              }}
            />
          )}

          {/* Interactive Service Inspector */}
          {inspectedNode && (
            <div className="mt-3 rounded-xl border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)] p-3.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    aria-hidden
                    style={{ color: STATUS_META[inspectedNode.status].color }}
                    className="text-[13px]"
                  >
                    {STATUS_META[inspectedNode.status].glyph}
                  </span>
                  <span className="font-mono text-[13px] font-semibold text-ink">
                    {inspectedNode.service}
                  </span>
                  <Pill
                    tone={
                      inspectedNode.status === "critical"
                        ? "critical"
                        : inspectedNode.status === "degraded"
                          ? "warn"
                          : inspectedNode.status === "healthy"
                            ? "good"
                            : "neutral"
                    }
                  >
                    {STATUS_META[inspectedNode.status].label}
                  </Pill>
                </div>
                <div className="flex items-center gap-2">
                  <Link
                    to={`/timeline?run_id=${encodeURIComponent(runId)}&service=${encodeURIComponent(inspectedNode.service)}`}
                    className="inline-flex items-center gap-1 rounded-md border border-[color:var(--color-hairline)] bg-surface px-2.5 py-1 text-[11px] font-medium text-ink hover:bg-[color:var(--color-accent-soft)]"
                  >
                    Filter Alert Stream
                    <ArrowRightIcon size={12} />
                  </Link>
                  <button
                    type="button"
                    onClick={() => setSelectedService(null)}
                    className="text-[11px] text-ink-muted hover:text-ink"
                  >
                    Close
                  </button>
                </div>
              </div>

              <dl className="mt-2 grid grid-cols-2 gap-x-6 border-t border-[color:var(--color-hairline)] pt-2 sm:grid-cols-4">
                <KV k="Confirmed alerts" v={inspectedNode.confirmed_alerts} />
                <KV k="Filtered by CTAV" v={inspectedNode.suppressed_alerts} />
                <KV
                  k="Incidents (root cause)"
                  v={`${inspectedNode.incident_count} (${inspectedNode.root_cause_count})`}
                />
                <KV
                  k="Peak anomaly score"
                  v={
                    inspectedNode.max_anomaly_score > 0
                      ? num(inspectedNode.max_anomaly_score, 3)
                      : "—"
                  }
                />
              </dl>

              {(inspectedNeighbors.upstream.length > 0 || inspectedNeighbors.downstream.length > 0) && (
                <div className="mt-2.5 grid gap-2 border-t border-[color:var(--color-hairline)] pt-2.5 sm:grid-cols-2">
                  <div>
                    <div className="mb-1 text-[10.5px] font-medium" style={{ color: UPSTREAM_COLOR }}>
                      ↑ Upstream callers ({inspectedNeighbors.upstream.length})
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {inspectedNeighbors.upstream.length === 0 ? (
                        <span className="text-[11px] text-ink-muted">Entrypoint service</span>
                      ) : (
                        inspectedNeighbors.upstream.map((svc) => (
                          <button
                            key={svc}
                            type="button"
                            onClick={() => setSelectedService(svc)}
                            className="rounded-md border border-[color:var(--color-hairline)] bg-surface px-2 py-0.5 font-mono text-[10.5px] text-ink hover:border-[#2563eb]"
                          >
                            {svc}
                          </button>
                        ))
                      )}
                    </div>
                  </div>
                  <div>
                    <div className="mb-1 text-[10.5px] font-medium" style={{ color: DOWNSTREAM_COLOR }}>
                      ↓ Downstream callees ({inspectedNeighbors.downstream.length})
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {inspectedNeighbors.downstream.length === 0 ? (
                        <span className="text-[11px] text-ink-muted">Leaf service</span>
                      ) : (
                        inspectedNeighbors.downstream.map((svc) => (
                          <button
                            key={svc}
                            type="button"
                            onClick={() => setSelectedService(svc)}
                            className="rounded-md border border-[color:var(--color-hairline)] bg-surface px-2 py-0.5 font-mono text-[10.5px] text-ink hover:border-[#ea580c]"
                          >
                            {svc}
                          </button>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </Card>

        <Card
          title="Priority Incident Feed"
          subtitle="Grouped incidents ranked by blast radius and alert density."
          right={
            <Link
              to={`/incidents?run_id=${encodeURIComponent(runId)}`}
              className="text-[11.5px] font-medium text-[color:var(--color-accent)] hover:underline"
            >
              View all ({incidents.length})
            </Link>
          }
        >
          {incidentsQ.loading ? (
            <Loading label="Loading incidents…" />
          ) : incidentsQ.error ? (
            <ErrorBox message={incidentsQ.error} />
          ) : priorityIncidents.length === 0 ? (
            <Empty>No active incidents in this telemetry window.</Empty>
          ) : (
            <ul className="space-y-2.5">
              {priorityIncidents.map((inc) => {
                const isCascade = inc.services.length > 1;
                const hasGt =
                  inc.ground_truth_service !== null && inc.ground_truth_service !== undefined;
                const match = hasGt && inc.root_cause_service === inc.ground_truth_service;
                return (
                  <li key={inc.incident_id}>
                    <Link
                      to={`/incidents/${inc.incident_id}?run_id=${encodeURIComponent(runId)}`}
                      className="block rounded-lg border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)]/60 p-3 transition-colors hover:border-[color:var(--color-accent)] hover:bg-[color:var(--color-plane)]"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5">
                          <AlertTriangleIcon
                            size={14}
                            style={{
                              color: isCascade ? statusPalette.critical : statusPalette.serious,
                            }}
                          />
                          <span className="font-mono text-[12.5px] font-semibold text-ink">
                            {inc.root_cause_service ?? "Inconclusive"}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          {isCascade && <Pill tone="critical">cascade · {inc.services.length} svcs</Pill>}
                          <Pill>{inc.alert_ids.length} alerts</Pill>
                        </div>
                      </div>

                      <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[11px] text-ink-2">
                        <span className="font-mono">{inc.services.join(" → ")}</span>
                      </div>

                      <div className="mt-2 flex items-center justify-between gap-2 text-[10.5px] text-ink-muted">
                        <span className="font-mono tabular-nums">
                          {clockUTC(inc.start_ts)} – {clockUTC(inc.end_ts)} UTC
                        </span>
                        {groundTruthOverlay ? (
                          <span
                            className="font-medium"
                            style={{
                              color: !hasGt
                                ? "var(--color-ink-muted)"
                                : match
                                  ? statusPalette.good
                                  : statusPalette.critical,
                            }}
                          >
                            {!hasGt
                              ? "unlabelled"
                              : match
                                ? `✓ matches ${inc.ground_truth_service}`
                                : `✗ gt: ${inc.ground_truth_service}`}
                          </span>
                        ) : (
                          <span className="font-mono">{inc.incident_id}</span>
                        )}
                      </div>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
