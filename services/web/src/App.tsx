import { useCallback, useEffect, useMemo, useState } from "react";
import { NavLink, Navigate, Route, Routes, useSearchParams } from "react-router-dom";
import { api } from "@/api/client";
import { FixtureBanner, StaticSnapshotBanner, Loading, ErrorBox } from "@/components/ui";
import { RunContext, isSensitivityRunId, resolveRunId, type RunCtx } from "@/lib/runContext";
import { useAsync } from "@/lib/util";
import { strategyLabel } from "@/theme/tokens";
import Timeline from "@/screens/Timeline";
import AlertDetail from "@/screens/AlertDetail";
import IncidentDetail from "@/screens/IncidentDetail";
import ExperimentComparison from "@/screens/ExperimentComparison";
import MethodologyGuide from "@/screens/MethodologyGuide";

const NAV = [
  {
    to: "/timeline",
    label: "Alert & Incident Timeline",
    hint: "Chronological validation verdicts and service-level incidents",
  },
  {
    to: "/compare",
    label: "Experiment Comparison",
    hint: "H0–H5 evaluation, ablations, budget curves & RCA benchmark",
  },
  {
    to: "/guide",
    label: "Methodology & Guide",
    hint: "Formulas, CTAV policy rules, ablations & glossary for committee review",
  },
];

export default function App() {
  const { data: runs, loading, error } = useAsync(() => api.listRuns(), []);
  const [searchParams, setSearchParams] = useSearchParams();
  const [chosenRunId, setChosenRunId] = useState<string | null>(null);

  const effectiveRunId = resolveRunId(runs ?? [], searchParams.get("run_id"), chosenRunId);
  const activeRun = runs?.find((r) => r.run_id === effectiveRunId) ?? runs?.[0];
  const isSensitivityRun = isSensitivityRunId(effectiveRunId);

  // Remember URL-selected run so navigation links without `?run_id=` keep the active run.
  useEffect(() => {
    if (effectiveRunId && searchParams.get("run_id") === effectiveRunId) {
      setChosenRunId(effectiveRunId);
    }
  }, [effectiveRunId, searchParams]);

  // Persist selected run in URL so refresh / copied links preserve the active run.
  const setRunId = useCallback(
    (id: string) => {
      setChosenRunId(id);
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.set("run_id", id);
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const ctx = useMemo<RunCtx>(
    () => ({
      runs: runs ?? [],
      runId: effectiveRunId,
      setRunId,
      runsLoading: loading,
      runsError: error,
    }),
    [runs, effectiveRunId, setRunId, loading, error],
  );

  return (
    <RunContext.Provider value={ctx}>
      <div className="flex min-h-full flex-col">
        <FixtureBanner />
        <StaticSnapshotBanner />

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
                    {activeRun
                      ? `Nezha Benchmark · split ${activeRun.split} · seed ${activeRun.seed} · Judge: gemini-2.5-flash`
                      : "Nezha Microservice Benchmark · Read-Only Experiment Dashboard"}
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
                disabled={loading || !runs?.length}
                onChange={(e) => setRunId(e.target.value)}
                className="rounded-lg border border-[color:var(--color-hairline)] bg-surface px-3 py-1.5 text-[12px] font-medium text-ink shadow-[0_1px_2px_rgba(15,23,42,0.03)] focus:border-[color:var(--color-seq-550)] focus:outline-none disabled:opacity-60"
              >
                {loading && <option value="">Loading runs…</option>}
                {!loading && (!runs || runs.length === 0) && (
                  <option value="">{error ? "Failed to load runs" : "No runs"}</option>
                )}
                {(runs ?? []).some((r) => r.alert_count > 0) && (
                  <optgroup label="With Alerts (ClickHouse + PostgreSQL)">
                    {(runs ?? [])
                      .filter((r) => r.alert_count > 0)
                      .map((r) => (
                        <option key={r.run_id} value={r.run_id}>
                          {strategyLabel[r.retrieval_strategy] ?? r.retrieval_strategy} — {r.run_id}{" "}
                          ({r.split} · {r.alert_count.toLocaleString("en-US")} alerts)
                        </option>
                      ))}
                  </optgroup>
                )}
                {(runs ?? []).some((r) => r.alert_count === 0) && (
                  <optgroup label="Incidents Only (M9 RCA)">
                    {(runs ?? [])
                      .filter((r) => r.alert_count === 0)
                      .map((r) => (
                        <option key={r.run_id} value={r.run_id}>
                          {strategyLabel[r.retrieval_strategy] ?? r.retrieval_strategy} — {r.run_id}{" "}
                          ({r.split})
                        </option>
                      ))}
                  </optgroup>
                )}
              </select>
            </label>
          </div>
        </header>

        {isSensitivityRun && (
          <div
            className="border-b px-6 py-1.5 text-[11.5px]"
            style={{
              borderColor: "var(--color-hairline)",
              background: "color-mix(in srgb, var(--color-warning) 14%, var(--color-surface))",
              color: "var(--color-ink-2)",
            }}
            role="status"
          >
            <div className="mx-auto max-w-[1440px]">
              <strong>Sensitivity line (c3_rolling_baseline):</strong> Outside pre-registered H5
              evaluation; shown for cascade demonstration &amp; mechanism analysis only, not an H5
              result.
            </div>
          </div>
        )}

        <main className="mx-auto w-full max-w-[1440px] flex-1 px-6 py-6">
          {error ? (
            <Routes>
              <Route path="/compare" element={<ExperimentComparison />} />
              <Route path="/guide" element={<MethodologyGuide />} />
              <Route
                path="*"
                element={<ErrorBox message={`Failed to load runs from API: ${error}`} />}
              />
            </Routes>
          ) : loading && !runs ? (
            <Routes>
              <Route path="/compare" element={<ExperimentComparison />} />
              <Route path="/guide" element={<MethodologyGuide />} />
              <Route path="*" element={<Loading label="Loading evaluation runs…" />} />
            </Routes>
          ) : (
            <Routes>
              <Route
                path="/"
                element={
                  <Navigate
                    to={{
                      pathname: "/timeline",
                      search: searchParams.toString() ? `?${searchParams}` : "",
                    }}
                    replace
                  />
                }
              />
              <Route path="/timeline" element={<Timeline />} />
              <Route path="/alerts/:alertId" element={<AlertDetail />} />
              <Route path="/incidents/:incidentId" element={<IncidentDetail />} />
              <Route path="/compare" element={<ExperimentComparison />} />
              <Route path="/guide" element={<MethodologyGuide />} />
              <Route
                path="*"
                element={
                  <Navigate
                    to={{
                      pathname: "/timeline",
                      search: searchParams.toString() ? `?${searchParams}` : "",
                    }}
                    replace
                  />
                }
              />
            </Routes>
          )}
        </main>

        <footer className="border-t border-[color:var(--color-hairline)] bg-surface px-6 py-3">
          <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-2 text-[11px] text-ink-muted">
            <span>
              CTAV — Calibrated Topology-Aware Alert Validation &amp; Root Cause Analysis Platform
            </span>
            <span>
              Timeline · Alert Inspection · Incident RCA Story · Experiment Comparison ·
              Methodology &amp; Guide (Read-Only)
            </span>
          </div>
        </footer>
      </div>
    </RunContext.Provider>
  );
}
