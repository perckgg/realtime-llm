# Archive — Phase 1 extra material (out of Phase 2 scope)

This folder holds Internship 1 (Phase 1) work that is explicitly **out of scope** for
Phase 2 per `docs/Final_Thesis_Phase2/06-scope-guard.md`: supporting a second dataset
is Phase 3 work, not Phase 2.

- `cloud_monitor_setup/` — Microsoft cloud-monitoring dataset experiment (detector-only,
  never used for RAG/API claims). Referenced by `docs/submission_docs/reports/cloud_monitoring_*`.
- `online_boutique_streaming_setup/` — controlled true-streaming sandbox built on the
  Online Boutique demo app (Kubernetes/kind), used for context-rescue validation.
- `data/cloud-monitoring-dataset/` — the raw dataset consumed by `cloud_monitor_setup/`.

This is a frozen reference copy, not an active part of the Phase 2 codebase:

- It is **not guaranteed to run as-is**. Both setups originally imported the shared
  Phase 1 modules via a relative `sys.path` bootstrap that assumed they were siblings
  of `src/` at the repo root; `src/` now lives under `legacy/`. Restoring a working
  copy (if ever needed) means pointing their imports at `legacy/src/` again.
- Kept only so the results and analysis already cited in submitted reports
  (`docs/submission_docs/`) remain traceable to their source code.
