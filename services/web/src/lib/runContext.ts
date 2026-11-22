import { createContext, useContext } from "react";
import type { Run } from "@/api/types";

/**
 * Run đang được chọn, dùng chung cho mọi màn hình.
 *
 * Nằm ở module riêng chứ không ở `App.tsx` để tránh vòng import: `App` import
 * các màn hình, nên màn hình không được import ngược lại `App`.
 */
export interface RunCtx {
  runs: Run[];
  runId: string;
  setRunId: (id: string) => void;
  runsLoading?: boolean;
  runsError?: string | null;
}

export const RunContext = createContext<RunCtx | null>(null);

export function useRuns(): RunCtx {
  const ctx = useContext(RunContext);
  if (!ctx) throw new Error("useRuns phải nằm trong RunContext");
  return ctx;
}

type RunLike = Pick<Run, "run_id" | "alert_count">;

/** Run độ nhạy (V36 (a) / V48 (b')): ngoài bản đăng ký H5, không được làm run mặc định. */
export function isSensitivityRunId(runId: string): boolean {
  return runId.includes("sens") || runId.includes("c3rolling");
}

/**
 * Run mặc định khi URL không chỉ định: run pipeline đầu tiên có cảnh báo và không phải
 * dòng độ nhạy (`GET /runs` xếp `started_at DESC`, nên run độ nhạy nạp sau cùng đứng đầu).
 */
export function pickDefaultRunId(runs: readonly RunLike[]): string {
  return (
    runs.find((r) => r.alert_count > 0 && !isSensitivityRunId(r.run_id))?.run_id ??
    runs.find((r) => r.alert_count > 0)?.run_id ??
    runs[0]?.run_id ??
    ""
  );
}

/**
 * Run đang chọn: `?run_id=` hợp lệ trên URL > run người dùng chọn trong phiên > run mặc định.
 * URL thắng để link trực tiếp và tải lại trang (F5) giữ đúng run của kịch bản demo.
 */
export function resolveRunId(
  runs: readonly RunLike[],
  urlRunId: string | null,
  chosenRunId: string | null,
): string {
  const known = (id: string | null): id is string =>
    id !== null && runs.some((r) => r.run_id === id);
  if (known(urlRunId)) return urlRunId;
  if (known(chosenRunId)) return chosenRunId;
  return pickDefaultRunId(runs);
}
