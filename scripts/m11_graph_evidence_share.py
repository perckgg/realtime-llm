"""M11: how much of the C1 context actually comes through the service graph (descriptive only).

Reads `fact_retrieval_trace` / `fact_alert_evaluation` of one pipeline run in ClickHouse (0 API calls)
and prints the numbers quoted in Ch6 next to the "How C1 built this context" card:
evidence by retrieval channel (`source_flags`), evidence from neighbour services (d_G >= 1), alerts
with any neighbour evidence, and the TRUE_ALERTs among them with their Nezha label.

    py -m scripts.m11_graph_evidence_share --run-id pipeline_test_v2
"""

from __future__ import annotations

import argparse
import json

from packages.storage import clickhouse


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default="pipeline_test_v2")
    run_id = ap.parse_args().run_id
    p = {"run_id": run_id}
    ch = clickhouse.get_client()
    try:
        total = ch.query("SELECT count() FROM fact_retrieval_trace WHERE run_id = {run_id:String}", parameters=p).result_rows[0][0]
        windows = ch.query(
            "SELECT count(DISTINCT window_id) FROM fact_retrieval_trace WHERE run_id = {run_id:String}", parameters=p
        ).result_rows[0][0]
        channels = ch.query(
            "SELECT JSONExtractRaw(debug_json, 'source_flags') AS sf, count() FROM fact_retrieval_trace "
            "WHERE run_id = {run_id:String} GROUP BY sf ORDER BY sf",
            parameters=p,
        ).result_rows
        by_distance = ch.query(
            "SELECT graph_distance, count() FROM fact_retrieval_trace WHERE run_id = {run_id:String} "
            "GROUP BY graph_distance ORDER BY graph_distance",
            parameters=p,
        ).result_rows
        neighbour_alerts = ch.query(
            "SELECT e.verdict, e.label_is_fault, count() FROM fact_alert_evaluation e INNER JOIN ("
            "  SELECT window_id FROM fact_retrieval_trace WHERE run_id = {run_id:String} "
            "  GROUP BY window_id HAVING countIf(graph_distance >= 1) > 0"
            ") t USING window_id WHERE e.run_id = {run_id:String} GROUP BY e.verdict, e.label_is_fault "
            "ORDER BY e.verdict, e.label_is_fault",
            parameters=p,
        ).result_rows
    finally:
        ch.close()

    via_graph = sum(n for sf, n in channels if "graph" in str(sf))
    neighbour = sum(n for d, n in by_distance if d is not None and d >= 1)
    out = {
        "run_id": run_id,
        "evidence_rows": total,
        "alerts_with_context": windows,
        "evidence_by_source_flags": {str(sf): n for sf, n in channels},
        "evidence_via_graph_channel": via_graph,
        "evidence_by_graph_distance": {str(d): n for d, n in by_distance},
        "evidence_from_neighbours": neighbour,
        "evidence_from_neighbours_share": round(neighbour / total, 4) if total else None,
        "alerts_with_neighbour_evidence": sum(n for _, _, n in neighbour_alerts),
        "alerts_with_neighbour_evidence_by_verdict_label": [
            {"verdict": v, "is_fault": bool(f), "count": n} for v, f, n in neighbour_alerts
        ],
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
