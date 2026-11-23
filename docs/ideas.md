# Ý tưởng bị từ chối hoặc hoãn

> Theo `docs/Final_Thesis_Phase2/06-scope-guard.md` §5: mọi ý tưởng ngoài phạm vi ghi vào
> đây, không xoá. Nguyên liệu cho phần "hướng phát triển" của luận văn và cho GĐ3.

| Ngày | Ý tưởng | Lý do không làm trong GĐ2 | Nguồn |
|---|---|---|---|
| 2026-10-18 | Retrieval `cross_modal` (3 kênh BM25 log/trace/metric + weighted fusion) | Câu hỏi nghiên cứu chuyển sang hiệu chỉnh quyết định trên topology (CTAV); không còn so sánh nhiều retriever; đang trễ ~4 tuần | QĐ-011 |
| 2026-10-18 | Chế độ RRF của `hybrid_bm25_graph` | Như trên; paper và luận văn dùng Weighted Context Fusion | QĐ-011 |
| 2026-10-18 | `temporal` và `graph` như strategy độc lập | Giữ dưới dạng ablation của C1 (β = 1, γ = 1), không cần module riêng | QĐ-011 |
| 2026-10-18 | Causal Span Grounding đầy đủ (chuỗi nhân quả từ metric bất thường tới span ID) | Bản GĐ2 chỉ làm phiên bản rút gọn là evidence anchoring (C3); bản đầy đủ để GĐ3 | Paper §4, QĐ-011 |
| 2026-10-18 | Local-first LLM routing (Ollama + fallback API) làm judge | Phần cứng máy thực nghiệm không đủ; routing tạo biến ẩn (model nào chấm phụ thuộc lỗi/timeout); GĐ1 đo 4/6 lần gọi phải fallback, độ trễ ~13,6× Gemini. Hướng GĐ3 khi có phần cứng | QĐ-013, `08` §4.1 |
| 2026-11-16 | Nâng cấp sâu đồ thị RCA & hiệu chỉnh CTAV tương tác cho GĐ3 (playback sóng lan truyền theo thời gian, click node/cạnh mở drawer xem telemetry + `duration_ms` vs `p90`, bản đồ service toàn hệ thống, và so sánh đồ thị trước/sau cổng hiệu chỉnh CTAV) | GĐ2 giới hạn 4 màn hình cố định và đồ thị 1-hop trên incident (`06-scope-guard.md` §3, QĐ-037); giữ làm điểm nhấn trình diễn và đóng góp hệ thống cho Phase 3 (luận văn tốt nghiệp) | Góp ý người dùng (demo `demo/gh-pages`), M10 |

---

## Phát hiện rà soát codebase (2026-11-22) — nợ kỹ thuật / hướng GĐ3

> Không chặn M11/M12 và **không làm sai lệch kết quả đã đóng băng** (H0–H5, parity 26/26 / 38/38 / 114/114,
> fingerprint `b0c54fa68ef65535`). Đây là danh sách dọn dẹp/hoàn thiện, không phải yêu cầu của mốc hiện tại.
> Chi tiết đầy đủ kèm dẫn chứng: `docs/review-2026-11-22-codebase.md`.

| # | Phát hiện | Mức | Vị trí |
|---|---|---|---|
| 1 | Rescue `evaluate()` sẽ `ValueError` nếu có điểm lưới infeasible (guard `rescued & ~judged` mâu thuẫn `plan()` chỉ union điểm feasible) | Cao (tiềm ẩn) | `eval/harness/rescue.py:186-187,207-211` |
| 2 | Hardcode tham số thí nghiệm: default `__init__` (detector, BM25, C1) + `readers.py` + `h1.py:318` | Trung bình | `services/detector/isolation_forest.py`, `services/retrieval/*`, `services/api/readers.py`, `eval/harness/h1.py`, `packages/schemas/models.py:123-125` |
| 3 | Registry judge chỉ check `startswith("gemini")` → lọt `flash-lite`/`3.x` cho API thật (trái QĐ-021) | Trung bình | `services/judge/registry.py:36-37` |
| 4 | JSON body HTTP tầng transport bị cắt/không hợp lệ không được bắt lỗi | Trung bình | `services/judge/backends.py:263` |
| 5 | `/health` tĩnh; DB down → 500 thô; unpack cột ClickHouse theo vị trí | Trung bình | `services/api/main.py:27-29`, `services/api/readers.py` |
| 6 | Thiếu subcommand `ablation` (lệch AGENTS.md); docstring thiếu `rca` | Trung bình | `eval/__main__.py` |
| 7 | Frontend hardcode nhãn giả thuyết override dữ liệu bảng thực nghiệm | Trung bình | `services/web/src/screens/ExperimentComparison.tsx:169-179` |
| 8 | `m10_pick_demo_cases.py` ghi đè `eval/results/` không chặn | Trung bình | `scripts/m10_pick_demo_cases.py:345-346` |
| 9 | Dead `cross_modal` còn sót (đã cắt QĐ-011) | Thấp | `services/web/src/api/types.ts:19-24`, `mock/fixtures.ts:152`, `theme/tokens.ts:95-117` |
| 10 | Tài liệu/comment lỗi thời (model judge, default T_group, thiết kế local-first) | Thấp | `packages/llm/README.md`, `packages/schemas/models.py:155`, `services/judge/README.md`, `services/rca_agent/grouping.py:10` — **đã sửa phiên này** |
