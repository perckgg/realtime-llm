import type { ReactNode } from "react";
import { cx } from "@/lib/util";
import { USING_FIXTURES } from "@/api/client";
import type { Verdict } from "@/api/types";
import { verdictColor, verdictGlyph, verdictLabel } from "@/theme/tokens";

export function Card({
  title,
  subtitle,
  right,
  children,
  className,
}: {
  title?: string;
  subtitle?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cx(
        "rounded-lg border border-[color:var(--color-hairline)] bg-surface",
        className,
      )}
    >
      {(title || right) && (
        <header className="flex items-start justify-between gap-4 border-b border-[color:var(--color-hairline)] px-4 py-3">
          <div>
            {title && <h2 className="text-[13px] font-semibold text-ink">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-[11px] text-ink-muted">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

/**
 * Con số đơn lẻ không cần biểu đồ. Dùng chữ số tỉ lệ (mặc định) cho số lớn,
 * chỉ bật tabular-nums ở bảng nơi các cột phải thẳng hàng.
 */
export function StatTile({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: string;
  hint?: string;
  accent?: string;
}) {
  return (
    <div className="rounded-lg border border-[color:var(--color-hairline)] bg-surface px-4 py-3">
      <div className="flex items-center gap-1.5">
        {accent && (
          <span
            aria-hidden
            className="h-2 w-2 shrink-0 rounded-full"
            style={{ background: accent }}
          />
        )}
        <span className="text-[11px] font-medium tracking-wide text-ink-muted uppercase">
          {label}
        </span>
      </div>
      <div className="mt-1.5 text-[26px] leading-none font-semibold text-ink">{value}</div>
      {hint && <div className="mt-1.5 text-[11px] text-ink-2">{hint}</div>}
    </div>
  );
}

/** Danh tính verdict không bao giờ chỉ nằm ở màu: có ký hiệu và có chữ. */
export function VerdictBadge({ verdict, compact }: { verdict: Verdict; compact?: boolean }) {
  const color = verdictColor[verdict];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium text-ink-2"
      style={{ borderColor: color, background: `${color}14` }}
      title={verdictLabel[verdict]}
    >
      <span aria-hidden style={{ color }}>
        {verdictGlyph[verdict]}
      </span>
      {compact ? verdict.split("_")[0] : verdictLabel[verdict]}
    </span>
  );
}

export function Pill({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "warn" }) {
  return (
    <span
      className={cx(
        "inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[10.5px]",
        tone === "warn"
          ? "border-[color:var(--color-serious)] text-[color:var(--color-serious)]"
          : "border-[color:var(--color-hairline)] text-ink-muted",
      )}
    >
      {children}
    </span>
  );
}

/**
 * Dải cảnh báo dữ liệu giả. Hiện trên mọi màn hình khi chạy bằng fixture — để
 * không ai chụp ảnh màn hình rồi đưa vào luận văn như kết quả thật.
 */
export function FixtureBanner() {
  if (!USING_FIXTURES) return null;
  return (
    <div
      className="flex items-center gap-2 border-b px-5 py-1.5 text-[11.5px]"
      style={{
        borderColor: "var(--color-hairline)",
        background: "color-mix(in srgb, var(--color-warning) 14%, var(--color-surface))",
        color: "var(--color-ink-2)",
      }}
      role="status"
    >
      <span aria-hidden>⚠</span>
      <span>
        <strong className="font-semibold">Synthetic fixture data.</strong> Pipeline has not run —
        all numbers on screen are deterministic seed fixtures, not experiment results. Set{" "}
        <code className="font-mono">VITE_DATA_SOURCE=http</code> to read from{" "}
        <code className="font-mono">services/api</code>.
      </span>
    </div>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return <div className="py-10 text-center text-[12px] text-ink-muted">{label}</div>;
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div
      className="rounded-lg border px-4 py-3 text-[12px]"
      style={{ borderColor: "var(--color-critical)", color: "var(--color-critical)" }}
    >
      {message}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="py-10 text-center text-[12px] text-ink-muted">{children}</div>;
}

/** Nhãn khoá–giá trị cho các khối siêu dữ liệu. */
export function KV({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1">
      <dt className="text-[11px] text-ink-muted">{k}</dt>
      <dd className="text-[12px] tabular-nums text-ink">{v}</dd>
    </div>
  );
}
