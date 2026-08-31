Phase 1 output namespace
========================

Purpose
- Keep a clean boundary between historical Phase 1 artifacts and new Phase 2 outputs.
- Avoid moving large legacy outputs to prevent breaking existing reports and commands.

What is stored here
- legacy_output_index.json: index of retained Phase 1 output roots currently used as source-of-truth.

Legacy outputs remain in-place under:
- nezha_setup/outputs/
- outputs/audit
- outputs/results

Phase 2 must write new artifacts under:
- outputs/phase2/

