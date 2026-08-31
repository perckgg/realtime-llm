# Microsoft Cloud Monitoring Dataset Setup

This folder adapts `data/cloud-monitoring-dataset` to the experiment pipeline without modifying the original dataset.

## Prepare Data

```powershell
py cloud_monitor_setup/prepare_cloud_monitor_data.py
```

The script writes:

- `cloud_monitor_setup/processed/metrics.csv`
- `cloud_monitor_setup/processed/logs.jsonl`
- `cloud_monitor_setup/processed/summary.json`

The Microsoft dataset contains time series and labels, but no operational logs. `logs.jsonl` therefore contains only metadata context from the dataset JSON files. Use the detector-only baseline as the primary evaluation; hybrid/RAG runs are useful only as plumbing checks until real logs/events are attached.

## Run

```powershell
py experiments/run_baseline.py --config cloud_monitor_setup/config/experiment.yaml --mode detector_only
py experiments/run_baseline.py --config cloud_monitor_setup/config/experiment.yaml --mode llm_without_rag
py experiments/run_hybrid.py --config cloud_monitor_setup/config/experiment.yaml
py experiments/compare_results.py --input cloud_monitor_setup/outputs/results
```

