import { useState } from "react";
import { Link } from "react-router-dom";
import rawExperimentTable from "@/data/experiment_table.json";
import { Card, Pill, STATIC_DEMO_STEPS, StatTile } from "@/components/ui";
import { cx, num } from "@/lib/util";
import { series, status } from "@/theme/tokens";

type SplitKey = "test" | "val";
type CiPair = [number, number];

interface MethodRow {
  key: string;
  label: string;
  tp: number;
  fp: number;
  fn: number;
  tn: number;
  precision: number;
  precision_ci95: CiPair;
  recall: number;
  recall_ci95: CiPair;
  f1: number;
  f1_ci95: CiPair;
  fpr: number;
  fpr_ci95: CiPair;
  llm_calls: number | null;
  estimated_cost_usd: number | null;
}

interface RcaRow {
  run_id: string;
  label: string;
  split: string;
  incidents: number;
  labelled: number;
  hit1: number;
  hit1_count: number;
  hit3: number;
  hit3_count: number;
  arr_all: number;
  summary_valid: number;
  summary_incidents: number;
}

interface GuideExperimentData {
  methods: Record<SplitKey, { windows: number; fault_windows: number; methods: MethodRow[] }>;
  ablation: Record<SplitKey, { variants: MethodRow[] }>;
  rca: RcaRow[];
}

const DATA = rawExperimentTable as unknown as GuideExperimentData;

const HYPOTHESIS_GUIDE = [
  {
    id: "H0",
    scope: "Topology Paradox (C1 vs. BM25 on holdout test, 11,985 windows)",
    finding:
      "Uncalibrated C1 raises Recall (+0.179 [+0.138; +0.226]) but inflates FPR (+0.0744 [+0.0694; +0.0798]); both McNemar tests p < 0.001.",
    status: "Accepted (4/4)",
    tone: "good" as const,
  },
  {
    id: "H1",
    scope: "Mechanism attribution (validation controlled subset)",
    finding:
      "C1 recall gain on fault windows comes primarily from temporally proximal trace/metric evidence rather than distant neighbor logs.",
    status: "Partial (val)",
    tone: "info" as const,
  },
  {
    id: "H2",
    scope: "Main CTAV claim (CTAV vs. BM25 & C1 on holdout test)",
    finding:
      "FPR drops 5.8× vs. BM25 (ΔFPR −0.0262) and 19.3× vs. C1, but fixed dev-p90 anchoring cuts Recall on shifted test traffic (ΔF1 −0.025 [−0.067; +0.014]).",
    status: "Rejected (1/3)",
    tone: "warn" as const,
  },
  {
    id: "H3",
    scope: "Component ablations (C2 gating, C3 anchoring, C4 routing, C5 rescue)",
    finding:
      "C3 anchoring drives the Precision gain (removing C3 drops Precision −0.107 [−0.197; −0.030]); C2 (ΔFPR 0.0000) and C4 (+66% cost, ΔF1 −0.001) confirmed dropped.",
    status: "Accepted",
    tone: "good" as const,
  },
  {
    id: "H4",
    scope: "Low-budget regime (120 LLM calls on holdout test)",
    finding:
      "Point-estimate F1(CTAV) = 0.034 [0.011; 0.064] exceeds LLM-no-RAG = 0.017 [0.000; 0.038] under strict budget.",
    status: "Accepted (point)",
    tone: "good" as const,
  },
  {
    id: "H5",
    scope: "RCA Agent on CTAV-grouped incidents (holdout test)",
    finding:
      "Hit@1 = Hit@3 = 8/17 (0.471), ΔHit@1 = 0.000 vs. baseline, 0/50 cascade injections under strict CTAV; schema-valid JSON reports 38/38 (100%).",
    status: "Rejected (0/4)",
    tone: "warn" as const,
  },
];

const GLOSSARY = [
  {
    term: "Confirmed Alert (TRUE_ALERT)",
    category: "Verdict",
    definition:
      "Positive classification retained only when the LLM judge cites at least one context event AND local service telemetry passes the C3 Baseline Anchoring gate.",
  },
  {
    term: "Suppressed / Uncertain (UNCERTAIN)",
    category: "Verdict",
    definition:
      "Ambiguous or downgraded candidate. Includes alerts initially predicted as TRUE_ALERT from neighbor context that failed either the Evidence Rule or C3 Local Anchoring.",
  },
  {
    term: "Precision = TP / (TP + FP)",
    category: "Metric",
    definition:
      "Fraction of Confirmed Alerts that align with ground-truth injected faults. Directly governs SRE signal-to-noise ratio.",
  },
  {
    term: "Recall = TP / (TP + FN)",
    category: "Metric",
    definition:
      "Fraction of all ground-truth fault windows surfaced as Confirmed Alerts across the split.",
  },
  {
    term: "False Positive Rate (FPR) = FP / (FP + TN)",
    category: "Metric",
    definition:
      "Probability of raising a false alarm on normal traffic windows. Lower values indicate stronger protection against neighbor-induced false alarms.",
  },
  {
    term: "C3 Local Baseline Anchor (P₉₀^dev)",
    category: "CTAV Policy",
    definition:
      "Per-service 90th-percentile trace span duration computed strictly on the dev split, paired with local ERROR/WARN log checks. Blocks neighbor noise at zero extra LLM cost.",
  },
  {
    term: "95% Bootstrap Confidence Interval",
    category: "Statistics",
    definition:
      "Non-parametric CI95 over 1,000 stratified paired bootstrap resamples (seed 42). Differences whose CI crosses 0 are not claimed as improvements.",
  },
  {
    term: "McNemar's Paired Test",
    category: "Statistics",
    definition:
      "Paired significance test comparing two validators on identical telemetry windows by counting discordant predictions separately on fault and normal subsets.",
  },
];

const METHOD_COLOR = {
  bm25: series[0],
  c1: series[4],
  ctav: series[2],
} as const;

function findMethod(split: SplitKey, key: string): MethodRow | undefined {
  return DATA.methods[split].methods.find((m) => m.key === key);
}

export default function MethodologyGuide() {
  const [split, setSplit] = useState<SplitKey>("test");

  const testBm25 = findMethod("test", "bm25");
  const testC1 = findMethod("test", "c1");
  const testCtav = findMethod("test", "ctav");
  const testRca = DATA.rca.find((r) => r.run_id === "rca_final_test_v1");

  const bm25 = findMethod(split, "bm25");
  const c1 = findMethod(split, "c1");
  const ctav = findMethod(split, "ctav");
  const splitWindows = DATA.methods[split].windows;
  const splitFaults = DATA.methods[split].fault_windows;

  const fprRatioC1 =
    testC1 && testCtav ? testC1.fpr / Math.max(0.00001, testCtav.fpr) : null;
  const fprRatioBm25 =
    testBm25 && testCtav ? testBm25.fpr / Math.max(0.00001, testCtav.fpr) : null;

  const compareCards = [
    {
      key: "bm25",
      title: "BM25 Lexical RAG (Baseline)",
      color: METHOD_COLOR.bm25,
      m: bm25,
      takeaway:
        split === "test"
          ? "Local-only lexical retrieval: moderate FPR (0.0317) and higher F1 (0.091) than strict CTAV on test, but misses cross-service anomalies caught by C1."
          : "Local-only lexical retrieval: lower FPR than C1 (0.0561 vs. 0.0816) on validation, but lower Recall (0.163) and F1 (0.103).",
    },
    {
      key: "c1",
      title: "Uncalibrated Topology RAG (C1)",
      color: METHOD_COLOR.c1,
      m: c1,
      takeaway:
        split === "test"
          ? "The Topology Paradox (H0 confirmed, p < 0.001): lifts Recall to 0.277 (96 TP), but leaks neighbor anomalies into 1,235 normal windows (FPR 0.1061)."
          : "Raises Recall to 0.263 (55 TP), but floods operators with 606 false positives (FPR 0.0816, Precision 0.083).",
    },
    {
      key: "ctav",
      title: "CTAV (C1 + C3 Anchoring)",
      color: METHOD_COLOR.ctav,
      m: ctav,
      takeaway:
        split === "test"
          ? "Cuts FPR 19.3× vs. C1 (0.0055) and raises Precision 2.5× (0.179), but fixed dev-p90 anchoring drops Recall to 0.040 on shifted test traffic (H2 rejected)."
          : "On validation, cuts FPR 11.9× vs. C1 (0.0069), raises Precision 4.4× (0.363), and reaches F1 0.201 without extra LLM calls.",
    },
  ];

  const ablationCount = DATA.ablation.test.variants.length;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-[20px] font-semibold tracking-tight text-ink">
              Methodology, Mathematical Formulations &amp; Committee Guide
            </h1>
            <Pill tone="info">Thesis Reference</Pill>
          </div>
          <p className="mt-1 max-w-3xl text-[12px] leading-relaxed text-ink-muted">
            Self-contained technical walkthrough explaining{" "}
            <strong className="font-semibold text-ink">
              CTAV (Calibrated Topology-Aware Alert Validation)
            </strong>{" "}
            and the downstream <strong className="font-semibold text-ink">RCA Agent</strong>:
            implemented scoring equations, zero-cost provenance calibration rules, pre-registered
            H0–H5 outcomes (including negative results), and interactive walkthrough links across
            validation (7,636 windows) and holdout test (11,985 windows).
          </p>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {STATIC_DEMO_STEPS.filter((h) => h.pathMatch !== "/guide").map((h) => (
            <Link
              key={h.step}
              to={h.to}
              title={h.title}
              className="rounded-lg border border-[color:var(--color-hairline)] bg-surface px-2.5 py-1.5 text-[11px] font-medium text-ink-2 transition-colors hover:border-[color:var(--color-seq-550)] hover:text-ink"
            >
              {h.step}. {h.label} →
            </Link>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3.5 md:grid-cols-4">
        <StatTile
          label="Test · FPR Reduction (C1 → CTAV)"
          value={fprRatioC1 ? `${fprRatioC1.toFixed(1)}× lower` : "—"}
          hint={
            testC1 && testCtav && fprRatioBm25
              ? `${num(testC1.fpr, 4)} → ${num(testCtav.fpr, 4)} (${fprRatioBm25.toFixed(1)}× vs. BM25)`
              : ""
          }
          accent={status.good}
        />
        <StatTile
          label="Test · Precision (C1 → CTAV)"
          value={
            testC1 && testCtav ? `${num(testC1.precision, 3)} → ${num(testCtav.precision, 3)}` : "—"
          }
          hint="2.5× higher Precision on test (4.4× on val: 0.083 → 0.363)"
          accent={METHOD_COLOR.ctav}
        />
        <StatTile
          label="Hypotheses H0–H5 (Test)"
          value="3 Pass · 1 Part · 2 Rej"
          hint="H0, H3, H4 accepted; H1 partial (val); H2 & H5 rejected"
          accent={METHOD_COLOR.c1}
        />
        <StatTile
          label="RCA Agent (Test · H5)"
          value={
            testRca
              ? `${testRca.hit1_count} / ${testRca.labelled} (${num(testRca.hit1, 3)})`
              : "—"
          }
          hint={
            testRca
              ? `${testRca.summary_valid}/${testRca.summary_incidents} JSON valid · ARR ${num(testRca.arr_all, 3)}`
              : ""
          }
          accent={METHOD_COLOR.bm25}
        />
      </div>

      <Card
        title="1. Pre-Registered Hypothesis Outcomes (H0–H5)"
        subtitle="All thresholds and policy choices were frozen on dev/val before running the holdout test split once. Both positive and negative outcomes are reported verbatim."
        right={
          <Link
            to="/compare"
            className="text-[11.5px] font-medium text-[color:var(--color-seq-550)] hover:underline"
          >
            Open Full H0–H5 Tables &amp; CI95 →
          </Link>
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[12px]">
            <thead>
              <tr className="border-b border-[color:var(--color-hairline)] text-left text-[11px] font-semibold tracking-wide text-ink-muted uppercase">
                <th className="py-2 pr-4">ID</th>
                <th className="py-2 pr-4">Registered Scope</th>
                <th className="py-2 pr-4">Observed Result</th>
                <th className="py-2 text-right">Verdict</th>
              </tr>
            </thead>
            <tbody>
              {HYPOTHESIS_GUIDE.map((h) => (
                <tr
                  key={h.id}
                  className="border-b border-[color:var(--color-hairline)] last:border-0"
                >
                  <td className="py-2.5 pr-4 font-mono font-semibold whitespace-nowrap text-ink">
                    {h.id}
                  </td>
                  <td className="py-2.5 pr-4 font-medium text-ink">{h.scope}</td>
                  <td className="py-2.5 pr-4 leading-relaxed text-ink-2">{h.finding}</td>
                  <td className="py-2.5 text-right">
                    <Pill tone={h.tone}>{h.status}</Pill>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card
        title="2. The Core Research Problem: The Topology Paradox & Calibration Trade-off"
        subtitle={`Comparing BM25, Uncalibrated Topology RAG (C1), and CTAV on ${split === "test" ? "Holdout Test" : "Validation"} (${splitWindows.toLocaleString("en-US")} windows, ${splitFaults} fault windows).`}
        right={
          <div className="inline-flex rounded-lg border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)] p-0.5 text-[11px]">
            {(
              [
                ["test", "Holdout Test (11,985)"],
                ["val", "Validation (7,636)"],
              ] as const
            ).map(([k, label]) => (
              <button
                key={k}
                type="button"
                onClick={() => setSplit(k)}
                className={cx(
                  "rounded-md px-2.5 py-1 font-medium transition-all",
                  split === k ? "bg-surface text-ink shadow-xs" : "text-ink-muted hover:text-ink",
                )}
              >
                {label}
              </button>
            ))}
          </div>
        }
      >
        <div className="grid gap-3.5 md:grid-cols-3">
          {compareCards.map((c) => (
            <div
              key={c.key}
              className="rounded-xl border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)]/55 p-4"
            >
              <div className="flex items-center gap-2">
                <span
                  aria-hidden
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ background: c.color }}
                />
                <span className="text-[12.5px] font-semibold text-ink">{c.title}</span>
              </div>
              {c.m && (
                <div className="mt-3 grid grid-cols-2 gap-2 text-[11.5px]">
                  <div className="rounded-md bg-surface px-2.5 py-1.5">
                    <div className="text-[10px] text-ink-muted">Precision</div>
                    <div className="font-semibold tabular-nums text-ink">
                      {num(c.m.precision, 3)}
                    </div>
                  </div>
                  <div className="rounded-md bg-surface px-2.5 py-1.5">
                    <div className="text-[10px] text-ink-muted">Recall</div>
                    <div className="font-semibold tabular-nums text-ink">
                      {num(c.m.recall, 3)}
                    </div>
                  </div>
                  <div className="rounded-md bg-surface px-2.5 py-1.5">
                    <div className="text-[10px] text-ink-muted">F1 Score</div>
                    <div className="font-semibold tabular-nums text-ink">{num(c.m.f1, 3)}</div>
                  </div>
                  <div className="rounded-md bg-surface px-2.5 py-1.5">
                    <div className="text-[10px] text-ink-muted">FPR (TP / FP)</div>
                    <div className="font-semibold tabular-nums text-ink">
                      {num(c.m.fpr, 4)}{" "}
                      <span className="text-[10px] font-normal text-ink-muted">
                        ({c.m.tp}/{c.m.fp})
                      </span>
                    </div>
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
        subtitle="Exact scoring, C1 retrieval fusion, C3 anchoring policy, and backward 1-hop RCA equations implemented in the platform."
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
            note="Filters raw telemetry into suspicious candidates before invoking Gemini 2.5 Flash (temperature 0, deterministic SHA-256 cache)."
          />

          <FormulaBlock
            step="Stage 2"
            title="C1 Hybrid Topology-Aware Retrieval Fusion"
            formula="S_fusion(e, w) = 0.35 · S_BM25(e, w) + 0.25 · S_time(e, w) + 0.40 · 1 / (1 + d(s_e, s_w))"
            variables={[
              ["α = 0.35", "Normalized lexical BM25 similarity between anomaly query and event e"],
              ["β = 0.25", "Temporal proximity weight within the candidate search horizon"],
              ["γ = 0.40", "Call-graph distance decay 1 / (1 + d) across hop band d ≤ 2"],
              ["K = 6", "Top-6 fused logs/traces passed to the LLM judge (see Alert Detail C1 card)"],
            ]}
            note="Graph search defines the ≤ 2-hop candidate scope; Fusion Score decides which local and neighbor events enter the prompt."
          />

          <FormulaBlock
            step="Stage 3"
            title="CTAV Decision Policy (Evidence Rule + C3 Anchoring)"
            formula="Keep TRUE_ALERT ⇔ raw = TRUE_ALERT  ∧  |Cited(w)| ≥ 1  ∧  LocalAnchor(w)"
            variables={[
              ["|Cited(w)| ≥ 1", "Evidence rule: empty judge citations downgrade directly to UNCERTAIN"],
              ["LocalAnchor(w)", "∃ e ∈ Context(w) at s_w: (level ∈ {ERROR, WARN}) ∨ (dur(e) > P₉₀^dev(s_w))"],
              ["P₉₀^dev(s)", "Per-service 90th-percentile trace duration frozen on dev (zero extra LLM cost)"],
            ]}
            note="C2 confidence gating (θ_topo = 0.85) was ablated and dropped because the judge outputs confidence ≥ 0.90 on almost all alerts."
          />

          <FormulaBlock
            step="Stage 4"
            title="RCA Agent: Grouping & Backward 1-Hop Localization"
            formula="Cluster(a_i, a_j) ⇔ |t_i − t_j| ≤ 180 s  ·  Vote(s) → alerted callees(s) else {s}"
            variables={[
              ["T_group = 180 s", "Temporal gap threshold grouping confirmed alerts into incidents"],
              ["Backward 1-hop", "Each alerted service blames its direct alerted callees; leaf alerted services blame themselves"],
              ["Summary JSON", "Structured diagnostic report (root cause, timeline, actions) — 38/38 schema-valid on test"],
            ]}
            note="Interactive step-through verification is embedded directly in every Incident Detail screen."
          />
        </div>

        <div className="mt-4 rounded-xl border border-[color:var(--color-hairline)] bg-[color:var(--color-plane)]/55 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-[12px] font-semibold text-ink">
                Evaluated Alternative Modules &amp; Negative Results (H3 Ablations — Holdout Test)
              </div>
              <div className="text-[11px] text-ink-muted">
                Every component was tested single-factor against CTAV ({ablationCount} ablation
                variants); non-beneficial modules were cleanly excluded from the final pipeline.
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
              <div className="font-semibold text-ink">C5 · Sub-Threshold Candidate Rescue</div>
              <div className="mt-1 font-mono text-[10.5px] text-ink-2">
                R(w) = η₁·λ_log + η₂·φ_topo + η₃·δ_time ≥ τ
              </div>
              <p className="mt-1.5 text-[11px] text-ink-muted">
                With η = (0, 0.4, 0.6), τ = 0.80 on test: ΔRecall +0.000, ΔFPR +0.0001 across +61
                extra LLM calls — no net gain.
              </p>
            </div>
            <div className="rounded-lg border border-[color:var(--color-hairline)] bg-surface p-3 text-[11.5px]">
              <div className="font-semibold text-ink">C3-Rolling · 60-Min Span Baseline</div>
              <div className="mt-1 font-mono text-[10.5px] text-ink-2">
                dur(e) &gt; P₉₀^rolling([t − 60m, t))
              </div>
              <p className="mt-1.5 text-[11px] text-ink-muted">
                Recovers Recall (+0.095) and F1 (+0.054) under test drift, at the cost of higher
                FPR (+0.0281). Retained as sensitivity line (outside H5 registration).
              </p>
            </div>
            <div className="rounded-lg border border-[color:var(--color-hairline)] bg-surface p-3 text-[11.5px]">
              <div className="font-semibold text-ink">C4 · Two-Tier Escalation Routing</div>
              <div className="mt-1 font-mono text-[10.5px] text-ink-2">
                Escalate BM25 → C1 if conf &lt; 0.95
              </div>
              <p className="mt-1.5 text-[11px] text-ink-muted">
                Tested against single-pass CTAV on test: increases API cost from $8.16 to $13.56
                (+66%) with ΔF1 = −0.001 — confirmed dropped.
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
            Evaluated validators: Detector-only · LLM-no-RAG · BM25 Baseline · C1 Topology · CTAV
            (C1 + C3)
          </span>
          <Link
            to="/timeline?run_id=pipeline_test_v2"
            className="font-medium text-[color:var(--color-seq-550)] hover:underline"
          >
            Explore Holdout Test Timeline →
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
            <dt className="min-w-[92px] shrink-0 font-mono font-semibold text-ink-2">{sym}</dt>
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
