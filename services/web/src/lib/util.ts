import { useEffect, useState } from "react";

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
