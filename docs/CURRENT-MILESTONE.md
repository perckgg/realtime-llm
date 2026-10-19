# Mốc hiện tại

> Cập nhật file này khi bắt đầu một mốc mới. Agent đọc file này để biết được phép làm gì.
> Chỉ chép phần mốc hiện tại từ `docs/Final_Thesis_Phase2/04-implementation-roadmap.md`.
> Đóng mốc = DoD đạt + báo cáo `docs/milestones/M<n>-*.md` (4 phần) + người dùng đã xem (`04` §2).

---

## Trạng thái — 2026-10-19

| Mốc | Trạng thái | Báo cáo / quyết định |
|---|---|---|
| M0 | QUA | `docs/milestones/M0-nen-tang.md` |
| M1 | QUA | `docs/milestones/M1-detector-bm25-judge.md`; QĐ-015, QĐ-016, QĐ-017 |
| M2 | **QUA** (đóng 2026-10-19) | `docs/milestones/M2-harness-gport.md`; QĐ-018, QĐ-019 |
| M3 | **Chưa mở** — đã khảo sát (QĐ-020), chờ chốt V12–V15 | Mục dưới |

Việc đã xong gần nhất (QĐ-019, QĐ-020): judge song song 8 worker + `RateLimiter` 200 lần/phút
(196 lần gọi Gemini trong 60 s, 0 lỗi); chặn lệch model (`ModelVersionMismatch`); dump và tái
lập được 489/489 prompt topology của paper; 104 test pass, mypy + ruff sạch.

---

## Mốc tiếp theo: M3 — Service graph + C1 + cổng chặn G-paper
## Dự kiến bắt đầu: ngay khi chốt V12–V15 · Hạn mục tiêu: 2026-11-08

### Việc (theo `04` M3, đã điều chỉnh theo khảo sát QĐ-020)

1. - [ ] `packages/graph/` + `scripts/build_service_graph.py`: port `legacy/src/phase2/retrieval/graph_builder.py`; đồ thị có hướng (cho C3) + vô hướng (cho C1, như paper); pod → service bằng `packages/schemas/nezha.py`. Kiểm tra trùng 68 cạnh của GĐ1
2. - [ ] `docs/graph-coverage.md`: 3 chỉ số `02` §1.3 — số đã đo sơ bộ: 56 service, 68 cạnh, 18 cô lập; fault window trên service có cạnh 100% ở cả 3 split
3. - [ ] `services/retrieval/hybrid_bm25_graph.py` (C1): port `topology_aware_retriever.py`, `fusion_ranker.py`, `topology_candidate_expander.py`; α 0,35 / β 0,25 / γ 0,40, τ 300 s, 2-hop, 20 event/service; chế độ parity (corpus GĐ1, BM25 toàn corpus không giới hạn thời gian, truy vấn có fault type); điền `origin`, `graph_distance`; registry + `01` §6.3 + bảng `debug` `03` §1.3 (R-F1)
4. - [ ] Nửa topology của G-paper: `scripts/check_gd1_parity.py --variant topology_aware_fusion_top6` → 489/489 top-6, prompt, key; verdict từ cache ⇒ F1 0,4759 / FP 137. `eval/configs/paper_viewA_replay.yaml`
5. - [ ] Chặn `parity_query_terms` khi `split` là `val`/`test` (R4 của báo cáo M2)
6. - [ ] Nếu V12 đổi model: chạy lại smoke `m2_parallel_judge_smoke` với model mới (run_id mới), cập nhật QĐ-013

### DoD (`04` M3)

- [ ] Tái lập Table 1 của paper từ cache, không gọi API: BM25 F1 0,7030 / FP 7 (**đã đạt ở M1**); Topology F1 0,4759 / FP 137
- [ ] Cache hit 100% cho cả hai biến thể
- [ ] `docs/graph-coverage.md` có ba chỉ số; coverage fault window < 60% ⇒ ghi fallback (hiện 100%)
- [ ] pytest / mypy / ruff sạch; báo cáo `docs/milestones/M3-*.md`

### Vấn đề cần chốt trước / trong M3

| # | Vấn đề | Phương án | Khuyến nghị | Chặn gì |
|---|---|---|---|---|
| **V12** | **Đổi judge lên Flash bậc cao hơn** (yêu cầu của bạn 2026-10-19). QĐ-013 chốt `gemini-2.5-flash-lite` để so được với paper. Thử 1 request (Bảng QĐ-020-2): mọi model nhận cấu hình hiện tại; `gemini-3.5-flash` và `gemini-3.7-flash` bị API **chuyển ngầm** sang 3.6/3.8 | (a) `gemini-2.5-flash` — đúng model được gọi, phiên bản "001", cùng thế hệ với paper (chỉ đổi cỡ model); (b) `gemini-3.8-flash` — mới và mạnh nhất, nhưng dòng 3.x đang được chuyển ngầm, rủi ro bị đổi giữa M4–M8 (harness sẽ dừng run nếu xảy ra); (c) giữ flash-lite | **(a)**: rủi ro tái lập thấp nhất trong 3–4 tháng còn lại, và so sánh với paper chỉ khác cỡ model. Giữ `thinkingBudget: 0`, temperature 0. G-paper vẫn dùng cache flash-lite. Giá: tôi không có bảng giá hiện hành đáng tin, sẽ đo từ token thật ở smoke; ước chừng vài USD mỗi run `val`, trong ngân sách ~80 USD | Không chặn M3 (G-paper dùng flash-lite); **chặn M4** |
| **V13** | **C1 có giới hạn thời gian hay không** (Phát hiện 3): 80% context topology của paper nằm ngoài ±8 phút, 100% normal có bằng chứng | (a) C1 GĐ2 giới hạn BM25 trong ±8 phút như `bm25_hybrid`, parity giữ nguyên paper; (b) giữ đúng paper; (c) làm cả hai qua cờ `bm25_pool`, đo cả hai ở H0 (M4) | **(c)**: H0 cần biết vấn đề của paper còn không khi bỏ lỗi lệch thời gian. Nếu C1-có-giới-hạn không còn tăng FPR thì câu chuyện CTAV phải viết lại — cần biết sớm | Thiết kế C1 (việc 3) |
| **V14** | Định nghĩa `origin` của `ContextEvent` cho C2/C3: event của chính `s0` lấy qua mở rộng đồ thị là local hay graph? | (a) Theo khoảng cách: d = 0 ⇒ local, d ≥ 1 ⇒ graph, cờ nguồn (bm25/graph) ghi ở `debug`; (b) theo kênh lấy được | **(a)**: C2/C3 hỏi "bằng chứng có nằm ở `s0` không", không hỏi "lấy bằng kênh nào" | Việc 3 |
| **V15** | Đồ thị có hướng hay vô hướng | C1 dùng vô hướng (như paper, để parity); C3 dùng có hướng (đường gọi tới `s0`) | Dựng cả hai ở việc 1 | Không |
| V1 | Mail GVHD — nên kèm V7, V8 và Phát hiện 3 | | | Nên trước M4 |
| V3 | Q5: mốc bảo vệ tuần 2027-02-08 | | | Không |
| V4–V6 | File `legacy/` chưa commit; file rác gốc repo; câu "LLM không RAG thất bại" là số mock | | | Không |

### Rủi ro đã biết

- Prompt topology làm tròn `score` 6 chữ số (BM25: 4) ⇒ `context_payload` phải làm tròn theo strategy, nếu không sẽ cache miss.
- Thứ tự sắp xếp và tie-break của `FusionRanker` (score, bm25_norm, time_sim, distance, doc_id) và `bm25_raw` tính trên thống kê toàn corpus phải giữ nguyên từng chi tiết.
- Mở rộng đồ thị trên kho Nezha đầy đủ: mỗi truy vấn đọc log/trace của mọi service trong 2-hop ±8 phút — cần đo độ trễ.

**Không làm ở mốc này:** H0 trên `val` (M4); C2–C4 (M6).

---

## Lệnh tái lập M0

```bash
bash scripts/download_nezha.sh          # nếu chưa có data/Nezha/
py scripts/verify_labels.py             # -> docs/label-audit.md (~80 s)
py scripts/make_splits.py --check       # xác nhận split không đổi
docker compose --profile dev up -d      # clickhouse + postgres
py -m pytest tests/ -q                  # 100 test (sau QĐ-018)
py scripts/replay_smoke.py --windows 50 --run-id <run_id-mới>   # fit + replay + ghi ClickHouse
```

## Lệnh tái lập M2

```bash
py scripts/map_gd1_windows.py
py scripts/dump_gd1_prompts.py --split phase4 --max-total-calls 40
py -m eval run --config eval/configs/gd1_phase4_parity.yaml      # run_id mới nếu đã có
py scripts/gport_layers.py --run gd1_phase4_parity_v1
py -m eval run --config eval/configs/val_detector_count.yaml     # ~5 phút
```

## Lệnh tái lập M1

```bash
py scripts/apply_clickhouse_migrations.py                # cột CTAV (idempotent)
py scripts/dump_gd1_prompts.py                           # 489 prompt GĐ1 paper_500, ~85 s
py scripts/check_gd1_parity.py                           # port GĐ2 vs GĐ1: 489/489
py scripts/evidence_coverage.py                          # bằng chứng theo nhãn: GĐ1 vs GĐ2
py scripts/judge_smoke.py --run-id <mới> --candidates 3  # BM25 -> judge mock + Gemini
```
