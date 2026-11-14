# Sườn báo cáo luận văn GĐ2 — CTAV và tác tử RCA

> Bản nháp sườn, dựng theo cấu trúc luận văn GĐ1 (`docs/Thesis_Phase1.pdf`) và template `docs/Template_LuanVan.docx`.
> Trạng thái mốc (cập nhật 2026-11-14): M7 đã đóng, H0–H5 **đã đăng ký 2026-11-14** (QĐ-034: δ = 0,05; C5 chỉ là ablation; chấm toàn bộ candidate trên `test`); M8 đang chạy. Mọi số `test` = [CHỜ M8] trừ khi mục ghi khác. Số liệu hiện có đều trên `val`/`dev`, kèm nguồn.

## Quy ước

- `[TÁI SỬ DỤNG GĐ1 §x]`: lấy lại và rút gọn từ luận văn GĐ1 · `[MỚI]`: nội dung GĐ2.
- ✅ đã có dữ liệu/hiện thực · ⏳ chờ mốc Mx · ✂️ đã loại khỏi phương pháp chính (giữ làm ablation) · [CẦN TRA CỨU]: trích dẫn chưa xác minh.
- Ký hiệu: τ_F = hằng số thời gian của Fusion Score (300 s); τ = ngưỡng của Rescue Score.
- Judge GĐ2: `gemini-2.5-flash` (QĐ-021, QĐ-023); `gemini-2.5-flash-lite` chỉ dùng để phát lại cache paper (G-paper).

## Đối chiếu cấu trúc với GĐ1 / template

| GĐ1 (template) | GĐ2 (sườn này) | Ghi chú |
|---|---|---|
| Ch1 Giới thiệu đề tài | Ch1 Giới thiệu đề tài | thêm câu hỏi nghiên cứu, đóng góp |
| Ch2 Cơ sở lý thuyết | Ch2 Cơ sở lý thuyết | bỏ local-first, học sâu; thêm topology, calibration, RCA, kiểm định |
| Ch3 Công trình liên quan | Ch3 Công trình liên quan | thêm graph RCA, GraphRAG, calibration judge |
| Ch4 Thực nghiệm (§4.3–4.4 chứa kiến trúc) | Ch4 Phương pháp đề xuất + Ch5 Thực nghiệm | tách phương pháp thành chương riêng |
| — | Ch6 Demo platform | [MỚI] |
| Ch5 Định hướng phát triển | Ch7 Thảo luận, hạn chế, hướng phát triển | |
| Ch6 Kết luận | Ch8 Kết luận | |

> Template quy định 6 chương; nếu khoa bắt buộc đúng 6, gộp Ch6 Demo vào Ch5 (mục "Hiện thực và demo") và Ch7 vào "Định hướng phát triển".


> Căn cứ: `docs/Template_LuanVan.docx` + bìa/mục lục/danh sách hình–bảng của GĐ1 (`phase1.txt` tr.1–6).
> Template chỉ có: trang hướng dẫn (xoá trước khi nộp), bìa, MỤC LỤC, Danh sách hình, Danh sách bảng, các chương (Heading 1/2/3) và "Tài liệu tham khảo". Các mục khác bên dưới là **bổ sung chuẩn luận văn** — đánh dấu "(ngoài template)"; hỏi GVHD/khoa nếu cần bỏ.

## Phần đầu (front matter)

### 0. Các phần bắt buộc theo template

| # | Phần | Ghi chú template | Trạng thái |
|---|---|---|---|
| 0 | Trang "HƯỚNG DẪN SỬ DỤNG TEMPLATE - XÓA TRANG NÀY TRƯỚC KHI NỘP" | Xoá | ✅ nhắc xoá |
| 1 | Bìa: ĐHQG-HCM / Trường ĐH Bách Khoa / Khoa KH&KT Máy tính / `[MÃ MÔN / HỌC KỲ]` / tên đề tài / Ngành: KHMT / GVHD: Võ Thị Ngọc Châu / HVTH: Nguyễn Văn Hoàng Khang 2570754 / `TP.HCM - [THÁNG]/[NĂM]` | GĐ1 ghi "BÁO CÁO THỰC TẬP 1"; GĐ2 đổi theo mã môn luận văn | ⏳ M12 |
| 2 | MỤC LỤC (TOC cấp 1–3, trường tự động) | Heading 1–3 | ⏳ M12 |
| 3 | Danh sách hình | Heading 1 | ⏳ M12 |
| 4 | Danh sách bảng | Heading 1; caption style "Caption": "Bảng N. …" | ⏳ M12 |
| 5 | Chương (Heading 1) → mục (Heading 2) → tiểu mục (Heading 3) | Template: 1 Giới thiệu đề tài · 2 Cơ sở lý thuyết · 3 Công trình liên quan · 4 Thực nghiệm · 5 Định hướng phát triển · 6 Kết luận | GĐ2: xem `parts/ch6-8.md` |
| 6 | Tài liệu tham khảo (Heading 1, cuối) | | ⏳ M12 |

Quy ước: đánh số "1.2.1"; chỗ hình `[Chèn hình minh họa tại đây]`; caption bảng ở trên bảng.

### 1. Trang bìa
- Giữ khối đầu của template; tên đề tài GĐ2 cập nhật theo hướng CTAV + RCA (chờ GVHD chốt, không tự đổi).
- HVTH + MSHV; GVHD; tháng/năm (bản chốt dự kiến ~2027-02-06, roadmap M12).
> Nguồn: Template_LuanVan.docx; 04 §M12. ⏳ M12.

### 2. Lời cam đoan (ngoài template)
- Công trình do tác giả thực hiện dưới hướng dẫn GVHD; kết quả sinh từ script `eval/`, tái lập được.
- Phần kế thừa GĐ1/paper ICAETM 2026 ghi nguồn; `test` split chỉ chạy một lần.
- Ký tên, ngày tháng. ⏳ M12 (văn bản chuẩn của khoa).

### 3. Lời cảm ơn (ngoài template)
- GVHD, khoa, đồng tác giả paper (nếu có), cộng đồng bộ dữ liệu Nezha, gia đình/bạn bè. ⏳ M12.

### 4. Tóm tắt (tiếng Việt, ≤ 1 trang)
- Bối cảnh: phát hiện bất thường tạo nhiều cảnh báo; LLM thẩm định cần ngữ cảnh (RAG).
- Vấn đề (paper ICAETM 2026, GĐ1): ngữ cảnh topology tăng recall nhưng tăng báo động giả so với BM25.
- Đề xuất **CTAV**: thành phần còn lại sau ablation là C1 (retrieval topology) + C3 (evidence anchoring); C2, C4 bị bỏ; C5 (Rescue) không thuộc phương pháp chính, chỉ là một điểm ablation (V34 (b), QĐ-034).
- Tác tử RCA (grouping → propagation → báo cáo JSON) + platform demo offline.
- Phương pháp: Nezha, split dev/val/test theo lần tiêm lỗi, giả thuyết H0–H5 viết trước, bootstrap CI + McNemar, `test` chạy một lần.
- Kết quả `val`: CTAV F1 0,201, FPR 0,0069 (BM25 0,103 / 0,056; C1 0,126 / 0,082); recall 0,139 < C1 0,263. Kết quả `test`, H5: `[CHỜ M8, M10]`.
- Hạn chế chính; từ khoá: AIOps, RCA, LLM-as-a-Judge, RAG, topology.
> Nguồn: 08 §1–5; QĐ-026, QĐ-031, QĐ-033. ⏳ M12 (số `test` điền sau). Không dùng số mock.

### 5. Abstract (English, ≤ 1 trang)
- Dịch sát phần 4; giữ CTAV, BM25, FPR; ghi rõ "validation-split estimates" tới khi có `test`.
- Keywords: AIOps; root cause analysis; alert validation; LLM-as-a-Judge; retrieval-augmented generation; service topology. ⏳ M12.

### 6. Mục lục
- Gồm: cam đoan, cảm ơn, tóm tắt, abstract, danh mục từ viết tắt, danh sách hình/bảng, Chương 1–8, tài liệu tham khảo, phụ lục. Cập nhật trường sau khi chốt. ⏳ M12.

### 7. Danh sách hình
Kế thừa GĐ1 (hình 1–8: sliding window; khoảng trống ngữ nghĩa; kiến trúc giám sát lai; định tuyến local-first `[chỉ giữ nếu còn ở Ch2/4]`; tiền xử lý metric; tiền xử lý log/trace; watermark; post-processing RCA). Bổ sung GĐ2:
- Kiến trúc platform (Replayer → Detector → CTAV → RCA → DB → API → Dashboard).
- Sơ đồ CTAV hai tầng (BM25 → C1 → C3).
- Split dev/val/test; đường θ_topo; đường F1 theo ngân sách (H4); đường τ Rescue.
- 4 ảnh chụp dashboard `[⏳ M10]`; đồ thị lan truyền incident.
> [TÁI SỬ DỤNG GĐ1] + ⏳ sinh từ script ở M12.

### 8. Danh sách bảng
Kế thừa GĐ1 (bảng 1–5: nguồn telemetry; định dạng output LLM; công trình liên quan; dataset; dữ liệu đầu ra tầng thẩm định). Bổ sung GĐ2:
- H0 `val` (QĐ-026) và `test` `[⏳ M8]`; đăng ký giả thuyết H0–H5; H1 (QĐ-028); H3 ablation (M6-5); H2 so baseline (M6-6); H4 theo ngân sách (M6-7); Rescue (M7-1, M7-2).
- RCA Hit@1/Hit@3/ARR/JSON valid `[⏳ M9–M10]`; đánh giá bằng người `[⏳ M11]`; chi phí/độ trễ/cache hit.
> [TÁI SỬ DỤNG GĐ1] + ✅ `val` / ⏳ `test`.

### 9. Danh mục từ viết tắt (ngoài template)
- AIOps — Artificial Intelligence for IT Operations
- ARR — Alert Reduction Ratio
- BFS — Breadth-First Search
- BM25 — Best Matching 25 (xếp hạng từ khoá)
- C1…C5 — thành phần CTAV (C1 retrieval topology; C2 gating θ_topo; C3 evidence anchoring; C4 routing; C5 Rescue Score)
- CI — Confidence Interval (bootstrap 95%)
- CTAV — Calibrated Topology-Aware Alert Validation
- FN/FP/TN/TP — âm/dương giả, âm/dương thật
- FPR — False Positive Rate
- GĐ1/GĐ2 — Giai đoạn 1 (thực tập) / 2 (luận văn)
- G-port, G-paper, G-test — cổng chặn kiểm chứng (M2, M3, M8)
- GVHD, HVTH — giảng viên hướng dẫn, học viên thực hiện
- Hit@k — root cause đúng nằm trong top-k
- IForest — Isolation Forest
- JSON — JavaScript Object Notation
- LLM — Large Language Model
- M0…M12 — cột mốc kế hoạch (QĐ-014)
- Nezha — bộ dữ liệu microservice có nhãn root cause
- QĐ — Quyết định (đánh số trong `docs/experiment-log.md`)
- RAG — Retrieval-Augmented Generation
- RCA — Root Cause Analysis
- Rescue — Context Rescue / Rescue Score
- θ, θ_local, θ_topo, τ, η, δ — ngưỡng/trọng số/biên
- dev / val / test — tập debug / tuning / kiểm định cuối
> ⏳ M12 (rà theo từ thực sự xuất hiện; GĐ1 và template không có mục này).

### 10. Thứ tự lắp ráp (đề xuất)
Bìa → Lời cam đoan → Lời cảm ơn → Tóm tắt → Abstract → Mục lục → Danh sách hình → Danh sách bảng → Danh mục từ viết tắt → Chương 1–8 → Tài liệu tham khảo → Phụ lục; đánh số La Mã cho phần trước Chương 1. ⏳ M12.

---


> Chú giải: **[TÁI SỬ DỤNG GĐ1 §x, rút gọn]** = lấy từ báo cáo GĐ1 và rút gọn · **[MỚI]** = viết mới cho GĐ2 · ✅ có dữ liệu · ⏳ chờ mốc · **[CHỜ M8]** = số liệu trên `test`, chưa được chạm (QĐ-005).
> Số liệu `val` lấy từ `docs/experiment-log.md` / `docs/CURRENT-MILESTONE.md`; số `test` để trống đến khi qua G-test (M8).

---

## Chương 1 — Giới thiệu đề tài

### 1.1 Bối cảnh đề tài

#### 1.1.1 Từ giám sát đến vận hành AIOps trên microservice [TÁI SỬ DỤNG GĐ1 §1.1, rút gọn]
- Hệ microservice sinh khối lượng lớn metric/log/trace; quá tải cảnh báo làm SRE khó tìm sự cố thật.
- Detector không giám sát (Isolation Forest) cho recall nhưng nhiều báo động giả; cần tầng thẩm định.
- Rút gọn: giữ 1–2 đoạn dẫn nhập, bỏ mô tả server/cloud chi tiết của GĐ1.

> Nguồn: `Thesis_Phase1.pdf` §1.1 (`phase1.txt` tr.7); `06-scope-guard.md` §1. Trạng thái: ✅

#### 1.1.2 Kết quả GĐ1 và paper ICAETM 2026 — động lực của GĐ2 [MỚI]
- GĐ1: kiến trúc lai (detector + RAG + LLM-as-a-Judge) chạy được; judge Phase 4/5 là **mock**, nên số GĐ1 không dùng làm kết luận khoa học.
- Paper ICAETM 2026 (`gemini-2.5-flash-lite`, `paper_500`: 100 fault + 400 normal): BM25 F1 0,703 / 7 FP; Topology F1 0,476 / 137 FP; recall 0,58 → 0,74; chi phí API 2,7×; McNemar p = 2,61×10⁻¹⁹.
- Hiện tượng: topology tăng recall nhưng làm LLM xác nhận cả sự cố không tồn tại (thiên lệch xác nhận do ngữ cảnh). Paper tự nhận hạn chế: chạy một lần, trọng số chọn có nhìn `paper_500`, chưa tách nguyên nhân, chưa có RCA.
- Bảng "GĐ1 → paper → GĐ2" (bản chất, câu hỏi, judge, dữ liệu, đầu ra).

> Nguồn: `08-research-direction.md` §2, §3; `AGENTS.md` (baseline G-paper). Trạng thái: ✅

#### 1.1.3 Phát hiện ở GĐ2 làm đổi cách phát biểu vấn đề [MỚI]
- H0 trên `val` tái lập **hiện tượng** (ΔRecall +0,100 [+0,052; +0,155]; ΔFPR +0,025 [+0,020; +0,031]; ΔF1 CI chứa 0) nhưng **không tái lập cơ chế** "bằng chứng lân cận": C1-quota ≡ C1-paper; hiệu ứng đến từ bằng chứng cục bộ sát t₀ (chủ yếu trace span); judge xác nhận 30–42% candidate normal có bằng chứng.
- Vấn đề phát biểu lại: **thiên lệch xác nhận theo nội dung bằng chứng** (QĐ-027, GVHD đồng ý 2026-10-29).
- Trình bày trung thực điểm đổi hướng này.

> Nguồn: QĐ-026, QĐ-027, Phát hiện 7; `docs/drafts/chuong-bai-toan.md` §5–6; `M4-h0.md`. Trạng thái: ✅ (số `val`)

### 1.2 Mục tiêu đề tài

#### 1.2.1 Mục tiêu tổng quát [MỚI]
- (A) Đề xuất và chứng minh CTAV: giữ mức tăng recall của topology mà không tăng báo động giả so với BM25 trong cùng ngân sách LLM.
- (B) Dùng CTAV làm nền cho tác tử RCA định vị service gốc, sinh báo cáo JSON có cấu trúc.
- (C) Hiện thực hoá (A)+(B) trên một platform chạy được để demo (offline từ cache).

> Nguồn: `06-scope-guard.md` §1; `08` §3. Trạng thái: ✅

#### 1.2.2 Mục tiêu cụ thể [MỚI]
- M-1 Tái lập baseline paper (G-paper) và hiện tượng (H0) trên split GĐ2 (dev/val/test, cửa sổ 60 s).
- M-2 Thiết kế CTAV: C1 (Fusion Score), C3 (evidence anchoring), θ hiệu chỉnh; C2, C4, C5 kiểm bằng ablation (H3).
- M-3 Chứng minh bằng giả thuyết đăng ký trước (H0–H5), `test` chạy một lần, CI bootstrap + McNemar.
- M-4 Xây RCA agent (grouping → propagation → summary), đo Hit@1/Hit@3, Alert Reduction.
- M-5 Dựng platform: replayer, detector IForest (+Rescue), ClickHouse/Postgres, API, dashboard 4 màn hình.

> Nguồn: `08` §4–§6; `04-implementation-roadmap.md`. Trạng thái: ✅ (M-1, M-2 trên `val`); ⏳ M8 (M-3); ⏳ M9–M11 (M-4, M-5)

#### 1.2.3 Câu hỏi nghiên cứu [MỚI]
- RQ1: Topology có tăng recall thẩm định cảnh báo trên split GĐ2 không, giá FPR là bao nhiêu? (H0)
- RQ2: Thiên lệch xác nhận phụ thuộc đặc tính nào của bằng chứng (độ gần thời gian, loại)? (H1)
- RQ3: Có chính sách quyết định nào giữ recall của C1 mà FPR không tệ hơn BM25 trong cùng ngân sách? (H2, H4)
- RQ4: Thành phần nào của chính sách đó là cần thiết? (H3)
- RQ5: Dựa trên cảnh báo CTAV, tác tử RCA định vị đúng service gốc ở mức nào? (H5)
- (Năm câu hỏi, đánh số khớp với §8.1.)

> Nguồn: `08` §3, §5.1. Trạng thái: ✅ (phát biểu); trả lời RQ3–RQ5 ⏳ M8–M9

#### 1.2.4 Đóng góp [MỚI]
- ĐG1: CTAV — chính sách thẩm định hiệu chỉnh theo nội dung/nguồn gốc bằng chứng (evidence anchoring + ngưỡng θ).
- ĐG2: giao thức đánh giá có kiểm soát: split chống rò rỉ (nhóm theo lần tiêm lỗi, đệm 600 s), cache LLM, đăng ký giả thuyết trước `test`.
- ĐG3: phân tích cơ chế thiên lệch xác nhận (H1) và kết quả âm: C2, C4 bị bỏ (QĐ-031), C5 không đáng kể (QĐ-033).
- ĐG4: RCA agent + platform tái lập được.
- Khi viết: CTAV `val` F1 0,201 [0,138; 0,264] vs BM25 0,103; FPR 0,007 vs 0,056; recall 0,139 < C1 0,263 (Phát hiện 10). Số `test` [CHỜ M8].

> Nguồn: `CURRENT-MILESTONE.md` (tóm tắt M6, M7); QĐ-031..033. Trạng thái: ✅ (`val`), ⏳ M8

### 1.3 Đối tượng và phạm vi

#### 1.3.1 Đối tượng nghiên cứu [TÁI SỬ DỤNG GĐ1 §1.3.1, điều chỉnh]
- Cảnh báo (cửa sổ metric 60 s) của hệ microservice; bằng chứng log/trace; đồ thị phụ thuộc service dựng từ trace.
- Judge LLM duy nhất qua API, cố định (QĐ-013: không local, không fallback; QĐ-021: `gemini-2.5-flash` cho thực nghiệm GĐ2, flash-lite chỉ phát lại cache paper).
- Bỏ khỏi đối tượng: LLM local, local-first (chỉ nêu lại như bối cảnh GĐ1).

> Nguồn: `06` §3; QĐ-013, QĐ-021. Trạng thái: ✅

#### 1.3.2 Dữ liệu và phạm vi nghiên cứu [MỚI]
- Nezha: 95.660 cửa sổ, 704 fault (0,74%); 101 lần tiêm lỗi có nhãn root-cause mức pod; Hit@k chấm mức service (dễ hơn mức pod — phải nêu).
- Split: dev 19.316 / val 28.898 / test 46.849 cửa sổ; giữ mất cân bằng; chỉ số chính trên cửa sổ có telemetry, "mọi cửa sổ" là phụ (QĐ-017).
- Trong phạm vi: 2 retrieval strategy, judge + policy, RCA agent, replayer, dashboard 4 màn hình, Docker Compose.
- Ngoài phạm vi (danh sách cấm, ghi `docs/ideas.md`): Kubernetes, vector DB, LangChain/AutoGen, fine-tuning, authentication, multi-tenant, notification, runbook, retrieval thứ 3, detector thứ hai.
- Nêu giới hạn: một dataset, một judge, không phải sản phẩm production.

> Nguồn: QĐ-001, QĐ-003, QĐ-004, QĐ-017; `06` §3–§4. Trạng thái: ✅

### 1.4 Ý nghĩa

#### 1.4.1 Ý nghĩa thực tiễn [TÁI SỬ DỤNG GĐ1 §1.4.1, điều chỉnh]
- Giảm báo động giả khi dùng LLM thẩm định mà vẫn giữ khả năng thấy sự cố khó (network_delay); kiểm soát chi phí API.
- Gom cảnh báo thành incident + gợi ý root cause cho SRE; mục tiêu Alert Reduction ≥ 30% trên cascade [CHỜ M8/M9].

> Nguồn: `08` §5.1 (H5); `06` §1. Trạng thái: ⏳ M8–M9

#### 1.4.2 Ý nghĩa khoa học [MỚI]
- Chứng cứ thực nghiệm về thiên lệch xác nhận của LLM judge theo bằng chứng truy xuất; báo cả kết quả dương lẫn âm, đăng ký trước.
- Mẫu giao thức đánh giá tái lập được (cache, replay verdict, bootstrap, McNemar).

> Nguồn: Phát hiện 7, 10, 12; `08` §5.2. Trạng thái: ✅ (`val`), ⏳ M8

### 1.5 Bố cục luận văn [MỚI]
- Tóm tắt từng chương theo cấu trúc 8 chương: Ch2 cơ sở lý thuyết, Ch3 công trình liên quan, Ch4 phương pháp CTAV + RCA, Ch5 thực nghiệm H0–H5, Ch6 demo platform, Ch7 thảo luận, hạn chế, hướng phát triển, Ch8 kết luận; chỉnh sau khi chốt mục lục cuối (xem ghi chú 6 chương của template).

> Nguồn: `08` §7. Trạng thái: ✅ (khung)

---

## Chương 2 — Cơ sở lý thuyết

### 2.1 Dữ liệu quan sát trên hệ microservice

#### 2.1.1 Metric, log, trace và cửa sổ phân tích [TÁI SỬ DỤNG GĐ1 §2.1.1–§2.1.3, rút gọn]
- Chuỗi thời gian đa biến, luồng thời gian thực, dữ liệu server/cloud: giữ 1–2 trang; bỏ tiền xử lý streaming (§2.1.4) trừ phần dùng thật (rolling buffer, xử lý NaN).
- Bổ sung log, trace (span, SpanID, quan hệ cha–con) là *bằng chứng*; cửa sổ = một mẫu metric của một pod, 60 s; nhãn theo [inject_ts − 60 s, inject_ts + 360 s].

> Nguồn: `phase1.txt` tr.12–16; QĐ-002, QĐ-003, QĐ-009. Trạng thái: ✅

#### 2.1.2 Benchmark Nezha và nhãn root-cause [MỚI]
- Mô tả Nezha, fault list, ánh xạ pod → service; lý do chọn Nezha (QĐ-001).
- Chống rò rỉ khi chia split: nhóm theo injection_id, vùng đệm 600 s.

> Nguồn: QĐ-001, QĐ-004; `docs/label-audit.md`. Trạng thái: ✅

### 2.2 Phát hiện bất thường và quá tải cảnh báo

#### 2.2.1 Định nghĩa, khoảng trống ngữ nghĩa, quá tải cảnh báo [TÁI SỬ DỤNG GĐ1 §2.2, rút gọn]
- Giữ định nghĩa và motivation alert fatigue; nối trực tiếp tới nhu cầu thẩm định cảnh báo.

> Nguồn: `phase1.txt` tr.17–19. Trạng thái: ✅

#### 2.2.2 Isolation Forest [TÁI SỬ DỤNG GĐ1 §2.3.1, rút gọn]
- Nguyên lý, điểm bất thường ∈ [0,1], ngưỡng 0,85 fit trên `dev`; rolling buffer.
- **Bỏ** mô hình học sâu (GĐ1 §2.3.2): không dùng, cấm detector thứ hai.

> Nguồn: GĐ1 §2.3; `01` §6.2; QĐ-015. Trạng thái: ✅

### 2.3 Truy xuất bằng chứng

#### 2.3.1 BM25 và truy xuất văn bản log/trace [MỚI]
- Công thức BM25 (tf, idf, độ dài tài liệu, k1, b); truy vấn sinh từ ứng viên; cửa sổ ±8 phút.
- Rủi ro rò nhãn: truy vấn không chứa tag fault type (có unit test).

> Nguồn: `chuong-bai-toan.md` §2; `08` §5.2; QĐ-016. Trạng thái: ✅

#### 2.3.2 Đồ thị phụ thuộc service [MỚI]
- Dựng từ quan hệ cha–con của span; 56 service / 68 cạnh trên Nezha; khoảng cách d_G trên đồ thị vô hướng; độ phủ đồ thị.
- Phân biệt "gần trên đồ thị" với "nhân quả".

> Nguồn: QĐ-021; `docs/graph-coverage.md`. Trạng thái: ✅

#### 2.3.3 Fusion retrieval và Fusion Score [MỚI]
- Score = α·BM25_norm + β·exp(−|t_e−t₀|/τ_F) + γ·GraphSim, α+β+γ = 1, hằng số thời gian τ_F = 300 s (viết τ_F để phân biệt với ngưỡng τ của Rescue Score); cấu hình A4 (0,35; 0,25; 0,40), 2-hop, top-6.
- Temporal-only / graph-only là ablation của C1; RRF/reranker/cross-modal không dùng (QĐ-011), chỉ nhắc để định vị.
- `k_graph` quét ở QĐ-024/025; CTAV dùng C1-paper `k_graph` 0 (`ctav_final.yaml`).

> Nguồn: `08` §2, §4; QĐ-011, QĐ-024, QĐ-025. Trạng thái: ✅

#### 2.3.4 Retrieval-Augmented Generation trong giám sát [TÁI SỬ DỤNG GĐ1 §2.6, rút gọn]
- Giữ khái niệm RAG và vai trò ngữ cảnh; "khôi phục ngữ cảnh" (GĐ1 §2.9) chỉ nêu như tiền thân của Rescue Score.

> Nguồn: `phase1.txt` tr.28–29, 33–34. Trạng thái: ✅

### 2.4 LLM làm bộ thẩm định (LLM-as-a-Judge)

#### 2.4.1 LLM, prompt và đầu ra có cấu trúc [TÁI SỬ DỤNG GĐ1 §2.4, rút gọn]
- LLM tổng quan, hạn chế (độ trễ, chi phí, không tất định); prompt + JSON schema (nhãn, confidence, evidence). Rút gọn mạnh phần kỹ thuật prompt (GĐ1 tr.24–27).
- **Bỏ** GĐ1 §2.5 (LLM cục bộ + API fallback): chỉ giữ 2–3 câu bối cảnh (qwen2.5:1.5b: F1 0,800 vs 0,769; độ trễ ~13,6×) để giải thích QĐ-013.

> Nguồn: `phase1.txt` tr.22–28; `08` §4.1; QĐ-013. Trạng thái: ✅

#### 2.4.2 Cơ chế LLM-as-a-Judge hai tầng [TÁI SỬ DỤNG GĐ1 §2.7, rút gọn]
- Định nghĩa judge; kiến trúc hai tầng (rẻ → đắt) là tiền đề của routing C4 (nay là ablation).
- Luật `require_evidence`; `manual_review` khi hết ngân sách/lỗi.

> Nguồn: `phase1.txt` tr.30–31; `chuong-bai-toan.md` §2. Trạng thái: ✅

#### 2.4.3 Thiên lệch xác nhận, hiệu chỉnh và nguồn gốc bằng chứng [MỚI]
- Thiên lệch xác nhận của LLM khi ngữ cảnh gợi ý sự cố; confidence bằng lời không tự hiệu chỉnh → ngưỡng θ chọn trên `val`/`dev` (θ = 0,80).
- Evidence anchoring (C3): TRUE_ALERT phải trích bằng chứng bất thường tại s₀ (log ERROR/WARN hoặc span vượt ngưỡng nền `dev` p90); độ phủ ≈ 32% span, 15 service không có ngưỡng (Phát hiện 11).
- Asymmetric gating C2 (θ_topo > θ_local) và routing C4: nêu lý thuyết và kết quả ablation bỏ chúng (QĐ-031).
- Tài liệu tham khảo ngoài repo về LLM-judge bias/calibration chưa có — cần bổ sung khi viết Ch3, không bịa trích dẫn.

> Nguồn: `08` §4 (C2–C4), QĐ-027, QĐ-029, QĐ-031. Trạng thái: ✅ (thiết kế/`val`); tham khảo ⏳ Ch3

#### 2.4.4 Rescue Score (C5) [MỚI, nối GĐ1 §2.9]
- RescueScore = η1·Λ_log + η2·Φ_topo + η3·Δ_time; η ≥ 0, Σ = 1; ngưỡng τ.
- `val` (QĐ-033): rút về 2 thành phần (η = 0; 0,4; 0,6; τ = 0,8), +2 TP / +16 FP, ΔF1 +0,001 [−0,014; +0,022] — không đáng kể; ở M8 chỉ là một điểm ablation của H3 (V34 (b), QĐ-034). Số `test` [CHỜ M8].
- Viết ngắn; không phải đóng góp chính.

> Nguồn: `01` §6.2; QĐ-008, QĐ-033; QĐ-034. Trạng thái: ✅ (`val`), ⏳ M8

### 2.5 Phân tích nguyên nhân gốc (RCA) trên microservice

#### 2.5.1 Bài toán RCA và gom incident [MỚI]
- Định nghĩa root cause service, cascade fault, alert → incident; grouping: cửa sổ trượt T_group = 300 s + thành phần liên thông trên đồ thị con (không gọi LLM).

> Nguồn: `01` §6.5. Trạng thái: ⏳ M9

#### 2.5.2 Lan truyền ngược trên đồ thị gọi [MỚI]
- Mức 1: từ span lỗi ở frontend đi ngược 1 hop, chọn upstream bất thường; mức 2: LLM lập luận call chain (nếu kịp).
- Giới hạn: replica, nhiễu, quan hệ gọi ≠ nhân quả.

> Nguồn: `01` §6.5. Trạng thái: ⏳ M9

#### 2.5.3 Báo cáo chẩn đoán có cấu trúc [MỚI]
- Summarizer gọi LLM một lần/incident, JSON schema cố định, validator, `require_evidence`; JSON valid rate.

> Nguồn: `01` §6.5; `03-schemas-and-contracts.md`. Trạng thái: ⏳ M9–M10

### 2.6 Tiêu chí và phương pháp đánh giá

#### 2.6.1 Chỉ số phân loại cảnh báo [TÁI SỬ DỤNG GĐ1 §2.8, rút gọn]
- Precision, Recall, F1, FPR trên dữ liệu mất cân bằng (không cân bằng lại — QĐ-004); coverage, độ trễ, token, chi phí.
- Hai view: cửa sổ có telemetry (chính), mọi cửa sổ (phụ).

> Nguồn: `phase1.txt` tr.32–33; QĐ-004, QĐ-017. Trạng thái: ✅

#### 2.6.2 Chỉ số RCA: Hit@k, Alert Reduction [MỚI]
- Hit@1, Hit@3 mức service (lưu ý khác mức pod), Alert Reduction Ratio, JSON valid rate, E2E latency; baseline "service có anomaly score cao nhất".
- Mục tiêu đăng ký: Hit@1 ≥ 0,60, Hit@3 ≥ 0,80, AR ≥ 30% [CHỜ M8/M9].

> Nguồn: `08` §5.1 (H5); `06` §3 Nhánh B; QĐ-001. Trạng thái: ⏳ M9

#### 2.6.3 Kiểm định thống kê: bootstrap CI và McNemar [MỚI]
- Bootstrap 95% (1.000 mẫu, seed 42) cho chỉ số và hiệu ghép cặp; McNemar chính xác hai phía, α = 0,05.
- H2 chính; H0, H3, H4 phụ, báo p thô, không hiệu chỉnh đa so sánh (nêu hạn chế); phương sai LLM bằng `repeat` 0/1/2 trên tập con 200 cửa sổ.

> Nguồn: mục "Đăng ký giả thuyết H0–H5" cuối `experiment-log.md` (đã đăng ký 2026-11-14, commit `be2b985`); `01` §6.8. Trạng thái: ✅

#### 2.6.4 Đánh giá theo ngân sách và chi phí [MỚI]
- Ngân sách gọi LLM, đường F1 theo ngân sách (120 … đủ), chi phí token/USD; cache key = sha256(prompt+model+temperature+max_tokens+repeat).

> Nguồn: `08` §4.1, §5; QĐ-013, QĐ-026. Trạng thái: ✅ (thiết kế), ⏳ M8

### 2.7 Giả thuyết nghiên cứu và đăng ký trước [MỚI]
- Vì sao đăng ký trước, và đăng ký những gì (giả thuyết, so sánh, tiêu chí chấp nhận). **Không lặp bảng ở đây:** bảng H0–H5 đầy đủ chỉ đặt ở §5.1 (Bảng 5.1), mục này trỏ sang đó. H2 là giả thuyết chính, δ = 0,05 (V33 (a)); H1 đã kiểm trên `val`, không chạy lại trên `test`.
- Kỷ luật: tuning chỉ trên `val`, `test` một lần sau đăng ký; bản đăng ký được commit riêng ngày 2026-11-14 (`be2b985`), trước mọi lần chạy trên `test`.

> Nguồn: `08` §5.1; mục đăng ký cuối `experiment-log.md`; QĐ-034. Trạng thái: ✅ (đăng ký), ⏳ M8 (kết quả)

### 2.8 Tóm tắt chương [MỚI]
- Bảng ánh xạ khái niệm Ch2 → thành phần (C1…C5, RCA) → giả thuyết kiểm.
- Ghi rõ phần GĐ1 bị lược: DL cho chuỗi thời gian, LLM local/fallback, prompt engineering chi tiết, khôi phục ngữ cảnh.

> Nguồn: tổng hợp. Trạng thái: ✅

---

## Chương 3 — Công trình liên quan

> Ghi chú: sườn, chưa phải văn hoàn chỉnh. Nhãn: [TÁI SỬ DỤNG GĐ1, rút gọn] = lấy từ phase1.txt tr.35–49; [MỚI] = bổ sung GĐ2. Trạng thái: ✅ đã có nội dung/nguồn trong repo · ⏳ cần viết hoặc cần kiểm chi tiết · [CẦN TRA CỨU] chưa chắc, phải xác minh trước khi trích dẫn.

### 3.0 Dẫn nhập và cách tổ chức chương [MỚI, viết lại ngắn]

- Nhắc lại luận điểm GĐ1: detector metric nhanh nhưng thiếu ngữ cảnh → LLM thẩm định cảnh báo ở tầng sau.
- Mở rộng GĐ2: (i) bằng chứng truy xuất có cấu trúc topology; (ii) độ tin cậy/hiệu chỉnh của judge; (iii) từ thẩm định cảnh báo sang định vị service gốc (RCA).
- Tổ chức: 3.1–3.3 (GĐ1, rút gọn) → 3.4 RCA topology/đồ thị → 3.5 retrieval đồ thị/GraphRAG → 3.6 calibration & thiên lệch judge → 3.7 cứu cảnh báo/triage → 3.8 bảng so sánh → 3.9 khoảng trống & định vị CTAV.

> Nguồn: phase1.txt tr.35; `docs\Final_Thesis_Phase2\08-research-direction.md` §1–3.
> Trạng thái: ⏳

### 3.1 Phát hiện bất thường chuỗi thời gian (thống kê và học sâu) [TÁI SỬ DỤNG GĐ1, rút gọn]

Rút gọn GĐ1 từ ~4 trang còn ~1 trang; giữ lập luận "detector chỉ là tầng sơ cấp".

#### Robust Random Cut Forest (Guha và cộng sự)
- Phát hiện bất thường trên dòng dữ liệu bằng cây cắt ngẫu nhiên; nhẹ, online (GĐ1 tr.35–36).
- Hạn chế: chỉ dựa hình dạng phân bố, không biết ý nghĩa vận hành (batch job, backup, rolling deploy, autoscaling).
- Liên hệ GĐ2: detector duy nhất của GĐ2 là Isolation Forest (+ Rescue); RRCF chỉ là bối cảnh (không thêm detector thứ hai — scope-guard).
> Nguồn: phase1.txt tr.35–36; `06-scope-guard.md`.
> Trạng thái: ✅

#### MTAD-GAT (Zhao và cộng sự) và Graph Deviation Network – GDN (Deng và Hooi)
- Đa biến, graph attention / học cấu trúc phụ thuộc giữa các **metric** (đồ thị đặc trưng, khác đồ thị gọi giữa service ở 3.4–3.5 — nêu rõ để tránh nhầm "graph").
- Hạn chế chung: chỉ định lượng, vẫn sinh cảnh báo giả khi thiếu ngữ cảnh log/sự kiện.
> Nguồn: phase1.txt tr.36–38.
> Trạng thái: ✅

### 3.2 LLM trong phân tích log và RCA [TÁI SỬ DỤNG GĐ1, rút gọn]

#### LogParser-LLM (Zhong và cộng sự) và LogLLM (Guan và cộng sự)
- LogParser-LLM: parsing log bằng LLM, tiết kiệm số lần gọi (LogPub, 14 hệ thống, TB 272,5 lần gọi LLM, F1 grouping 90,6%, parsing accuracy 81,1% — theo GĐ1).
- LogLLM: BERT + Llama + projector cho phát hiện bất thường log; chỉ dùng log, huấn luyện nhiều giai đoạn.
- Liên hệ GĐ2: log là một loại bằng chứng (cùng trace span) trong EvidenceDoc; GĐ2 không fine-tune (cấm).
> Nguồn: phase1.txt tr.38–41.
> Trạng thái: ✅

#### RCAgent (Wang và cộng sự)
- LLM agent tự chủ dùng công cụ để điều tra; phù hợp sau sự cố, độ trễ cao.
- Tham chiếu chính cho phần B (RCA Agent) ở 3.4; khác biệt: GĐ2 dùng pipeline cố định (grouping → propagation → summary), không dùng agent framework (cấm LangChain/AutoGen/CrewAI).
> Nguồn: phase1.txt tr.40–43.
> Trạng thái: ✅

### 3.3 Kiến trúc giám sát lai và LLM-as-a-Judge [TÁI SỬ DỤNG GĐ1, rút gọn]

#### RAAD-LLM (Russell-Gilbert), ARGOS (Gu), CALM (Devireddy và Huang)
- RAAD-LLM: LLM + RAG cho bất thường thích ứng, bảo trì dự đoán (70,7% → 88,6%).
- ARGOS: LLM sinh luật phát hiện (F1 +9,5% dữ liệu công khai, +28,3% dữ liệu nội bộ Microsoft).
- CALM: Apache Beam + TimesFM + LLM-as-a-Judge + fine-tuning liên tục (TSB-UAD); gần nhất về kiến trúc.
- Điểm chung: LLM đặt sau tầng lọc; chưa nghiên cứu **cách chọn bằng chứng** đưa vào judge và hệ quả lên FP.
> Nguồn: phase1.txt tr.42–47.
> Trạng thái: ✅

#### LLM-as-a-Judge for Time Series Explanations (Sivalingam và cộng sự)
- Benchmark 350 trường hợp, 7 loại truy vấn; LLM đánh giá ổn định hơn khi sinh → cơ sở cho vai trò judge.
- Chưa xét pipeline cloud, chưa xét thiên lệch do ngữ cảnh truy xuất.
> Nguồn: phase1.txt tr.45.
> Trạng thái: ✅

#### Nezha (Yu và cộng sự) — vừa là công trình RCA vừa là bộ dữ liệu
- RCA phi giám sát đa phương thức (metric, log, trace), đồ thị sự kiện theo trace; Top-1 trung bình 89,77% trên 101 kịch bản (theo GĐ1).
- Vai trò kép: baseline RCA ngoại tuyến (3.4) và dataset đánh giá của GĐ1 + GĐ2 (nhãn root-cause mức pod: QĐ-001).
- Khác biệt: Nezha chẩn đoán sau khi biết có sự cố; CTAV quyết định cảnh báo có thật hay không.
> Nguồn: phase1.txt tr.45–47; `docs\experiment-log.md` QĐ-001.
> Trạng thái: ✅

### 3.4 RCA trên microservice dựa topology/đồ thị và nhân quả [MỚI]

#### Nhóm đồ thị phụ thuộc/lan truyền
- MonitorRank (Kim và cộng sự, SIGMETRICS 2013): random walk trên đồ thị gọi để xếp hạng nguyên nhân.
- CauseInfer (Chen và cộng sự, INFOCOM 2014): đồ thị nhân quả phân tầng cho dịch vụ đa tầng.
- MicroRCA (Wu, Tordsson, Elmroth, Kao; NOMS 2020): đồ thị attributed, personalized PageRank, metric ứng dụng + hạ tầng.
- Điểm chung: chạy trên bất thường **đã có**, không thẩm định cảnh báo thật/giả; topology dùng cho lan truyền ngược — cùng ý với RCA Agent của GĐ2.
> Nguồn: bài gốc các công trình (chi tiết trích dẫn: [CẦN TRA CỨU] khi lập danh mục tham khảo); `08-research-direction.md` dòng "B RCA Agent".
> Trạng thái: ⏳

#### Nhóm nhân quả/benchmark hiện đại
- RCD (Ikram và cộng sự, NeurIPS 2022) và CIRCA (Li và cộng sự, KDD 2022): suy diễn nhân quả cho RCA — [CẦN TRA CỨU] xác minh tên/hội nghị.
- BARO (Pham và cộng sự, FSE 2024) và benchmark RCAEval (Pham và cộng sự) — [CẦN TRA CỨU] chi tiết.
- Hạn chế cần nêu: đánh giá top-k trên sự cố đã biết; không đo FP của khâu cảnh báo; ít tích hợp LLM judge.
> Nguồn: [CẦN TRA CỨU].
> Trạng thái: [CẦN TRA CỨU]

#### RCA bằng LLM
- RCAgent (3.2); RCACopilot (Chen và cộng sự, EuroSys 2024): handler thu thập thông tin theo loại sự cố + LLM dự đoán nguyên nhân dựa trên sự cố lịch sử tương tự — ⏳ xác minh chi tiết.
- Ahmed và cộng sự (ICSE 2023): LLM đề xuất nguyên nhân/giảm thiểu sự cố đám mây (có fine-tune; GĐ2 không) — [CẦN TRA CỨU].
- Roy và cộng sự (2024): agent ReAct cho RCA — [CẦN TRA CỨU].
- Khác biệt với GĐ2: đầu vào là incident đã có; không xử lý FP khâu cảnh báo.
> Nguồn: [CẦN TRA CỨU] (RCACopilot, Ahmed, Roy); phase1.txt tr.40–42 cho RCAgent.
> Trạng thái: [CẦN TRA CỨU]

#### Liên hệ phần B của GĐ2
- Grouping theo thời gian + topology → lan truyền ngược → báo cáo JSON; đánh giá Hit@1/Hit@3, Alert Reduction (H5).
- Điểm nhấn: đầu vào RCA là cảnh báo đã được CTAV hiệu chỉnh (ít FP), không phải mọi bất thường.
> Nguồn: `08-research-direction.md` §4 (B), H5; `01-architecture-design.md` §6.5.
> Trạng thái: ✅

### 3.5 Truy xuất dựa đồ thị / GraphRAG cho AIOps [MỚI]

- RAG nền tảng (Lewis và cộng sự, NeurIPS 2020) và BM25 lai là baseline truy xuất (bm25_hybrid, GĐ1).
- GraphRAG (Edge và cộng sự, Microsoft Research, 2024): đồ thị tri thức + tóm tắt cộng đồng cho văn bản; khác topology gọi giữa service — ⏳ xác minh.
- Fusion Score của paper ICAETM (α, β, γ: lexical + thời gian + lân cận đồ thị) là retrieval đồ thị tối giản của đề tài (C1); không dùng vector DB/KG riêng (cấm).
- Hệ AIOps dùng retrieval lịch sử (RCACopilot) truy xuất sự cố tương tự, không truy xuất telemetry lân cận trên topology — [CẦN TRA CỨU] kiểm tra có công trình AIOps dùng graph retrieval trên topology không trước khi khẳng định "chưa có".
- Thực nghiệm tham chiếu: paper — topology tăng recall, FP ×19,6; GĐ2 (QĐ-027) — cơ chế là bằng chứng cục bộ sát thời điểm (chủ yếu trace span), không phải service lân cận.
> Nguồn: `08-research-direction.md` §2 (cập nhật QĐ-027); `docs\experiment-log.md` QĐ-026, QĐ-027; tài liệu GraphRAG/RAG [CẦN TRA CỨU].
> Trạng thái: ⏳

### 3.6 Calibration và độ tin cậy của LLM-as-a-Judge [MỚI]

#### Thiên lệch của LLM judge
- Zheng và cộng sự (NeurIPS 2023, MT-Bench/Chatbot Arena): thiên lệch vị trí, độ dài, tự ưu tiên.
- Wang và cộng sự (2023, "Large Language Models are not Fair Evaluators"): thiên lệch thứ tự trình bày.
- Liên hệ: thiên lệch **theo nội dung ngữ cảnh** (judge xác nhận sự cố khi đọc telemetry bình thường) ít được nghiên cứu trong AIOps; QĐ-026 Phát hiện 7: judge xác nhận 30–42% candidate normal có bằng chứng.
> Nguồn: [CẦN TRA CỨU] xác minh MT-Bench và Wang 2023; `docs\experiment-log.md` QĐ-026.
> Trạng thái: ⏳

#### Calibration độ tin cậy mô hình
- Guo và cộng sự (ICML 2017): calibration mạng nơ-ron hiện đại (temperature scaling, ECE).
- Kadavath và cộng sự (2022); Xiong và cộng sự (ICLR 2024): độ tự tin LLM diễn đạt bằng lời — [CẦN TRA CỨU] kiểm tra chi tiết.
- Khác biệt: CTAV hiệu chỉnh theo hồ sơ/nguồn gốc bằng chứng (C2: θ_topo > θ_local; C3: neo bằng chứng bất thường), không hiệu chỉnh xác suất đầu ra. Nêu thẳng: C2 bị bỏ (QĐ-031), trọng tâm là C3.
> Nguồn: `08-research-direction.md` §4 (C2, C3); `docs\experiment-log.md` QĐ-028, QĐ-029, QĐ-031.
> Trạng thái: ⏳

#### Grounding / trích dẫn bằng chứng (provenance)
- Hướng attribution/grounded generation — [CẦN TRA CỨU] chọn 1–2 công trình chắc chắn.
- C3 là grounding có kiểm chứng bằng ngưỡng nền (p90 trên `dev`), không chỉ yêu cầu trích dẫn.
> Nguồn: [CẦN TRA CỨU]; `08-research-direction.md` C3.
> Trạng thái: [CẦN TRA CỨU]

### 3.7 Cứu cảnh báo (rescue) và alert triage [MỚI]

- Bối cảnh: alert fatigue, alert storm, gom cảnh báo thành incident — [CẦN TRA CỨU] chọn công trình triage/gom nhóm có thật (không nêu tên trước khi xác minh).
- Context Rescue GĐ1: tăng recall nhưng tốn LLM; số liệu mock GĐ1 không dùng làm kết luận khoa học (AGENTS.md).
- C5 Rescue Score GĐ2 (Λ_log, Φ_topo, Δ_time; η, τ): trên `val` (QĐ-033) rút về 2 thành phần, η = (0; 0,4; 0,6), τ = 0,8; thêm 2 TP / 16 FP, ΔF1 CI chứa 0 → không có ý nghĩa thống kê; vai trò ở M8 theo V34. Trình bày trung thực như ablation/hạn chế.
- Grouping cảnh báo theo thời gian + topology là tiền đề của RCA Agent (3.4).
> Nguồn: `docs\experiment-log.md` QĐ-032, QĐ-033; `08-research-direction.md` dòng C5; `AGENTS.md`.
> Trạng thái: ⏳ (phần công trình ngoài: [CẦN TRA CỨU])

### 3.8 Bảng so sánh các công trình [MỚI]

Ký hiệu: ● có / ◐ một phần / ○ không / ? chưa xác minh. Ô của công trình ngoài GĐ1 phải kiểm lại với bài gốc.

| Công trình | Topology | LLM judge | Calibration theo nguồn bằng chứng | RCA | Đánh giá FP |
|---|---|---|---|---|---|
| RRCF (Guha) | ○ | ○ | ○ | ○ | ○ |
| MTAD-GAT / GDN | ◐ (đồ thị metric) | ○ | ○ | ◐ (thu hẹp biến) | ○ |
| LogParser-LLM / LogLLM | ○ | ○ | ○ | ○ | ○ |
| RAAD-LLM | ○ | ◐ (LLM + RAG) | ○ | ○ | ○ |
| ARGOS | ○ | ○ | ○ | ○ | ◐ (F1) |
| CALM | ○ | ● | ○ | ○ | ◐ |
| LLM-as-a-Judge for TS Explanations | ○ | ● (chấm giải thích) | ○ | ○ | ○ |
| RCAgent | ? | ○ | ○ | ● | ○ |
| Nezha | ◐ (đồ thị sự kiện theo trace) | ○ | ○ | ● | ○ |
| MonitorRank / CauseInfer / MicroRCA | ● | ○ | ○ | ● | ○ |
| RCACopilot [CẦN TRA CỨU] | ? | ○ | ○ | ● | ? |
| RCD / CIRCA / BARO / RCAEval [CẦN TRA CỨU] | ? | ○ | ○ | ● | ? |
| Paper ICAETM 2026 | ● (C1 Fusion) | ● | ○ (chỉ ghi nhận FP ×19,6) | ○ | ● |
| **CTAV (GĐ2)** | ● (C1) | ● | ● (C3; C2 là ablation) | ● (RCA Agent) | ● (FPR, McNemar, CI bootstrap) |

> Nguồn: phase1.txt tr.48 (Bảng 3 GĐ1); 3.4–3.7; `08-research-direction.md` §1–4.
> Trạng thái: ⏳

### 3.9 Khoảng trống nghiên cứu và định vị CTAV [MỚI, thay 3.4 GĐ1]

#### Khoảng trống
- (G1) RCA topology/đồ thị giả định bất thường đã đúng; không đo FP của khâu cảnh báo.
- (G2) LLM-judge cho cảnh báo chưa xét thiên lệch xác nhận do **nội dung bằng chứng truy xuất** (paper: recall tăng, FP 7 → 137, F1 0,703 → 0,476).
- (G3) Calibration judge thường ở mức xác suất/độ tự tin, chưa theo nguồn gốc/hồ sơ bằng chứng.
- (G4) Thẩm định cảnh báo và RCA thường tách rời; thiếu pipeline end-to-end tái lập được trên cùng dữ liệu có nhãn.
> Nguồn: `08-research-direction.md` §2–3; phase1.txt tr.47–49; 3.4–3.7.
> Trạng thái: ⏳ (khẳng định "chưa có công trình" cần khảo sát thêm: [CẦN TRA CỨU])

#### Định vị CTAV
- Giữ C1 (topology) để giữ recall; C3 (evidence anchoring) giảm FP; C2/C4 thử và bỏ có chủ đích sau ablation (QĐ-031); C5 Rescue không có đóng góp có ý nghĩa trên `val` (QĐ-033).
- Phát biểu khiêm tốn: thẩm định cảnh báo có hiệu chỉnh theo bằng chứng + RCA trên cảnh báo đã thẩm định; một dataset (Nezha), một judge (`gemini-2.5-flash`, QĐ-021) — nêu trong hạn chế.
- H2 giữ nguyên văn, báo trung thực recall CTAV < C1 trên `val` (QĐ-032); kết quả `test` chưa có (M8).
> Nguồn: `08-research-direction.md` §4–5; `docs\experiment-log.md` QĐ-027, QĐ-031, QĐ-032, QĐ-033.
> Trạng thái: ✅ (cấu trúc)

#### Tóm tắt chương
- 3–4 gạch ý chuyển sang Chương 4 (bài toán và phương pháp CTAV).
> Nguồn: tự tổng hợp.
> Trạng thái: ⏳

### Phụ lục: việc tra cứu cho danh mục tài liệu tham khảo
- Xác minh trích dẫn đầy đủ: MonitorRank, CauseInfer, MicroRCA, RCACopilot, RCD, CIRCA, BARO, RCAEval, MT-Bench, Wang 2023, Guo 2017, Kadavath 2022, Xiong 2024, GraphRAG, Lewis 2020.
- Tìm 1–2 công trình alert triage/gom cảnh báo có thật (3.7); công trình grounding/attribution (3.6).
- Kiểm tra có công trình AIOps nào kết hợp graph retrieval + LLM judge + đo FP (xác nhận G2/G3).

---

## Chương 4 — Phương pháp đề xuất: CTAV và tác tử RCA

> Trạng thái tại 2026-11-11 (`docs/CURRENT-MILESTONE.md`): M0–M6 đã qua (M6 qua có điều kiện), M7 đã đóng 2026-11-14 (H0–H5 đã đăng ký, QĐ-034), M8 (G-test) đang chạy. RCA agent mới có `grouping.py`; `propagation`, `summarizer`, `pipeline` thuộc M9 (⏳). API/dashboard dữ liệu thật thuộc M10 (⏳).
> Ký hiệu: ✅ đã hiện thực · ⏳ chờ mốc · ✂️ đã thử rồi bỏ/ablation (có QĐ).

### 4.1 Phát biểu bài toán hình thức

- Dữ liệu: telemetry (metric, log, trace span) hệ microservice Nezha, chia **cửa sổ** `w` 60 s (GĐ1: 120 s), nhãn theo wall-clock (QĐ-002..004); mỗi `w` gắn service `s_0`, thời điểm `t_0` (`TelemetryWindow`).
- **Cảnh báo ứng viên** `AlertCandidate` (từ Detector, `source ∈ {metric, rescue}`); nhãn thật `y(w) ∈ {fault, normal}`; verdict judge ∈ {TRUE_ALERT, FALSE_POSITIVE, UNCERTAIN} kèm `confidence` và bằng chứng trích dẫn.
- Cần thiết kế ánh xạ `(w, E(w)) → verdict`, `E(w)` = bằng chứng truy hồi (top-k, ngân sách token), dưới **ngân sách LLM** `B` (số lần gọi); đo Recall, FPR, F1 cùng `B`.
- Vấn đề nghiên cứu: topology tăng recall nhưng gây thiên lệch xác nhận (paper: BM25 F1 0,703/FP 7 vs topology 0,476/FP 137); phát biểu lại theo QĐ-027 là thiên lệch theo **nội dung/nguồn gốc bằng chứng**.
- Bài toán B (RCA): từ alert đã xác nhận + đồ thị phụ thuộc `G`, gom incident và xếp hạng service gốc (Hit@k).
- Hình/bảng: **Bảng 4.1** Bảng ký hiệu (w, s_0, t_0, E(w), θ, α/β/γ, τ_F của Fusion, η và τ của Rescue, B). **Hình 4.1** Cửa sổ 60 s + ngữ cảnh + nhãn wall-clock.
> Nguồn: `08-research-direction.md` §2–§3, QĐ-002..004, QĐ-027; `03-schemas-and-contracts.md` §1.1–1.4; `02-data-and-experiment-protocol.md` §1–2. Trạng thái: ✅

### 4.2 Kiến trúc tổng thể của platform

- Pipeline: `Replayer → Detector (IForest + Rescue) → CTAV (retrieval → judge → policy) → RCA Agent → ClickHouse/Postgres → API → Dashboard 4 màn hình`; một pipeline cho cả thực nghiệm lẫn demo; demo offline từ cache.
- **Bốn Protocol lõi** (`packages/schemas/protocols.py`): `SourceAdapter`, `Detector`, `RetrievalStrategy` (`retrieve(candidate, budget)`), `Judge`; tham số riêng trong `__init__`, không đổi signature.
- Critical path vs non-critical path (ghi ClickHouse/Postgres, dashboard không chặn luồng chấm).
- **[TÁI SỬ DỤNG GĐ1 Ch4 §4.3–§4.4]**: kiến trúc giám sát lai, thành phần chính, cấu hình LLM; chuẩn hoá log/trace, Streaming Replay & watermark. Chỉ tóm tắt + dẫn chiếu; nêu phần mới: judge LLM thật + cache bắt buộc, split dev/val/test, cửa sổ 60 s, topology, tầng chính sách.
- Quyết định: một model API cố định, không local-first/fallback (QĐ-013; GĐ1 đo local-first F1 0,769 vs 0,800, trễ ~13,6×); QĐ-021 đổi sang `gemini-2.5-flash`.
- Hình/bảng: **Hình 4.2** Kiến trúc tổng thể (`01` §3). **Hình 4.3** 4 Protocol ↔ module. **Bảng 4.2** Tái sử dụng GĐ1 vs mới GĐ2.
> Nguồn: `01-architecture-design.md` §1–§5, §8; `08` §4.1, §6; QĐ-013, QĐ-021; GĐ1 `phase1.txt` Ch4 §4.3–4.4. Trạng thái: ✅ (đến CTAV); ⏳ M10 (API/Dashboard dữ liệu thật; MVP dữ liệu giả QĐ-007)

### 4.3 Detector: Isolation Forest và luật tạo candidate

- `IsolationForestDetector` (`services/detector/isolation_forest.py`): đặc trưng GĐ1 mỗi metric (mean/std/min/max/last/delta) trên bộ đệm cuộn theo pod/service; `fit` chỉ trên train; điểm chuẩn hoá [0,1]; ngưỡng 0,85; không promote khi cold-start (QĐ-015); `top_features` để giải thích.
- Luật candidate (`candidates.py`): `score ≥ 0,85 → AlertCandidate(source="metric")`.
- **C5 Rescue Score** (`rescue.py`): cửa sổ chưa qua ngưỡng tính `η1·Λ_log + η2·Φ_topo + η3·Δ_time`; `Λ_log = 1 − exp(−N_err/k_log)`; `Φ_topo = max 1/(1+d_G)`; `Δ_time = max exp(−|t_w−t_a|/σ)`; `≥ τ` ⇒ `source="rescue"`; ràng buộc nhân quả (không dùng alert tương lai); lưới η bước 0,2 (21 điểm).
- Kết quả M7 (QĐ-033, `val`): η = (0; 0,4; 0,6), τ = 0,8 ⇒ rút về 2 thành phần (Λ_log không đóng góp); +2 TP/+16 FP, ΔF1 +0,001 CI chứa 0 (Phát hiện 12: nút thắt ở judge). Vai trò C5 ở M8 chờ V34 — ghi là thành phần chờ quyết định, không khẳng định đóng góp.
- Hình/bảng: **Hình 4.4** Luồng detector + Rescue gate. **Bảng 4.3** Tham số Detector/Rescue (ngưỡng, k_log, σ, η, τ) + nguồn config. **Bảng 4.4** Quét η/τ (tham chiếu Ch5).
> Nguồn: `01` §6.2; `02` §6.1–6.4; `services/detector/*`; QĐ-008, QĐ-015, QĐ-033. Trạng thái: IForest ✅; Rescue ✅ (offline, M7); không đưa vào CTAV cuối (V34 (b)); một điểm ablation trên `test` ⏳ M8

### 4.4 CTAV — Calibrated Topology-Aware Alert Validation

#### 4.4.1 Tổng quan và vai trò hiện tại của từng thành phần

- Thiết kế ban đầu (08 §4): tầng 1 BM25 → judge; tầng 2 topology (C4) khi cần; chính sách C2 gating + C3 anchoring.
- **Cấu hình chốt sau M6 (QĐ-031, `ctav_final.yaml`)**: mọi candidate → C1 → judge → θ_local = 0,80 → C3; `gating: false`, `routing.enabled: false`.
- Bảng vai trò: C1 ✅ chính (port từ paper) · C2 ✂️ bỏ (QĐ-031: bỏ C2 chỉ thêm 2 FP, ΔFPR CI [0,0000; +0,0007]) · C3 ✅ chính (ngưỡng nền `dev` p90, QĐ-030..032) · C4 ✂️ bỏ (C1 cho mọi candidate rẻ hơn: 3,28 vs 3,95–5,14 USD, F1 không thấp hơn) · C5 ✂️ chỉ là ablation (QĐ-033, V34 (b)). Code C2/C4 giữ cho ablation H3.
- Kết quả `val` (QĐ-031): F1 0,201 [0,138; 0,264] vs BM25 0,103; FPR 0,007 vs 0,056; nhưng recall 0,139 < C1 0,263 (Phát hiện 10) ⇒ chưa đạt "giữ recall của C1"; nêu như hạn chế (M6 "qua có điều kiện"; H2/H3 trên `test` ⏳ M8).
- Hình/bảng: **Hình 4.5** CTAV thiết kế vs cấu hình chốt. **Bảng 4.5** Vai trò & trạng thái C1–C5 kèm QĐ.
> Nguồn: `08` §4 (khối "Kết quả M6"), `eval/configs/ctav_final.yaml`, QĐ-027, QĐ-029..033. Trạng thái: ✅ (cấu hình `val`); kiểm định `test` ⏳ M8

#### 4.4.2 Tầng 1 — BM25 + judge (baseline cục bộ)

- `bm25_hybrid`: truy vấn BM25 trên bằng chứng cục bộ của `s_0` trong cửa sổ; truy vấn không chứa tag fault type (unit test chặn rò nhãn, paper §3.5).
- Vừa là baseline (H0) vừa là tầng 1 của thiết kế hai tầng (C4 — ablation); `no_retrieval` (LLM không RAG) là baseline cùng ngân sách.
- Hình/bảng: **Bảng 4.6** Các strategy: `bm25_hybrid`, `hybrid_bm25_graph`, `no_retrieval` (temporal/graph thuần = ablation của C1).
> Nguồn: `services/retrieval/bm25_hybrid.py`, `no_retrieval.py`; `08` §4 (QĐ-011). Trạng thái: ✅

#### 4.4.3 Tầng 2 — Topology retrieval C1 (Fusion Score)

- Công thức: `Score = α·BM25_norm + β·exp(−|t_i−t_0|/τ_F) + γ·GraphSim(s_i,s_0)`, `α+β+γ=1`, τ_F = 300 s (τ không chỉ số dành cho ngưỡng của Rescue); cấu hình A4: α 0,35, β 0,25, γ 0,40; mở rộng 2-hop; top-k = 6.
- `HybridBm25GraphRetriever` (`build_pool` → `top_events` → `reweighted`): pool BM25 top-`bm25_k` + mở rộng đồ thị (`packages/graph/service_graph.py`); ngân sách token; biến thể quota `k_graph` (C1-quota).
- Cơ chế (QĐ-026/027, Phát hiện 7): C1-quota ≡ C1-paper; hiệu ứng đến từ bằng chứng cục bộ sát t_0 (chủ yếu trace span), không từ lân cận; judge xác nhận 30–42% candidate normal có bằng chứng ⇒ động cơ của C3.
- Ablation α/β/γ (β=1, γ=1 là temporal/graph thuần) và k-hop (`m4_kgraph_val_k0..k3`).
- Hình/bảng: **Hình 4.6** Mở rộng 2-hop + xếp hạng Fusion. **Bảng 4.7** Tham số Fusion (α, β, γ, τ, k, k-hop, `bm25_k`).
> Nguồn: `08` §2, §4 (C1); `01` §5.3, §6.3; `services/retrieval/hybrid_bm25_graph.py`; `02` §6.5; QĐ-020, QĐ-026, QĐ-027. Trạng thái: ✅

#### 4.4.4 Chính sách quyết định: C3 evidence anchoring (và C2 gating)

- **C3**: TRUE_ALERT chỉ giữ khi judge trích ≥ 1 bằng chứng **bất thường của `s_0`** — log ERROR/WARN, hoặc span có `duration_ms` vượt ngưỡng nền p90 của cùng service+operation (tính trên `dev`; span không có ngưỡng ⇒ không neo được); không thì hạ UNCERTAIN (`is_abnormal`, `decide`, `apply_policy` trong `policy.py`; mở rộng `require_evidence` của GĐ1).
- Ngưỡng nền `dev` p90 chọn thay baseline trượt 60 phút (V30: trượt phủ 93% nhưng F1 thấp hơn có ý nghĩa); hạn chế: 15 service chưa có ngưỡng (Phát hiện 11, V31 (a); C3-trượt là ablation bắt buộc ở M8, QĐ-032); `span_baseline.py`.
- **C2** (✂️ bỏ): ngưỡng bất đối xứng `θ_topo > θ_local` theo hồ sơ bằng chứng/tầng sinh (QĐ-027 đổi trục từ "nguồn gốc đồ thị"; QĐ-029 V28 (b): H1 không chọn được đặc trưng nên chỉ quét θ); `PolicyConfig.threshold(tier)`; loại bởi H3 (QĐ-031).
- Tính chất: policy là **hàm thuần trên verdict đã cache** ⇒ quét θ/ablation tốn 0 lần gọi LLM; lưu cả verdict thô lẫn verdict sau policy để đo đóng góp (H3).
- Hình/bảng: **Hình 4.7** Sơ đồ quyết định (verdict thô → θ → anchoring → verdict cuối). **Bảng 4.8** Điều kiện neo C3 + độ phủ. **Hình 4.8** Ví dụ ca alert normal bị hạ bởi C3.
> Nguồn: `08` §4 (C2, C3); `01` §6.4; `services/judge/policy.py`, `span_baseline.py`; QĐ-027, QĐ-029..032. Trạng thái: C3 ✅; C2 ✂️ (QĐ-031)

#### 4.4.5 Định tuyến hai tầng thích nghi C4 (✂️ ablation)

- `routing.route`: chạy tầng 1 BM25; leo tầng 2 khi `no_context`, `uncertain` (gồm bị C2/C3 hạ) hoặc `weak_fp` (FP với confidence < `fp_confidence` = 0,95) — `escalation_reason`, `RoutingConfig`.
- Lý do bỏ (QĐ-031): toàn bộ recall thêm của C1 trên `val` nằm ở FP của BM25; TRUE_ALERT tầng 1 qua θ_local thêm nhiều FP; C1 cho mọi candidate rẻ hơn. Trình bày như thiết kế đã kiểm chứng và loại (kết quả âm).
- Hình/bảng: **Bảng 4.9** Chi phí USD/F1: two-tier vs topology-only.
> Nguồn: `services/judge/routing.py`; `08` §4 (C4); QĐ-031. Trạng thái: ✂️ (code giữ cho ablation)

#### 4.4.6 Judge: prompt, đầu ra có cấu trúc, cache LLM

- Prompt: nguyên văn prompt GĐ1 (`prompt.py`: `compose_prompt`, `alert_payload`, `context_payload`); `gemini-2.5-flash`, temperature 0, `thinkingBudget: 0`, kiểm `modelVersion` (lệch ⇒ run dừng) (QĐ-021).
- Đầu ra 3 nhãn + `confidence` + bằng chứng trích dẫn; `require_evidence_for_true_alert` hạ TRUE_ALERT → UNCERTAIN nếu thiếu bằng chứng; lỗi API: retry có trần, hết ⇒ `manual_review`.
- Cache JSONL append-only, tương thích GĐ1 (`cache.py`): key `sha256(provider|model|prompt|"max=<max_tokens>|t=0")` + `|repeat=n` khi n>0 (QĐ-013; tương đương quy tắc sha256(prompt+model+temperature+max_tokens+repeat)); lưu nguyên response + model id ⇒ tái lập, chạy offline.
- Backend: `backends.py` (Gemini, Mock — mock chỉ cho G-port), `registry.py`; phương sai đo bằng `repeat ∈ {0,1,2}` trên tập con.
- Hình/bảng: **Hình 4.9** Luồng gọi judge qua cache. **Bảng 4.10** Cấu hình judge & cache. **Hình 4.10** Ví dụ prompt/JSON đầu ra.
> Nguồn: `01` §6.4; `03` §6; `services/judge/{prompt,cache,backends,llm_judge,registry}.py`; `08` §4.1; QĐ-013, QĐ-021. Trạng thái: ✅

### 4.5 Tác tử RCA (Nhánh B)

- Ba nhiệm vụ: **grouping → propagation → summarizer** (`pipeline.py` điều phối); đầu vào là alert TRUE_ALERT từ CTAV.
- **Grouping** (`grouping.py`, thuần thuật toán, không LLM): cụm theo `T_group` (mặc định 300 s; quét {180,300,600} trên `val`) → đồ thị con từ dependency graph → mỗi thành phần liên thông = 1 `Incident` (`time_clusters`, `group_alerts`, `_incident_id`). Đo Alert Reduction Ratio = 1 − (#incident/#alert) trên cascade.
- **Propagation**: mức 1 (bắt buộc) lan ngược 1 hop từ span lỗi frontend, chọn upstream trực tiếp có bất thường; mức 2 (nếu kịp) LLM suy luận toàn call-chain; so sánh hai mức; baseline "service điểm bất thường cao nhất". Nhãn root-cause mức pod 100% (QĐ-001) ⇒ Hit@k hợp lệ; incident đa-fault = `ambiguous`, loại và báo số lượng.
- **Summarizer**: 1 lần gọi LLM / incident → `DiagnosticReport` JSON theo schema (`03` §2); validator + `diagnostic_rejected`; `require_evidence`; chặn câu lệnh thực thi; JSON valid rate ≥ 0,95.
- Lưu trữ: `incidents` vào PostgreSQL, fact vào ClickHouse; màn hình Incident detail.
- Hình/bảng: **Hình 4.11** Sơ đồ 3 bước RCA. **Hình 4.12** Ví dụ đồ thị lan truyền + root cause. **Bảng 4.11** Schema DiagnosticReport. **Bảng 4.12** Chỉ số RCA (Hit@1, Hit@3, ARR, JSON valid, E2E latency).
> Nguồn: `01` §6.5; `03` §1.5, §2; `02` §4.3; `04` M9; `services/rca_agent/grouping.py`; H5. Trạng thái: grouping ✅ (mã; chưa quét T_group); propagation, summarizer, pipeline ⏳ M9 — không mô tả như đã hoàn thành

### 4.6 Hiện thực hoá

- Công nghệ: Python (`py`), pytest/mypy/ruff, Docker Compose (profile `dev`/`full`), ClickHouse (`fact_alert_evaluation`, `fact_retrieval_trace`), PostgreSQL, API + dashboard 4 màn hình (Timeline, Alert detail, Incident detail, Experiment comparison); không K8s, vector DB, LangChain, auth (scope guard).
- Cấu trúc repo: `packages/{schemas,graph,llm,storage}`, `services/{replayer,detector,retrieval,judge,rca_agent,api,web}`, `eval/{configs,harness,results}` (`runner`, `ctav`, `compare`, `fusion_ablation`, `h1`, `kgraph`, `rescue`, `metrics`, `stats`).
- **Harness điều khiển bằng config**: không hardcode tham số; `py -m eval run|ctav|compare|ablation --config eval/configs/<name>.yaml`; ví dụ `ctav_final.yaml` (tiers, policy, routing, ngân sách, `n_boot`, `seed`).
- **Tái lập**: `run_id` bất biến `<biến_thể>_<mục_đích>_v<n>`, không ghi đè; mỗi run xuất `metrics.json`, `per_window.csv`, `retrieval.jsonl`, `config.snapshot.yaml`, `git_commit.txt`, `runtime.json`; CTAV đánh giá bằng replay verdict đã cache (0 USD); chạm `test` một lần ở M8; bootstrap CI + McNemar.
- Cổng chặn: G-port (M2: P 0,3158; R 0,375; FPR 0,0458), G-paper (M3: BM25 F1 0,703/FP 7; Topology 0,476/FP 137, cache hit 100%), G-test (M8 ⏳).
- Hình/bảng: **Hình 4.13** Cây thư mục repo ↔ mốc. **Bảng 4.13** Công nghệ & lý do. **Bảng 4.14** Output một run. **Bảng 4.15** Lệnh/config chính.
> Nguồn: `01` §7–§8; `02` §3.1–3.3; `05-agent-coding-rules.md`; `06-scope-guard.md`; AGENTS.md; `eval/harness/*`. Trạng thái: harness ✅; API/dashboard dữ liệu thật ⏳ M10; đóng gói ⏳ M12

### Danh mục hình/bảng đề xuất

- Hình 4.1–4.13; Bảng 4.1–4.15 (xem từng mục).
- Khi viết: chỉ dùng số `val` đã ghi trong experiment-log cho M6/M7; số `test` chưa có — đánh dấu "chờ M8".

---

## Chương 5 — Thực nghiệm và đánh giá

> Ghi chú cho người viết: khung GĐ1 (mục tiêu → dữ liệu → thiết lập → thước đo → kịch bản → kết quả → thảo luận) được giữ, nhưng sắp theo logic GĐ2: cổng tái lập (G-port, G-paper) → tuning trên `val` → kiểm định một lần trên `test` (G-test, M8) → RCA (H5). Mọi số trong chương là số `val`/tái lập, **chưa có số `test`**. Trạng thái: ✅ có số · ⏳ chờ mốc. Mốc hiện tại: M7 đang làm (CURRENT-MILESTONE, 2026-11-11).

### 5.1 Mục tiêu thực nghiệm và giả thuyết H0–H5

- Mục tiêu (A): chứng minh CTAV giữ recall của topology mà không tăng FPR so với BM25 trong cùng ngân sách LLM; mục tiêu (B): CTAV làm nền cho tác tử RCA định vị service gốc. Khác GĐ1 (khả thi tổng thể, ảnh hưởng ngữ cảnh), GĐ2 phát biểu thành giả thuyết kiểm định được, đăng ký trước khi chạm `test`.
- Quy ước đăng ký (cuối `docs/experiment-log.md`, mục "Đăng ký giả thuyết H0–H5 (M7)"): CI 95% bootstrap (1.000 mẫu, seed 42), McNemar chính xác hai phía α = 0,05; H2 là giả thuyết chính, H0/H3/H4 là phụ, báo p thô không hiệu chỉnh đa so sánh; chỉ số chính trên cửa sổ có telemetry.
- Trạng thái đăng ký: **ĐÃ ĐĂNG KÝ 2026-11-14** (QĐ-034, commit `be2b985`, trước mọi lần chạy trên `test`): GVHD đã được báo việc bỏ C2/C4 và kết quả C5 (V29); δ = 0,05 (V33 (a)); C5 chỉ là một điểm ablation (V34 (b)); judge chấm toàn bộ candidate của `test` (V27).
- Giả thuyết đã được định hình lại sau M4–M6 (QĐ-027: đổi trục C2/C3/H1; QĐ-031: CTAV chốt chỉ còn C1 + C3, bỏ C2 và C4) — luận văn phải nêu rõ đây là thay đổi phương pháp có ghi lại, không phải chỉnh sau khi xem `test`.

#### Bảng 5.1: Giả thuyết H0–H5, tiêu chí chấp nhận đã đăng ký và trạng thái

| | Giả thuyết | Tiêu chí chấp nhận (đã đăng ký) | Trạng thái |
|---|---|---|---|
| H0 | Topology chưa hiệu chỉnh (C1) tăng recall và tăng FPR so với BM25 | CI ΔRecall và CI ΔFPR có cận dưới > 0; McNemar fault/normal p < 0,05 | ✅ `val` (tái lập hiện tượng, không tái lập cơ chế); ⏳ `test` M8 |
| H1 | Cơ chế: TRUE_ALERT trên normal tăng theo độ gần thời gian và loại bằng chứng (trace) | Xu hướng đơn điệu + CI; **không chạy lại trên `test`** | ✅ `val` — giữ một phần (QĐ-028) |
| H2 (chính) | CTAV tốt hơn BM25 | (i) CI ΔF1 (CTAV−BM25) cận dưới > 0 và p < 0,05; (ii) CI ΔFPR không có cận dưới > 0; (iii) ΔRecall(CTAV−C1) ≥ −δ, δ = 0,05 (V33 (a)). Vế (iii) không đạt ⇒ "H2 đạt một phần" (V32 (a)) | ✅ sơ bộ `val`; ⏳ M8 |
| H3 | Từng thành phần đóng góp; thành phần đã bỏ không đóng góp | C3: bỏ C3 ⇒ CI ΔPrecision cận trên < 0; C2/C4: xác nhận bỏ; báo C3-trượt (V31) và C5 | ✅ `val`; ⏳ M8 |
| H4 | Ở ngân sách 120 lần gọi CTAV không kém LLM-không-RAG | F1(CTAV) ≥ F1(không-RAG) ở 120; báo đường {120…đủ} | ✅ `val` (điểm); ⏳ M8 |
| H5 | Tác tử RCA: Hit@1 ≥ 0,60, Hit@3 ≥ 0,80, vượt baseline "anomaly score cao nhất"; Alert Reduction ≥ 30% trên cascade | CI ΔHit@1 cận dưới > 0 | ⏳ sau M9/M10 |

> Nguồn: `docs/Final_Thesis_Phase2/08-research-direction.md` §5.1; `docs/experiment-log.md` (mục "Đăng ký giả thuyết H0–H5", cuối file; QĐ-027..033). Trạng thái: ✅ giả thuyết/tiêu chí có · ⏳ V29, V33, V34 chờ người dùng.

### 5.2 Dữ liệu và giao thức chia split

- Dữ liệu: Nezha (TrainTicket + OnlineBoutique; metric/log/trace; lỗi tiêm có chủ đích). Cửa sổ 60 s, nhãn wall-clock (QĐ-002..004), so với GĐ1 (cửa sổ 120 s, tập 300/500, kho lọc theo nhãn) — đối chiếu GĐ1 §4.2. Đồ thị dịch vụ: 56 service, 68 cạnh, trùng GĐ1 (M3).
- Chia split (QĐ-004; seed 42; `data/splits/*.json` commit cứng): nhóm theo `injection_id` (7 cửa sổ/lần tiêm không bị tách) + vùng đệm 600 s (loại 597 cửa sổ normal cùng pod); normal gán theo khối `ngày|pod`; **không lấy mẫu bớt normal** (mất cân bằng ≈ 1:135).
- Quy tắc sử dụng: `dev` (debug, không giới hạn) · `val` (tuning Fusion/C3/Rescue) · `test` (một lần, M8, sau đăng ký). Đến nay chưa config nào dùng `split: test`.
- Tập chấm chính = cửa sổ **có telemetry** (QĐ-016/017) vì Nezha chỉ có log/trace quanh lần tiêm lỗi (Phát hiện 1): `val` 7.636 cửa sổ, 209 fault; toàn split là số phụ. Tập GĐ1 cho tái lập: `paper_300` (G-port), `paper_500` = 100 fault + 400 normal, 56 service (G-paper).

#### Bảng 5.2: Kích thước split và tỷ lệ cửa sổ có telemetry

| Split | Cửa sổ | Fault | Lần tiêm lỗi | Fault có telemetry | Normal có telemetry |
|---|---|---|---|---|---|
| dev | 19.316 | 149 | 21 | 149/149 | 4.881/19.167 (25,5%) |
| val | 28.898 | 209 | 30 | 209/209 | 7.427/28.689 (25,9%) |
| test | 46.849 | 346 | 50 | 346/346 | 11.639/46.503 (25,0%) |

#### Bảng 5.3: Có bằng chứng ⇔ gần sự cố (động lực của tập chấm chính)

| | Fault (98) | Normal (391) |
|---|---|---|
| Kho GĐ1/paper (lọc theo nhãn): top-6 không rỗng | 89 (90,8%) | 21 (5,4%) |
| Kho GĐ2 đầy đủ: top-6 không rỗng | 98 (100%) | 76 (19,4%) |
| Có file log/trace ±8 phút | 98 (100%) | 106 (27,1%) |

> Nguồn: Bảng 5.2 — `docs/experiment-log.md` QĐ-004 + `docs/milestones/M1-detector-bm25-judge.md` Bảng M1-3. Bảng 5.3 — M1 Bảng M1-2 (`scripts/evidence_coverage.py`). Quy tắc: `02-data-and-experiment-protocol.md` §2. Trạng thái: ✅.

### 5.3 Thiết lập thực nghiệm

- Judge duy nhất: Gemini qua API, temperature 0, `repeat` 0 mặc định; mọi lời gọi qua cache (key = sha256(prompt + model + temperature + max_tokens + repeat)). G-paper dùng `gemini-2.5-flash-lite` (cache paper); GĐ2 trên `val` dùng `gemini-2.5-flash` (V12) và bỏ cột `PodSuccessRate(%)` khỏi prompt (V20, Phát hiện 5) — cần giải thích lý do trong luận văn (Bảng M4-4, QĐ-022).
- Detector: Isolation Forest, ngưỡng 0,85, fit trên `dev`. Candidate `val`: 5.677 toàn split, 1.749 trên tập chính (recall detector 0,52 [0,45–0,59], FPR 0,221).
- Ngân sách: "đủ" và 120 lần gọi theo thứ tự thời gian; đường {120, 250, 500, 1.000, 2.000, 4.000, đủ}. Retrieval: BM25 (`bm25_hybrid`); C1 (`hybrid_bm25_graph`, α/β/γ = 0,35/0,25/0,40, 2-hop, τ 300 s), C1-quota (`k_graph`). Engine vectorized ≈ 0,45 s/lần (Bảng M4-1).
- Cấu hình: toàn bộ ở `eval/configs/*.yaml`, không hardcode; mỗi run → `eval/results/<run_id>/`, không ghi đè. CTAV đánh giá bằng **replay verdict đã cache** (`py -m eval ctav`, 0 USD), khớp run gốc 0 lệch (M6).
- Vận hành: Docker compose (profile dev/full); judge song song 8 worker, RateLimiter 200 lần/phút (tier 1, V11); ~25 phút/run `val` judge thật (M2).

#### Bảng 5.4: Chi phí API theo mốc

| Mốc | Nội dung | Chi phí | Ghi chú |
|---|---|---|---|
| M2 | Smoke judge 196 lần gọi | 0,056 USD | ước một run `val` ≈ 0,50 USD |
| M3 | Smoke `gemini-2.5-flash` 196 lần | ≈ 0,23 USD | G-paper tái lập từ cache = 0 USD |
| M4 | Probe + smoke + H0 (≈ 4.722 + 4.808 lần gọi…) | ≈ 8,6 USD theo token | **Billing người dùng báo 5 USD, ≈ 8k request, chưa đối chiếu được** (QĐ-026, V26) |
| M5 | H1: 6.988 lần gọi thành công | 9,4755 USD theo token | ước tính, không phải billing |
| M6 | CTAV: replay | 0 USD | mô phỏng 3,28 USD/run C1 mọi candidate |
| M7 | Rescue: 1.459 lần gọi | 1,03 USD theo token | `m7_rescue_val_c1_v1` |
| M8 (đang chạy) | Chấm `test`, toàn bộ candidate (V27) | BM25 8,87 + C1 4,71 USD theo token đã chạy; còn không-RAG, `repeat`, C5 [CHỜ M8] | ước ban đầu 13,0 USD (QĐ-035); `test` có 13.699 candidate |

> Nguồn: `docs/milestones/M2..M7`; `eval/configs/*.yaml`; `services/judge/backends.py` (`PRICES_PER_1M`). Cảnh báo: giá chưa đối chiếu billing (V26). Trạng thái: ✅ (chưa có tổng USD M1; bổ sung nếu cần tổng cộng).

### 5.4 Thước đo

- Phân loại (nhánh A): Precision, Recall, F1, FPR (`02` §4.1). Recall tính trên **toàn bộ fault window** của split (không chỉ candidate); `manual_review` không tính là alert; chỉ số chính trên tập telemetry, toàn split là phụ.
- Thống kê: bootstrap CI 95% (multinomial 8 ô, có cặp), McNemar chính xác tách fault/normal; Δ = biến thể − so sánh (`eval/harness/stats.py`, `compare.py`). Phương sai LLM: `repeat` 0/1/2, tỷ lệ "lật" verdict.
- Retrieval: tỷ lệ bằng chứng lân cận, root hit, root lỗi cùng lúc, latency trung bình/P95, token trung bình; context precision chấm tay 50 cửa sổ (M8, `eval/manual/`) ⏳.
- RCA (nhánh B): Hit@1, Hit@3, Alert Reduction Ratio, JSON valid rate, E2E latency; chất lượng chẩn đoán chấm tay 30 incident (thang 0–2, M11) ⏳.
- Chi phí/vận hành: lần gọi LLM, token, USD theo token, cache hit, thời gian run.

> Nguồn: `02-data-and-experiment-protocol.md` §4–5; `eval/harness/metrics.py`, `stats.py`, `compare.py`. Trạng thái: ✅ (thước đo đã cài); chấm tay ⏳ M8/M11.

### 5.5 Kiểm chứng tái lập (G-port, G-paper)

#### 5.5.1 G-port (M2) — port đúng GĐ1 Phase 4

- Cấu hình GĐ1 Phase 4: judge mock, `paper_300`, threshold 0,95, gate 0,80/0,98, ngân sách 30 → Precision 0,3158 (6 TP / 13 FP), Recall 0,375, FPR 0,0458 (`gd1_phase4_parity.yaml`, run `gd1_phase4_parity_v1`).
- Theo tầng: retrieval 40/40, judge mock 30/30, tầng 3a (đầu vào candidate GĐ1) 6/13/10/271 trùng tuyệt đối; tầng 3b (toàn pipeline GĐ2) 6/19/10/265 (P 0,2400, FPR 0,0669) — lệch FP +6 do detector khác (Spearman 0,79), đã phân rã; người dùng chốt "đạt theo tầng" (V10 (a), QĐ-019).
- Phát hiện kèm: 10/13 FP của Phase 4 GĐ1 đến từ quy tắc "hết ngân sách → route_alert" (cả 10 là normal); judge chỉ gây 3 FP.

#### 5.5.2 G-paper (M1, M3) — baseline khoa học

- Tái lập Table 1 paper ICAETM 2026 (`paper_500`, `gemini-2.5-flash-lite`) từ cache, 489/489 cache hit, không gọi API; nửa BM25 đạt từ M1 (Bảng M1-1).
- BM25: TP 58 / FP 7, F1 **0,7030**; Topology: TP 74 / FP 137, F1 **0,4759** — trùng chính xác paper.
- Phát hiện liên quan: P1 (95% normal của paper không có bằng chứng ⇒ FP = 7 là hệ quả giao thức), P2 (confidence ≈ `anomaly_score` chép lại), P3 (biến thể "topology" chủ yếu là BM25 không giới hạn thời gian), P4 (C1 đúng paper không đưa bằng chứng lân cận: 0/810 event, 0/196 prompt).

#### Bảng 5.5: Kiểm chứng G-port theo tầng (M2-1)

| Tầng | Kết quả | Đạt |
|---|---|---|
| 1. Retrieval BM25 | top-6 trùng 40/40 | ✅ |
| 2. Judge mock | 30/30 | ✅ |
| 3a. Gate + ngân sách + quyết định (candidate GĐ1) | 6/13/10/271 = GĐ1 | ✅ |
| 3b. Toàn pipeline GĐ2 | 6/19/10/265 (lệch FP +6) | ⚠ chấp nhận V10 (a) |
| 4. Detector | Spearman 0,79 | so phân phối |

#### Bảng 5.6: Kiểm chứng G-paper (M3-1)

| Biến thể | Top-6 / prompt / cache trùng | TP | FP | P | R | F1 (paper) |
|---|---|---|---|---|---|---|
| BM25 | 489/489/489 | 58 | 7 | 0,8923 | 0,58 | 0,7030 (0,7030) |
| Topology | 489/489/489 | 74 | 137 | 0,3507 | 0,74 | 0,4759 (0,4759) |

> Nguồn: `M2-harness-gport.md`, `M3-graph-c1-gpaper.md`, `M1-detector-bm25-judge.md`; run `gd1_phase4_parity_v1`; `eval/results/gpaper_viewA_paper500.json`, `gport_layers_phase4.json`; `scripts/check_gd1_parity.py`, `scripts/gport_layers.py`. Trạng thái: ✅.

### 5.6 Kết quả trên `val` (tuning và lựa chọn phương pháp)

#### 5.6.1 H0 trên `val` — tái lập hiện tượng, không tái lập cơ chế (M4)

- Tập telemetry (7.636 cửa sổ, 209 fault): C1-paper − BM25: ΔRecall +0,100 [+0,052; +0,155], ΔFPR +0,025 [+0,020; +0,031], McNemar p = 5,1e-4 (fault) / 5,0e-24 (normal) ⇒ cùng chiều paper nhưng nhỏ hơn nhiều.
- C1-quota (k = 1) − C1-paper: ΔRecall −0,010 [−0,044; +0,028], ΔFPR −0,003 ⇒ quota lân cận không đổi gì. Mọi biến thể có judge precision 0,075–0,098, F1 không khác detector-only (0,111).
- Phát hiện 5 (`PodSuccessRate(%)` ≡ 0; bỏ cột: FP 25 → 1), P6 (trọng số Fusion không điều khiển bằng chứng lân cận; giữ trọng số paper), P7 (C1 chọn trace sát thời điểm: median |Δt| 66–73 s so với 139–167 s).

#### Bảng 5.7: H0 trên `val` (M4-6)

| Phương pháp | TP | FP | P | R [CI95] | F1 [CI95] | FPR |
|---|---|---|---|---|---|---|
| Detector-only | 109 | 1.640 | 0,062 | 0,522 [0,454; 0,589] | 0,111 [0,094; 0,131] | 0,221 |
| BM25 | 34 | 417 | 0,075 | 0,163 [0,115; 0,214] | 0,103 [0,072; 0,133] | 0,056 |
| C1-paper (k=0) | 55 | 606 | 0,083 | 0,263 [0,205; 0,326] | 0,126 [0,095; 0,156] | 0,082 |
| C1-quota (k=1) | 53 | 585 | 0,083 | 0,254 [0,197; 0,315] | 0,125 [0,094; 0,156] | 0,079 |
| LLM không RAG (`require_evidence: false`) | 18 | 166 | 0,098 | 0,086 [0,052; 0,128] | 0,092 [0,056; 0,134] | 0,022 |

#### Bảng 5.8: Hiệu số có cặp và McNemar (M4-7)

| So sánh | ΔRecall | ΔFPR | ΔF1 | p (fault / normal) |
|---|---|---|---|---|
| C1-paper − BM25 | +0,100 [+0,052; +0,155] | +0,025 [+0,020; +0,031] | +0,023 [−0,004; +0,052] | 5,1e-4 / 5,0e-24 |
| C1-quota − BM25 | +0,091 [+0,040; +0,145] | +0,023 [+0,018; +0,028] | +0,022 | 1,3e-3 / 2,2e-20 |
| C1-quota − C1-paper | −0,010 | −0,003 | −0,001 | 0,79 / 0,16 |
| Không RAG − BM25 | −0,077 | −0,034 | −0,011 | 2,5e-3 / 4,0e-31 |

> Nguồn: `M4-h0.md` (Bảng M4-1..7); QĐ-022..027; `eval/results/h0_val_{bm25_v3,c1_k0_v1,c1_k1_v1,norag_v1}`, `h0_val_compare_v1`, `h0_val_compare_k1_vs_k0_v1`, `h0_val_evidence_diff_v1`. Trạng thái: ✅ `val`; ⏳ `test` M8.

#### 5.6.2 Tuning C1: `k_graph` và Fusion α/β/γ (M4)

- Quét `k_graph` 0–3 (retrieval-only): root hit 109/109 ở mọi k ⇒ proxy suy biến, chọn k = 1 theo quy tắc hòa (V18, QĐ-024) — phải nêu thẳng.
- Ablation α/β/γ (32 điểm, bước 0,25 + trọng số paper): không quota thì gần như toàn local (3 candidate có lân cận); temporal-only mất bằng chứng root (root hit 9/109); giữ trọng số paper.

#### Bảng 5.9: Quét `k_graph` trên `val` (M4-3)

| k | Root hit (/109) | Normal có lân cận (/1.640) | Root lỗi cùng lúc (/166) | Tỷ lệ chỗ local |
|---|---|---|---|---|
| 0 | 109 | 3 | 0 | 0,997 |
| 1 | 109 | 1.177 | 7 | 0,831 |
| 2 | 109 | 1.177 | 10 | 0,665 |
| 3 | 109 | 1.177 | 16 | 0,499 |

> Nguồn: `M4-h0.md` Bảng M4-3, M4-5; `eval/results/m4_kgraph_val_k0..k3_v1`, `m4_kgraph_selection_v2.json`, `m4_fusion_ablation_val_v1/`. Trạng thái: ✅.

#### 5.6.3 H1 — cơ chế thiên lệch xác nhận (M5)

- Mẫu cố định `eval/samples/h1_val_v1.json.gz` (1.749 candidate: 1.640 normal, 109 fault), 9 điều kiện, judge thật. Thứ tự bằng chứng không tác dụng đo được; điểm hiển thị tác động nhỏ (+0,020, p = 0,0617).
- Độ gần thời gian: độ dốc normal +0,094 [+0,050; +0,134], fault +0,230 [+0,086; +0,370]; chững từ 67%. Loại bằng chứng mạnh nhất: trace `s0` 0,507 vs log 0,181 (≈ 2,8 lần).
- Tác động không riêng cho normal (tăng cả recall) ⇒ độ nhạy chung của judge; `ref` gần như không phân biệt nhãn (0,515 vs 0,505). Nhiễu judge nhỏ (lật 0,007 / 0,035). QĐ-028: **giữ một phần**; không chọn đặc trưng nào cho C2 (V28 (b)).

#### Bảng 5.10: Tỷ lệ TRUE_ALERT thô theo điều kiện can thiệp (M5-1, trích)

| Điều kiện | normal [CI95] | fault [CI95] |
|---|---|---|
| `ref` | 0,515 [0,486; 0,543] | 0,505 [0,404; 0,596] |
| `time_0` / `time_33` / `time_67` | 0,515 / 0,554 / 0,611 | 0,411 / 0,625 / 0,643 |
| `near_trace` | 0,608 [0,570; 0,646] | 0,667 [0,544; 0,789] |
| `near_log` | 0,181 [0,146; 0,215] | 0,211 [0,105; 0,316] |
| `neighbor_trace` | 0,277 [0,243; 0,314] | 0,386 [0,263; 0,509] |

> Nguồn: `M5-h1.md` (Bảng M5-1..6); QĐ-028, QĐ-029; `eval/results/h1_val_analysis_v2/h1_analysis.json`, `h1_val_*_r{0,1,2}_v1`. Chi phí M5 9,4755 USD (ước theo token). Trạng thái: ✅.

#### 5.6.4 C3 (neo bằng chứng), C2/C4 và lý do loại (M6)

- C3: ngưỡng `duration_ms` nền; P8: ngưỡng "phân vị trên `dev`" chỉ phủ 33,2% span `h0_val_bm25_v3`, 31,8% `h0_val_c1_k0_v1` (15 service không có normal trong `dev`); baseline trượt phủ 93%. Chọn `dev` p90 theo quy tắc ghi trước; baseline trượt giữ làm ablation (V31).
- C4 loại (P9): tầng 1 BM25 θ_local 0,80 sinh 276 cảnh báo, 15 TP / 261 FP; bước 1: bỏ C4 ΔF1 +0,036 [+0,022; +0,049], rẻ hơn 1,6 USD. C2 loại: bỏ C2 chỉ thêm 2 FP, ΔFPR +0,0003 [+0,0000; +0,0007] (QĐ-029). Cấu hình chốt `ctav_final.yaml` = C1 mọi candidate → judge → θ 0,80 → C3 (`dev` p90).
- CTAV trên `val`: F1 0,201 [0,138; 0,264] vs BM25 0,103 (ΔF1 +0,098 [+0,046; +0,149]); FPR 0,0069 vs 0,056. Nhưng Recall 0,139 < C1 0,263 (P10: mất chủ yếu `network_delay`, mọi neo là span); vế (iii) H2 chỉ đạt với δ ≥ 0,124 ⇒ dự kiến "H2 đạt một phần" (V32 (a)). P11: ngưỡng `dev` thắng một phần nhờ "im lặng có cấu trúc" — rủi ro hiệu lực lớn nhất trước M8.

#### Bảng 5.11: H3 tại cấu hình chốt, `val` telemetry (M6 Bảng 1 / M6-5)

| Biến thể | TP | FP | P | R | F1 [CI95] | FPR | USD | ΔF1 [CI95] |
|---|---:|---:|---:|---:|---|---:|---:|---|
| **CTAV** | 29 | 51 | 0,363 | 0,139 | 0,201 [0,138; 0,264] | 0,0069 | 3,28 | |
| + C2 | 29 | 49 | 0,372 | 0,139 | 0,202 | 0,0066 | 3,28 | +0,001 |
| bỏ C3 (= C1) | 55 | 606 | 0,083 | 0,263 | 0,126 | 0,0816 | 3,28 | −0,074 [−0,124; −0,027] |
| + C4 | 31 | 90 | 0,256 | 0,148 | 0,188 | 0,0121 | 5,14 | −0,013 [−0,030; +0,008] |
| C3 baseline trượt | 34 | 255 | 0,118 | 0,163 | 0,137 | 0,0343 | 3,28 | −0,064 [−0,109; −0,022] |

#### Bảng 5.12: CTAV so với baseline (H2 sơ bộ, `val`; chưa phải kiểm định) (M6-6)

| | F1 [CI95] | Recall | FPR | CTAV − X: ΔF1 [CI95] |
|---|---|---:|---:|---|
| BM25 | 0,103 [0,072; 0,133] | 0,163 | 0,056 | +0,098 [+0,046; +0,149] |
| C1 | 0,126 [0,095; 0,156] | 0,263 | 0,082 | +0,074 [+0,027; +0,124] |
| LLM không RAG | 0,092 [0,056; 0,134] | 0,086 | 0,022 | +0,109 [+0,051; +0,174] |
| Detector-only | 0,111 [0,094; 0,131] | 0,522 | 0,221 | |

> Nguồn: `M6-ctav.md`; QĐ-030..032; `eval/configs/ctav_final.yaml`; runs `ctav_final_val_v1`, `m6_anchor_features_val_v1`, `m6_ctav_select_val_v1/_v2`, `m6_span_baseline_v1`, `m6_rolling_probe_v1`. Trạng thái: ✅ `val`; lần nhìn `val` thứ hai (bước 2) làm số lạc quan — chỉ `test` không thiên lệch (nêu ở 5.10).

#### 5.6.5 C5 — Rescue Score (M7)

- A = cảnh báo CTAV (không nhãn, nhân quả, cửa sổ 300 s); tính offline 147 tổ hợp (η1, η2, η3, τ), chấm một lần 1.459 cửa sổ được cứu (1,03 USD theo token). Chọn η = (0; 0,4; 0,6), τ = 0,8 ⇒ công thức **rút về 2 thành phần** (Φ_topo, Δ_time; Λ_log không đóng góp).
- Kết quả: +52 lần gọi; +2 TP / +16 FP; ΔF1 +0,001 [−0,014; +0,022], ΔRecall +0,010 [0,000; +0,025], ΔFPR +0,0022 [+0,0011; +0,0034], McNemar p = 0,0013 (16 vs 2). P12: C5 không thêm được recall; nút thắt ở judge (21 fault đưa vào: 16 bị C1 trả FALSE_POSITIVE, 3 bị C3 hạ); Λ_log gần như luôn 0 (13 cửa sổ).
- Vai trò C5 ở M8: chỉ là ablation, một điểm không quét (V34 (b), QĐ-034).

#### Bảng 5.13: Rescue trên CTAV (M7-1)

| | η (Λ, Φ, Δ) | τ | +lần gọi | TP | FP | R | F1 [CI95] | FPR |
|---|---|---:|---:|---:|---:|---:|---|---:|
| CTAV | | | 0 | 29 | 51 | 0,139 | 0,201 [0,138; 0,264] | 0,0069 |
| CTAV + C5 | (0; 0,4; 0,6) | 0,8 | 52 | 31 | 67 | 0,148 | 0,202 [0,143; 0,261] | 0,0090 |

> Nguồn: `M7-rescue-dang-ky.md`; QĐ-033 (Bảng M7-1, M7-2); `eval/results/m7_rescue_features_val_v1`, `m7_rescue_plan_val_v1`, `m7_rescue_val_c1_v1`, `m7_rescue_val_v1` (`rescue.json`, `points.csv`), `m7_anchor_features_rescue_val_v1`. Trạng thái: ✅ `val`.

### 5.7 Kết quả trên `test` (G-test, M8) — ⏳ CHỜ M8

- Điều kiện mở (đã đạt 2026-11-14): bản đăng ký H0–H5 "ĐÃ ĐĂNG KÝ" và commit riêng `be2b985`; phạm vi chấm V27 = toàn bộ candidate; config `test` sao từ `val` (chỉ đổi `split`, `g_test`, `run_id`) theo danh sách 9 nhóm trong bản nháp đăng ký.
- Chạy một lần: BM25, C1, không-RAG, detector-only, replay CTAV + ablation (+C2 0,85; bỏ C3; +C4 0,95; C3-trượt), C5 một điểm; `repeat` 1, 2 trên tập con 200 cửa sổ; chấm tay context precision 50 cửa sổ. Kết luận H2 viết ra **dù kết quả là gì**.
- Rủi ro báo trước: P11 (phân bố service `test` khác `val`).

#### Bảng 5.14: Kết quả H0–H4 trên `test` (placeholder)

| Giả thuyết | So sánh | Chỉ số | Giá trị [CI95] | p (fault / normal) | Tiêu chí đạt (đã đăng ký) | Kết luận | Run_id |
|---|---|---|---|---|---|---|---|
| H0 | C1 − BM25 | ΔRecall, ΔFPR | ⏳ | ⏳ | CI cận dưới > 0 cả hai; p < 0,05 | ⏳ | ⏳ |
| H2 (i) | CTAV − BM25 | ΔF1 | ⏳ | ⏳ | cận dưới > 0, p < 0,05 | ⏳ | ⏳ |
| H2 (ii) | CTAV − BM25 | ΔFPR | ⏳ | ⏳ | cận dưới không > 0 | ⏳ | ⏳ |
| H2 (iii) | CTAV − C1 | ΔRecall | ⏳ | ⏳ | ≥ −δ (δ = 0,05) | ⏳ | ⏳ |
| H2 phụ | CTAV − {C1, không-RAG, detector-only} | ΔF1 | ⏳ | ⏳ | — | ⏳ | ⏳ |
| H3 | bỏ C3 / +C2 / +C4 / C3-trượt / +C5 | ΔPrecision, ΔFPR, ΔF1, chi phí | ⏳ | ⏳ | theo bản đăng ký | ⏳ | ⏳ |
| H4 | CTAV vs không-RAG, ngân sách 120 | F1 | ⏳ | ⏳ | F1(CTAV) ≥ F1(không-RAG) | ⏳ | ⏳ |
| H5 | RCA vs baseline | Hit@1, Hit@3, ARR | ⏳ | ⏳ | xem Bảng 5.1 | ⏳ (sau M9/M10) | ⏳ |

> Nguồn (khi có): `eval/results/comparison_final/` (roadmap M8), `ctav_final_test`, `h0_test_*`. Hiện chưa có run `test` (CURRENT-MILESTONE; M7 §1). Trạng thái: ⏳ M8 (ngân sách ≈ 17 USD).

### 5.8 Ablation và đường cong (θ, ngân sách, τ)

- Đã có trên `val` (✅): đường θ_topo (Bảng 5.15), đường ngân sách (5.16), đường τ Rescue (5.17), ablation Fusion α/β/γ × `k_graph` (5.9), ablation thành phần H3 (5.11), lưới 147 tổ hợp Rescue (`points.csv`).
- Lưu ý khi trình bày: confidence của judge rời rạc (0,80/0,85/0,90) nên đường θ chỉ có bậc; đoạn phẳng ngân sách 250–1.000 do candidate thứ 250–1.000 không có telemetry; CI ở ngân sách 120 chồng nhau (`ctav.json`); đường τ: recall phẳng 0,148 từ τ 0,3 đến 0,8 trong khi FPR giảm (hạ τ chỉ thêm FP).
- Chờ (⏳ M8): xác nhận ablation H3 và đường ngân sách trên `test`; θ/τ chọn trên `val`, báo cáo một điểm trên `test`. Không quét Rescue trên `test` (chủ ý, V34).

#### Bảng 5.15: Đường θ_topo (C1 mọi candidate, C3 `dev` p90) (M6-4)

| θ_topo | TP | FP | Recall | FPR | F1 |
|---|---:|---:|---:|---:|---:|
| 0,80 | 29 | 51 | 0,139 | 0,0069 | 0,201 |
| 0,85 | 29 | 49 | 0,139 | 0,0066 | 0,202 |
| 0,90 | 27 | 47 | 0,129 | 0,0063 | 0,191 |
| 0,95 | 2 | 2 | 0,010 | 0,0003 | 0,019 |

#### Bảng 5.16: F1 theo ngân sách lần gọi (H4, `val`) (M6-7)

| Ngân sách | CTAV | BM25 | C1 | Không RAG |
|---:|---|---|---|---|
| 120 | 0,028 (3 TP/0 FP) | 0,016 (2/44) | 0,023 (3/52) | 0,000 (0/8) |
| 250 = 500 = 1.000 | 0,109 (12/0) | 0,081 (12/75) | 0,076 (12/95) | 0,053 (6/11) |
| 2.000 | 0,195 (23/4) | 0,127 (26/175) | 0,141 (38/292) | 0,092 (12/39) |
| 4.000 | 0,207 (25/7) | 0,096 (28/345) | 0,115 (42/479) | 0,075 (12/97) |
| đủ (5.677) | 0,201 (29/51) | 0,103 | 0,126 | 0,092 |

#### Bảng 5.17: Đường τ Rescue tại η = (0; 0,4; 0,6) (M7-2)

| τ | 0,3 | 0,4 | 0,5 | 0,6 | 0,7 | 0,8 | 0,9 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Cửa sổ được cứu | 1.286 | 1.130 | 614 | 447 | 159 | 52 | 4 |
| Lần gọi LLM | 6.963 | 6.807 | 6.291 | 6.124 | 5.836 | 5.729 | 5.681 |
| Recall | 0,148 | 0,148 | 0,148 | 0,148 | 0,148 | 0,148 | 0,139 |
| FPR | 0,0137 | 0,0133 | 0,0124 | 0,0116 | 0,0097 | 0,0090 | 0,0070 |
| F1 | 0,181 | 0,183 | 0,187 | 0,190 | 0,199 | 0,202 | 0,200 |

> Nguồn: Bảng 5.15 — `docs/experiment-log.md` Bảng M6-4; `m6_ctav_select_val_v1/_v2`. Bảng 5.16 — Bảng M6-7; `ctav_final_val_v1/ctav.json` → `budget_curve`; run ngân sách thật `h0_val_{bm25,c1_k0,norag}_b120_v1`. Bảng 5.17 — Bảng M7-2; `m7_rescue_val_v1/rescue.json` → `tau_curve`. Trạng thái: ✅ `val`; ⏳ `test` M8. Hình cần sinh từ script `eval/` (không vẽ tay): đường θ, ngân sách, τ.

### 5.9 Đánh giá RCA (H5): Hit@1 / Hit@3 — ⏳ CHỜ M9–M10 (và M11)

- Theo roadmap (`04` M9–M11): M9 hoàn thiện `grouping` (quét `T_group ∈ {180, 300, 600}` s trên `val`), `propagation` mức 1 (backward 1-hop) và mức 2 (LLM full call chain, cắt đầu tiên nếu trễ), `summarizer` JSON; DoD M9: ARR ≥ 30% trên network_delay, Hit@1/Hit@3 mức 1, JSON valid rate ≥ 0,95 **trên `val`**. Số **chính thức H5 trên `test`** chỉ có sau M10 (end-to-end, E2E latency, token, cache hit); M11: chấm tay 30 incident + phân tích ca sai.
- Hiện có: `services/rca_agent/grouping.py` bản khởi động (M6) + `Incident` + `tests/test_grouping.py`; chưa chạy trên alert thật. Chưa có Hit@k nào.
- Lưu ý: H5 phụ thuộc recall CTAV (0,139 trên `val`, P10) — số incident cascade có thể ít; báo số incident `ambiguous` bị loại (`02` §4.3).

#### Bảng 5.18: Kết quả RCA (placeholder)

| Phương pháp | Mức | Hit@1 [CI] | Hit@3 [CI] | ARR | JSON valid | E2E latency | Split | Run_id |
|---|---|---|---|---|---|---|---|---|
| Baseline "anomaly score cao nhất" | — | ⏳ | ⏳ | — | — | — | `val`/`test` | ⏳ |
| RCA mức 1 (backward 1-hop) | 1 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | `val` (M9), `test` (M10) | ⏳ |
| RCA mức 2 (LLM call chain) | 2 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | như trên | ⏳ |
| Chẩn đoán chấm tay (30 incident, thang 0–2) | — | ⏳ | | | | | `test` (M11) | `eval/manual/diagnostic_quality.csv` |

> Nguồn: `04-implementation-roadmap.md` §M9–M11; `02` §4.3–4.4; `08` §5.1 (H5). Trạng thái: ⏳ M9 (val) → M10 (test) → M11 (chấm tay).

### 5.10 Phân tích và thảo luận

- **Giao thức quyết định kết quả (P1, P3, P4).** Số paper (BM25 F1 0,703 / Topology 0,476) chịu ảnh hưởng giao thức: kho lọc theo nhãn, BM25 không giới hạn thời gian, tag fault lộ vào truy vấn. Trên giao thức đầy đủ (7.636 cửa sổ, 209 fault) mọi phương pháp có judge đạt F1 ≈ 0,09–0,13, khác xa 0,70. Liên hệ GĐ1 §4.8: kết quả "khả thi" của GĐ1 phải được đọc lại.
- **Hiện tượng đúng, cơ chế sai (P7, H0/H1).** Topology tăng recall và FPR như paper nhưng không nhờ bằng chứng lân cận (0 event ở C1-paper; thêm quota không đổi); khác biệt nằm ở *bằng chứng cục bộ nào* (trace sát thời điểm). H1 giữ một phần: độ gần thời gian và loại bằng chứng tăng cả TP lẫn FP ⇒ judge nhạy chung với bằng chứng, không chỉ thiên lệch xác nhận.
- **Judge và prompt (P2, P5).** Confidence chủ yếu là `anomaly_score` chép lại (83% prompt không context); cột `PodSuccessRate(%)` ≡ 0 khiến Gemini 3.x không bác bỏ; đổi judge sang `gemini-2.5-flash` + bỏ cột là quyết định phương pháp có ghi nhận, ảnh hưởng mọi so sánh.
- **CTAV: giảm FP, không giữ recall (P8–P11).** F1 0,201 so với 0,103 (BM25), FPR giảm 8 lần so với BM25 (12 lần so với C1), nhưng recall 0,139 < 0,263 của C1: mục tiêu (A) "giữ recall topology" chưa đạt trên `val` — H2 dự kiến "đạt một phần". C2 và C4 bị loại theo tiêu chí H3. Rủi ro hiệu lực: 15 service không có ngưỡng `dev`; lần nhìn `val` thứ hai; chỉ `test` không thiên lệch.
- **C5 (P12).** Rescue thêm ≤ 2 TP trên 100 fault bị detector bỏ sót; nút thắt ở judge, không ở cổng Rescue ⇒ kết quả âm có giá trị (hướng GĐ3: cải thiện judge/log).
- **Chi phí, vận hành.** Một run `val` ≈ 0,5–3,3 USD tùy retrieval; chi phí theo token chưa đối chiếu billing (V26); ngân sách 120 lần gọi chỉ phủ ≈ 7% candidate telemetry ⇒ H4 cần đường cong. Liên hệ GĐ1 (local-first, ổn định streaming): GĐ2 chốt judge API duy nhất (QĐ-013).
- **Hạn chế:** một dataset (Nezha), một judge, phương sai `repeat` chỉ đo trên tập con, so sánh phụ không hiệu chỉnh đa so sánh, H5 chưa có số.

#### Bảng 5.19: Tổng hợp Phát hiện 1–12 (nguồn và vai trò)

| P | Nội dung ngắn | Nguồn | Dùng ở mục |
|---|---|---|---|
| 1 | Có bằng chứng ⇔ gần sự cố (paper: 5,4% normal có bằng chứng) | M1; QĐ-016 | 5.2, 5.5 |
| 2 | Confidence ≈ `anomaly_score` chép lại (83% / 45% / 8%) | M2 (cập nhật QĐ-019) | 5.10 |
| 3 | "Topology" của paper ≈ BM25 không giới hạn thời gian | QĐ-020 | 5.5, 5.10 |
| 4 | C1-paper không đưa bằng chứng lân cận (0/810 event) | M3; QĐ-021 | 5.5 |
| 5 | `PodSuccessRate(%)` ≡ 0 ⇒ Gemini 3.x không bác bỏ | M4; QĐ-022 | 5.6.1 |
| 6 | Trọng số Fusion không điều khiển bằng chứng lân cận | M4; QĐ-025 | 5.6.2 |
| 7 | H0 tái lập hiện tượng, không cơ chế | M4; QĐ-026 | 5.6.1 |
| 8 | Ngưỡng `dev` chỉ phủ 31,8–33,2% span | M6; QĐ-030 | 5.6.4 |
| 9 | C4 không đóng góp (261 FP/15 TP ở tầng 1) | M6; QĐ-031 | 5.6.4 |
| 10 | CTAV giảm FP, không giữ recall | M6; QĐ-031 | 5.6.4, 5.10 |
| 11 | Ngưỡng `dev` thắng nhờ "im lặng có cấu trúc" | M6; QĐ-031 | 5.6.4, 5.10 |
| 12 | C5 không thêm recall (≤ 2 TP) | M7; QĐ-033 | 5.6.5 |

> Nguồn: `docs/experiment-log.md` (các mục "Phát hiện n"); `docs/milestones/M1..M7`. Trạng thái: ✅ (thảo luận dựa trên `val`; cập nhật sau M8 và M9–M10).

---

**Phụ lục chương (gợi ý):** run_id liên quan (`eval/results/`): `gd1_phase4_parity_v1`; `h0_val_bm25_{v1,v2,v3,b120_v1}`, `h0_val_c1_k0_{v1,b120_v1}`, `h0_val_c1_k1_{v1,b120_v1}`, `h0_val_norag_{v1,reqev_v1,b120_v1}`, `h0_val_compare_{v1,k1_vs_k0_v1}`, `h0_val_evidence_diff_v1`; `h1_val_*`, `h1_val_analysis_v2`; `m4_kgraph_val_k0..k3_v1`, `m4_fusion_ablation_val_v1`; `m6_anchor_features_val_v1`, `m6_ctav_select_val_v{1,2}`, `ctav_final_val_v1`; `m7_*_val_*`; `val_detector_count_v1`. Các run smoke `m1..m4_*_smoke_*` không đưa vào bảng kết quả. Lệnh tái lập: cuối mỗi báo cáo milestone.

---


> Số `val` từ `docs/experiment-log.md` (QĐ-026, 028, 031, 033), **chưa** là kết quả cuối. Số `test` = `[CHỜ M8]`. Không dùng số mock làm kết luận.

---

## Chương 6 — Demo platform

### 6.1 Vai trò của platform
- Platform là hiện thực của CTAV: cùng một pipeline chạy thực nghiệm và demo.
- Tối ưu cho tái lập, không cho production; không auth, multi-tenant, notification, runbook thực thi.
- Chạy hoàn toàn offline từ cache (không cần mạng/API key lúc bảo vệ).
> Nguồn: 08 §1, §6; 06-scope-guard. ✅ thiết kế; ⏳ chờ M10.

### 6.2 Luồng end-to-end
- Replayer → Detector (IForest + Rescue) → CTAV (BM25 → C1 khi cần → policy C3) → RCA Agent (grouping → propagation → summary) → ClickHouse/Postgres → API (FastAPI) → Dashboard.
- Bốn Protocol lõi: `SourceAdapter`, `Detector`, `RetrievalStrategy`, `Judge`; điều phối ở `rca_agent/pipeline.py`.
- Chèn hình: sơ đồ kiến trúc.
> Nguồn: AGENTS.md; 01; 04 §M10. ⏳ chờ M10; grouping ✅ M6 (chưa chạy alert thật, chờ M9).

### 6.3 Dashboard 4 màn hình
- Timeline: alert theo thời gian, màu theo verdict và tầng routing.
- Alert detail: top-k bằng chứng, hồ sơ bằng chứng (tầng, thời gian, loại, bất thường hay không), lý do bị anchoring hạ xuống.
- Incident detail: đồ thị lan truyền, root cause, báo cáo JSON.
- Experiment comparison: bảng H0–H4 có CI, sinh từ `eval/results/`.
- Chèn 4 ảnh chụp; hiện MVP dữ liệu giả (React + Vite, QĐ-007).
> Nguồn: 08 §6; QĐ-007. ⏳ chờ M10 (nếu trễ: Experiment thành bảng tĩnh).

### 6.4 Kịch bản demo 5 phút
- (1) `docker compose --profile dev up -d` → replay → alert vào Timeline.
- (2) Alert normal mà topology chưa hiệu chỉnh xác nhận nhầm → CTAV hạ xuống (C3: chỉ có telemetry bình thường).
- (3) Ca `network_delay` BM25 bỏ sót → tầng topology tìm span chậm downstream. **Lưu ý trung thực:** trên `val` CTAV mất cả 10 ca `network_delay` mà C1 bắt được (Phát hiện 10) ⇒ **không dựng bước này trên ca `network_delay` trước khi có số `test`**: sau M8 chọn một ca CTAV thực sự bắt được trên `test` (theo loại lỗi có TP), hoặc đổi thông điệp của bước thành "C1 thấy, CTAV thận trọng" `[CHỜ M8, hỏi người dùng]`.
- (4) Cascade → nhiều alert gom thành một Incident → đồ thị chỉ root cause.
- (5) Tab Experiment → bảng sinh tự động.
> Nguồn: 08 §6; Phát hiện 10. ⏳ chờ M10; duyệt lần 1 ở M11, lần 2 ở M12.

### 6.5 Kiểm thử demo và dự phòng
- Chạy khi rút mạng; cache hit 100%; E2E latency/token/cache hit ghi `runtime.json`.
- Danh sách lỗi demo từ tổng duyệt M11.
> Nguồn: 04 §M10–M12. ⏳ chờ M10–M12.

---

## Chương 7 — Thảo luận, hạn chế và hướng phát triển

### 7.1 Tổng hợp kết quả chính
- H0 `val`: C1 − BM25 ΔRecall +0,100 [+0,052; +0,155], ΔFPR +0,025 [+0,020; +0,031]; tái lập về hiện tượng, không về cơ chế (Phát hiện 7).
- CTAV `val`: F1 0,201 [0,138; 0,264], FPR 0,0069; recall thấp hơn C1 0,124 [0,079; 0,170] ⇒ phương pháp giảm FP, không giữ recall topology (Phát hiện 10).
- H1 giữ một phần; C3 đóng góp; C2, C4 không; C5 chỉ +2 TP. `test`: `[CHỜ M8]`.
> Nguồn: QĐ-026, 028, 031, 033. ✅ `val` / ⏳ M8.

### 7.2 Thảo luận
- Vì sao C3 hiệu quả: bằng chứng không bất thường thì không được xác nhận; liên hệ Phát hiện 1–2 (có bằng chứng ≈ lộ nhãn; confidence ≈ anomaly_score).
- Vì sao C2/C4 không đóng góp (Phát hiện 9; confidence rời rạc 0,80/0,85/0,90).
- Vì sao C5 không thêm recall: nút thắt ở judge — 16/21 fault được đưa vào bị C1 trả FALSE_POSITIVE; Λ_log gần như luôn 0 (Phát hiện 12).
- Cột `PodSuccessRate(%)` lỗi làm lệch judge (Phát hiện 5); đánh đổi recall–FPR–chi phí (đường ngân sách H4).
> Nguồn: Phát hiện 1–12. ✅ `val`; ⏳ cập nhật sau M8.

### 7.3 Hạn chế
- **Một dataset** (Nezha); phân bố service `val` ≠ `test` có thể đổi số mạnh (V31); 15 service không có ngưỡng `dev` ⇒ C3 không neo được (Phát hiện 11).
- **Judge duy nhất** Gemini qua API (QĐ-013); Gemini 3.x thận trọng hơn (recall 0,14 vs 0,33, QĐ-023); phương sai LLM chỉ đo trên tập con (`repeat` 1, 2).
- **Detector bỏ sót fault:** 100 fault có telemetry bị bỏ sót, C5 cứu tối đa 2 TP (Phát hiện 12); recall CTAV 0,139.
- **C2, C4, C5 không đạt** ⇒ phương pháp thu về C1 + C3; không đăng ký lại H2 sau khi thấy `val` (V32 (a)).
- **Chi phí/độ trễ:** ≈ 4,40 USD token cho H0 `val` (billing báo 5 USD); 1,03 USD cho Rescue; phụ thuộc API; không đo local-first (GĐ1: 4/6 lần fallback, ~13,6× độ trễ).
- Nhìn `val` hai lần khi chọn cấu hình ⇒ số `val` lạc quan; chỉ `test` không thiên lệch.
- Cỡ mẫu RCA/đánh giá người nhỏ (30 incident, 50 window) `[⏳ M9, M11]`.
> Nguồn: QĐ-013, 023, 026, 031–033; 08 §4.1. ✅ `val`; ⏳ M8/M11.

### 7.4 Mối đe doạ tính hợp lệ
- **Internal:** rò nhãn qua tag fault type/"có bằng chứng" (Phát hiện 1; có unit test chặn); chọn tham số trên `val` hai lần; cột dataset lỗi (Phát hiện 5); model bị chuyển ngầm (QĐ-020, đã chặn); không hiệu chỉnh đa so sánh (H2 chính, còn lại phụ).
- **External:** một dataset, một judge, chủ yếu lỗi `cpu_*`/`network_delay`; chưa kiểm trên hệ thống khác/luồng thật.
- **Construct:** nhãn cửa sổ theo quy tắc QĐ-003; chỉ số trên tập có telemetry so với mọi cửa sổ; δ chốt sau khi thấy `val` (V33).
- **Conclusion:** bootstrap CI, McNemar; CI chồng ở ngân sách thấp; `test` chạy một lần.
> Nguồn: 08 §5.2; QĐ-003, 016, 020; registration. ✅ khung; ⏳ rà sau M8.

### 7.5 Phân tích ca sai
- FP còn lại của CTAV (51 trên `val`): loại nào, vì sao anchoring không chặn; FN: 10 ca `network_delay` mất (Phát hiện 10); ca RCA sai.
> Nguồn: 04 §M11. ⏳ chờ M11.

### 7.6 Hướng phát triển (tương lai, **không** là việc của luận văn)
- Causal Span Grounding đầy đủ (GĐ2 chỉ làm anchoring rút gọn).
- Local-first LLM routing khi có phần cứng; đo lại hiệu chỉnh và biến ẩn do routing.
- Retrieval `cross_modal`, RRF; `temporal`/`graph` độc lập (QĐ-011).
- Hình thức hoá Rescue Score; mở rộng chỉ số chất lượng ngữ cảnh; baseline trượt cho service thiếu ngưỡng; thêm dataset/streaming thật (kế thừa GĐ1 Ch5).
- Mục cấm (K8s, vector DB, fine-tuning, multi-tenant, notification, runbook…) chỉ nhắc nếu GVHD yêu cầu, nêu rõ ngoài phạm vi.
> Nguồn: docs/ideas.md; GĐ1 Ch5 (tr.79–82); 06. ✅; [TÁI SỬ DỤNG GĐ1] cho phần kế thừa.

---

## Chương 8 — Kết luận

### 8.1 Trả lời câu hỏi nghiên cứu
- RQ1 topology có tăng recall và FPR không? → H0 `[val ✅; test ⏳ M8]`.
- RQ2 cơ chế? → H1 giữ một phần (độ gần thời gian + loại bằng chứng; vế số lượng chưa kiểm).
- RQ3 CTAV hơn BM25 trong cùng ngân sách? → H2 `[CHỜ M8]`; sơ bộ `val` ΔF1 +0,098 [+0,046; +0,149] nhưng vế recall ≥ C1 − δ không đạt.
- RQ4 thành phần nào cần? → H3: C3 có; C2, C4 không; C5 chỉ là ablation `[CHỜ M8]`.
- RQ5 RCA định vị tốt không? → H5 `[CHỜ M9–M10]`.
> Nguồn: 08 §5.1; registration. ⏳ M8, M10.

### 8.2 Tóm tắt đóng góp
- Tái lập vấn đề của paper trên split có kỷ luật (G-port/G-paper, `test` một lần).
- Phát hiện về cơ chế và lỗi đánh giá của paper (Phát hiện 1–4, 6–7).
- CTAV (C1 + C3) giảm FPR ~8× so với BM25 trên `val`; kết quả âm trung thực cho C2/C4/C5.
- Tác tử RCA + platform demo offline `[⏳ M9–M10]`.
> ✅ phần `val`; ⏳ cập nhật sau M8.

### 8.3 Kết quả H0–H5
| | Kết quả | TT |
|---|---|---|
| H0 | `[CHỜ M8]` (val: đạt) | ⏳ |
| H1 | giữ một phần (QĐ-028) | ✅ |
| H2 | `[CHỜ M8]` (báo từng vế; vế recall có nguy cơ "đạt một phần") | ⏳ |
| H3 | `[CHỜ M8]` (val: C3 có; C2, C4 không) | ⏳ |
| H4 | `[CHỜ M8]` | ⏳ |
| H5 | `[CHỜ M9–M10]` | ⏳ |
> Nguồn: bản đăng ký (2026-11-14, QĐ-034). Viết H2 dù kết quả là gì.

### 8.4 Ý nghĩa và kết luận chung
- Hiệu chỉnh theo nguồn gốc bằng chứng quan trọng hơn thêm ngữ cảnh; FPR và chi phí là ràng buộc cốt lõi.
- Một câu hạn chế chính; trỏ sang Ch7. ⏳ viết sau M8.

---

## Tài liệu tham khảo
- Kế thừa toàn bộ danh mục GĐ1 (cuối `phase1.txt`) `[TÁI SỬ DỤNG GĐ1]`, giữ định dạng trích dẫn.
- Bổ sung: paper ICAETM 2026; bài gốc Nezha; tài liệu Gemini API (ghi ngày truy cập); scikit-learn Isolation Forest, ClickHouse, PostgreSQL, FastAPI, React/Vite; bootstrap CI, McNemar, BM25; công trình RCA microservice mới nếu Ch3 cập nhật.
- Chỉ trích dẫn nguồn đã đọc. ⏳ M12.

---

## Phụ lục

### Phụ lục A — Cấu hình thực nghiệm
- `eval/configs/*.yaml`: `gd1_phase4_parity`, `h0_val_*`, `m6_*`, `ctav_final`, `m7_*`, bản `test` `[⏳ M8]`; tham số (θ_local 0,80; C3 `dev` p90; IForest 0,85; `repeat`; seed 42).
> Nguồn: registration; QĐ-031. ✅ val.

### Phụ lục B — Prompt judge
- Prompt BM25 và C1, schema đầu ra, bỏ metric chết (V20); không lộ API key.
> Nguồn: QĐ-023; `services/judge`. ✅.

### Phụ lục C — Schema và hợp đồng
- Model pydantic, DDL, JSON báo cáo RCA, 4 Protocol lõi.
> Nguồn: 03. ✅; RCA ⏳ M9.

### Phụ lục D — Bảng đầy đủ trên `val`
- QĐ-026-1/2 (H0), H1, M6-4…M6-7, M7-1/2; chi phí/token.
> Nguồn: experiment-log. ✅.

### Phụ lục E — Hướng dẫn tái lập
- Môi trường: `docker compose --profile dev up -d`; `pip install -e`; Windows dùng `py`.
- `py -m eval run --config eval/configs/<name>.yaml` (run_id mới mỗi lần, không ghi đè `eval/results/`); `py -m eval compare --runs bm25_baseline,topology_c1,ctav_final`; `py -m eval ctav --config eval/configs/ctav_final.yaml`; `py -m eval rescue --config ...`; `py -m eval ablation --config ...`.
- Kiểm tra: `py -m pytest`, `py -m mypy packages services`, `py -m ruff check .`; cache LLM để cache hit 100%.
> Nguồn: AGENTS.md; experiment-log. ✅; ⏳ kiểm "người lạ clone" ở M12.

### Phụ lục F — Đánh giá bằng người, báo cáo mốc
- `eval/manual/` (50 window, 30 incident); `docs/milestones/M0…M12`. ⏳ M8, M11.
