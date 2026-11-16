/**
 * Kiểm tra khói: render thật cả bốn màn hình trong jsdom trên dữ liệu thực nghiệm
 * trích từ `eval/results/`, rồi soi HTML kết quả.
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
      ["có biểu đồ cột", (h) => countOf(h, "recharts-bar-rectangle") > 10],
      ["có đường nhãn ground truth", (h) => h.includes("recharts-line-curve")],
      ["có bảng cảnh báo thật", (h) => countOf(h, "<tr") > 20],
      ["không kẹt ở trạng thái tải", (h) => !h.includes("Đang tải")],
    ],
  },
  {
    name: "Alert detail",
    path: `/alerts/${firstAlert.alert_id}`,
    routePath: "/alerts/:alertId",
    element: <AlertDetail />,
    expect: [
      ["có biểu đồ vùng", (h) => h.includes("recharts-area-area")],
      ["có ngưỡng detector", (h) => h.includes("ngưỡng 0.85")],
      ["có sự kiện ngữ cảnh", (h) => countOf(h, "debug") >= 6],
      ["không kẹt ở trạng thái tải", (h) => !h.includes("Đang tải")],
    ],
  },
  {
    name: "Incident detail",
    path: `/incidents/${firstIncident.incident_id}`,
    routePath: "/incidents/:incidentId",
    element: <IncidentDetail />,
    expect: [
      ["có node đồ thị", (h) => countOf(h, "react-flow__node") >= 2],
      ["có cạnh đồ thị", (h) => h.includes("react-flow__edge")],
      ["có báo cáo chẩn đoán", (h) => h.includes("root_cause_service")],
      ["có bảng thay thế cho đồ thị", (h) => h.includes("Xem dạng bảng")],
    ],
  },
  {
    name: "Experiment comparison",
    path: "/compare",
    routePath: "/compare",
    element: <ExperimentComparison />,
    expect: [
      ["có 4 panel chỉ số + latency", (h) => countOf(h, "recharts-bar-rectangle") >= 20],
      ["có thanh sai số CI", (h) => countOf(h, "recharts-errorBar") >= 20],
      ["có đường ngân sách H4", (h) => countOf(h, "recharts-line-curve") >= 4],
      ["có vạch baseline", (h) => h.includes("baseline")],
      ["bảng đủ 5 phương pháp & H3 & H0 test", (h) => h.includes("CTAV (C1 + θ 0,80 + C3 dev p90)") && h.includes("H0 được chấp nhận")],
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
    console.error(`  FAIL  ${c.name} — ném lỗi khi render\n        ${e instanceof Error ? e.stack : e}`);
    continue;
  }
  if (process.env.SMOKE_DEBUG) console.error(`--- ${c.name} (${html.length} ký tự)\n${html.slice(0, 800)}\n`);
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
    console.error(`  FAIL  snapshot ${run.run_id}: ${alerts.length} alert, ${incidents.length} sự cố`);
  }
  const missAlert = alerts.find((a) => !getAlertDetail(a.alert_id));
  if (missAlert) {
    failed += 1;
    console.error(`  FAIL  snapshot ${run.run_id}: thiếu AlertDetail cho ${missAlert.alert_id}`);
  }
  const missInc = incidents.find((i) => !getIncidentDetail(i.incident_id));
  if (missInc) {
    failed += 1;
    console.error(`  FAIL  snapshot ${run.run_id}: thiếu IncidentDetail cho ${missInc.incident_id}`);
  }
}
console.log(`  ok    snapshot               ${runs.length} run đều đủ alert, detail và incident`);

function countOf(haystack: string, needle: string): number {
  return haystack.split(needle).length - 1;
}

if (failed) {
  console.error(`\n${failed} lỗi`);
  process.exit(1);
}
console.log("\nBốn màn hình render được trên snapshot thật, biểu đồ có vẽ ra mark, bảng có dữ liệu.");
process.exit(0);
