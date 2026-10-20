"""V18 (QD-024): pick `k_graph` from the val sweep (eval/configs/m4_kgraph_val_k*.yaml).

    py scripts/kgraph_select.py --runs 0=m4_kgraph_val_k0_v1,1=m4_kgraph_val_k1_v1,... \
        --out eval/results/m4_kgraph_selection_v1.json

Rule and criterion: eval/harness/kgraph.py. The output file must not exist.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from eval.harness.kgraph import choose_k, load_run  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", required=True, help="k=run_id,... (must include k=0)")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists: results are never overwritten")
    run_ids = dict(item.split("=", 1) for item in args.runs.split(","))
    runs = {int(k): load_run(REPO / "eval/results" / run_id) for k, run_id in run_ids.items()}
    result = {"runs": run_ids, **choose_k(runs)}
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    for k, s in result["by_k"].items():
        print(
            f"k={k}: root hit {s['hits']}/{s['n']} ({s['hit_rate']:.1%}, CI95 "
            f"{s['hit_rate_ci95'][0]:.1%}-{s['hit_rate_ci95'][1]:.1%}) | s0=root "
            f"{s['s0_is_root']['hits']}/{s['s0_is_root']['n']} | s0!=root "
            f"{s['s0_not_root']['hits']}/{s['s0_not_root']['n']} | graph evidence {s['with_graph_evidence']} | "
            f"constraint {'ok' if s['passes_local_constraint'] else 'FAIL'} | McNemar vs k0 p={s['mcnemar_p_vs_k0']:.3g}"
        )
    print("chosen k_graph:", result["chosen_k_graph"], "->", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
