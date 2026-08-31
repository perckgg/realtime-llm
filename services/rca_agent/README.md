# services/rca_agent

Not yet implemented (Phase 2, Month 4 — Week 9/13 grouping, Week 14-15 propagation, Week 17 summary).

Three-step pipeline per `docs/Final_Thesis_Phase2/01-architecture-design.md` §6.5:
`grouping.py` -> `propagation.py` -> `summarizer.py`, orchestrated by `pipeline.py`.
Runs off the critical path (non-critical path, §4.2) — never synchronous with Judge.
