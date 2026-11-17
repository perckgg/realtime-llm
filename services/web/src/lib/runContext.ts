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
