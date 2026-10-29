# 08 — Giải pháp GĐ2 và kế hoạch chứng minh

> Chốt ngày 2026-10-18 (QĐ-011 trong `docs/experiment-log.md`); **cập nhật 2026-10-29 theo QĐ-027**
> (GVHD đồng ý 2026-10-29: đổi trục C2, C3, H1 sau Phát hiện 7 — xem các khối "Cập nhật QĐ-027"). Đây là tài liệu gốc
> cho câu hỏi "luận văn đề xuất gì và chứng minh bằng cách nào". `00`, `04`, `06` đã
> được cập nhật theo file này; nếu mâu thuẫn, file này thắng và phải sửa file kia.
>
> Nguồn: paper ICAETM 2026 (`C:\Working\Internship1-paper\paper\revision\`), báo cáo
> GĐ1 (`docs/Thesis_Phase1.pdf`), góp ý GVHD (`5_diem_can_sua_chien_luoc_bao_luan_van.docx`),
> review code + kế hoạch ngày 2026-10-18.

---

## 1. Yêu cầu của GVHD

GĐ1 là **thực nghiệm khả thi**. GĐ2 phải **đề xuất một giải pháp và chứng minh giải
pháp đó** — không dừng ở "so sánh vài biến thể RAG xem cái nào tốt hơn". Đồng thời
vẫn phải có **platform chạy được để demo trước hội đồng**.

Luận văn vì vậy có ba phần không tách rời:

| Phần | Vai trò | Ở đâu |
|---|---|---|
| **Vấn đề** | Đã được paper đo và công bố | §2 |
| **Giải pháp + chứng minh** | Đóng góp chính của luận văn | §4, §5 |
| **Platform** | Hiện thực hoá giải pháp end-to-end, là thứ demo | §6 |

---

## 2. Vấn đề — paper ICAETM 2026 đã chỉ ra

**Tên:** *Topology-Guided Evidence Retrieval for Cost-Aware LLM Alert Validation in Microservices.*

**Đóng góp của paper:**

1. **Fusion Score có topology** để xếp hạng bằng chứng:
   `Score = α·BM25_norm + β·exp(−|t_i−t_0|/τ) + γ·GraphSim(s_i, s_0)`, `α+β+γ = 1`, τ = 300 s.
   Cấu hình A4: α = 0.35, β = 0.25, γ = 0.40; mở rộng 2-hop; top-k = 6.
2. **Giao thức đánh giá có kiểm soát chi phí, có cả traffic bình thường:** `paper_500`
   đóng băng (100 fault + 400 normal, 56 service); View A (công bằng retrieval) và View B
   (mức kiến trúc); ngân sách 120 và 489 lần gọi; bootstrap CI + McNemar.
3. **Kết quả hai mặt** (gemini-2.5-flash-lite, temperature 0):

   | | BM25 | Topology |
   |---|---|---|
   | Recall (full budget) | 0.58 | **0.74** |
   | Recall network_delay | 0.375 | **0.70** |
   | Báo động giả / 400 normal | **7** | 137 |
   | F1 (full budget) | **0.703** | 0.476 (McNemar p = 2.61×10⁻¹⁹) |
   | Chi phí API | 1× | 2.7× |
   | F1 @ 120 lần gọi | 0.508 | 0.514 — LLM **không** RAG cao nhất: 0.566 |

**Vấn đề nghiên cứu của luận văn** (rút từ paper):

> Topology giúp LLM thấy bằng chứng mà BM25 bỏ sót (recall ↑), nhưng cũng đưa vào
> telemetry bình thường của service lân cận, khiến LLM xác nhận cả sự cố không tồn tại
> (*thiên lệch xác nhận do ngữ cảnh*). Gần trên đồ thị không có nghĩa là nguyên nhân.
> Retrieval và chính sách quyết định không thể tối ưu tách rời.

Paper tự nhận còn bỏ ngỏ: chưa tách được nguyên nhân thiên lệch (khối lượng, thứ tự hay
prompt); chạy một lần; trọng số chọn có nhìn `paper_500`; truy vấn BM25 lỡ chứa tag fault
type; chỉ thẩm định cảnh báo, chưa RCA. Hướng tiếp paper đã hứa: Asymmetric Confidence
Gating, Causal Span Grounding, Adaptive Multi-Tier Routing.

> **Cập nhật QĐ-027 (2026-10-29; GVHD đồng ý).** Trên giao thức GĐ2, H0 tái lập **hiện tượng**
> (topology tăng recall +0,10 và FPR +0,025 so với BM25, McNemar có ý nghĩa) nhưng **không tái lập
> cơ chế**: hiệu ứng không đến từ bằng chứng của service lân cận (C1-quota ≡ C1-paper) mà từ việc C1
> chọn bằng chứng cục bộ sát thời điểm cửa sổ (chủ yếu trace span); judge xác nhận 30–42% candidate
> normal có bằng chứng (QĐ-026, Phát hiện 7). Vấn đề nghiên cứu được phát biểu lại là **thiên lệch
> xác nhận theo nội dung bằng chứng**: judge xác nhận sự cố khi đọc telemetry bình thường của chính
> service bị cảnh báo, và cách chọn bằng chứng (độ gần thời gian, loại bằng chứng) làm mức thiên lệch
> thay đổi. Mục tiêu GĐ2 (§3) giữ nguyên.

---

## 3. GĐ1 → paper → GĐ2

| | GĐ1 (Thực tập 1) | Paper ICAETM | GĐ2 (luận văn) |
|---|---|---|---|
| Bản chất | Thực nghiệm khả thi | Phát hiện vấn đề | **Giải pháp + chứng minh + platform** |
| Câu hỏi | Kiến trúc lai có chạy? LLM có cần ngữ cảnh? | Topology có giúp thẩm định cảnh báo? | Giữ recall của topology mà không bị thiên lệch xác nhận, trong ngân sách? Dùng nó để định vị root cause? |
| Kết quả | Chạy được; Context Rescue tăng recall nhưng tốn | Recall ↑, FP ×19.6, F1 ↓ | CTAV vượt BM25 có ý nghĩa thống kê trên `test` chưa nhìn |
| Judge | Phase 4/5 dùng **judge giả (mock)** | LLM thật | LLM thật, cache bắt buộc |
| Dữ liệu | Cửa sổ 120 s; tập 300/500 | `paper_500` | Split mới dev/val/test, cửa sổ 60 s, nhãn wall-clock (QĐ-002..004) |
| Đầu ra cho SRE | Nhãn từng cảnh báo | Nhãn từng cảnh báo | Incident + root cause + báo cáo JSON có bằng chứng, xem trên dashboard |

**Mục tiêu GĐ2 (một câu):**

> Đề xuất và chứng minh **CTAV**, một phương pháp thẩm định cảnh báo có nhận biết
> topology, được hiệu chỉnh theo nguồn gốc bằng chứng: giữ mức tăng recall của topology
> mà không làm tăng báo động giả so với BM25 trong cùng ngân sách LLM; dùng CTAV làm
> nền cho tác tử RCA định vị service gốc; hiện thực hoá cả hai trên một platform chạy
> được để demo.

---

## 4. Giải pháp: CTAV — Calibrated Topology-Aware Alert Validation

```text
AlertCandidate (detector, + Rescue Score)
   │
   ▼  Tầng 1: BM25 (bằng chứng cục bộ, rẻ)
   │   └─ judge ─► TRUE/FP đủ chắc + bằng chứng neo ─► quyết định
   │                    │ UNCERTAIN / thiếu bằng chứng
   ▼  Tầng 2 (C4): Fusion Score topology (C1) ─► judge
   │
   ▼  Chính sách quyết định
       C2: ngưỡng theo nguồn gốc bằng chứng  θ_topo > θ_local
       C3: TRUE_ALERT phải trích bằng chứng bất thường tại s0 (QĐ-027)
   │
   ▼  JudgedAlert ─► RCA Agent (grouping → propagation → summary)
```

| # | Thành phần | Giải quyết điểm yếu nào của paper | Hiện thực |
|---|---|---|---|
| C1 | **Fusion Score topology** — giữ nguyên công thức paper | Recall thấp của BM25 (network_delay) | `services/retrieval/hybrid_bm25_graph.py`, port từ `legacy/src/phase2/retrieval/` |
| C2 | **Asymmetric Confidence Gating** — ~~theo nguồn gốc đồ thị~~ (QĐ-027): ngưỡng bất đối xứng theo **hồ sơ bằng chứng** judge trích — tầng sinh ra (BM25 / C1), độ gần thời gian, loại (trace / log); hồ sơ rủi ro cần `confidence ≥ θ_topo > θ_local`; đặc trưng cụ thể chốt sau H1 | FP tăng khi chọn bằng chứng sát thời điểm (Phát hiện 7) | `services/judge/policy.py`; chạy trên verdict đã cache — không tốn thêm lần gọi LLM |
| C3 | **Evidence anchoring** (QĐ-027) — TRUE_ALERT phải trích ít nhất một bằng chứng **bất thường** tại `s_0`: log mức lỗi, hoặc span có `duration_ms` vượt ngưỡng nền của cùng service + operation (phân vị tính trên `dev`); không thì hạ xuống UNCERTAIN. Biến thể phụ: span lỗi/chậm trên đường gọi tới `s_0` | Judge xác nhận 30–42% normal có bằng chứng (Phát hiện 7) | `services/judge/policy.py`; mở rộng `require_evidence` sẵn có |
| C4 | **Adaptive Two-Tier Routing** — chạy BM25 trước; chỉ mở rộng topology khi tầng 1 UNCERTAIN hoặc không có bằng chứng | Chi phí ×2.7 | `services/judge/routing.py` |
| C5 | **Rescue Score** (η1, η2, η3, τ) — đưa cửa sổ detector bỏ sót vào pipeline | Detector bỏ sót | Đã có trong kế hoạch, giữ nguyên công thức QĐ-008 |
| B | **RCA Agent** — grouping theo thời gian + topology → backward propagation → báo cáo JSON | SRE cần biết sự cố nào, gốc ở đâu | `services/rca_agent/`; Nezha có nhãn root-cause mức pod 100% (QĐ-001) ⇒ Hit@k hợp lệ (điểm 4 của GVHD) |

**Ký hiệu:** ngưỡng gating dùng **θ_local, θ_topo** (paper viết η_topo/η_local — đổi để
không trùng η1..η3 của Rescue Score, QĐ-008). Fusion Score giữ α, β, γ.

**Biến thể retrieval bị thu gọn** (QĐ-011): không còn "so sánh 5 biến thể". Còn lại:
- `bm25_hybrid` — baseline.
- `hybrid_bm25_graph` (C1) — topology chưa hiệu chỉnh = phương pháp của paper.
- `temporal` và `graph` thuần trở thành **ablation của C1** (β = 1, γ = 1 trong lưới α, β, γ), không còn là module riêng.
- `cross_modal` và RRF bị cắt, ghi vào `docs/ideas.md`.

### 4.1 Judge: một LLM API cố định, không chạy LLM local (QĐ-013)

> **Cập nhật QĐ-021 (2026-10-19):** judge của mọi thực nghiệm GĐ2 là `gemini-2.5-flash`
> (cùng thế hệ, lớn hơn flash-lite), temperature 0, `thinkingBudget: 0`, cùng prompt; mọi câu
> trả lời phải có `modelVersion` đúng model này, lệch thì run dừng. `gemini-2.5-flash-lite`
> chỉ còn dùng để phát lại cache của paper (G-paper). Các lập luận dưới đây (một model cố
> định, không local-first, không fallback) giữ nguyên.

**Quyết định.** Mọi thực nghiệm chính dùng **một** model API cố định:
`gemini-2.5-flash-lite`, temperature 0, cùng prompt. Không có local-first, không có
fallback sang model khác. LLM local (Ollama) không chạy trong GĐ2.

**Lý do — trình bày được trước hội đồng:**

1. **Judge là biến cố định của thiết kế thực nghiệm.** Câu hỏi nghiên cứu nằm ở retrieval
   và chính sách quyết định (C1–C4), không ở LLM. Muốn quy chênh lệch kết quả cho C2/C3/C4
   thì judge phải giống hệt nhau ở mọi cấu hình (`06` §4: không đổi backend giữa chừng).
2. **Local-first tạo ra một biến ẩn.** Với routing local → API, model nào chấm một alert
   phụ thuộc vào việc model local có lỗi/timeout/thiếu tự tin hay không. Hai cấu hình
   CTAV khác nhau có thể bị chấm bởi hai tổ hợp model khác nhau, nên không còn so sánh có
   kiểm soát, cũng không tái lập được.
3. **So sánh được với paper.** Baseline khoa học (G-paper, H0) là kết quả của paper, đo
   bằng `gemini-2.5-flash-lite`. Dùng cùng model mới tái lập được paper từ cache (cache
   hit 100% là điều kiện của G-paper) và mới nói được "CTAV giải quyết đúng vấn đề paper chỉ ra".
4. **GĐ1 đã đo: model local nhỏ chưa đủ làm judge chính** (báo cáo GĐ1 §4.7.5, §4.8.4,
   qwen2.5:1.5b qua Ollama, 45 cửa sổ):

   | | Gemini-only | Local-first |
   |---|---|---|
   | F1 | 0.800 | 0.769 |
   | Lần gọi phải chuyển sang Gemini | — | 4/6 (3 do `local_error`) |
   | Độ trễ LLM trung bình | 338 ms | 4.585 ms (~13,6×) |

   Kết luận chính GĐ1 đã viết: model local "chưa thể thay thế hoàn toàn API bên ngoài" và
   "không nên diễn giải Local-first như một chiến lược tăng tốc".
5. **Phần cứng.** Máy thực nghiệm không đủ tài nguyên chạy model local đủ lớn với hàng
   nghìn lần gọi mỗi run, song song với ClickHouse/Postgres. Model ≤ 3B chạy được thì lại
   rơi vào điểm 4.
6. **Chi phí API thấp và kiểm soát được.** Paper đo được ≈ 0,00013 USD mỗi lần chấm với
   BM25 và ≈ 0,00034 USD với topology (0,0628 và 0,1669 USD cho 489 lần chấm). Chi phí
   một run ≈ số candidate × đơn giá — đo số candidate thật trên `val` ở mốc M2 rồi ghi
   ngân sách vào experiment-log. Policy C2/C3 chạy lại trên verdict đã cache, không tốn
   thêm lần gọi nào.
7. **Không có rủi ro riêng tư dữ liệu.** Lý do phổ biến nhất để chạy LLM local trong
   doanh nghiệp là không gửi log ra ngoài. Nezha là benchmark công khai, nên lý do này
   không áp dụng cho luận văn.

**Rủi ro của việc phụ thuộc API, và cách giảm:**

| Rủi ro | Cách giảm |
|---|---|
| Model bị đổi/ngừng cung cấp | Ghi chính xác model id + phiên bản API trả về trong mỗi bản ghi; cache lưu nguyên response ⇒ chạy lại luận văn không cần API |
| Không hoàn toàn tất định dù temperature 0 | Cache theo key cố định; đo phương sai riêng (xem dưới) |
| Giới hạn tốc độ gọi, lỗi mạng | Giới hạn số lần gọi/phút, retry có trần (`tenacity`); hết retry ⇒ `manual_review`, ghi log, như chính sách của paper |
| Demo lúc bảo vệ không có mạng | Demo chạy offline hoàn toàn từ cache (§6) |
| Hội đồng hỏi "sao không local?" | 7 lý do ở trên; local-first được báo cáo như kết quả GĐ1 và hướng GĐ3 |

**Hệ quả cho cache và phương sai.** Với temperature 0 và cache, "3 lần chạy" trả về đúng
cùng một kết quả, nên không đo được phương sai. Key cache vì vậy thêm trường `repeat`
(mặc định 0): kết quả chính dùng `repeat = 0`; phương sai đo trên một tập con với
`repeat ∈ {0, 1, 2}` để thực sự gọi lại API. Bootstrap CI vẫn là thước đo bất định chính.

**Local-first trong luận văn:** trình bày như kết quả của GĐ1 (khả thi về vận hành, chưa
đủ tin cậy làm judge chính) và là hướng GĐ3 khi có phần cứng. Ghi vào `docs/ideas.md`.

---

## 5. Cách chứng minh

"Chứng minh" = **giả thuyết viết trước** + **kiểm định trên `test` chưa nhìn** + **loại
trừ giải thích khác** + **từng thành phần đều cần thiết**. Không phải chạy rồi thấy số đẹp.

### 5.1 Giả thuyết

Chốt bản cuối vào `experiment-log.md` (mục "Đăng ký giả thuyết") **trước khi chạm `test`**.
Ngưỡng định lượng (Δ tối thiểu, θ) điền sau khi có số liệu `val`, không sửa sau khi chạy `test`.

| | Giả thuyết | Thí nghiệm | Kiểm định | Bác bỏ khi |
|---|---|---|---|---|
| **H0** tái lập vấn đề | Trên split GĐ2, topology chưa hiệu chỉnh tăng recall nhưng tăng FPR so với BM25 | BM25 vs C1, cùng judge, cùng ngân sách | Bootstrap CI ΔRecall, ΔFPR; McNemar | Không tái lập ⇒ viết lại câu chuyện (vấn đề không tổng quát) |
| **H1** cơ chế (QĐ-027) | Tỷ lệ TRUE_ALERT trên normal tăng theo **độ gần thời gian** và **loại bằng chứng** (trace), không phải do số lượng hay thứ tự | Trên mẫu cố định của `val`: giữ k = 6, thay (i) tỷ lệ event trong ±60 s quanh t₀ 0/33/67/100%, (ii) trace ↔ log, (iii) xáo thứ tự; nhánh tỷ lệ lân cận 0/100% làm đối chứng âm | Xu hướng đơn điệu + CI | Không có quan hệ ⇒ C2 mất cơ sở (C3 vẫn kiểm được ở H3), báo cáo trung thực |
| **H2** giải pháp | CTAV: recall ≥ C1 − δ và FPR không tệ hơn BM25 có ý nghĩa ⇒ F1(CTAV) > F1(BM25) | CTAV vs BM25 vs C1 vs LLM-không-RAG vs detector-only | McNemar cặp; CI ΔF1 | CI ΔF1 chứa 0 |
| **H3** từng thành phần | Bỏ C2 ⇒ FPR tăng; bỏ C3 ⇒ precision giảm; bỏ C4 ⇒ chi phí tăng mà F1 không tăng | Ablation một-thành-phần-một-lần trên `val`, xác nhận trên `test` | CI từng Δ | Thành phần không đóng góp ⇒ bỏ khỏi phương pháp, ghi lại |
| **H4** chi phí | Ở ngân sách 120 lần gọi, CTAV ≥ LLM-không-RAG; đường cong F1 theo ngân sách của CTAV trội | Quét ngân sách | CI | |
| **H5** RCA | Tác tử RCA đạt Hit@1 ≥ 0.60, Hit@3 ≥ 0.80, vượt baseline "service có anomaly score cao nhất"; Alert Reduction ≥ 30% trên cascade | Trên incident của `test` | CI bootstrap | |

### 5.2 Kỷ luật thực nghiệm để kết luận đứng vững

- Tuning chỉ trên `val`; `test` chạy **đúng một lần**, sau đăng ký giả thuyết (QĐ-005).
- Cùng judge, cùng prompt, cùng temperature cho mọi so sánh (`06` §4: không đổi LLM giữa chừng).
- Phương sai do LLM: ≥ 3 lần gọi lại thật (`repeat ∈ {0, 1, 2}`, §4.1) trên tập con, báo cáo độ lệch (paper mới chạy một lần).
- Không mang lỗi rò tag fault type vào truy vấn BM25 (paper §3.5) — có unit test chặn.
- Đường cong độ nhạy θ_topo và đường cong ngân sách, không chỉ một điểm.
- Phân tích ca sai: FP còn lại của CTAV thuộc loại nào, vì sao.
- Mọi bảng/hình sinh bằng script trong `eval/`, không vẽ tay.

### 5.3 Ba cổng chặn để chứng minh có giá trị

| Cổng | Khi nào | Điều kiện | Ý nghĩa |
|---|---|---|---|
| G-port | M2 | Pipeline GĐ2 tái lập đúng GĐ1 Phase 4 (judge mock, `paper_300`) | Code port đúng |
| G-paper | M3 | Tái lập View A của paper trên `paper_500` bằng cache Gemini | Baseline khoa học đúng |
| G-test | M8 | Chạm `test` một lần, sau đăng ký giả thuyết | Kết luận hợp lệ |

Chi tiết từng mốc: `04-implementation-roadmap.md`.

---

## 6. Platform demo trước hội đồng

Platform **là hiện thực của CTAV**, không phải sản phẩm riêng: cùng một pipeline chạy
thực nghiệm và chạy demo (`01` §1).

```text
Replayer → Detector (+Rescue) → CTAV (BM25 → topology khi cần → policy C2/C3)
        → RCA Agent → ClickHouse/Postgres → API → Dashboard 4 màn hình
```

**Dashboard 4 màn hình** (MVP đã có trên dữ liệu giả, QĐ-007; còn phải nối dữ liệu thật):

| Màn hình | Cho hội đồng thấy gì về CTAV |
|---|---|
| Timeline | Luồng alert theo thời gian, màu theo verdict và tầng routing |
| Alert detail | Top-k bằng chứng, hồ sơ bằng chứng (tầng, thời gian, loại, bất thường hay không), vì sao bị gating/anchoring hạ xuống |
| Incident detail | Đồ thị lan truyền, root cause, báo cáo JSON |
| Experiment comparison | Bảng H0–H4: BM25 vs topology vs CTAV, có CI |

**Kịch bản demo 5 phút:**
1. `docker compose --profile dev up -d` → replay chạy, alert vào Timeline.
2. Mở một alert normal mà topology chưa hiệu chỉnh xác nhận nhầm → CTAV hạ xuống vì judge chỉ dựa trên telemetry bình thường của `s_0`, không có bằng chứng bất thường để neo (C3, QĐ-027).
3. Mở một network_delay mà BM25 bỏ sót → tầng 2 topology tìm được span chậm ở downstream, CTAV xác nhận (C1/C4).
4. Cascade fault → nhiều alert gom thành một Incident → đồ thị lan truyền chỉ đúng root cause.
5. Tab Experiment → bảng so sánh sinh tự động từ `eval/results/`.

Platform phải chạy được **hoàn toàn offline từ cache** (không phụ thuộc mạng/API key
lúc bảo vệ).

---

## 7. Đầu ra cuối cùng của GĐ2

1. **Luận văn** (Word): vấn đề (paper) → CTAV + RCA → chứng minh H0–H5 → hạn chế, hướng GĐ3.
2. **Phần mềm tái lập được:** một lệnh dựng môi trường; `py -m eval run --config ...` sinh
   `eval/results/<run_id>/`; repo công khai; người lạ clone chạy lại được bảng kết quả.
3. **Số liệu:** bảng H0–H5 trên `test` có CI + McNemar; ablation C2–C4; đường cong θ_topo
   và ngân sách; ablation Rescue Score + đường cong τ; Hit@1/Hit@3, Alert Reduction, JSON
   valid rate; chi phí, độ trễ, cache hit; chấm tay context precision (50 window) và chất
   lượng chẩn đoán (30 incident).
4. **Demo:** platform + dashboard 4 màn hình + kịch bản 5 phút, chạy offline.
5. **Tùy chọn:** bản mở rộng của paper (journal) với H1–H4.

---

## 8. Việc phải sửa ở mốc M1

Kết quả review 2026-10-18 (cũng có trong `docs/milestones/M0-nen-tang.md` §2). Đã đưa vào `docs/CURRENT-MILESTONE.md`.

### 8.1 Code detector (từ M0)

| # | Việc | Vị trí | Cần quyết định? |
|---|---|---|---|
| D1 | Detector điền 0.0 vào metric NaN mà loader đã cố tình bỏ — 4.164/19.316 cửa sổ dev (21,6%) | `services/detector/isolation_forest.py:64` | Có — cách điền thay thế |
| D2 | Lịch sử buffer không liên tục: 19% cặp liền kề cách > 60 s; 18/138 cửa sổ fault (gần như mọi cửa sổ khởi phát) có lịch sử từ ≥ 10 phút trước do vùng đệm 600 s (QĐ-004). Đề xuất: replayer phát lịch sử liên tục, split chỉ lọc cửa sổ được chấm | `isolation_forest.py:126,148`, `nezha_source.py` | Có |
| D3 | `score()` có trạng thái ẩn (đẩy buffer); gọi hai lần là hỏng lịch sử | `isolation_forest.py:148` | Không |
| D4 | mypy không chạy được (`python_version = "3.11"`, máy dùng 3.14); ruff 11 lỗi | `pyproject.toml:48` | Không |
| D5 | Chạy lại `replay_smoke.py` cùng `run_id` ⇒ nhân đôi dòng ClickHouse | `scripts/replay_smoke.py:33` | Không |
| D6 | Nhỏ: buffer theo service không theo pod; `packages` import từ `scripts`; `buffer_size`/cách fit chưa có trong config | | Không |

### 8.2 Cấu hình và tài liệu

- `eval/configs/bm25_baseline.yaml` khác GĐ1 Phase 4 ở ngưỡng (0.85 vs 0.95), cách fit
  (toàn dev vs 1.000 cửa sổ đầu), judge (LLM thật vs mock), gate (không có vs 0.80/0.98,
  30 lần gọi), tập cửa sổ (dev đầu tiên vs `paper_300`). Tách thành `gd1_phase4_parity.yaml`
  (cho G-port) và `paper_viewA_replay.yaml` (cho G-paper) — QĐ-012.
- 4 file `legacy/` sửa chưa commit; cache `legacy/outputs/test_results/*_cache_*.jsonl`
  chưa ignore; `front_matter.txt`, `refs_sample.txt`, `toc_out.txt` ở gốc repo.
- `CURRENT-WEEK.md` đã thay bằng `docs/CURRENT-MILESTONE.md`; bản mẫu trống trong `Final_Thesis_Phase2/` đã xoá (QĐ-014).

---

## 9. Quyết định còn mở

| # | Câu hỏi | Mặc định nếu không có ý kiến khác | Hạn |
|---|---|---|---|
| ~~Q1~~ | ~~Judge chính~~ | **Đã chốt 2026-10-18 (QĐ-013):** `gemini-2.5-flash-lite` qua API, không local, không fallback — §4.1 | — |
| ~~Q2~~ | ~~Toàn split hay tập cố định~~ | **Đã chốt 2026-10-19 (QĐ-017):** chỉ số chính trên cửa sổ có telemetry (có file log/trace Nezha trong ±8 phút); toàn split là số phụ | — |
| ~~Q3~~ | ~~D1~~ | **Đã chốt 2026-10-18:** giá trị gần nhất của cùng pod + cột chỉ báo thiếu | — |
| ~~Q4~~ | ~~D2~~ | **Đã chốt 2026-10-18:** có — split chỉ quyết định cửa sổ nào được chấm | — |
| Q5 | Mốc bảo vệ (M12) có cố định không? | Cố định, tuần 2027-02-08 | Ngay |
