import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { cx } from "@/lib/util";
import { USING_FIXTURES } from "@/api/client";
import type { Verdict } from "@/api/types";
import { demoHighlights, snapshotMeta } from "@/mock/fixtures";
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

export function Pill({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "warn" | "good";
}) {
  return (
    <span
      className={cx(
        "inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[10.5px]",
        tone === "warn"
          ? "border-[color:var(--color-serious)] text-[color:var(--color-serious)]"
          : tone === "good"
            ? "border-[color:var(--color-good)] text-[color:var(--color-good)]"
            : "border-[color:var(--color-hairline)] text-ink-muted",
      )}
    >
      {children}
    </span>
  );
}

/**
 * Thanh thông tin chế độ Demo Offline (Snapshot thực nghiệm thật từ eval/results/)
 * kèm các lối tắt tương ứng với kịch bản trình diễn 5 phút (08 §6).
 */
export function FixtureBanner() {
  if (!USING_FIXTURES) return null;
  return (
    <div
      className="flex flex-wrap items-center justify-between gap-2 border-b px-5 py-2 text-[11.5px]"
      style={{
        borderColor: "var(--color-hairline)",
        background: "color-mix(in srgb, var(--color-seq-250) 10%, var(--color-surface))",
        color: "var(--color-ink-2)",
      }}
      role="status"
    >
      <div className="flex items-center gap-2">
        <span
          className="rounded border px-1.5 py-0.5 font-mono text-[10px] font-semibold"
          style={{ borderColor: "var(--color-seq-550)", color: "var(--color-seq-550)" }}
        >
          DEMO OFFLINE
        </span>
        <span>
          Dữ liệu thực nghiệm thật từ <code className="font-mono">eval/results/</code> (
          <code className="font-mono">val</code> {snapshotMeta.val_telemetry_windows.toLocaleString("vi-VN")} cửa sổ telemetry · H0{" "}
          <code className="font-mono">test</code> {snapshotMeta.test_h0_telemetry_windows.toLocaleString("vi-VN")} cửa sổ).
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-[10.5px] text-ink-muted">Kịch bản:</span>
        {demoHighlights.map((h) => (
          <Link
            key={h.id}
            to={h.path}
            title={h.subtitle}
            className="rounded border border-[color:var(--color-hairline)] bg-surface px-2 py-0.5 text-[11px] text-ink-2 transition-colors hover:border-[color:var(--color-seq-550)] hover:text-ink"
          >
            {h.step}. {h.title}
          </Link>
        ))}
      </div>
    </div>
  );
}

export function Loading({ label = "Đang tải…" }: { label?: string }) {
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

export function KV({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1">
      <dt className="text-[11px] text-ink-muted">{k}</dt>
      <dd className="text-[12px] tabular-nums text-ink">{v}</dd>
    </div>
  );
}
