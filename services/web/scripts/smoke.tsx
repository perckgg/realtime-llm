/**
 * Smoke test: renders all four analytical views in jsdom against the real
 * exported benchmark snapshot and asserts chart marks, tables, and English labels.
 *
 *     npm run smoke
 */

import { JSDOM } from "jsdom";

const dom = new JSDOM("<!doctype html><html><body><div id='root'></div></body></html>", {
  url: "http://localhost/",
  pretendToBeVisual: true,
});

const g = globalThis as unknown as Record<string, unknown>;
g.window = dom.window;
g.document = dom.window.document;
Object.defineProperty(globalThis, "navigator", {
  value: dom.window.navigator,
  configurable: true,
});
g.HTMLElement = dom.window.HTMLElement;
g.SVGElement = dom.window.SVGElement;
g.Element = dom.window.Element;
g.Node = dom.window.Node;
g.getComputedStyle = dom.window.getComputedStyle;
g.requestAnimationFrame = (cb: FrameRequestCallback) => dom.window.setTimeout(() => cb(0), 0);
g.cancelAnimationFrame = (id: number) => dom.window.clearTimeout(id);
g.IS_REACT_ACT_ENVIRONMENT = true;

const BOX = { width: 880, height: 320 };

g.ResizeObserver = class {
  constructor(private cb: ResizeObserverCallback) {}
  observe(target: Element) {
    this.cb(
      [{ target, contentRect: { ...BOX, top: 0, left: 0, bottom: BOX.height, right: BOX.width, x: 0, y: 0 } }] as unknown as ResizeObserverEntry[],
      this as unknown as ResizeObserver,
    );
  }
  unobserve() {}
  disconnect() {}
};
dom.window.Element.prototype.getBoundingClientRect = function () {
  return { ...BOX, top: 0, left: 0, bottom: BOX.height, right: BOX.width, x: 0, y: 0, toJSON() {} };
};
g.DOMMatrixReadOnly = class {
  m22 = 1;
  constructor(_t?: string) {}
};

const { act } = await import("react");
const { createRoot } = await import("react-dom/client");
const { MemoryRouter, Route, Routes } = await import("react-router-dom");
const { RunContext } = await import("@/lib/runContext");
const { runs, listAlerts, listIncidents, getAlertDetail, getIncidentDetail } = await import("@/mock/fixtures");
const Timeline = (await import("@/screens/Timeline")).default;
const AlertDetail = (await import("@/screens/AlertDetail")).default;
const IncidentDetail = (await import("@/screens/IncidentDetail")).default;
const ExperimentComparison = (await import("@/screens/ExperimentComparison")).default;
const MethodologyGuide = (await import("@/screens/MethodologyGuide")).default;

const firstRun = runs[0]!;
const firstAlert = listAlerts(firstRun.run_id).find((a) => a.context_event_count >= 6) ?? listAlerts(firstRun.run_id)[0]!;
const firstIncident =
  listIncidents(firstRun.run_id).find((i) => i.services.length > 1) ?? listIncidents(firstRun.run_id)[0]!;

async function render(path: string, routePath: string, element: React.ReactElement): Promise<string> {
  const container = dom.window.document.createElement("div");
  dom.window.document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(
      <RunContext.Provider value={{ runs, runId: firstRun.run_id, setRunId: () => {} }}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path={routePath} element={element} />
          </Routes>
        </MemoryRouter>
      </RunContext.Provider>,
    );
  });
  await act(async () => {
    await new Promise((r) => setTimeout(r, 500));
  });
  const html = container.innerHTML;
  await act(async () => root.unmount());
  container.remove();
  return html;
}

const CASES: {
  name: string;
  path: string;
  routePath: string;
  element: React.ReactElement;
  expect: [string, (html: string) => boolean][];
}[] = [
  {
    name: "Timeline",
    path: "/timeline",
    routePath: "/timeline",
    element: <Timeline />,
    expect: [
      ["renders stacked verdict bars", (h) => countOf(h, "recharts-bar-rectangle") > 10],
      ["renders ground-truth line", (h) => h.includes("recharts-line-curve")],
      ["renders evaluated alert rows", (h) => countOf(h, "<tr") > 20],
      ["not stuck on loading state", (h) => !h.includes("Loading")],
    ],
  },
  {
    name: "Alert detail",
    path: `/alerts/${firstAlert.alert_id}`,
    routePath: "/alerts/:alertId",
    element: <AlertDetail />,
    expect: [
      ["renders anomaly score area chart", (h) => h.includes("recharts-area-area")],
      ["renders detector threshold marker", (h) => h.includes("Threshold 0.85")],
      ["renders retrieved context events", (h) => countOf(h, "telemetry metadata") >= 6],
      ["not stuck on loading state", (h) => !h.includes("Loading")],
    ],
  },
  {
    name: "Incident detail",
    path: `/incidents/${firstIncident.incident_id}`,
    routePath: "/incidents/:incidentId",
    element: <IncidentDetail />,
    expect: [
      ["renders propagation graph nodes", (h) => countOf(h, "react-flow__node") >= 2],
      ["renders propagation graph edges", (h) => h.includes("react-flow__edge")],
      ["renders diagnostic report root cause", (h) => h.includes("Predicted Root Cause")],
      ["renders accessible call-graph edge table", (h) => h.includes("View Call-Graph Edge Table")],
      [
        "renders interactive node inspector and CTAV diff mode",
        (h) => h.includes("Node Inspector") && h.includes("Before vs. After CTAV Gate (Diff)"),
      ],
    ],
  },
  {
    name: "Experiment comparison",
    path: "/compare",
    routePath: "/compare",
    element: <ExperimentComparison />,
    expect: [
      ["renders metric and latency bar charts", (h) => countOf(h, "recharts-bar-rectangle") >= 20],
      ["renders bootstrap CI error bars", (h) => countOf(h, "recharts-errorBar") >= 20],
      ["renders budget sweep line curves", (h) => countOf(h, "recharts-line-curve") >= 4],
      ["renders baseline reference line", (h) => h.includes("baseline")],
      [
        "renders 5-method benchmark and holdout test confirmation",
        (h) =>
          h.includes("CTAV (Calibrated Topology-Aware Validation)") &&
          h.includes("Confirmed on holdout test split"),
      ],
    ],
  },
  {
    name: "Methodology & Guide",
    path: "/guide",
    routePath: "/guide",
    element: <MethodologyGuide />,
    expect: [
      ["renders thesis milestone table", (h) => h.includes("Phase 3 · CTAV Calibration Policy")],
      ["renders Topology Paradox section", (h) => h.includes("The Core Research Problem: Solving the Topology Paradox")],
      ["renders mathematical formulations", (h) => h.includes("S_fusion(e, w)") && h.includes("LocalAnchor(w)")],
      ["renders terminology glossary", (h) => h.includes("McNemar") && h.includes("Historical p90 Baseline Anchor")],
    ],
  },
];

let failed = 0;
for (const c of CASES) {
  let html = "";
  try {
    html = await render(c.path, c.routePath, c.element);
  } catch (e) {
    failed += 1;
    console.error(`  FAIL  ${c.name} — threw during render\n        ${e instanceof Error ? e.stack : e}`);
    continue;
  }
  if (process.env.SMOKE_DEBUG) console.error(`--- ${c.name} (${html.length} chars)\n${html.slice(0, 800)}\n`);
  for (const [what, check] of c.expect) {
    if (check(html)) {
      console.log(`  ok    ${c.name.padEnd(22)} ${what}`);
    } else {
      failed += 1;
      console.error(`  FAIL  ${c.name.padEnd(22)} ${what}`);
    }
  }
}

for (const run of runs) {
  const alerts = listAlerts(run.run_id);
  const incidents = listIncidents(run.run_id);
  if (!alerts.length || !incidents.length) {
    failed += 1;
    console.error(`  FAIL  snapshot ${run.run_id}: ${alerts.length} alerts, ${incidents.length} incidents`);
  }
  const missAlert = alerts.find((a) => !getAlertDetail(a.alert_id));
  if (missAlert) {
    failed += 1;
    console.error(`  FAIL  snapshot ${run.run_id}: missing AlertDetail for ${missAlert.alert_id}`);
  }
  const missInc = incidents.find((i) => !getIncidentDetail(i.incident_id));
  if (missInc) {
    failed += 1;
    console.error(`  FAIL  snapshot ${run.run_id}: missing IncidentDetail for ${missInc.incident_id}`);
  }
  for (const i of incidents) {
    const det = getIncidentDetail(i.incident_id);
    if (!det) continue;
    for (const node of det.nodes) {
      for (const sid of [...(node.confirmed_alert_ids ?? []), ...(node.suppressed_alert_ids ?? [])]) {
        if (!getAlertDetail(sid)) {
          failed += 1;
          console.error(`  FAIL  snapshot ${run.run_id}: missing linked AlertDetail ${sid} on ${i.incident_id}`);
        }
      }
    }
  }
}
console.log(`  ok    snapshot               ${runs.length} runs verified with full alert, detail, and incident records`);

function countOf(haystack: string, needle: string): number {
  return haystack.split(needle).length - 1;
}

if (failed) {
  console.error(`\n${failed} failures`);
  process.exit(1);
}
console.log("\nAll 5 views (4 analytical screens + Methodology & Guide) rendered cleanly against the benchmark snapshot.");
process.exit(0);
