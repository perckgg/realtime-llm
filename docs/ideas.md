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
