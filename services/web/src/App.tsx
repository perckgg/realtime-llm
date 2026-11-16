import { useMemo, useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { api } from "@/api/client";
import { FixtureBanner, Loading } from "@/components/ui";
import { RunContext, type RunCtx } from "@/lib/runContext";
import { useAsync } from "@/lib/util";
import { snapshotMeta } from "@/mock/fixtures";
import { strategyShortLabel } from "@/theme/tokens";
import Timeline from "@/screens/Timeline";
import AlertDetail from "@/screens/AlertDetail";
import IncidentDetail from "@/screens/IncidentDetail";
import ExperimentComparison from "@/screens/ExperimentComparison";

const NAV = [
  { to: "/timeline", label: "Alert & Incident Timeline", hint: "Chronological validation verdicts and service-level incidents" },
  { to: "/compare", label: "Benchmark & Ablation", hint: "5-method performance comparison, ablations, budget curves & holdout test" },
];

export default function App() {
  const { data: runs, loading } = useAsync(() => api.listRuns(), []);
  const [runId, setRunId] = useState<string | null>(null);

  const effectiveRunId = runId ?? runs?.[0]?.run_id ?? "";
  const ctx = useMemo<RunCtx>(
    () => ({ runs: runs ?? [], runId: effectiveRunId, setRunId }),
    [runs, effectiveRunId],
  );

  if (loading || !runs) return <Loading label="Loading evaluation runs…" />;

  return (
    <RunContext.Provider value={ctx}>
      <div className="flex min-h-full flex-col">
        <FixtureBanner />

        <header className="sticky top-0 z-30 border-b border-[color:var(--color-hairline)] bg-surface/95 backdrop-blur-sm">
          <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-4 px-6 py-3">
            <div className="flex flex-wrap items-center gap-6">
              <div className="flex items-center gap-3">
                <div
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg font-mono text-[11px] font-bold tracking-tight text-white shadow-xs"
                  style={{ background: "var(--color-seq-700)" }}
                  aria-hidden
                >
                  CTAV
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[14px] font-semibold tracking-tight text-ink">
                      AIOps RCA Platform
                    </span>
                    <span className="rounded border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)] px-1.5 py-0.5 text-[10px] font-medium text-ink-muted">
                      Calibrated Validation
                    </span>
                  </div>
                  <div className="text-[11px] text-ink-muted">
                    Nezha Microservice Benchmark · {snapshotMeta.val_telemetry_windows.toLocaleString("en-US")} telemetry windows · Judge: {snapshotMeta.judge_model}
                  </div>
                </div>
              </div>

              <nav className="flex items-center gap-1 rounded-lg border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)] p-1">
                {NAV.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    title={item.hint}
                    className={({ isActive }) =>
                      `rounded-md px-3 py-1.5 text-[12px] font-medium transition-all ${
                        isActive
                          ? "bg-surface text-ink shadow-xs"
                          : "text-ink-muted hover:text-ink-2"
                      }`
                    }
                  >
                    {item.label}
                  </NavLink>
                ))}
              </nav>
            </div>

            <label className="flex items-center gap-2 text-[11.5px] font-medium text-ink-muted">
              Evaluation Run
              <select
                value={effectiveRunId}
                onChange={(e) => setRunId(e.target.value)}
                className="rounded-lg border border-[color:var(--color-hairline)] bg-surface px-3 py-1.5 text-[12px] font-medium text-ink shadow-[0_1px_2px_rgba(15,23,42,0.03)] focus:border-[color:var(--color-seq-550)] focus:outline-none"
              >
                {runs.map((r) => (
                  <option key={r.run_id} value={r.run_id}>
                    {strategyShortLabel[r.retrieval_strategy]} — {r.run_id}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1440px] flex-1 px-6 py-6">
          <Routes>
            <Route path="/" element={<Navigate to="/timeline" replace />} />
            <Route path="/timeline" element={<Timeline />} />
            <Route path="/alerts/:alertId" element={<AlertDetail />} />
            <Route path="/incidents/:incidentId" element={<IncidentDetail />} />
            <Route path="/compare" element={<ExperimentComparison />} />
            <Route path="*" element={<Navigate to="/timeline" replace />} />
          </Routes>
        </main>

        <footer className="border-t border-[color:var(--color-hairline)] bg-surface px-6 py-3">
          <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-2 text-[11px] text-ink-muted">
            <span>
              CTAV — Calibrated Topology-Aware Alert Validation &amp; Root Cause Analysis Platform
            </span>
            <span>
              Four analytical views: Timeline · Alert Inspection · Incident RCA Graph · Benchmark &amp; Ablation (Read-Only Demo)
            </span>
          </div>
        </footer>
      </div>
    </RunContext.Provider>
  );
}
