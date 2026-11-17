import { useEffect, useState } from "react";
import type { Alert } from "@/api/types";

/**
 * Hook tải dữ liệu tối giản. Cố ý không dùng react-query: dashboard chỉ đọc,
 * không có mutation, không cần cache tinh vi — thêm một thư viện nữa chỉ làm
 * dày phần "phụ thuộc" phải giải trình trong luận văn.
 */
export function useAsync<T>(
  fn: () => Promise<T>,
  deps: readonly unknown[],
): { data: T | null; error: string | null; loading: boolean } {
  const [state, setState] = useState<{ data: T | null; error: string | null; loading: boolean }>({
    data: null,
    error: null,
    loading: true,
  });

  useEffect(() => {
    let alive = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    fn()
      .then((data) => alive && setState({ data, error: null, loading: false }))
      .catch((e: unknown) =>
        alive &&
        setState({ data: null, error: e instanceof Error ? e.message : String(e), loading: false }),
      );
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}

export const pct = (x: number, places = 1): string => `${(x * 100).toFixed(places)}%`;

export const num = (x: number, places = 3): string => x.toFixed(places);

export const ms = (x: number): string =>
  x >= 1000 ? `${(x / 1000).toFixed(2)} s` : `${Math.round(x)} ms`;

export const clockUTC = (isoTs: string): string => isoTs.slice(11, 19);

export const dayUTC = (isoTs: string): string => isoTs.slice(0, 10);

export const stampUTC = (isoTs: string): string => `${isoTs.slice(0, 10)} ${isoTs.slice(11, 19)}Z`;

/** Gộp className có điều kiện, thay cho clsx. */
export const cx = (...parts: (string | false | null | undefined)[]): string =>
  parts.filter(Boolean).join(" ");

export type PolicyStepStatus = "passed" | "downgraded" | "na";

export interface PolicyStepInfo {
  status: PolicyStepStatus;
  label: string;
}

export interface PolicyEvaluation {
  shortReason: string | null;
  evidenceRule: PolicyStepInfo;
  gating: PolicyStepInfo;
  anchoring: PolicyStepInfo;
}

/**
 * Suy diễn 3 bước kiểm tra policy CTAV đúng thứ tự `services/judge/policy.py::decide`:
 * 1) raw_verdict != TRUE_ALERT -> dừng;
 * 2) require_evidence (`downgraded_by_evidence_rule`);
 * 3) ngưỡng θ_local / C2 gating (`downgraded_by_gating`);
 * 4) C3 neo bằng chứng (`downgraded_by_anchoring`).
 */
export function policySteps(
  a: Pick<
    Alert,
    | "raw_verdict"
    | "verdict"
    | "downgraded_by_evidence_rule"
    | "downgraded_by_gating"
    | "downgraded_by_anchoring"
  >,
): PolicyEvaluation {
  const raw = a.raw_verdict ?? a.verdict;
  if (raw !== "TRUE_ALERT") {
    const na = { status: "na" as const, label: "không áp dụng (dừng ở raw_verdict ≠ TRUE_ALERT)" };
    return { shortReason: null, evidenceRule: na, gating: na, anchoring: na };
  }
  if (a.downgraded_by_evidence_rule) {
    const na = { status: "na" as const, label: "không áp dụng (dừng ở luật bằng chứng)" };
    return {
      shortReason: "thiếu chứng cứ",
      evidenceRule: { status: "downgraded", label: "đã hạ verdict" },
      gating: na,
      anchoring: na,
    };
  }
  if (a.downgraded_by_gating) {
    return {
      shortReason: "C2 gate",
      evidenceRule: { status: "passed", label: "đạt (có bằng chứng)" },
      gating: { status: "downgraded", label: "đã hạ verdict" },
      anchoring: { status: "na", label: "không áp dụng (dừng ở C2 gating)" },
    };
  }
  if (a.verdict !== "TRUE_ALERT" && !a.downgraded_by_anchoring) {
    const na = { status: "na" as const, label: "không áp dụng (dừng ở ngưỡng θ)" };
    return {
      shortReason: "dưới ngưỡng θ",
      evidenceRule: { status: "passed", label: "đạt (có bằng chứng)" },
      gating: na,
      anchoring: na,
    };
  }
  if (a.downgraded_by_anchoring) {
    return {
      shortReason: "C3 neo",
      evidenceRule: { status: "passed", label: "đạt (có bằng chứng)" },
      gating: { status: "passed", label: "qua ngưỡng" },
      anchoring: { status: "downgraded", label: "đã hạ verdict" },
    };
  }
  return {
    shortReason: null,
    evidenceRule: { status: "passed", label: "đạt (có bằng chứng)" },
    gating: { status: "passed", label: "qua ngưỡng" },
    anchoring: { status: "passed", label: "đạt ngưỡng neo" },
  };
}
