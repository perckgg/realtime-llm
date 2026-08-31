"""Stdlib-only loaders for the Nezha dataset — Week 1 data audit.

Week 1 of the roadmap forbids pipeline code (see docs/CURRENT-WEEK.md), so this
module deliberately stays on the standard library: no pydantic, no pandas, no
sklearn. It exists to answer the Week 1 label questions in
docs/Final_Thesis_Phase2/02-data-and-experiment-protocol.md §1.2 and to produce
the reproducible split required by §2.

Week 2 will wrap these functions in packages/schemas/loaders.py so they emit
TelemetryWindow objects (docs/Final_Thesis_Phase2/03-schemas-and-contracts.md
§1.1). Until then nothing here imports from packages/ or services/.

Window definition
-----------------
The Nezha per-pod metric CSVs sample once per 60 s. One window is therefore one
metric sample of one pod, covering [start_ts, start_ts + 60 s).

Labelling rule
--------------
Copied from the Phase 1 pipeline (legacy/nezha_setup/prepare_nezha_data.py,
recorded as "label_rule" in legacy/nezha_setup/processed/summary.json): a window
is a fault window when it belongs to the *same pod* as an injection and starts
within [inject_ts - 60 s, inject_ts + 360 s].

Which clock defines inject_ts
-----------------------------
Nezha records every timestamp twice and the two copies disagree in two places:

* On 2023-01-29, 24 of 28 injections have an ``inject_timestamp`` epoch that
  runs 8 hours behind the ``inject_time`` wall clock, while the metric CSVs of
  that day follow the wall clock. Joining on the epoch loses those 24
  injections entirely.
* Every row of ``2022-08-22/metric/adservice-...csv`` carries a ``TimeStamp``
  epoch about 6.3 years ahead of its own ``Time`` column, which loses that pod
  as well.

The wall-clock columns agree with each other across all four days, so
``time_source="wall"`` is the default and is what the committed splits use. The
absolute time zone is irrelevant here — only the relative alignment between
injections and metrics matters, and both columns declare "+0000 UTC".

``time_source="epoch"`` reproduces the Phase 1 behaviour bug-for-bug. Keep it:
the Week 3 gate (Precision 0.32, FPR 0.046) was measured under that labelling,
so reproducing it requires the same labels. See docs/experiment-log.md.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

# Constants fixed by the Phase 1 pipeline. Changing them invalidates the Week 3
# comparison, so record the reason in docs/experiment-log.md first.
WINDOW_SECONDS = 60
LABEL_BEFORE_SECONDS = 60
LABEL_AFTER_SECONDS = 360

# "wall" reads the human-readable Time / inject_time columns, "epoch" reads the
# TimeStamp / inject_timestamp columns. See the module docstring.
TimeSource = Literal["wall", "epoch"]
DEFAULT_TIME_SOURCE: TimeSource = "wall"

# Fallback pod -> service rule, used only when the pod name matches no service
# listed in construct_data/root_cause_*.json. Strips the Kubernetes ReplicaSet
# hash and the pod suffix: "frontend-579b9bff58-t2dbm" -> "frontend".
_POD_SUFFIX_RE = re.compile(r"^(?P<service>.+?)(?:-[0-9a-z]{8,10})?(?:-[0-9a-z]{5})?$")

REPO_ROOT = Path(__file__).resolve().parent.parent


def dataset_root() -> Path:
    """Root of the Nezha checkout. Overridable with NEZHA_DATA_DIR."""
    raw = os.environ.get("NEZHA_DATA_DIR", "./data/Nezha")
    path = Path(raw)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


# ---------------------------------------------------------------------------
# Services and pod -> service mapping
# ---------------------------------------------------------------------------

def load_known_services(root: Path) -> dict[str, str]:
    """Return {service_name: system} from the two root-cause manifests."""
    services: dict[str, str] = {}
    for filename, system in (
        ("root_cause_hipster.json", "online_boutique"),
        ("root_cause_ts.json", "train_ticket"),
    ):
        path = root / "construct_data" / filename
        if not path.exists():
            continue
        with path.open(encoding="utf-8-sig") as handle:
            for service in json.load(handle):
                services[service] = system
    return services


def pod_to_service(pod: str, known: dict[str, str]) -> tuple[str, str]:
    """Map a pod name to a service name.

    Returns (service, method) where method is "exact" when the pod name is
    already a service name, "prefix" when it matched a known service prefix, or
    "regex" when only the suffix-stripping fallback applied. The method counts
    go into docs/label-audit.md: they are the evidence that the pod-level ground
    truth can be lifted to the service level.
    """
    pod = pod.removesuffix("_metric.csv")
    if pod in known:
        return pod, "exact"
    # Longest known service the pod name starts with, so that
    # "ts-travel2-service-..." does not collapse onto "ts-travel-service".
    candidates = [name for name in known if pod.startswith(name + "-")]
    if candidates:
        return max(candidates, key=len), "prefix"
    match = _POD_SUFFIX_RE.match(pod)
    return (match.group("service") if match else pod), "regex"


# ---------------------------------------------------------------------------
# Fault injections
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Injection:
    injection_id: str
    day: str
    system: str
    inject_ts: datetime
    inject_pod: str
    root_cause_service: str
    fault_type: str


def parse_wall_clock(value: str) -> datetime:
    """Parse a Nezha wall-clock string as UTC, ignoring any fractional part.

    Handles both "2022-08-22 03:53:54" (fault list) and
    "2022-08-22 03:51:19.607158889 +0000 UTC m=+0.113" (metric CSV).
    """
    return datetime.strptime(value.strip()[:19], "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=UTC
    )


def load_injections(
    root: Path, time_source: TimeSource = DEFAULT_TIME_SOURCE
) -> list[Injection]:
    """Read every rca_data/<day>/<day>-fault_list.json into a flat sorted list."""
    known = load_known_services(root)
    injections: list[Injection] = []
    for path in sorted((root / "rca_data").glob("*/*-fault_list.json")):
        day = path.parent.name
        with path.open(encoding="utf-8-sig") as handle:
            by_hour = json.load(handle)
        items = [item for hour in sorted(by_hour) for item in by_hour[hour]]
        items.sort(key=lambda item: (str(item["inject_time"]), int(item["inject_timestamp"])))
        for index, item in enumerate(items):
            pod = str(item["inject_pod"])
            service, _ = pod_to_service(pod, known)
            if time_source == "wall":
                inject_ts = parse_wall_clock(str(item["inject_time"]))
            else:
                inject_ts = datetime.fromtimestamp(
                    int(item["inject_timestamp"]), tz=UTC
                )
            injections.append(
                Injection(
                    injection_id=f"{day}#{index:03d}",
                    day=day,
                    system=known.get(service, "unknown"),
                    inject_ts=inject_ts,
                    inject_pod=pod,
                    root_cause_service=service,
                    fault_type=str(item["inject_type"]),
                )
            )
    return injections


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Window:
    window_id: str
    day: str
    system: str
    pod: str
    service: str
    start_ts: datetime
    is_fault: bool
    fault_type: str          # one of the five inject types, or "normal"
    root_cause_service: str  # empty for normal windows
    injection_id: str        # empty for normal windows

    def as_row(self) -> dict[str, str]:
        row = asdict(self)
        row["start_ts"] = self.start_ts.isoformat()
        row["is_fault"] = "1" if self.is_fault else "0"
        return row


WINDOW_CSV_FIELDS = [
    "window_id", "day", "system", "pod", "service",
    "start_ts", "is_fault", "fault_type", "root_cause_service", "injection_id",
]


def make_window_id(service: str, pod: str, start_ts: datetime) -> str:
    """Deterministic window id, per 03-schemas-and-contracts.md §1.1.

    That document specifies hash(service + start_ts). The pod is folded in as
    well because two pods of one service can be alive at once (ts-basic-service
    runs two replicas on the 2023-01 days) and the ground truth is attached to
    the pod, not the service.
    """
    key = f"{service}|{pod}|{start_ts.isoformat()}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


@dataclass
class MetricScanStats:
    files: int = 0
    rows: int = 0
    skipped_rows: int = 0
    timestamp_mismatches: int = 0
    duplicate_window_ids: int = 0


def build_windows(
    root: Path, time_source: TimeSource = DEFAULT_TIME_SOURCE
) -> tuple[list[Window], MetricScanStats]:
    """Enumerate every (pod, minute) window in rca_data and label it."""
    known = load_known_services(root)
    by_day: dict[str, list[Injection]] = {}
    for injection in load_injections(root, time_source):
        by_day.setdefault(injection.day, []).append(injection)

    before = timedelta(seconds=LABEL_BEFORE_SECONDS)
    after = timedelta(seconds=LABEL_AFTER_SECONDS)

    windows: list[Window] = []
    seen: set[str] = set()
    stats = MetricScanStats()
    for path in sorted((root / "rca_data").glob("*/metric/*_metric.csv")):
        day = path.parent.parent.name
        stats.files += 1
        with path.open(newline="", encoding="utf-8-sig") as handle:
            for raw in csv.DictReader(handle):
                try:
                    if time_source == "wall":
                        start_ts = parse_wall_clock(raw["Time"])
                    else:
                        start_ts = datetime.fromtimestamp(
                            int(float(raw["TimeStamp"])), tz=UTC
                        )
                    pod = raw.get("PodName") or path.name
                except (KeyError, TypeError, ValueError):
                    stats.skipped_rows += 1
                    continue
                stats.rows += 1
                if not _timestamp_agrees(raw.get("Time"), raw.get("TimeStamp")):
                    stats.timestamp_mismatches += 1

                service, _ = pod_to_service(pod, known)
                window_id = make_window_id(service, pod, start_ts)
                if window_id in seen:
                    stats.duplicate_window_ids += 1
                    continue
                seen.add(window_id)

                hit = _matching_injection(start_ts, pod, by_day.get(day, ()), before, after)
                windows.append(
                    Window(
                        window_id=window_id,
                        day=day,
                        system=known.get(service, "unknown"),
                        pod=pod,
                        service=service,
                        start_ts=start_ts,
                        is_fault=hit is not None,
                        fault_type=hit.fault_type if hit else "normal",
                        root_cause_service=hit.root_cause_service if hit else "",
                        injection_id=hit.injection_id if hit else "",
                    )
                )
    return windows, stats


def _matching_injection(start_ts, pod, injections, before, after) -> Injection | None:
    """Earliest injection on the same pod whose labelled interval covers start_ts.

    Injections arrive pre-sorted by time, so windows where two injections on one
    pod overlap are attributed to the earlier one. The audit counts how often
    that happens.
    """
    for injection in injections:
        if injection.inject_pod != pod:
            continue
        if injection.inject_ts - before <= start_ts <= injection.inject_ts + after:
            return injection
    return None


def _timestamp_agrees(time_column: str | None, epoch_column: str | None) -> bool:
    """Cross-check a row's two timestamp columns against each other.

    Disagreement is a data-quality signal, not a parse failure: the audit reports
    the count so the reader can see which pods and days are affected.
    """
    if not time_column or not epoch_column:
        return True
    try:
        wall = parse_wall_clock(time_column)
        epoch = datetime.fromtimestamp(int(float(epoch_column)), tz=UTC)
    except (TypeError, ValueError):
        return True
    return abs((wall - epoch).total_seconds()) <= 2


def write_window_index(windows: list[Window], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=WINDOW_CSV_FIELDS)
        writer.writeheader()
        for window in windows:
            writer.writerow(window.as_row())


def read_window_index(path: Path) -> list[Window]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            Window(
                window_id=row["window_id"],
                day=row["day"],
                system=row["system"],
                pod=row["pod"],
                service=row["service"],
                start_ts=datetime.fromisoformat(row["start_ts"]),
                is_fault=row["is_fault"] == "1",
                fault_type=row["fault_type"],
                root_cause_service=row["root_cause_service"],
                injection_id=row["injection_id"],
            )
            for row in csv.DictReader(handle)
        ]
