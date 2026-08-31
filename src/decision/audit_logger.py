from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AuditLogger:
    def __init__(self, audit_dir: str) -> None:
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    def write(self, mode: str, records: list[dict[str, Any]]) -> Path:
        path = self.audit_dir / f"{mode}_audit.jsonl"
        with path.open("w", encoding="utf-8") as file:
            for record in records:
                file.write(json.dumps(record, ensure_ascii=True) + "\n")
        return path

