# services/rca_agent

Three-step pipeline per `docs/Final_Thesis_Phase2/01-architecture-design.md` §6.5:
`grouping.py` -> `propagation.py` -> `summarizer.py`, orchestrated by `pipeline.py`.
Runs off the critical path (non-critical path, §4.2) — never synchronous with Judge.

- `grouping.py` (M6): time clusters (`t_group_seconds`, default 300 s from the caller's
  config) + connected components of the service graph induced by the alerted services
  -> `Incident`. No LLM.
- `propagation.py` (M9): level 1, backward 1-hop along the call direction, votes per alerted service
  (never per alert); baseline `rank_by_anomaly_score`. Level 2 (LLM over the call chain) was cut (QD-037).
- `summarizer.py` (M9): one LLM call per Incident -> `DiagnosticReport` (03 SS2). The root cause is rank 1
  of level 1, not the LLM's choice. Validation of 03 SS2.1 (`invalid_json`, `confidence_out_of_range`,
  `executable_action`, `no_evidence`, `suspicious`); backends `mock` and Gemini through the judge's cache.
- `store.py` (M9): PostgreSQL writer for `run_registry`, `incidents`, `diagnostic_reports`,
  `diagnostic_rejected` (03 SS4); refuses a run_id that is already registered.
- Evaluation: `py -m eval rca --config eval/configs/rca_final.yaml` (`eval/harness/rca.py`).
- `pipeline.py`: M10.
