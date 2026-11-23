# packages/llm

> Thư mục này hiện **không chứa code LLM** — giữ làm nơi neo tài liệu. Code LLM thật nằm ở
> `services/judge/` (judge) và `services/rca_agent/summarizer.py` (RCA summary).

- **Judge duy nhất**: `gemini-2.5-flash` qua API, temperature 0 (QĐ-021); `gemini-2.5-flash-lite`
  chỉ dùng để replay cache bài báo G-paper (`PAPER_MODEL` trong `services/judge/backends.py`).
- **Cache phản hồi**: `services/judge/cache.py`, key =
  `sha256(provider | model | prompt | "max=<n>|t=0"[|repeat=n])`, `repeat` mặc định 0 (QĐ-013).
- Thiết kế cũ "local-first routing (Ollama + fallback API)" đã bị cắt (QĐ-013/QĐ-021) —
  xem `docs/ideas.md` (mục 2026-10-18).
