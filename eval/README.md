# eval

Not yet implemented (Phase 2, Week 4). CLI harness (`harness/`) reads a config from `configs/`,
runs the pipeline, and writes to `results/<run_id>/` — which is immutable once written (R-A3:
no command in this repo may `rm -rf eval/results/`; a re-run with different parameters gets a
new `run_id`). `results/` is committed to git, not ignored.
