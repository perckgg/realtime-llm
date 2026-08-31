from __future__ import annotations

import re
from typing import Any

from src.models import LogEvent
from src.time_utils import parse_timestamp


NOISE_PATTERNS = [re.compile(r"periodic healthcheck succeeded", re.IGNORECASE)]


def preprocess_logs(records: list[dict[str, Any]]) -> list[LogEvent]:
    seen: set[tuple[str, str, str]] = set()
    events: list[LogEvent] = []
    for index, record in enumerate(records):
        message = str(record.get("message", ""))
        if any(pattern.search(message) for pattern in NOISE_PATTERNS):
            continue
        timestamp = parse_timestamp(str(record["timestamp"]))
        key = (timestamp.isoformat(), str(record.get("service_id", "")), message)
        if key in seen:
            continue
        seen.add(key)
        events.append(
            LogEvent(
                doc_id=str(record.get("doc_id") or f"log-{index + 1}"),
                timestamp=timestamp,
                node_id=str(record.get("node_id", "unknown")),
                service_id=str(record.get("service_id", "unknown")),
                pod_id=record.get("pod_id"),
                severity=str(record.get("severity", "INFO")).upper(),
                event_type=str(record.get("event_type", "log")),
                message=message,
                source=str(record.get("source", "log")),
                metadata={key: value for key, value in record.items() if key not in {"message"}},
            )
        )
    return events

