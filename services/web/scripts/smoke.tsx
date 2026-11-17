/**
 * Kiểm tra khói: render thật cả bốn màn hình trong jsdom, chờ dữ liệu về, rồi
 * soi HTML kết quả.
 *
 * Không thay cho việc mở trình duyệt — nó không thấy được bố cục, màu sắc hay
 * chồng chữ. Việc nó bắt được là loại lỗi hay xảy ra nhất khi sửa fixture hoặc
 * schema: một màn hình ném lỗi lúc chạy, một biểu đồ không vẽ ra mark nào, một
 * bảng rỗng. `tsc` không bắt được những lỗi đó.
 *
 * Dùng jsdom chứ không dùng `renderToString` vì `useAsync` nạp dữ liệu trong
 * `useEffect`, mà react-dom/server không chạy effect — render phía server sẽ
 * dừng mãi ở trạng thái "đang tải" và không đụng tới phần biểu đồ.
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
// Node 24 định nghĩa `navigator` là getter-only nên phải ghi đè bằng
// defineProperty thay vì gán thẳng.
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
g.__USE_MOCK__ = true;

const BOX = { width: 880, height: 320 };

// Recharts và react-flow đo container để biết vẽ to bao nhiêu. jsdom trả về 0
// cho mọi phép đo, nên nếu không giả lập thì biểu đồ render ra khung rỗng và bài
// kiểm tra này sẽ chẳng khẳng định được gì.
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
const { runs, listAlerts, listIncidents } = await import("@/mock/fixtures");
const { policySteps } = await import("@/lib/util");
const Timeline = (await import("@/screens/Timeline")).default;
const AlertDetail = (await import("@/screens/AlertDetail")).default;
const IncidentDetail = (await import("@/screens/IncidentDetail")).default;
const ExperimentComparison = (await import("@/screens/ExperimentComparison")).default;

const firstRun = runs[0]!;
const firstAlert = listAlerts(firstRun.run_id)[0]!;
const firstIncident = listIncidents(firstRun.run_id)[0]!;

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
  // Nguồn mock trả kết quả sau 120 ms. Lần `act` thứ hai này mới là lần nhận
  // dữ liệu: lần đầu chỉ dựng cây và chạy effect, promise chưa kịp về.
  await act(async () => {
    await new Promise((r) => setTimeout(r, 500));
  });
  const html = container.innerHTML;
  await act(async () => root.unmount());
  container.remove();
  return html;
}

/** Mỗi màn hình phải chứa những dấu hiệu này thì mới coi là render thật. */
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
      ["renders stacked bar chart", (h) => countOf(h, "recharts-bar-rectangle") > 10],
      ["renders ground-truth curve", (h) => h.includes("recharts-line-curve")],
      ["renders alert rows", (h) => countOf(h, "<tr") > 20],
      ["not stuck loading", (h) => !h.includes("Loading")],
    ],
  },
  {
    name: "Alert detail",
    path: `/alerts/${firstAlert.alert_id}`,
    routePath: "/alerts/:alertId",
    element: <AlertDetail />,
    expect: [
      ["renders metric area chart", (h) => h.includes("recharts-area-area")],
      ["renders detector threshold", (h) => h.includes("threshold 0.85")],
      ["renders CTAV policy card", (h) => h.includes("CTAV Decision Policy")],
      ["renders 6 context events", (h) => countOf(h, "debug") >= 6],
      ["not stuck loading", (h) => !h.includes("Loading")],
    ],
  },
  {
    name: "Incident detail",
    path: `/incidents/${firstIncident.incident_id}`,
    routePath: "/incidents/:incidentId",
    element: <IncidentDetail />,
    expect: [
      ["renders graph nodes", (h) => countOf(h, "react-flow__node") >= 3],
      ["renders graph edges", (h) => h.includes("react-flow__edge")],
      ["renders diagnostic report", (h) => h.includes("root_cause_service")],
      ["renders table fallback", (h) => h.includes("View as table")],
    ],
  },
  {
    name: "Experiment comparison",
    path: "/compare",
    routePath: "/compare",
    element: <ExperimentComparison />,
    expect: [
      ["renders 5-method bar chart", (h) => countOf(h, "recharts-bar-rectangle") >= 20],
      ["renders 95% CI error bars", (h) => countOf(h, "recharts-errorBar") >= 15],
      ["renders H4 budget curve", (h) => countOf(h, "recharts-line-curve") >= 4],
      ["renders H0–H5 hypotheses", (h) => ["H0", "H1", "H2", "H3", "H4", "H5"].every((k) => h.includes(k))],
      ["renders H1 partially retained", (h) => h.includes("Partially retained")],
      ["renders H5 0/4 criteria", (h) => h.includes("Rejected (0/4 criteria)") && h.includes("Alert Reduction ≥ 30% on cascade incidents")],
      ["renders real CTAV test F1 (0.066)", (h) => h.includes("0.066")],
      ["renders H5 RCA table", (h) => h.includes("C3-rolling (test — sensitivity)")],
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
    console.error(`  FAIL  ${c.name} — error during render\n        ${e instanceof Error ? e.stack : e}`);
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

// Verify 4 cases of pure `policySteps` matching `services/judge/policy.py::decide`.
const policyCases: [string, Parameters<typeof policySteps>[0], string][] = [
  [
    "raw FALSE_POSITIVE",
    {
      raw_verdict: "FALSE_POSITIVE",
      verdict: "FALSE_POSITIVE",
      downgraded_by_evidence_rule: false,
      downgraded_by_gating: false,
      downgraded_by_anchoring: false,
    },
    "N/A (stopped at raw_verdict ≠ TRUE_ALERT)",
  ],
  [
    "evidence rule downgrade",
    {
      raw_verdict: "TRUE_ALERT",
      verdict: "UNCERTAIN",
      downgraded_by_evidence_rule: true,
      downgraded_by_gating: false,
      downgraded_by_anchoring: false,
    },
    "N/A (stopped at evidence rule)",
  ],
  [
    "C3 anchoring downgrade",
    {
      raw_verdict: "TRUE_ALERT",
      verdict: "UNCERTAIN",
      downgraded_by_evidence_rule: false,
      downgraded_by_gating: false,
      downgraded_by_anchoring: true,
    },
    "downgraded",
  ],
  [
    "final TRUE_ALERT",
    {
      raw_verdict: "TRUE_ALERT",
      verdict: "TRUE_ALERT",
      downgraded_by_evidence_rule: false,
      downgraded_by_gating: false,
      downgraded_by_anchoring: false,
    },
    "anchored",
  ],
];
for (const [label, input, expectedAnchoring] of policyCases) {
  const actual = policySteps(input).anchoring.label;
  if (actual === expectedAnchoring) {
    console.log(`  ok    policySteps            ${label} -> ${actual}`);
  } else {
    failed += 1;
    console.error(`  FAIL  policySteps            ${label}: got "${actual}", want "${expectedAnchoring}"`);
  }
}

// Fixture của MỌI run, không chỉ run đầu — để bắt lỗi chỉ lộ ra ở một biến thể.
for (const run of runs) {
  const nAlerts = listAlerts(run.run_id).length;
  const nIncidents = listIncidents(run.run_id).length;
  if (!nAlerts || !nIncidents) {
    failed += 1;
    console.error(`  FAIL  fixture ${run.run_id}: ${nAlerts} alert, ${nIncidents} sự cố`);
  }
}
console.log(`  ok    fixture                ${runs.length} run đều sinh được dữ liệu`);

function countOf(haystack: string, needle: string): number {
  return haystack.split(needle).length - 1;
}

if (failed) {
  console.error(`\n${failed} lỗi`);
  process.exit(1);
}
console.log("\nBốn màn hình render được, biểu đồ có vẽ ra mark, bảng có dữ liệu.");
process.exit(0);
