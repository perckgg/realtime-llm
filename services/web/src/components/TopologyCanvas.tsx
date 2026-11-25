import { useEffect, useState, type ReactNode } from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
  type NodeTypes,
} from "@xyflow/react";
import { MaximizeIcon, MinimizeIcon } from "@/components/icons";
import { cx } from "@/lib/util";

interface TopologyCanvasProps<T extends Record<string, unknown>> {
  flowKey: string;
  nodes: Node<T>[];
  edges: Edge[];
  nodeTypes: NodeTypes;
  heightClass?: string;
  title?: string;
  hint?: string;
  minimapColor?: (node: Node) => string;
  onPaneClick?: () => void;
  topLeftOverlay?: ReactNode;
}

/**
 * Reusable observability ReactFlow canvas with theme-aware MiniMap,
 * zoom controls, subtle focus hint, and a Fullscreen projection modal (ESC closes).
 */
export default function TopologyCanvas<T extends Record<string, unknown>>({
  flowKey,
  nodes,
  edges,
  nodeTypes,
  heightClass = "h-[450px]",
  title = "Service Dependency Topology",
  hint = "Hover or click a service to trace upstream & downstream · Click canvas to reset",
  minimapColor,
  onPaneClick,
  topLeftOverlay,
}: TopologyCanvasProps<T>) {
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (!expanded) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setExpanded(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [expanded]);

  const canvas = (isFullscreen: boolean) => (
    <div
      className={cx(
        "relative overflow-hidden rounded-lg border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)]",
        isFullscreen ? "h-full w-full" : heightClass,
      )}
    >
      {/* Top-left hint / filter overlay */}
      <div className="pointer-events-none absolute top-2.5 left-2.5 z-10 flex flex-wrap items-center gap-2">
        {topLeftOverlay && <div className="pointer-events-auto">{topLeftOverlay}</div>}
        <span className="hidden rounded-md border border-[color:var(--color-hairline)] bg-surface/90 px-2.5 py-1 text-[10.5px] text-ink-muted backdrop-blur sm:inline-block">
          {hint}
        </span>
      </div>

      {/* Top-right Expand button (inline only; fullscreen modal has Close in header) */}
      {!isFullscreen && (
        <div className="absolute top-2.5 right-2.5 z-10">
          <button
            type="button"
            onClick={() => setExpanded(true)}
            aria-label="Expand topology fullscreen"
            className="inline-flex items-center gap-1.5 rounded-md border border-[color:var(--color-hairline)] bg-surface/95 px-2.5 py-1 text-[11px] font-medium text-ink shadow-xs backdrop-blur transition-colors hover:bg-[color:var(--color-plane)]"
          >
            <MaximizeIcon size={13} />
            Expand
          </button>
        </div>
      )}

      <ReactFlow
        key={`${flowKey}-${isFullscreen ? "fs" : "inline"}`}
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: isFullscreen ? 0.12 : 0.18 }}
        proOptions={{ hideAttribution: true }}
        minZoom={0.25}
        maxZoom={1.75}
        nodesConnectable={false}
        onPaneClick={onPaneClick}
      >
        <Background variant={BackgroundVariant.Dots} gap={18} size={1} color="var(--color-grid)" />
        <Controls showInteractive={false} />
        {isFullscreen && (
          <MiniMap
            pannable
            zoomable
            nodeColor={minimapColor ?? (() => "#64748b")}
            nodeStrokeColor={minimapColor ?? (() => "#475569")}
            nodeStrokeWidth={3}
            nodeBorderRadius={4}
            maskColor="rgb(15 23 42 / 0.14)"
            style={{
              backgroundColor: "var(--color-surface)",
              border: "1px solid var(--color-hairline)",
              borderRadius: 8,
              width: 160,
              height: 96,
            }}
          />
        )}
      </ReactFlow>
    </div>
  );

  return (
    <>
      {!expanded ? (
        canvas(false)
      ) : (
        <>
          <div
            className={cx(
              "flex items-center justify-center rounded-lg border border-dashed border-[color:var(--color-hairline)] bg-[color:var(--color-plane)] text-[12px] text-ink-muted",
              heightClass,
            )}
          >
            Topology expanded in fullscreen view — press Esc to return.
          </div>
          <div
            role="dialog"
            aria-modal="true"
            aria-label={title}
            className="fixed inset-0 z-50 flex flex-col bg-black/55 p-4 backdrop-blur-xs"
          >
            <div className="flex h-full w-full flex-col overflow-hidden rounded-xl border border-[color:var(--color-hairline)] bg-surface shadow-2xl">
              <div className="flex items-center justify-between border-b border-[color:var(--color-hairline)] px-4 py-2.5">
                <span className="text-[13px] font-semibold text-ink">{title}</span>
                <button
                  type="button"
                  onClick={() => setExpanded(false)}
                  className="inline-flex items-center gap-1.5 rounded-md border border-[color:var(--color-hairline)] px-2.5 py-1 text-[11.5px] font-medium text-ink hover:bg-[color:var(--color-plane)]"
                >
                  <MinimizeIcon size={13} />
                  Close (Esc)
                </button>
              </div>
              <div className="min-h-0 flex-1 p-3">{canvas(true)}</div>
            </div>
          </div>
        </>
      )}
    </>
  );
}
