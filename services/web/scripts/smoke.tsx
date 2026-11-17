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
      ["có biểu đồ cột", (h) => countOf(h, "recharts-bar-rectangle") > 10],
      ["có đường nhãn ground truth", (h) => h.includes("recharts-line-curve")],
      ["có bảng cảnh báo", (h) => countOf(h, "<tr") > 20],
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
      ["có thẻ chính sách CTAV", (h) => h.includes("Chính sách quyết định CTAV")],
      ["có đủ 6 sự kiện ngữ cảnh", (h) => countOf(h, "debug") >= 6],
      ["không kẹt ở trạng thái tải", (h) => !h.includes("Đang tải")],
    ],
  },
  {
    name: "Incident detail",
    path: `/incidents/${firstIncident.incident_id}`,
    routePath: "/incidents/:incidentId",
    element: <IncidentDetail />,
    expect: [
      ["có node đồ thị", (h) => countOf(h, "react-flow__node") >= 3],
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
      ["có biểu đồ cột 5 phương pháp", (h) => countOf(h, "recharts-bar-rectangle") >= 20],
      ["có thanh sai số CI", (h) => countOf(h, "recharts-errorBar") >= 15],
      ["có đường cong ngân sách H4", (h) => countOf(h, "recharts-line-curve") >= 4],
      ["có đủ giả thuyết H0–H5", (h) => ["H0", "H1", "H2", "H3", "H4", "H5"].every((k) => h.includes(k))],
      ["có số đo CTAV test thật (0.066)", (h) => h.includes("0.066")],
      ["có bảng H5 RCA", (h) => h.includes("C3-trượt (test — độ nhạy)")],
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
