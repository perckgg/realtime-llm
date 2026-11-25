import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import type { Incident } from "@/api/types";
import { AlertTriangleIcon, ArrowRightIcon, FlameIcon, SearchIcon } from "@/components/icons";
import { Card, Empty, ErrorBox, Loading, Pill, StatTile } from "@/components/ui";
import { useRuns } from "@/lib/runContext";
import { clockUTC, cx, stampUTC, useAsync } from "@/lib/util";
import { status as statusPalette } from "@/theme/tokens";

type ScopeFilter = "all" | "cascade" | "single";

export default function Incidents() {
  const { runId, runsLoading, runsError, groundTruthOverlay } = useRuns();
  const [query, setQuery] = useState("");
  const [scope, setScope] = useState<ScopeFilter>("all");
  const [sortBy, setSortBy] = useState<"alerts" | "recent">("recent");

  const incidentsQ = useAsync(
    () => (runId ? api.listIncidents(runId) : Promise.resolve<Incident[]>([])),
    [runId],
  );
  const incidents = incidentsQ.data ?? [];

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = incidents.filter((inc) => {
      if (scope === "cascade" && inc.services.length < 2) return false;
      if (scope === "single" && inc.services.length > 1) return false;
      if (!q) return true;
      return (
        inc.incident_id.toLowerCase().includes(q) ||
        (inc.root_cause_service ?? "").toLowerCase().includes(q) ||
        inc.services.some((s) => s.toLowerCase().includes(q)) ||
        (inc.fault_type ?? "").toLowerCase().includes(q)
      );
    });
    return [...list].sort((a, b) =>
      sortBy === "alerts"
        ? b.alert_ids.length - a.alert_ids.length || b.start_ts.localeCompare(a.start_ts)
        : b.start_ts.localeCompare(a.start_ts),
    );
  }, [incidents, query, scope, sortBy]);

  const stats = useMemo(() => {
    const cascades = incidents.filter((i) => i.services.length > 1).length;
    const totalAlerts = incidents.reduce((sum, i) => sum + i.alert_ids.length, 0);
    const distinctRoots = new Set(incidents.map((i) => i.root_cause_service).filter(Boolean)).size;
    return { cascades, totalAlerts, distinctRoots };
  }, [incidents]);

  if (runsLoading) return <Loading label="Loading telemetry streams…" />;
  if (runsError) return <ErrorBox message={runsError} />;
  if (!runId) return <Empty>No telemetry stream selected.</Empty>;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[19px] font-semibold tracking-tight text-ink">Incident Queue</h1>
          <p className="mt-0.5 text-[12px] text-ink-muted">
            Correlated alert clusters with topology-guided root cause localization and diagnostic
            reports
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <SearchIcon
              size={14}
              className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-ink-muted"
            />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter service or incident ID…"
              className="w-56 rounded-lg border border-[color:var(--color-hairline)] bg-surface py-1.5 pr-3 pl-8 text-[12px] text-ink placeholder:text-ink-muted"
            />
          </div>
          <div className="flex rounded-lg border border-[color:var(--color-hairline)] bg-surface p-0.5">
            {(
              [
                ["all", "All"],
                ["cascade", "Multi-service"],
                ["single", "Single-service"],
              ] as const
            ).map(([k, label]) => (
              <button
                key={k}
                type="button"
                onClick={() => setScope(k)}
                className={cx(
                  "rounded-md px-2.5 py-1 text-[11.5px] font-medium transition-colors",
                  scope === k
                    ? "bg-[color:var(--color-plane)] text-ink"
                    : "text-ink-muted hover:text-ink",
                )}
              >
                {label}
              </button>
            ))}
          </div>
          <select
            aria-label="Sort incidents"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as "alerts" | "recent")}
            className="rounded-lg border border-[color:var(--color-hairline)] bg-surface px-2.5 py-1.5 text-[12px] text-ink"
          >
            <option value="recent">Sort: Most recent</option>
            <option value="alerts">Sort: Most alerts</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile
          label="Total Incidents"
          value={String(incidents.length)}
          hint={`${filtered.length} matching current filter`}
          accent={statusPalette.critical}
          icon={<FlameIcon size={16} />}
        />
        <StatTile
          label="Multi-Service Cascades"
          value={String(stats.cascades)}
          hint="Incidents spanning >= 2 traced services"
          accent={stats.cascades > 0 ? statusPalette.serious : undefined}
        />
        <StatTile
          label="Correlated Alerts"
          value={String(stats.totalAlerts)}
          hint="Grouped via 180s window + call graph"
          accent="var(--color-accent)"
        />
        <StatTile
          label="Root Cause Services"
          value={String(stats.distinctRoots)}
          hint="Distinct primary fault origins identified"
        />
      </div>

      <Card
        title={`Grouped Incidents (${filtered.length})`}
        subtitle="Select any incident to inspect its service propagation graph, backward 1-hop vote breakdown, and structured diagnostic report."
      >
        {incidentsQ.loading ? (
          <Loading label="Loading incident queue…" />
        ) : incidentsQ.error ? (
          <ErrorBox message={incidentsQ.error} />
        ) : filtered.length === 0 ? (
          <Empty>No incidents match the current filter.</Empty>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-[12px]">
              <thead>
                <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] text-ink-muted">
                  <th className="py-2 pr-3 font-medium">Incident</th>
                  <th className="py-2 pr-3 font-medium">Predicted Root Cause</th>
                  <th className="py-2 pr-3 font-medium">Blast Radius</th>
                  <th className="py-2 pr-3 font-medium">Time Window (UTC)</th>
                  <th className="py-2 pr-3 text-right font-medium">Alerts</th>
                  {groundTruthOverlay && <th className="py-2 pr-3 font-medium">Ground Truth</th>}
                  <th className="py-2 text-right font-medium">Inspect</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((inc) => {
                  const isCascade = inc.services.length > 1;
                  const hasGt =
                    inc.ground_truth_service !== null && inc.ground_truth_service !== undefined;
                  const correct = hasGt && inc.root_cause_service === inc.ground_truth_service;
                  return (
                    <tr
                      key={inc.incident_id}
                      className="border-b border-[color:var(--color-hairline)] last:border-0 hover:bg-[color:var(--color-plane)]"
                    >
                      <td className="py-2.5 pr-3 font-mono text-[11px] whitespace-nowrap text-ink-2">
                        <Link
                          to={`/incidents/${inc.incident_id}?run_id=${encodeURIComponent(runId)}`}
                          className="font-medium text-ink hover:text-[color:var(--color-accent)] hover:underline"
                        >
                          {inc.incident_id}
                        </Link>
                      </td>
                      <td className="py-2.5 pr-3">
                        <div className="flex items-center gap-1.5">
                          <AlertTriangleIcon
                            size={13}
                            style={{
                              color: isCascade ? statusPalette.critical : statusPalette.serious,
                            }}
                          />
                          <span className="font-mono font-semibold text-ink">
                            {inc.root_cause_service ?? "Inconclusive"}
                          </span>
                        </div>
                      </td>
                      <td className="py-2.5 pr-3">
                        <div className="flex flex-wrap items-center gap-1.5">
                          {isCascade && <Pill tone="critical">cascade</Pill>}
                          <span className="font-mono text-[11px] text-ink-2">
                            {inc.services.join(" → ")}
                          </span>
                        </div>
                      </td>
                      <td className="py-2.5 pr-3 font-mono text-[11px] tabular-nums whitespace-nowrap text-ink-2">
                        {stampUTC(inc.start_ts)} → {clockUTC(inc.end_ts)}
                      </td>
                      <td className="py-2.5 pr-3 text-right font-mono tabular-nums text-ink">
                        {inc.alert_ids.length}
                      </td>
                      {groundTruthOverlay && (
                        <td className="py-2.5 pr-3 whitespace-nowrap">
                          {!hasGt ? (
                            <span className="text-[11px] text-ink-muted">unlabelled</span>
                          ) : correct ? (
                            <Pill tone="good">✓ {inc.ground_truth_service}</Pill>
                          ) : (
                            <Pill tone="critical">✗ {inc.ground_truth_service}</Pill>
                          )}
                        </td>
                      )}
                      <td className="py-2.5 text-right whitespace-nowrap">
                        <Link
                          to={`/incidents/${inc.incident_id}?run_id=${encodeURIComponent(runId)}`}
                          className="inline-flex items-center gap-1 text-[11.5px] font-medium text-[color:var(--color-accent)] hover:underline"
                        >
                          Open RCA
                          <ArrowRightIcon size={12} />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
