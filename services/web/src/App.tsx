import { useMemo, useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { api } from "@/api/client";
import { FixtureBanner, Loading, ErrorBox } from "@/components/ui";
import { RunContext, type RunCtx } from "@/lib/runContext";
import { useAsync } from "@/lib/util";
import { strategyLabel } from "@/theme/tokens";
import Timeline from "@/screens/Timeline";
import AlertDetail from "@/screens/AlertDetail";
import IncidentDetail from "@/screens/IncidentDetail";
import ExperimentComparison from "@/screens/ExperimentComparison";

const NAV = [
  { to: "/timeline", label: "Timeline", hint: "Cảnh báo và sự cố theo thời gian" },
  { to: "/compare", label: "So sánh thực nghiệm", hint: "Năm biến thể RAG" },
];

export default function App() {
  const { data: runs, loading, error } = useAsync(() => api.listRuns(), []);
  const [runId, setRunId] = useState<string | null>(null);

  const effectiveRunId = runId ?? runs?.[0]?.run_id ?? "";
  const activeRun = runs?.find((r) => r.run_id === effectiveRunId) ?? runs?.[0];
  const ctx = useMemo<RunCtx>(
    () => ({
      runs: runs ?? [],
      runId: effectiveRunId,
      setRunId,
      runsLoading: loading,
      runsError: error,
    }),
    [runs, effectiveRunId, loading, error],
  );

  return (
    <RunContext.Provider value={ctx}>
      <div className="flex min-h-full flex-col">
        <FixtureBanner />
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-[color:var(--color-hairline)] bg-surface px-5 py-3">
          <div className="flex items-baseline gap-6">
            <div>
              <div className="text-[13px] font-semibold tracking-tight text-ink">
                AIOps RCA — bảng điều khiển thực nghiệm
              </div>
              <div className="text-[11px] text-ink-muted">
                {activeRun
                  ? `Nezha · split ${activeRun.split} · seed ${activeRun.seed} · chỉ đọc`
                  : "Nezha · kết nối API · chỉ đọc"}
              </div>
            </div>
            <nav className="flex items-center gap-1">
              {NAV.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  title={item.hint}
                  className={({ isActive }) =>
                    `rounded-md px-3 py-1.5 text-[12px] font-medium transition-colors ${
                      isActive
                        ? "bg-[color:var(--color-plane)] text-ink"
                        : "text-ink-muted hover:text-ink-2"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>

          <label className="flex items-center gap-2 text-[11px] text-ink-muted">
            Run
            <select
              value={effectiveRunId}
              disabled={loading || !runs?.length}
              onChange={(e) => setRunId(e.target.value)}
              className="rounded-md border border-[color:var(--color-hairline)] bg-surface px-2 py-1.5 text-[12px] text-ink disabled:opacity-60"
            >
              {loading && <option value="">Đang tải danh sách run…</option>}
              {!loading && (!runs || runs.length === 0) && (
                <option value="">{error ? "Lỗi tải run" : "Chưa có run"}</option>
              )}
              {(runs ?? []).map((r) => (
                <option key={r.run_id} value={r.run_id}>
                  {strategyLabel[r.retrieval_strategy] ?? r.retrieval_strategy} — {r.run_id} (
                  {r.split})
                </option>
              ))}
            </select>
          </label>
        </header>

        <main className="mx-auto w-full max-w-[1400px] flex-1 px-5 py-5">
          {error ? (
            <Routes>
              <Route path="/compare" element={<ExperimentComparison />} />
              <Route
                path="*"
                element={<ErrorBox message={`Không tải được danh sách run từ API: ${error}`} />}
              />
            </Routes>
          ) : loading && !runs ? (
            <Routes>
              <Route path="/compare" element={<ExperimentComparison />} />
              <Route path="*" element={<Loading label="Đang tải danh sách run…" />} />
            </Routes>
          ) : (
            <Routes>
              <Route path="/" element={<Navigate to="/timeline" replace />} />
              <Route path="/timeline" element={<Timeline />} />
              <Route path="/alerts/:alertId" element={<AlertDetail />} />
              <Route path="/incidents/:incidentId" element={<IncidentDetail />} />
              <Route path="/compare" element={<ExperimentComparison />} />
              <Route path="*" element={<Navigate to="/timeline" replace />} />
            </Routes>
          )}
        </main>

        <footer className="border-t border-[color:var(--color-hairline)] px-5 py-3 text-[11px] text-ink-muted">
          Bốn màn hình theo <code className="font-mono">01-architecture-design.md</code> §6.7 —
          Timeline · Alert detail · Incident detail · Experiment comparison. Không thêm màn hình
          nào khác (xem <code className="font-mono">06-scope-guard.md</code> §6.4).
        </footer>
      </div>
    </RunContext.Provider>
  );
}
