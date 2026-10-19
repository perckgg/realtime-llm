# services/judge

**Làm gì.** `LLMJudge` (`01` §5.4): dựng prompt GĐ1 **nguyên văn** từ candidate + context,
hỏi backend, parse JSON 3 nhãn, áp luật quyết định → `JudgedAlert`.

| File | Nội dung |
|---|---|
| `prompt.py` | `compose_prompt` nguyên văn GĐ1; `alert_payload`, `context_payload` chuyển object GĐ2 sang dict GĐ1 |
| `cache.py` | Cache JSONL đọc thẳng được file cache GĐ1; key GĐ1 + `repeat` (`03` §6) |
| `backends.py` | `GeminiBackend` (`gemini-2.5-flash-lite`, temperature 0, retry có trần, giới hạn lần gọi/phút, ghi `modelVersion`); `MockBackend` = mock GĐ1, chỉ cho G-port |
| `llm_judge.py` | Luật: lỗi ⇒ `UNCERTAIN`/`manual_review`; `require_evidence`; ngưỡng 0,80 đối xứng của GĐ1 (`03` §1.4) |
| `registry.py` | `build_judge(config["judge"])`; từ chối model không phải Gemini và temperature ≠ 0 (QĐ-013) |

Chưa có (theo lộ trình): `policy.py` C2/C3 (M6), `routing.py` C4 (M6).

**Chạy thế nào.**

```python
from services.judge.registry import build_judge
judged = build_judge({"backend": "api"}).evaluate(candidate, retrieval_result)
```

Cache mặc định `data/llm_cache/gemini.jsonl`; `cache_read_paths` thêm cache chỉ-đọc (cache
GĐ1 cho G-paper). Cache hit không cần `GEMINI_API_KEY` ⇒ chạy lại/demo offline được. Cache
miss mà thiếu key ⇒ `manual_review`, không gọi model khác.

Smoke end-to-end: `py scripts/judge_smoke.py --run-id <mới> [--candidates N] [--fault-only]`.

**Input/Output.** `AlertCandidate` + `RetrievalResult` → `JudgedAlert` (verdict sau luật,
`raw_verdict`, trường CTAV, `debug`). Test: `tests/test_judge.py`.
