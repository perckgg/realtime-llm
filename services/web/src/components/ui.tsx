import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { cx } from "@/lib/util";
import { USING_FIXTURES, USING_STATIC_SNAPSHOT } from "@/api/client";
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
        "rounded-xl border border-[color:var(--color-hairline)] bg-surface shadow-[0_1px_2px_rgba(15,23,42,0.03)]",
        className,
      )}
    >
      {(title || right) && (
        <header className="flex flex-wrap items-start justify-between gap-4 border-b border-[color:var(--color-hairline)] px-5 py-3.5">
          <div>
            {title && (
              <h2 className="text-[13.5px] font-semibold tracking-tight text-ink">{title}</h2>
            )}
            {subtitle && (
              <p className="mt-0.5 text-[11.5px] leading-relaxed text-ink-muted">{subtitle}</p>
            )}
          </div>
          {right}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

/**
 * Single KPI stat tile with optional series accent dot.
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
      {compact ? verdict.split("_")[0] : verdictLabel[verdict]}
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
 * Warning ribbon displayed when running on synthetic fixture data.
 */
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
      <div className="mx-auto flex max-w-[1440px] items-center gap-2">
        <span aria-hidden>⚠</span>
        <span>
          <strong className="font-semibold text-ink">Synthetic fixture data.</strong> Pipeline has
          not run — all numbers on screen are deterministic seed fixtures, not experiment results.
          Set <code className="font-mono">VITE_DATA_SOURCE=http</code> to read from{" "}
          <code className="font-mono">services/api</code>.
        </span>
      </div>
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
        background: "color-mix(in srgb, #e8d9b8 28%, var(--color-surface))",
        color: "var(--color-ink-2)",
      }}
      role="status"
    >
      <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className="rounded-md border px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wide"
            style={{
              borderColor: "#b48a3e",
              color: "#6b4b12",
              background: "color-mix(in srgb, #ebdcb9 45%, var(--color-surface))",
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
