# services/retrieval

Not yet implemented. Five strategies planned per `docs/Final_Thesis_Phase2/01-architecture-design.md` §6.3:

- `bm25_hybrid.py` — baseline, ported from `legacy/` (Week 3)
- `temporal.py` (Week 7)
- `cross_modal.py` (Week 9)
- `graph.py` (Week 5–6)
- `hybrid_bm25_graph.py` (Week 10)
- `base.py` — `RetrievalStrategy` Protocol + `RetrievalBudget` + `RetrievalResult`
- `registry.py` — name -> class

Adding a strategy means updating three places — see `05-agent-coding-rules.md` R-F1.
