import type {
  GraphEdge,
  GraphNode,
  IncidentDetail,
  TopologyData,
  TopologyEdge,
  TopologyNode,
  TopologyStatus,
} from "@/api/types";

export const STATUS_PRIORITY: Record<TopologyStatus, number> = {
  critical: 0,
  degraded: 1,
  suppressed: 2,
  healthy: 3,
};

/**
 * Map a wide dynamic range of call counts (e.g. 126..369,044) onto a clean
 * stroke width range [1.25, 3.5] px using log10 scaling.
 */
export function edgeWidthFromCalls(callCount: number, minCalls: number, maxCalls: number): number {
  const safeVal = Math.max(1, callCount);
  const lo = Math.log10(Math.max(1, minCalls));
  const hi = Math.log10(Math.max(1, maxCalls));
  if (hi <= lo) return 1.8;
  const t = Math.max(0, Math.min(1, (Math.log10(safeVal) - lo) / (hi - lo)));
  return Number((1.25 + t * 2.25).toFixed(2));
}

export function formatCallCount(count: number): string {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  if (count >= 1_000) return `${(count / 1_000).toFixed(count >= 10_000 ? 0 : 1)}k`;
  return String(count);
}

export interface NeighborhoodFocus {
  focused: string;
  upstream: Set<string>;
  downstream: Set<string>;
  relatedNodes: Set<string>;
  relatedEdges: Set<string>;
}

/**
 * Given a selected/hovered service id and directed call edges (source calls target),
 * return upstream callers, downstream callees, and incident edge IDs (`source->target`).
 */
export function computeNeighborhoodFocus(
  focusId: string | null,
  edges: readonly { source: string; target: string }[],
): NeighborhoodFocus | null {
  if (!focusId) return null;
  const upstream = new Set<string>();
  const downstream = new Set<string>();
  const relatedNodes = new Set<string>([focusId]);
  const relatedEdges = new Set<string>();

  for (const e of edges) {
    if (e.target === focusId) {
      upstream.add(e.source);
      relatedNodes.add(e.source);
      relatedEdges.add(`${e.source}->${e.target}`);
    }
    if (e.source === focusId) {
      downstream.add(e.target);
      relatedNodes.add(e.target);
      relatedEdges.add(`${e.source}->${e.target}`);
    }
  }
  return { focused: focusId, upstream, downstream, relatedNodes, relatedEdges };
}

export type TopologyScope = "active_faults" | "online_boutique" | "train_ticket" | "all";

export interface TopologyLayoutOptions {
  scope: TopologyScope;
  includeFilteredNoise?: boolean;
  includeHealthyNeighbors?: boolean;
}

export interface PositionedTopologyNode {
  node: TopologyNode;
  x: number;
  y: number;
}

export interface TopologyLayoutResult {
  nodes: PositionedTopologyNode[];
  edges: TopologyEdge[];
  minCalls: number;
  maxCalls: number;
  subsystemBands: { subsystem: TopologyNode["subsystem"]; label: string; yTop: number; yBottom: number }[];
}

const SUBSYSTEM_ORDER: TopologyNode["subsystem"][] = ["online_boutique", "train_ticket", "other"];
const SUBSYSTEM_LABEL: Record<TopologyNode["subsystem"], string> = {
  online_boutique: "Online Boutique",
  train_ticket: "Train Ticket",
  other: "Shared / Other",
};

/**
 * Layout a single disconnected subsystem cluster using longest-path DAG layering,
 * 1-pass barycenter crossing reduction, and sub-column wrapping for crowded layers.
 */
function layoutCluster(
  clusterNodes: TopologyNode[],
  clusterEdges: TopologyEdge[],
  yOffset: number,
): { placed: PositionedTopologyNode[]; yBottom: number } {
  if (clusterNodes.length === 0) return { placed: [], yBottom: yOffset };

  const nodeMap = new Map(clusterNodes.map((n) => [n.service, n]));
  const inDeg = new Map<string, number>();
  const adj = new Map<string, string[]>();
  const parents = new Map<string, string[]>();

  for (const n of clusterNodes) {
    inDeg.set(n.service, 0);
    adj.set(n.service, []);
    parents.set(n.service, []);
  }
  for (const e of clusterEdges) {
    if (!nodeMap.has(e.source) || !nodeMap.has(e.target) || e.source === e.target) continue;
    inDeg.set(e.target, (inDeg.get(e.target) ?? 0) + 1);
    adj.get(e.source)!.push(e.target);
    parents.get(e.target)!.push(e.source);
  }

  // Assign layers from entrypoints (inDeg === 0); cap at layer 5 to tolerate any cycle.
  const layer = new Map<string, number>();
  const roots = clusterNodes
    .filter((n) => (inDeg.get(n.service) ?? 0) === 0)
    .sort((a, b) => STATUS_PRIORITY[a.status] - STATUS_PRIORITY[b.status] || a.service.localeCompare(b.service));

  const queue: string[] = [];
  for (const r of roots) {
    layer.set(r.service, 0);
    queue.push(r.service);
  }
  while (queue.length > 0) {
    const cur = queue.shift()!;
    const d = layer.get(cur) ?? 0;
    for (const nxt of adj.get(cur) ?? []) {
      const cand = Math.min(d + 1, 5);
      if (!layer.has(nxt) || (layer.get(nxt) ?? 0) < cand) {
        layer.set(nxt, cand);
        queue.push(nxt);
      }
    }
  }
  for (const n of clusterNodes) {
    if (!layer.has(n.service)) {
      const hasEdges = (adj.get(n.service)?.length ?? 0) > 0 || (parents.get(n.service)?.length ?? 0) > 0;
      layer.set(n.service, hasEdges ? 1 : 0);
    }
  }

  // Group nodes per layer
  const rawLayers = new Map<number, TopologyNode[]>();
  for (const n of clusterNodes) {
    const col = layer.get(n.service) ?? 0;
    const arr = rawLayers.get(col) ?? [];
    arr.push(n);
    rawLayers.set(col, arr);
  }

  const sortedLayerKeys = [...rawLayers.keys()].sort((a, b) => a - b);
  const rowIndex = new Map<string, number>();

  // 1-pass barycenter ordering to reduce edge crossings
  for (const k of sortedLayerKeys) {
    const list = rawLayers.get(k)!;
    list.sort((a, b) => {
      const pA = (parents.get(a.service) ?? []).filter((p) => rowIndex.has(p));
      const pB = (parents.get(b.service) ?? []).filter((p) => rowIndex.has(p));
      const baryA = pA.length ? pA.reduce((s, p) => s + (rowIndex.get(p) ?? 0), 0) / pA.length : Number.POSITIVE_INFINITY;
      const baryB = pB.length ? pB.reduce((s, p) => s + (rowIndex.get(p) ?? 0), 0) / pB.length : Number.POSITIVE_INFINITY;
      if (baryA !== baryB) return baryA - baryB;
      return (
        STATUS_PRIORITY[a.status] - STATUS_PRIORITY[b.status] ||
        b.confirmed_alerts - a.confirmed_alerts ||
        a.service.localeCompare(b.service)
      );
    });
    list.forEach((n, i) => rowIndex.set(n.service, i));
  }

  // Split crowded columns (> MAX_PER_COL) into 2 staggered sub-columns so the graph stays compact horizontally
  const MAX_PER_COL = 7;
  const X_GAP = 250;
  const Y_GAP = 104;
  const placed: PositionedTopologyNode[] = [];

  let xCursor = 0;
  let maxY = yOffset;

  for (const k of sortedLayerKeys) {
    const list = rawLayers.get(k)!;
    const subCols = Math.max(1, Math.ceil(list.length / MAX_PER_COL));
    const perSub = Math.ceil(list.length / subCols);

    for (let sc = 0; sc < subCols; sc++) {
      const slice = list.slice(sc * perSub, (sc + 1) * perSub);
      slice.forEach((node, idx) => {
        const x = (xCursor + sc) * X_GAP;
        const y = yOffset + idx * Y_GAP + (sc % 2 === 1 ? 26 : 0);
        placed.push({ node, x, y });
        if (y > maxY) maxY = y;
      });
    }
    xCursor += subCols;
  }

  return { placed, yBottom: maxY + 96 };
}

/**
 * Filter & place the full service dependency topology with clean subsystem separation.
 */
export function layoutServiceTopology(
  topology: TopologyData,
  options: TopologyLayoutOptions,
): TopologyLayoutResult {
  const { scope, includeFilteredNoise = false, includeHealthyNeighbors = true } = options;
  const keep = new Set<string>();

  if (scope === "active_faults") {
    const active = topology.nodes.filter(
      (n) =>
        n.status === "critical" ||
        n.status === "degraded" ||
        (includeFilteredNoise && n.status === "suppressed"),
    );
    for (const n of active) keep.add(n.service);

    if (includeHealthyNeighbors) {
      const core = new Set(
        topology.nodes
          .filter((n) => n.status === "critical" || n.status === "degraded")
          .map((n) => n.service),
      );
      for (const e of topology.edges) {
        if (core.has(e.source) || core.has(e.target)) {
          keep.add(e.source);
          keep.add(e.target);
        }
      }
    }

    // Fallback if a run has zero active faults
    if (keep.size === 0) {
      for (const n of topology.nodes.slice(0, 12)) keep.add(n.service);
    }
  } else if (scope === "all") {
    for (const n of topology.nodes) keep.add(n.service);
  } else {
    for (const n of topology.nodes) {
      if (n.subsystem === scope) keep.add(n.service);
    }
  }

  const visibleNodes = topology.nodes.filter((n) => keep.has(n.service));
  const visibleEdges = topology.edges.filter((e) => keep.has(e.source) && keep.has(e.target));

  const placedAll: PositionedTopologyNode[] = [];
  const subsystemBands: TopologyLayoutResult["subsystemBands"] = [];
  let yCursor = 0;

  for (const sub of SUBSYSTEM_ORDER) {
    const subNodes = visibleNodes.filter((n) => n.subsystem === sub);
    if (subNodes.length === 0) continue;
    const subSet = new Set(subNodes.map((n) => n.service));
    const subEdges = visibleEdges.filter((e) => subSet.has(e.source) && subSet.has(e.target));
    const yTop = yCursor;
    const { placed, yBottom } = layoutCluster(subNodes, subEdges, yCursor);
    placedAll.push(...placed);
    subsystemBands.push({ subsystem: sub, label: SUBSYSTEM_LABEL[sub], yTop, yBottom });
    yCursor = yBottom + 110;
  }

  const weights = visibleEdges.map((e) => e.call_count);
  const minCalls = weights.length ? Math.min(...weights) : 1;
  const maxCalls = weights.length ? Math.max(...weights) : 1;

  return {
    nodes: placedAll,
    edges: visibleEdges,
    minCalls,
    maxCalls,
    subsystemBands,
  };
}

export interface IncidentLayoutResult {
  nodes: { node: GraphNode; pathIndex: number | null; x: number; y: number }[];
  edges: GraphEdge[];
  hiddenHealthyCount: number;
  minCalls: number;
  maxCalls: number;
}

/**
 * Horizontal fan layout for IncidentDetail:
 * - Propagation spine (`root_cause -> affected`) sits cleanly on y = 0.
 * - Healthy upstream callers sit in compact horizontal rows ABOVE (y < 0).
 * - Healthy downstream callees sit in compact horizontal rows BELOW (y > 0).
 * In `focus` mode, caps healthy neighbors to top 3 callers + top 3 callees by call_count
 * so the propagation chain stays large and legible on initial load.
 */
export function layoutIncidentNeighborhood(
  detail: IncidentDetail,
  mode: "focus" | "full",
): IncidentLayoutResult {
  const spine =
    detail.report?.propagation_path && detail.report.propagation_path.length > 0
      ? detail.report.propagation_path
      : detail.services;
  const spineSet = new Set(spine);

  // Any non-healthy node (root_cause, ground_truth, affected) is always kept
  const coreNodes: GraphNode[] = [];
  const healthyNodes: GraphNode[] = [];
  for (const n of detail.nodes) {
    if (spineSet.has(n.service) || n.role !== "healthy") {
      coreNodes.push(n);
    } else {
      healthyNodes.push(n);
    }
  }

  // Classify healthy neighbors as upstream callers vs downstream callees relative to core
  const coreSet = new Set(coreNodes.map((n) => n.service));
  const callWeight = new Map<string, number>();
  const upstreamHealthy: GraphNode[] = [];
  const downstreamHealthy: GraphNode[] = [];

  for (const n of healthyNodes) {
    let upW = 0;
    let downW = 0;
    for (const e of detail.edges) {
      if (e.source === n.service && coreSet.has(e.target)) upW += e.call_count;
      if (e.target === n.service && coreSet.has(e.source)) downW += e.call_count;
    }
    callWeight.set(n.service, Math.max(upW, downW));
    if (upW >= downW) {
      upstreamHealthy.push(n);
    } else {
      downstreamHealthy.push(n);
    }
  }

  const byWeightDesc = (a: GraphNode, b: GraphNode) =>
    (callWeight.get(b.service) ?? 0) - (callWeight.get(a.service) ?? 0) ||
    a.service.localeCompare(b.service);
  upstreamHealthy.sort(byWeightDesc);
  downstreamHealthy.sort(byWeightDesc);

  const MAX_FOCUS_PER_SIDE = 3;
  const visibleUp = mode === "focus" ? upstreamHealthy.slice(0, MAX_FOCUS_PER_SIDE) : upstreamHealthy;
  const visibleDown = mode === "focus" ? downstreamHealthy.slice(0, MAX_FOCUS_PER_SIDE) : downstreamHealthy;
  const hiddenHealthyCount =
    (upstreamHealthy.length - visibleUp.length) + (downstreamHealthy.length - visibleDown.length);

  const X_SPINE = 270;
  const X_FAN = 225;
  const Y_ROW = 130;
  const MAX_PER_ROW = 4;

  const positioned: IncidentLayoutResult["nodes"] = [];
  const placedSet = new Set<string>();

  // 1. Place spine left-to-right at y = 0
  spine.forEach((svc, idx) => {
    const node = detail.nodes.find((n) => n.service === svc);
    if (!node) return;
    positioned.push({ node, pathIndex: idx, x: idx * X_SPINE, y: 0 });
    placedSet.add(svc);
  });

  // Any extra core nodes not in spine sit to the right on y = 0
  let extraIdx = spine.length;
  for (const n of coreNodes) {
    if (placedSet.has(n.service)) continue;
    positioned.push({ node: n, pathIndex: null, x: extraIdx * X_SPINE, y: 0 });
    placedSet.add(n.service);
    extraIdx += 1;
  }

  const spineCenterX = Math.max(0, ((Math.max(1, placedSet.size) - 1) * X_SPINE) / 2);

  // 2. Place upstream callers in compact horizontal rows ABOVE (y < 0)
  visibleUp.forEach((node, idx) => {
    const row = Math.floor(idx / MAX_PER_ROW);
    const col = idx % MAX_PER_ROW;
    const rowCount = Math.min(MAX_PER_ROW, visibleUp.length - row * MAX_PER_ROW);
    const rowWidth = (rowCount - 1) * X_FAN;
    const x = spineCenterX - rowWidth / 2 + col * X_FAN;
    const y = -Y_ROW * (row + 1);
    positioned.push({ node, pathIndex: null, x, y });
    placedSet.add(node.service);
  });

  // 3. Place downstream callees in compact horizontal rows BELOW (y > 0)
  visibleDown.forEach((node, idx) => {
    const row = Math.floor(idx / MAX_PER_ROW);
    const col = idx % MAX_PER_ROW;
    const rowCount = Math.min(MAX_PER_ROW, visibleDown.length - row * MAX_PER_ROW);
    const rowWidth = (rowCount - 1) * X_FAN;
    const x = spineCenterX - rowWidth / 2 + col * X_FAN;
    const y = Y_ROW * (row + 1);
    positioned.push({ node, pathIndex: null, x, y });
    placedSet.add(node.service);
  });

  const visibleEdges = detail.edges.filter((e) => placedSet.has(e.source) && placedSet.has(e.target));
  const weights = visibleEdges.map((e) => e.call_count);
  const minCalls = weights.length ? Math.min(...weights) : 1;
  const maxCalls = weights.length ? Math.max(...weights) : 1;

  return {
    nodes: positioned,
    edges: visibleEdges,
    hiddenHealthyCount,
    minCalls,
    maxCalls,
  };
}
