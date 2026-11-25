import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "@/api/client";
import {
  ActivityIcon,
  BarChartIcon,
  BookOpenIcon,
  BrandMark,
  CompassIcon,
  EyeIcon,
  FlameIcon,
  MoonIcon,
  NetworkIcon,
  SunIcon,
} from "@/components/icons";
import { FixtureBanner, StaticSnapshotBanner, Loading, ErrorBox } from "@/components/ui";
import {
  formatSessionLabel,
  GUIDED_SCENARIOS,
  isSensitivityRunId,
  resolveRunId,
  RunContext,
  type RunCtx,
  type ThemeMode,
} from "@/lib/runContext";
import { cx, useAsync } from "@/lib/util";

const Overview = lazy(() => import("@/screens/Overview"));
const Incidents = lazy(() => import("@/screens/Incidents"));
const Timeline = lazy(() => import("@/screens/Timeline"));
const AlertDetail = lazy(() => import("@/screens/AlertDetail"));
const IncidentDetail = lazy(() => import("@/screens/IncidentDetail"));
const ExperimentComparison = lazy(() => import("@/screens/ExperimentComparison"));
const MethodologyGuide = lazy(() => import("@/screens/MethodologyGuide"));

const OPS_NAV = [
  { to: "/overview", label: "Operations", hint: "Service topology & command center", icon: NetworkIcon },
  { to: "/incidents", label: "Incidents", hint: "Correlated incident triage queue", icon: FlameIcon },
  { to: "/timeline", label: "Alert Stream", hint: "Telemetry timeline & live replay", icon: ActivityIcon },
];

const EVAL_NAV = [
  { to: "/compare", label: "Benchmark", hint: "Offline H0–H5 evaluation & comparison", icon: BarChartIcon },
  {
    to: "/guide",
    label: "Methodology",
    hint: "Formulas, CTAV policy rules, ablations & glossary for committee review",
    icon: BookOpenIcon,
  },
];

function readInitialTheme(): ThemeMode {
  try {
    const saved = window.localStorage.getItem("aiops-theme");
    if (saved === "dark" || saved === "light") return saved;
  } catch {
    // ignore storage errors in restricted contexts
  }
  return "light";
}

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const { data: runs, loading, error } = useAsync(() => api.listRuns(), []);
  const healthQ = useAsync(() => api.health(), []);
  const [searchParams, setSearchParams] = useSearchParams();
  const [chosenRunId, setChosenRunId] = useState<string | null>(null);
  const [groundTruthOverlay, setGroundTruthOverlay] = useState<boolean>(
    () => searchParams.get("gt") === "1",
  );
  const [theme, setTheme] = useState<ThemeMode>(readInitialTheme);
  const [walkthroughOpen, setWalkthroughOpen] = useState(false);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      window.localStorage.setItem("aiops-theme", theme);
    } catch {
      // ignore storage errors
    }
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  const effectiveRunId = resolveRunId(runs ?? [], searchParams.get("run_id"), chosenRunId);
  const isSensitivityRun = isSensitivityRunId(effectiveRunId);
  const onCompareRoute =
    location.pathname.startsWith("/compare") || location.pathname.startsWith("/guide");

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
      groundTruthOverlay,
      setGroundTruthOverlay,
      theme,
      toggleTheme,
    }),
    [runs, effectiveRunId, setRunId, loading, error, groundTruthOverlay, theme, toggleTheme],
  );

  const apiHealthy = Boolean(healthQ.data?.status && !healthQ.error);
  const streamRuns = (runs ?? []).filter((r) => r.alert_count > 0);
  const archivedRuns = (runs ?? []).filter((r) => r.alert_count === 0);

  return (
    <RunContext.Provider value={ctx}>
      <div className="flex min-h-full bg-[color:var(--color-plane)] text-ink">
        {/* Production Left Sidebar */}
        <aside
          className="hidden w-[228px] shrink-0 flex-col border-r border-[color:var(--color-hairline)] lg:flex"
          style={{ background: "var(--color-sidebar)", color: "var(--color-sidebar-ink)" }}
        >
          <div className="flex h-[56px] items-center gap-2.5 border-b border-white/10 px-4">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[color:var(--color-accent)] text-white shadow-xs">
              <BrandMark size={17} />
            </span>
            <div className="leading-tight">
              <div className="text-[13px] font-semibold tracking-tight text-white">
                AIOps RCA
              </div>
              <div className="text-[10.5px] text-slate-400">Incident Intelligence</div>
            </div>
          </div>

          <nav aria-label="Primary navigation" className="flex-1 space-y-5 px-3 py-4">
            <div>
              <div className="mb-1.5 px-2.5 text-[10px] font-semibold tracking-wider text-slate-400 uppercase">
                Operations
              </div>
              <ul className="space-y-0.5">
                {OPS_NAV.map((item) => {
                  const Icon = item.icon;
                  return (
                    <li key={item.to}>
                      <NavLink
                        to={item.to}
                        title={item.hint}
                        className={({ isActive }) =>
                          cx(
                            "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[12.5px] font-medium transition-colors",
                            isActive
                              ? "bg-white/12 text-white"
                              : "text-slate-300 hover:bg-white/6 hover:text-white",
                          )
                        }
                      >
                        <Icon size={16} />
                        {item.label}
                      </NavLink>
                    </li>
                  );
                })}
              </ul>
            </div>

            <div>
              <div className="mb-1.5 px-2.5 text-[10px] font-semibold tracking-wider text-slate-400 uppercase">
                Evaluation
              </div>
              <ul className="space-y-0.5">
                {EVAL_NAV.map((item) => {
                  const Icon = item.icon;
                  return (
                    <li key={item.to}>
                      <NavLink
                        to={item.to}
                        title={item.hint}
                        className={({ isActive }) =>
                          cx(
                            "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[12.5px] font-medium transition-colors",
                            isActive
                              ? "bg-white/12 text-white"
                              : "text-slate-300 hover:bg-white/6 hover:text-white",
                          )
                        }
                      >
                        <Icon size={16} />
                        {item.label}
                      </NavLink>
                    </li>
                  );
                })}
              </ul>
            </div>
          </nav>

          {/* Guided Walkthrough launcher */}
          <div className="border-t border-white/10 p-3">
            <button
              type="button"
              onClick={() => setWalkthroughOpen((v) => !v)}
              aria-expanded={walkthroughOpen}
              className="flex w-full items-center justify-between gap-2 rounded-lg border border-white/12 bg-white/5 px-3 py-2 text-left text-[12px] font-medium text-slate-100 transition-colors hover:bg-white/10"
            >
              <span className="flex items-center gap-2">
                <CompassIcon size={15} className="text-blue-400" />
                Guided Scenarios
              </span>
              <span className="text-[10px] text-slate-400">{walkthroughOpen ? "▾" : "▸"}</span>
            </button>
            {walkthroughOpen && (
              <ul className="mt-2 space-y-1">
                {GUIDED_SCENARIOS.map((sc) => (
                  <li key={sc.id}>
                    <button
                      type="button"
                      onClick={() => {
                        if (sc.enableGroundTruth !== undefined) {
                          setGroundTruthOverlay(sc.enableGroundTruth);
                        }
                        navigate(sc.to);
                      }}
                      className="w-full rounded-md px-2.5 py-1.5 text-left transition-colors hover:bg-white/10"
                    >
                      <div className="text-[11px] font-medium text-slate-100">
                        {sc.step}. {sc.title}
                      </div>
                      <div className="truncate text-[10px] text-slate-400">{sc.subtitle}</div>
                    </button>
                  </li>
                ))}
              </ul>
            )}

            <div className="mt-3 flex items-center gap-2 px-1 text-[11px] text-slate-400">
              <span
                className={cx(
                  "h-2 w-2 rounded-full",
                  apiHealthy ? "bg-emerald-400 ops-pulse" : "bg-red-400",
                )}
              />
              <span>{apiHealthy ? "Engine Healthy · Offline Ready" : "API Disconnected"}</span>
            </div>
          </div>
        </aside>

        {/* Main Workspace Column */}
        <div className="flex min-w-0 flex-1 flex-col">
          <FixtureBanner />
          <StaticSnapshotBanner />

          {/* Sticky Top Command Bar */}
          <header className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-3 border-b border-[color:var(--color-hairline)] bg-surface/95 px-5 py-2.5 backdrop-blur">
            {/* Compact nav for narrow screens */}
            <div className="flex items-center gap-3 lg:hidden">
              <span className="flex h-7 w-7 items-center justify-center rounded-md bg-[color:var(--color-accent)] text-white">
                <BrandMark size={15} />
              </span>
              <nav className="flex items-center gap-1">
                {[...OPS_NAV, ...EVAL_NAV].map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      cx(
                        "rounded-md px-2.5 py-1 text-[12px] font-medium",
                        isActive
                          ? "bg-[color:var(--color-plane)] text-ink"
                          : "text-ink-muted hover:text-ink",
                      )
                    }
                  >
                    {item.label}
                  </NavLink>
                ))}
              </nav>
            </div>

            {/* Stream / Session Selector */}
            <div className="flex flex-wrap items-center gap-2.5">
              <label className="flex items-center gap-2 text-[11px] font-medium text-ink-muted">
                <span>Stream</span>
                <select
                  value={effectiveRunId}
                  disabled={loading || !runs?.length}
                  onChange={(e) => setRunId(e.target.value)}
                  className="max-w-[340px] rounded-lg border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)] px-2.5 py-1.5 text-[12px] font-medium text-ink disabled:opacity-60"
                >
                  {loading && <option value="">Connecting…</option>}
                  {!loading && (!runs || runs.length === 0) && (
                    <option value="">{error ? "Failed to load streams" : "No streams"}</option>
                  )}
                  {streamRuns.length > 0 && (
                    <optgroup label="Active Telemetry Streams">
                      {streamRuns.map((r) => (
                        <option key={r.run_id} value={r.run_id}>
                          {formatSessionLabel(r)} ({r.alert_count.toLocaleString("en-US")} windows)
                        </option>
                      ))}
                    </optgroup>
                  )}
                  {archivedRuns.length > 0 && (
                    <optgroup label="Archived Incident Sessions">
                      {archivedRuns.map((r) => (
                        <option key={r.run_id} value={r.run_id}>
                          {formatSessionLabel(r)}
                        </option>
                      ))}
                    </optgroup>
                  )}
                </select>
              </label>
            </div>

            {/* Right Controls: Operations/Eval Overlay + Theme Toggle */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                role="switch"
                aria-checked={groundTruthOverlay}
                onClick={() => setGroundTruthOverlay((v) => !v)}
                title="Toggle benchmark ground-truth overlay on operational screens"
                className={cx(
                  "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[11.5px] font-medium transition-colors",
                  groundTruthOverlay
                    ? "border-[color:var(--color-accent)] bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent)]"
                    : "border-[color:var(--color-hairline)] bg-surface text-ink-2 hover:bg-[color:var(--color-plane)] hover:text-ink",
                )}
              >
                <EyeIcon size={14} />
                {groundTruthOverlay ? "Eval Overlay: ON" : "Ops View"}
              </button>

              <button
                type="button"
                onClick={toggleTheme}
                aria-label={theme === "dark" ? "Switch to Light theme" : "Switch to Dark Ops theme"}
                title={theme === "dark" ? "Switch to Light theme" : "Switch to Dark Ops theme"}
                className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-[color:var(--color-hairline)] bg-surface text-ink-2 transition-colors hover:bg-[color:var(--color-plane)] hover:text-ink"
              >
                {theme === "dark" ? <SunIcon size={15} /> : <MoonIcon size={15} />}
              </button>
            </div>
          </header>

          {isSensitivityRun && !onCompareRoute && (
            <div
              className="border-b px-5 py-1.5 text-[11.5px]"
              style={{
                borderColor: "var(--color-hairline)",
                background: "color-mix(in srgb, var(--color-warning) 14%, var(--color-surface))",
                color: "var(--color-ink-2)",
              }}
              role="status"
            >
              <strong className="text-ink">High-Recall Mode (c3_rolling_baseline):</strong>{" "}
              Rolling-baseline sensitivity stream enabled for multi-service cascade walkthroughs;
              primary registered benchmark numbers remain under the default CTAV stream.
            </div>
          )}

          <main className="mx-auto w-full max-w-[1440px] flex-1 px-5 py-5">
            <Suspense fallback={<Loading label="Loading view…" />}>
              {error ? (
                <Routes>
                  <Route path="/compare" element={<ExperimentComparison />} />
                  <Route path="/guide" element={<MethodologyGuide />} />
                  <Route
                    path="*"
                    element={<ErrorBox message={`Unable to reach telemetry API: ${error}`} />}
                  />
                </Routes>
              ) : loading && !runs ? (
                <Routes>
                  <Route path="/compare" element={<ExperimentComparison />} />
                  <Route path="/guide" element={<MethodologyGuide />} />
                  <Route path="*" element={<Loading label="Connecting to telemetry store…" />} />
                </Routes>
              ) : (
                <Routes>
                  <Route
                    path="/"
                    element={
                      <Navigate
                        to={{
                          pathname: "/overview",
                          search: searchParams.toString() ? `?${searchParams}` : "",
                        }}
                        replace
                      />
                    }
                  />
                  <Route path="/overview" element={<Overview />} />
                  <Route path="/incidents" element={<Incidents />} />
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
                          pathname: "/overview",
                          search: searchParams.toString() ? `?${searchParams}` : "",
                        }}
                        replace
                      />
                    }
                  />
                </Routes>
              )}
            </Suspense>
          </main>

          <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-[color:var(--color-hairline)] px-5 py-2.5 text-[11px] text-ink-muted">
            <span>AIOps RCA Platform · CTAV Alert Validation &amp; Topology-Aware Root Cause Analysis</span>
            <span className="font-mono">
              ClickHouse + PostgreSQL · {groundTruthOverlay ? "Evaluation Overlay" : "Operations Mode"}
            </span>
          </footer>
        </div>
      </div>
    </RunContext.Provider>
  );
}
