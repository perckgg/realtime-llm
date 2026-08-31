from __future__ import annotations

import json
from typing import Literal

try:
    from pydantic import BaseModel, Field, ValidationError
except ImportError:  # pragma: no cover
    BaseModel = object  # type: ignore
    Field = None  # type: ignore
    ValidationError = ValueError  # type: ignore


class JudgeDecision(BaseModel):
    label: Literal["true_alert", "false_positive", "uncertain"]
    severity: Literal["P1", "P2", "P3", "none"]
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str]
    reason: str
    recommended_action: str


def validate_judge_json(text: str) -> JudgeDecision:
    data = json.loads(extract_json_object(text))
    return JudgeDecision.model_validate(data)


def extract_json_object(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return stripped[start : end + 1]
    return stripped
