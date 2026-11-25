import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { cx } from "@/lib/util";
import { USING_FIXTURES, USING_STATIC_SNAPSHOT } from "@/api/client";
import type { Verdict } from "@/api/types";
import { AlertTriangleIcon } from "@/components/icons";
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
        "rounded-xl border border-[color:var(--color-hairline)] bg-surface shadow-[0_1px_2px_rgb(15_23_42/0.04)]",
        className,
      )}
    >
      {(title || right) && (
        <header className="flex flex-wrap items-start justify-between gap-4 border-b border-[color:var(--color-hairline)] px-4 py-3">
          <div>
            {title && <h2 className="text-[13px] font-semibold tracking-tight text-ink">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-[11.5px] text-ink-muted">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

/**
 * Operational KPI tile with clean typographic hierarchy and optional status accent bar.
 */
export function StatTile({
  label,
  value,
  hint,
  accent,
  icon,
}: {
  label: string;
  value: string;
  hint?: string;
  accent?: string;
  icon?: ReactNode;
}) {
  return (
    <div
      className="relative overflow-hidden rounded-xl border border-[color:var(--color-hairline)] bg-surface px-4 py-3.5 shadow-[0_1px_2px_rgb(15_23_42/0.04)] transition-colors"
    >
      {accent && (
        <span
          aria-hidden
          className="absolute inset-y-0 left-0 w-[3px]"
          style={{ background: accent }}
        />
      )}
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-medium tracking-wider text-ink-muted uppercase">
          {label}
        </span>
        {icon && <span style={{ color: accent ?? "var(--color-ink-muted)" }}>{icon}</span>}
      </div>
      <div className="mt-2 font-mono text-[24px] leading-none font-semibold tracking-tight text-ink">
        {value}
      </div>
      {hint && <div className="mt-1.5 text-[11.5px] text-ink-2">{hint}</div>}
    </div>
  );
}

/** Verdict badge pairing color, shape glyph, and explicit text label. */
export function VerdictBadge({ verdict, compact }: { verdict: Verdict; compact?: boolean }) {
  const color = verdictColor[verdict];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium text-ink"
      style={{ borderColor: color, background: `${color}18` }}
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
  tone?: "neutral" | "warn" | "good" | "critical" | "accent" | "info";
}) {
  const toneClass =
    tone === "warn"
      ? "border-[color:var(--color-serious)] text-[color:var(--color-serious)] bg-[color:var(--color-serious)]/8"
      : tone === "critical"
        ? "border-[color:var(--color-critical)] text-[color:var(--color-critical)] bg-[color:var(--color-critical)]/10"
        : tone === "good"
          ? "border-[color:var(--color-good)] text-[color:var(--color-good)] bg-[color:var(--color-good)]/10"
          : tone === "accent" || tone === "info"
            ? "border-[color:var(--color-accent)] text-[color:var(--color-accent)] bg-[color:var(--color-accent-soft)]"
            : "border-[color:var(--color-hairline)] text-ink-2 bg-[color:var(--color-plane)]";
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 font-mono text-[10.5px] leading-tight",
        toneClass,
      )}
    >
      {children}
    </span>
  );
}

/** Displayed only when running in synthetic fixture mode (smoke/dev without backend). */
export function FixtureBanner() {
  if (!USING_FIXTURES) return null;
  return (
    <div
      className="border-b px-6 py-2 text-[11.5px]"
      style={{
        borderColor: "var(--color-hairline)",
        background: "color-mix(in srgb, var(--color-warning) 14%, var(--color-surface))",
        color: "var(--color-ink-2)",
      }}
      role="status"
    >
      <AlertTriangleIcon size={14} style={{ color: "var(--color-warning)" }} />
      <span>
        <strong className="font-semibold text-ink">Sandbox fixture mode.</strong> Running on
        deterministic local fixtures. Connect <code className="font-mono">services/api</code> with{" "}
        <code className="font-mono">VITE_DATA_SOURCE=http</code> for ClickHouse &amp; PostgreSQL
        telemetry.
      </span>
    </div>
  );
}

export const STATIC_DEMO_STEPS = [
  {
    step: "1",
    label: "Timeline (test)",
    to: "/timeline?run_id=pipeline_test_v2",
    pathMatch: "/timeline",
    title: "13,699 candidates -> 78 TRUE_ALERT -> 38 incidents",
  },
  {
    step: "2",
    label: "C3 downgrade",
    to: "/alerts/cand-ad327c0b162f6198%3Ahybrid_bm25_graph%3Ar0?run_id=pipeline_test_v2",
    pathMatch: "/alerts/cand-ad327c0b162f6198",
    title: "Normal window on productcatalogservice downgraded by C3 anchoring",
  },
  {
    step: "3",
    label: "CTAV network_delay",
    to: "/alerts/cand-fa85e82f02f08574%3Ahybrid_bm25_graph%3Ar0?run_id=pipeline_test_v2",
    pathMatch: "/alerts/cand-fa85e82f02f08574",
    title: "cartservice network_delay caught by C1 + C3 (missed by BM25)",
  },
  {
    step: "4",
    label: "Cascade RCA (sens.)",
    to: "/incidents/inc-46289ea526eaa3f3?run_id=pipeline_sens_test_v1",
    pathMatch: "/incidents/inc-46289ea526eaa3f3",
    title: "Multi-service cascade on sensitivity line (outside H5 registration)",
  },
  {
    step: "5",
    label: "H0–H5 Results",
    to: "/compare",
    pathMatch: "/compare",
    title: "Pre-registered H0-H5 evaluation table on test and val",
  },
  {
    step: "6",
    label: "Guide",
    to: "/guide",
    pathMatch: "/guide",
    title: "Formulas, CTAV policy rules, ablation summary & glossary",
  },
] as const;

/**
 * Top context ribbon for the static GitHub Pages snapshot: states provenance of the
 * verified M8–M10 runs and provides 1-click guided walkthrough shortcuts.
 */
export function StaticSnapshotBanner() {
  const { pathname } = useLocation();
  if (!USING_STATIC_SNAPSHOT) return null;

  return (
    <div
      className="border-b px-6 py-2 text-[11.5px]"
      style={{
        borderColor: "var(--color-hairline)",
        background: "color-mix(in srgb, var(--color-warning) 8%, var(--color-surface))",
        color: "var(--color-ink-2)",
      }}
      role="status"
    >
      <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className="rounded-md border px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wide"
            style={{
              borderColor: "var(--color-warning)",
              color: "var(--color-ink)",
              background: "color-mix(in srgb, var(--color-warning) 14%, var(--color-surface))",
            }}
          >
            STATIC BENCHMARK SNAPSHOT
          </span>
          <span>
            Verified M8–M10 runs (<code className="font-mono text-ink">pipeline_test_v2</code>,{" "}
            <code className="font-mono text-ink">pipeline_val_v2</code>,{" "}
            <code className="font-mono text-ink">pipeline_sens_test_v1</code>; 0 live API calls)
          </span>
        </div>

        <nav aria-label="Guided walkthrough" className="flex flex-wrap items-center gap-1.5">
          <span className="mr-0.5 text-[10.5px] font-semibold tracking-wide text-ink-muted uppercase">
            Guided Walkthrough:
          </span>
          {STATIC_DEMO_STEPS.map((s) => {
            const active = pathname === s.pathMatch || pathname.startsWith(`${s.pathMatch}%3A`);
            return (
              <Link
                key={s.step}
                to={s.to}
                title={s.title}
                className={cx(
                  "inline-flex items-center gap-1 rounded-md border px-2.5 py-1 text-[11px] font-medium transition-all",
                  active
                    ? "border-[color:var(--color-seq-550)] bg-surface text-ink shadow-xs"
                    : "border-[color:var(--color-hairline)] bg-surface/80 text-ink-2 hover:border-[color:var(--color-seq-550)] hover:bg-surface hover:text-ink",
                )}
              >
                <span className="font-mono text-[10px] text-ink-muted">{s.step}.</span>
                <span>{s.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}

export function Loading({ label = "Loading telemetry…" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-center text-[12px] text-ink-muted">
      <span className="h-2 w-2 rounded-full bg-[color:var(--color-accent)] ops-pulse" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div
      className="flex items-center gap-2.5 rounded-xl border px-4 py-3 text-[12px]"
      style={{
        borderColor: "var(--color-critical)",
        background: "color-mix(in srgb, var(--color-critical) 8%, var(--color-surface))",
        color: "var(--color-critical)",
      }}
      role="alert"
    >
      <AlertTriangleIcon size={16} className="shrink-0" />
      <span>{message}</span>
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="py-12 text-center text-[12.5px] text-ink-muted">{children}</div>;
}

/** Key-value row for structured operational metadata blocks. */
export function KV({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1.5">
      <dt className="text-[11.5px] text-ink-muted">{k}</dt>
      <dd className="text-right text-[12px] tabular-nums text-ink">{v}</dd>
    </div>
  );
}
