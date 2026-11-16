import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { cx } from "@/lib/util";
import { USING_FIXTURES } from "@/api/client";
import type { Verdict } from "@/api/types";
import { demoHighlights, snapshotMeta } from "@/mock/fixtures";
import { verdictColor, verdictGlyph, verdictLabel, verdictShortLabel } from "@/theme/tokens";

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
        "rounded-xl border border-[color:var(--color-hairline)] bg-surface shadow-[0_1px_2px_rgba(15,23,42,0.03)]",
        className,
      )}
    >
      {(title || right) && (
        <header className="flex flex-wrap items-start justify-between gap-4 border-b border-[color:var(--color-hairline)] px-5 py-3.5">
          <div>
            {title && <h2 className="text-[13.5px] font-semibold tracking-tight text-ink">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-[11.5px] leading-relaxed text-ink-muted">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      <div className="p-5">{children}</div>
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
    <div className="rounded-xl border border-[color:var(--color-hairline)] bg-surface px-4 py-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.025)]">
      <div className="flex items-center gap-1.5">
        {accent && (
          <span
            aria-hidden
            className="h-2 w-2 shrink-0 rounded-full"
            style={{ background: accent }}
          />
        )}
        <span className="text-[10.5px] font-semibold tracking-wider text-ink-muted uppercase">
          {label}
        </span>
      </div>
      <div className="mt-1.5 text-[25px] leading-tight font-semibold tracking-tight tabular-nums text-ink">
        {value}
      </div>
      {hint && <div className="mt-1 text-[11px] leading-snug text-ink-2">{hint}</div>}
    </div>
  );
}

/** Verdict badge combining shape glyph and descriptive text label. */
export function VerdictBadge({ verdict, compact }: { verdict: Verdict; compact?: boolean }) {
  const color = verdictColor[verdict];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium whitespace-nowrap text-ink-2"
      style={{ borderColor: `${color}66`, background: `${color}12` }}
      title={verdictLabel[verdict]}
    >
      <span aria-hidden style={{ color }}>
        {verdictGlyph[verdict]}
      </span>
      {compact ? verdictShortLabel[verdict] : verdictLabel[verdict]}
    </span>
  );
}

export function Pill({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "warn" | "good" | "info";
}) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 font-mono text-[10.5px] whitespace-nowrap",
        tone === "warn"
          ? "border-[color:var(--color-serious)]/60 bg-[color:var(--color-serious)]/8 text-[#9a3412]"
          : tone === "good"
            ? "border-[color:var(--color-good)]/50 bg-[color:var(--color-good)]/8 text-[#065f46]"
            : tone === "info"
              ? "border-[color:var(--color-series-1)]/50 bg-[color:var(--color-series-1)]/8 text-[#1e40af]"
              : "border-[color:var(--color-hairline)] bg-[color:var(--color-plane)] text-ink-2",
      )}
    >
      {children}
    </span>
  );
}

/**
 * Top context ribbon with offline benchmark provenance and 1-click guided
 * case studies highlighting CTAV's core mechanisms.
 */
export function FixtureBanner() {
  const { pathname } = useLocation();
  if (!USING_FIXTURES) return null;

  return (
    <div
      className="border-b px-6 py-2 text-[11.5px]"
      style={{
        borderColor: "var(--color-hairline)",
        background: "color-mix(in srgb, var(--color-seq-250) 9%, var(--color-surface))",
        color: "var(--color-ink-2)",
      }}
      role="status"
    >
      <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className="rounded-md border px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wide"
            style={{
              borderColor: "var(--color-seq-550)",
              color: "var(--color-seq-700)",
              background: "color-mix(in srgb, var(--color-seq-250) 18%, var(--color-surface))",
            }}
          >
            STATIC BENCHMARK SNAPSHOT
          </span>
          <span>
            Validation split ({" "}
            <strong className="font-semibold text-ink">
              {snapshotMeta.val_telemetry_windows.toLocaleString("en-US")}
            </strong>{" "}
            telemetry windows) · Holdout test verification ({" "}
            <strong className="font-semibold text-ink">
              {snapshotMeta.test_h0_telemetry_windows.toLocaleString("en-US")}
            </strong>{" "}
            windows)
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <span className="mr-0.5 text-[10.5px] font-semibold tracking-wide text-ink-muted uppercase">
            Guided Walkthrough:
          </span>
          {demoHighlights.map((h) => {
            const active = pathname === h.path;
            return (
              <Link
                key={h.id}
                to={h.path}
                title={h.subtitle}
                className={cx(
                  "inline-flex items-center gap-1 rounded-md border px-2.5 py-1 text-[11px] font-medium transition-all",
                  active
                    ? "border-[color:var(--color-seq-550)] bg-surface text-ink shadow-xs"
                    : "border-[color:var(--color-hairline)] bg-surface/80 text-ink-2 hover:border-[color:var(--color-seq-550)] hover:bg-surface hover:text-ink",
                )}
              >
                <span className="font-mono text-[10px] text-ink-muted">{h.step}.</span>
                <span>{h.title}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export function Loading({ label = "Loading evaluation data…" }: { label?: string }) {
  return <div className="py-12 text-center text-[12.5px] text-ink-muted">{label}</div>;
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div
      className="rounded-xl border px-4 py-3 text-[12.5px]"
      style={{ borderColor: "var(--color-critical)", color: "var(--color-critical)" }}
    >
      {message}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="py-12 text-center text-[12.5px] text-ink-muted">{children}</div>;
}

export function KV({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5">
      <dt className="text-[11.5px] text-ink-muted">{k}</dt>
      <dd className="text-right text-[12px] tabular-nums text-ink">{v}</dd>
    </div>
  );
}
