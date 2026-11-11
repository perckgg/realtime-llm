# services/rca_agent

Three-step pipeline per `docs/Final_Thesis_Phase2/01-architecture-design.md` §6.5:
`grouping.py` -> `propagation.py` -> `summarizer.py`, orchestrated by `pipeline.py`.
Runs off the critical path (non-critical path, §4.2) — never synchronous with Judge.

- `grouping.py` (M6): time clusters (`t_group_seconds`, default 300 s from the caller's
  config) + connected components of the service graph induced by the alerted services
  -> `Incident`. No LLM.
- `propagation.py`, `summarizer.py`, `pipeline.py`: M9–M10.
