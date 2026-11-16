import { Link } from "react-router-dom";
import { Card, Pill, StatTile } from "@/components/ui";
import { num } from "@/lib/util";
import {
  ablationRows,
  demoHighlights,
  h0TestComparison,
  runMetrics,
  snapshotMeta,
} from "@/mock/fixtures";
import { status, strategyColor, strategyShortLabel } from "@/theme/tokens";

const MILESTONES = [
  {
    phase: "Phase 1 · Data & Detector Foundation",
    scope: "Nezha time-series split hygiene (dev / val / test), Isolation Forest scoring (threshold 0.85), deterministic cache",
    status: "Completed",
    tone: "good" as const,
  },
  {
    phase: "Phase 2 · Topology Paradox Discovery",
    scope: "Quantified why uncalibrated 1-hop graph retrieval improves Recall but inflates False Positives on val and 11,985-window holdout test",
    status: "Verified (p < 0.001)",
    tone: "good" as const,
  },
  {
    phase: "Phase 3 · CTAV Calibration Policy",
    scope: "Designed Baseline Evidence Gate (dev p90 latency + local error log anchoring) cutting validation FPR by 11.8× without extra LLM cost",
    status: "Completed",
    tone: "good" as const,
  },
  {
    phase: "Phase 4 · RCA Graph & Interactive Demo",
    scope: "300s call-graph alert clustering, 1-hop backward root-cause localization, interactive React dashboard & static GitHub Pages showcase",
    status: "Live Preview",
    tone: "info" as const,
  },
  {
    phase: "Phase 5 · Full Holdout Test & E2E API",
    scope: "Completing holdout test runs across all 5 methods and wiring live ClickHouse/PostgreSQL FastAPI endpoints",
    status: "In Progress",
    tone: "warn" as const,
  },
];

const GLOSSARY = [
  {
    term: "Confirmed Alert (TRUE_ALERT)",
    category: "Verdict",
    definition:
      "Positive classification retained after both the LLM judge and the Baseline Evidence Gate agree that local service telemetry corroborates an active fault.",
  },
  {
    term: "Suppressed / Uncertain (UNCERTAIN)",
    category: "Verdict",
    definition:
      "Ambiguous or downgraded candidate. Includes windows initially flagged by the LLM from neighbor context that failed the Historical p90 Latency / Error-Log Anchor check.",
  },
  {
    term: "Precision = TP / (TP + FP)",
    category: "Metric",
    definition:
      "Fraction of Confirmed Alerts that correspond to real injected faults. Critical for preventing SRE alert fatigue.",
  },
  {
    term: "Recall = TP / (TP + FN)",
    category: "Metric",
    definition:
      "Fraction of all ground-truth injected fault windows successfully surfaced as Confirmed Alerts.",
  },
  {
    term: "False Positive Rate (FPR) = FP / (FP + TN)",
    category: "Metric",
    definition:
      "Probability of raising a false alarm on normal healthy traffic windows. Lower values indicate stronger suppression of spurious alerts.",
  },
  {
    term: "Historical p90 Baseline Anchor",
    category: "CTAV Mechanism",
    definition:
      "Per-service 90th-percentile trace span duration computed strictly from the training (dev) split. Used to distinguish true local degradation from benign upstream/downstream slowness.",
  },
  {
    term: "95% Bootstrap Confidence Interval",
    category: "Statistics",
    definition:
      "Non-parametric confidence interval computed over 1,000 stratified bootstrap resamples (seed 42) across telemetry windows.",
  },
  {
    term: "McNemar's Paired Test",
    category: "Statistics",
    definition:
      "Statistical hypothesis test comparing two validators on the exact same windows by analyzing discordant predictions separately on fault and normal subsets.",
  },
];

export default function MethodologyGuide() {
  const bm25 = runMetrics["h0_val_bm25_v3"];
  const topo = runMetrics["h0_val_c1_k0_v1"];
  const ctav = runMetrics["ctav_final_val_v1"];

  const compareCards = [
    {
      title: "BM25 Lexical RAG (Baseline)",
      color: strategyColor.bm25_hybrid,
      m: bm25,
      takeaway: "Conservative: keeps false alarms low, but misses cross-service anomalies.",
    },
    {
      title: "Uncalibrated Topology RAG",
      color: strategyColor.hybrid_bm25_graph,
      m: topo,
      takeaway: "The Topology Paradox: raises Recall, but leaks neighbor spikes into healthy services (low Precision).",
    },
    {
      title: "CTAV (Proposed Calibrated Pipeline)",
      color: strategyColor.ctav,
      m: ctav,
      takeaway: "Solves the paradox: preserves fault recall while cutting FPR by 11.8× vs. uncalibrated Topology RAG.",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-[20px] font-semibold tracking-tight text-ink">
              Methodology, Mathematical Formulations &amp; Progress Guide
            </h1>
            <Pill tone="info">Advisor Review Reference</Pill>
          </div>
          <p className="mt-1 max-w-3xl text-[12px] leading-relaxed text-ink-muted">
            Self-contained technical walkthrough explaining the research motivation behind{" "}
            <strong className="font-semibold text-ink">CTAV (Calibrated Topology-Aware Alert Validation)</strong>,
            all scoring equations, baseline gating rules, and current benchmark progress across validation (
            {snapshotMeta.val_telemetry_windows.toLocaleString("en-US")} windows) and holdout test splits.
          </p>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {demoHighlights.slice(0, 4).map((h) => (
            <Link
              key={h.id}
              to={h.path}
              className="rounded-lg border border-[color:var(--color-hairline)] bg-surface px-2.5 py-1.5 text-[11px] font-medium text-ink-2 transition-colors hover:border-[color:var(--color-seq-550)] hover:text-ink"
            >
              {h.step}. {h.title} →
            </Link>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3.5 md:grid-cols-4">
        <StatTile
          label="CTAV Precision Gain"
          value={ctav && topo ? `${num(topo.precision.value, 3)} → ${num(ctav.precision.value, 3)}` : "—"}
          hint="4.4× higher Precision vs. Uncalibrated Topology RAG"
          accent={strategyColor.ctav}
        />
        <StatTile
          label="False Positive Reduction"
          value={ctav && topo ? `${(topo.fpr.value / Math.max(0.0001, ctav.fpr.value)).toFixed(1)}× lower` : "—"}
          hint={ctav && topo ? `FPR reduced from ${num(topo.fpr.value, 4)} to ${num(ctav.fpr.value, 4)}` : ""}
          accent={status.good}
        />
        <StatTile
          label="Holdout Test (11,985 win)"
          value={h0TestComparison.criteria.every((c) => c.passed) ? "4 / 4 Passed" : "Partial"}
          hint="Topology Recall gain & FPR inflation confirmed (p < 0.001)"
          accent={strategyColor.hybrid_bm25_graph}
        />
        <StatTile
          label="RCA 1-Hop Preview"
          value={`${snapshotMeta.ctav_val_1hop_hit1} / ${snapshotMeta.ctav_val_fault_incidents}`}
          hint="Root-cause service match on CTAV validation fault clusters"
          accent={strategyColor.bm25_hybrid}
        />
      </div>

      <Card
        title="1. Current Progress & Thesis Milestone Overview"
        subtitle="Strict train/validation/holdout-test separation ensures all hyperparameters and thresholds are tuned before touching the test split."
      >
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[12px]">
            <thead>
              <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] font-semibold tracking-wide text-ink-muted uppercase">
                <th className="py-2 pr-4">Workstream / Milestone</th>
                <th className="py-2 pr-4">Implemented Scope &amp; Artifacts</th>
                <th className="py-2 text-right">Status</th>
              </tr>
            </thead>
            <tbody>
              {MILESTONES.map((m) => (
                <tr key={m.phase} className="border-b border-[color:var(--color-hairline)] last:border-0">
                  <td className="py-2.5 pr-4 font-semibold whitespace-nowrap text-ink">{m.phase}</td>
                  <td className="py-2.5 pr-4 leading-relaxed text-ink-2">{m.scope}</td>
                  <td className="py-2.5 text-right">
                    <Pill tone={m.tone}>{m.status}</Pill>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card
        title="2. The Core Research Problem: Solving the Topology Paradox"
        subtitle="Why naively feeding microservice call-graph neighbors into an LLM judge fails, and how provenance calibration resolves it."
      >
        <div className="grid gap-3.5 md:grid-cols-3">
          {compareCards.map((c) => (
            <div
              key={c.title}
              className="rounded-xl border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)]/55 p-4"
            >
              <div className="flex items-center gap-2">
                <span aria-hidden className="h-2.5 w-2.5 rounded-full" style={{ background: c.color }} />
                <span className="text-[12.5px] font-semibold text-ink">{c.title}</span>
              </div>
              {c.m && (
                <div className="mt-3 grid grid-cols-2 gap-2 text-[11.5px]">
                  <div className="rounded-md bg-surface px-2.5 py-1.5">
                    <div className="text-[10px] text-ink-muted">Precision</div>
                    <div className="font-semibold tabular-nums text-ink">{num(c.m.precision.value, 3)}</div>
                  </div>
                  <div className="rounded-md bg-surface px-2.5 py-1.5">
                    <div className="text-[10px] text-ink-muted">Recall</div>
                    <div className="font-semibold tabular-nums text-ink">{num(c.m.recall.value, 3)}</div>
                  </div>
                  <div className="rounded-md bg-surface px-2.5 py-1.5">
                    <div className="text-[10px] text-ink-muted">F1 Score</div>
                    <div className="font-semibold tabular-nums text-ink">{num(c.m.f1.value, 3)}</div>
                  </div>
                  <div className="rounded-md bg-surface px-2.5 py-1.5">
                    <div className="text-[10px] text-ink-muted">FPR</div>
                    <div className="font-semibold tabular-nums text-ink">{num(c.m.fpr.value, 4)}</div>
                  </div>
                </div>
              )}
              <p className="mt-3 text-[11.5px] leading-relaxed text-ink-2">{c.takeaway}</p>
            </div>
          ))}
        </div>
      </Card>

      <Card
        title="3. System Architecture & Mathematical Formulations"
        subtitle="Exact scoring, retrieval fusion, calibration gating, and root-cause ranking equations implemented in the platform."
      >
        <div className="grid gap-4 lg:grid-cols-2">
          <FormulaBlock
            step="Stage 1"
            title="Unsupervised Telemetry Anomaly Detection"
            formula="score(w) = IForest(x_w) ≥ 0.85"
            variables={[
              ["x_w", "Normalized resource & latency metric vector for service window w"],
              ["0.85", "Candidate threshold calibrated exclusively on dev split normal windows"],
            ]}
            note="Filters raw telemetry into suspicious candidates before invoking expensive LLM calls."
          />

          <FormulaBlock
            step="Stage 2"
            title="Hybrid Topology-Aware Retrieval Fusion"
            formula="S_fusion(e, w) = α · S_BM25(e, w) + β · S_graph(e, w) + γ · S_time(e, w)"
            variables={[
              ["α = 0.35", "Lexical BM25 similarity between anomaly features and telemetry event e"],
              ["β = 0.25", "Normalized call-graph proximity weight (1.0 local, decayer across hops)"],
              ["γ = 0.40", "Temporal closeness exp(−|t_e − t_w| / τ) within ±480 s search window"],
              ["K = 6", "Top-6 fused logs/traces injected into LLM judge context"],
            ]}
            note="Enables cross-service visibility when faults originate downstream and propagate upstream."
          />

          <FormulaBlock
            step="Stage 3"
            title="Calibrated Baseline Evidence Gate (Zero Extra LLM Cost)"
            formula="Keep TRUE_ALERT ⇔ |Cited(w)| ≥ 1  ∧  (origin = local ∨ conf ≥ θ)  ∧  LocalAnchor(w)"
            variables={[
              ["θ = 0.80", "Minimum LLM judge confidence when retrieved evidence includes neighbors"],
              ["LocalAnchor(w)", "∃ e ∈ Context(w) at s_w: (level ∈ {ERROR, WARN}) ∨ (dur(e) > P₉₀^dev(s_w))"],
              ["P₉₀^dev(s)", "Historical 90th-percentile trace duration for service s fit on dev split"],
            ]}
            note="Blocks neighbor-induced hallucinations while keeping genuine faults grounded in local p90 violations."
          />

          <FormulaBlock
            step="Stage 4"
            title="Call-Graph Incident Clustering & 1-Hop Localization"
            formula="Merge(a_i, a_j) ⇔ |t_i − t_j| ≤ 300 s  ∧  Connected_≤1hop(svc_i, svc_j)"
            variables={[
              ["T_group = 300 s", "Temporal correlation horizon grouping confirmed CTAV alerts"],
              ["Rank(s)", "(out_degree_sub == 0, in_degree_sub, max_anomaly(s), count(s))"],
            ]}
            note="Prefers downstream callee leaf services whose failures propagate upstream to callers."
          />
        </div>

        <div className="mt-4 rounded-xl border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)]/55 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-[12px] font-semibold text-ink">
                Evaluated Alternative Modules (Ablation Studies — Validation Split)
              </div>
              <div className="text-[11px] text-ink-muted">
                Every design hypothesis was tested single-factor against CTAV; non-beneficial extensions were isolated cleanly.
              </div>
            </div>
            <Link
              to="/compare"
              className="text-[11.5px] font-medium text-[color:var(--color-seq-550)] hover:underline"
            >
              Inspect Full Ablation Table →
            </Link>
          </div>
          <div className="mt-3 grid gap-2.5 md:grid-cols-3">
            <div className="rounded-lg border border-[color:var(--color-hairline)] bg-surface p-3 text-[11.5px]">
              <div className="font-semibold text-ink">Sub-Threshold Candidate Rescue</div>
              <div className="mt-1 font-mono text-[10.5px] text-ink-2">
                R(w) = η₁·λ_log + η₂·φ_topo + η₃·δ_time ≥ τ
              </div>
              <p className="mt-1.5 text-[11px] text-ink-muted">
                With η = (0, 0.4, 0.6), τ = 0.80: adds +2 TP at the expense of +16 FP; retained strictly as ablation.
              </p>
            </div>
            <div className="rounded-lg border border-[color:var(--color-hairline)] bg-surface p-3 text-[11.5px]">
              <div className="font-semibold text-ink">Rolling 60-Min Span Baseline</div>
              <div className="mt-1 font-mono text-[10.5px] text-ink-2">
                dur(e) &gt; P₉₀^rolling([t − 60m, t))
              </div>
              <p className="mt-1.5 text-[11px] text-ink-muted">
                Covers 93% of spans dynamically, but a ~0.3× lower threshold permits extra false positives compared to fixed dev p90.
              </p>
            </div>
            <div className="rounded-lg border border-[color:var(--color-hairline)] bg-surface p-3 text-[11.5px]">
              <div className="font-semibold text-ink">Two-Tier Escalation Routing</div>
              <div className="mt-1 font-mono text-[10.5px] text-ink-2">
                Escalate BM25 → Topo if conf &lt; 0.95
              </div>
              <p className="mt-1.5 text-[11px] text-ink-muted">
                Tested against single-pass CTAV: increases LLM invocations by +57% without F1 improvement ({ablationRows.length} variants tested).
              </p>
            </div>
          </div>
        </div>
      </Card>

      <Card
        title="4. Glossary of Terminology, Verdicts & Evaluation Metrics"
        subtitle="Quick reference for interpreting badges, confidence intervals, and call-graph statuses across all screens."
      >
        <div className="grid gap-3 md:grid-cols-2">
          {GLOSSARY.map((item) => (
            <div
              key={item.term}
              className="rounded-xl border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)]/45 p-3.5"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-[12.5px] font-semibold text-ink">{item.term}</span>
                <Pill>{item.category}</Pill>
              </div>
              <p className="mt-1.5 text-[11.5px] leading-relaxed text-ink-2">{item.definition}</p>
            </div>
          ))}
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-[color:var(--color-hairline)] pt-3 text-[11px] text-ink-muted">
          <span>
            Evaluated methods tracked: {Object.values(strategyShortLabel).join(" · ")}
          </span>
          <Link to="/timeline" className="font-medium text-[color:var(--color-seq-550)] hover:underline">
            Explore Live Validation Timeline →
          </Link>
        </div>
      </Card>
    </div>
  );
}

function FormulaBlock({
  step,
  title,
  formula,
  variables,
  note,
}: {
  step: string;
  title: string;
  formula: string;
  variables: [string, string][];
  note: string;
}) {
  return (
    <div className="rounded-xl border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)]/45 p-4">
      <div className="flex items-center gap-2">
        <Pill tone="info">{step}</Pill>
        <h3 className="text-[13px] font-semibold text-ink">{title}</h3>
      </div>
      <div className="mt-2.5 overflow-x-auto rounded-lg border border-[color:var(--color-hairline)] bg-surface px-3 py-2 font-mono text-[11.5px] font-medium text-ink">
        {formula}
      </div>
      <dl className="mt-2.5 space-y-1 text-[11px]">
        {variables.map(([sym, desc]) => (
          <div key={sym} className="flex items-baseline gap-2">
            <dt className="min-w-[84px] shrink-0 font-mono font-semibold text-ink-2">{sym}</dt>
            <dd className="text-ink-muted">{desc}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-2.5 border-t border-[color:var(--color-hairline)] pt-2 text-[11px] text-ink-2">
        {note}
      </p>
    </div>
  );
}
