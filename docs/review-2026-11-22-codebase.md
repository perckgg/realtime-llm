# Rà soát codebase toàn bộ — 2026-11-22

> Tổng hợp đợt dò toàn bộ code (`packages/`, `services/`, `eval/`, `scripts/`, `tests/`, `infra/`) bằng 6 nhánh rà song song + đối chiếu chéo.
>
> **Kết luận chính:** không có phát hiện nào làm sai lệch kết quả đã đóng băng (H0–H5, parity `26/26` / `38/38` / `114/114`,
> fingerprint `b0c54fa68ef65535`). Các thuật toán lõi (Isolation Forest, Rescue Score, BM25 fusion, Fusion Score α/β/γ,
> window index, C2/C3/C4 policy, grouping, propagation 1-hop, validator `require_evidence`, SQL parameterized, offline
> `DEMO_OFFLINE` cache-only) đều đúng và khớp paper/đặc tả. Toàn bộ phát hiện là vệ sinh / lỗi tiềm ẩn / tài liệu lỗi thời —
> không chặn M11/M12, dành cho GĐ3 hoặc phần "hạn chế & hướng phát triển".

## Tóm tắt theo mức

- **Cao: 1** — bug tiềm ẩn (chưa từng kích hoạt) trong `eval/harness/rescue.py`.
- **Trung bình: 8** — hardcode tham số, validation judge lỏng, API health/DB-down, thiếu subcommand, frontend/script.
- **Thấp: ~20** — tài liệu/comment lỗi thời, dead `cross_modal`, magic string, thiếu type hint, path traversal, TOCTOU…

---

## 🔴 Cao

### 1. `eval/harness/rescue.py:186-187` + `:207-211` — `evaluate()` sẽ `ValueError` với điểm lưới infeasible

```python
def entry(name, rescued, nonzero, extra):
    if (rescued & ~judged).any():                              # :186
        raise ValueError(f"{name}: ... rescued windows were never judged")  # :187
...
rows = [entry(point_name(p), masks[point_name(p)], ...) for p in points]  # :207-211 (MỌI điểm)
```

`plan()` (`:130`) chỉ union cửa sổ của các điểm **feasible** để chấm (`rescue_windows.csv`), nhưng `evaluate()` dựng
`entry` cho **toàn bộ 147 điểm** kể cả infeasible → guard raise cho điểm infeasible đầu tiên có cửa sổ chưa được chấm.
**Ở M7 không kích hoạt** vì `147/147` điểm đều feasible (cap đủ lớn); chỉ crash nếu chạy lại với `max_call_increase` nhỏ.
Khắc phục: chỉ dựng `entry` cho điểm feasible (và `off`), hoặc `plan()` union mọi điểm cho khớp comment `m7_rescue_val_c1.yaml`.

---

## 🟡 Trung bình

### 2. Hardcode tham số thí nghiệm (theme lớn nhất)
- `services/api/readers.py:49,53-55` — `DEFAULT_DETECTOR_THRESHOLD=0.85` + C1 fusion weights `α=0.35, β=0.25, γ=0.40, τ=300, graph_max_distance=2` hardcode thay vì đọc từ `eval/configs/h0_*_c1_k0.yaml`.
- `eval/harness/h1.py:318` — `GATE_THETAS=(0.80,0.85,0.90,0.95)` sweep θ hardcode; kèm `h1.py:49-52` (`K=6`, `FLAT_SCORES`, `TIME_LEVELS`, `CONDITIONS`).
- `packages/schemas/models.py:123-125` — `RetrievalBudget` default `top_k=6, max_tokens=4000, timeout_ms=500`.
- `services/detector/isolation_forest.py:126-132` — default `threshold/contamination/n_estimators/random_state/min_fit_windows`; `bm25_baseline.yaml` + `h0_val_*.yaml` chỉ khai `threshold+buffer_size`.
- `services/retrieval/bm25_hybrid.py:98,122,197,206-217` — `k1/b`, blend `0.6/0.4`, severity score, trọng số `0.45/0.25/0.2/0.1`.
- `services/retrieval/hybrid_bm25_graph.py:125-137` — default `α/β/γ/τ/bm25_k/graph_max_distance/...`.

> Các giá trị nằm đúng vị trí `__init__` (override được qua config) — đúng tinh thần AGENTS.md; vấn đề là **giá trị paper bị nhân đôi ở code** và vài config không khai báo lại đủ.

### 3. Judge model — validation lỏng + lỗi chưa bắt
- `services/judge/registry.py:36-37` — chỉ check `model.startswith("gemini")` → `flash-lite` (và `3.x`) lọt cho API thật, trái QĐ-021. Nên thắt về `model == JUDGE_MODEL`.
- `services/judge/backends.py:263` — `json.loads(response.read())` không nằm trong try (retry chỉ bắt `HTTPError/OSError/HTTPException`) → body 200 rỗng/méo văng exception thay vì → `manual_review`.

### 4. API read-only — health & DB-down
- `services/api/main.py:27-29` — `/health` trả `{"status":"ok"}` tĩnh, không kiểm ClickHouse/PostgreSQL.
- `services/api/readers.py` (nhiều chỗ) — gọi DB không try/except → DB down trả 500 + traceback.
- `services/api/readers.py:124-156` vs `:58-66` — unpack 30 cột theo vị trí cứng, phải khớp thủ công SELECT (không assert số cột).

### 5. Eval CLI lệch tài liệu
- `eval/__main__.py:100-116` — thiếu subcommand `ablation` (AGENTS.md ghi `py -m eval ablation ...`; file `rescue_ablation.yaml` cũng không tồn tại); docstring `:1-4` thiếu `rca`.

### 6. Frontend + script
- `services/web/src/screens/ExperimentComparison.tsx:169-179,383,391` — `HYPOTHESIS_META_EN` hardcode title/status override dữ liệu bảng (chữ từ map, màu từ `h.status`) → hai nguồn sự thật.
- `scripts/m10_pick_demo_cases.py:345-346` — ghi `eval/results/m10_demo_cases_v1/demo_cases.json` không chặn ghi đè (khác mọi script M8/M11).

---

## 🟢 Thấp (gom chủ đề)

- **Tài liệu/comment lỗi thời** — `packages/llm/README.md` (mô tả local-first đã cắt), `packages/schemas/models.py:155`, `services/judge/README.md`, `services/rca_agent/grouping.py:10` — **đã sửa phiên này**; còn sót `docs/Final_Thesis_Phase2/06-scope-guard.md:80` và bản `docs/Final_Thesis_Phase2/AGENTS.md` vẫn ghi `flash-lite` (lệch AGENTS.md gốc repo).
- **Dead `cross_modal`** (cắt QĐ-011): `services/web/src/api/types.ts:19-24`, `mock/fixtures.ts:152`, `theme/tokens.ts:95-117`.
- **Magic string/duplication**: `IncidentDetail.tsx:208`, `AlertDetail.tsx:45`, `m10_pick_demo_cases.py:75`, `readers.py:244-246`.
- **Hardcode hằng số script phân tích (parity check giòn)**: `m8_tables.py:28-29`, `m11_error_analysis.py:568-577,610,629`, `m8_context_precision_rule_label.py:135-136`.
- **Thiếu type hint**: `packages/schemas/nezha.py:301`, `loaders.py:119-127,184-187`, `window_index.py:135`.
- **Khác**: `readers.py:359-371` path traversal `../`; `store.py:48-49` TOCTOU; `rescue.py:79-89` không validate `tau`; `bm25_hybrid.py:294` ước lượng token `message[:240]`; `stats.py:36-37` vs `:60` hai quy ước percentile bootstrap; `cache.py:25` temperature hardcode `"t=0"`; `backends.py:160` `timeout_seconds=60` không configurable; `summarizer.py:357-360` nhánh `require_evidence=False` tự gán `evidence[0]`.

---

## Đối chiếu 5 quy tắc AGENTS.md

| Quy tắc | Kết quả |
|---|---|
| 1. Không hardcode tham số | ⚠️ Vi phạm nhẹ — default `__init__` + vài chỗ thật sự hardcode (`readers.py`, `h1.py:318`) |
| 2. Không chạm `test` split | ✅ Đúng — guard `g_test`/`h5_test` ở `runner.py:99-101`, `ctav.py:68-70`, `rescue.py:63-65`, `rca.py:91-93` |
| 3. Không ghi đè `eval/results/` | ✅ Đúng ở harness — ngoại lệ `m10_pick_demo_cases.py` |
| 4. LLM qua cache | ✅ Đúng — key `sha256(provider\|model\|prompt\|max\|t=0\|repeat)`; ngoại lệ registry model validation lỏng |
| 5. Scope guard | ✅ Đúng — không tech/tính năng cấm; sót nhẹ `cross_modal` trong web types |

---

## Vệ sinh repo (git status 2026-11-22)

- **Chưa commit**: file LaTeX luận văn (`docs/drafts/Internship2_HK262/...`), `CURRENT-MILESTONE.md`, `experiment-log.md`, `M11-danh-gia-nguoi.md`.
- **Chưa track** (`??`): `scripts/m8_context_precision_{rule_label,score}.py`, `tests/test_m8_context_precision.py`, `eval/results/m8_context_precision_v1/`, `eval/manual/*.ai_scores.csv`, `eval/manual/diagnostic_quality.ai_review.md`, `graphify-out/`.
- **Rác**: `_bt/`, `_bt_0c6f1c/` (rỗng, Permission denied), `graphify-out/`; comment đầu `docker-compose.yml:1-2` lỗi thời; `infra/redpanda/.gitkeep` placeholder.

---

## Đã xử lý trong phiên này (2026-11-22)

- Sửa tài liệu lỗi thời (thuần văn bản, không đụng code/kết quả): `packages/llm/README.md`, `packages/schemas/models.py:155`, `services/judge/README.md` (model judge + "chưa có policy/routing"), `services/rca_agent/grouping.py:10`.
- Ghi danh sách nợ kỹ thuật vào `docs/ideas.md`.
