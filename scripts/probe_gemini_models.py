"""Probe which model the Gemini API really serves for each requested id (QD-020, QD-022).

    py scripts/probe_gemini_models.py --models gemini-2.5-flash gemini-3.5-flash gemini-3.8-flash

Sends the same judge request as `GeminiBackend` (temperature 0, thinkingBudget 0,
JSON response schema) with prompt #`--index` of GD1's paper_500 BM25 dump, once per
model, bypassing the cache, and prints the `modelVersion` the API answered with.
A model is usable as a judge only if `modelVersion` == the requested id
(`GeminiBackend` stops a run otherwise). Costs one API call per model.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib import request
from urllib.error import HTTPError

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from services.judge.backends import _RESPONSE_SCHEMA, GEMINI_URL  # noqa: E402

DUMP = REPO / "data" / "gd1_parity" / "paper_500_hybrid_bm25_top6.jsonl"


def _prompt(index: int) -> str:
    with DUMP.open(encoding="utf-8") as handle:
        for i, line in enumerate(handle):
            if i == index:
                return str(json.loads(line)["prompt"])
    raise SystemExit(f"{DUMP} has fewer than {index + 1} prompts")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--max-output-tokens", type=int, default=1024)
    args = parser.parse_args()
    load_dotenv(REPO / ".env")
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY is not set")
    prompt = _prompt(args.index)
    payload = json.dumps(
        {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": args.max_output_tokens,
                "thinkingConfig": {"thinkingBudget": 0},
                "responseMimeType": "application/json",
                "responseSchema": _RESPONSE_SCHEMA,
            },
        }
    ).encode("utf-8")
    for model in args.models:
        req = request.Request(
            GEMINI_URL.format(model=model),
            data=payload,
            headers={"Content-Type": "application/json", "x-goog-api-key": key},
            method="POST",
        )
        started = time.perf_counter()
        try:
            with request.urlopen(req, timeout=120) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            print(json.dumps({"model": model, "error": f"HTTP {exc.code}: {exc.read().decode('utf-8')[:300]}"}))
            continue
        latency = time.perf_counter() - started
        usage = body.get("usageMetadata") or {}
        parts = (body.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
        text = "".join(str(p.get("text", "")) for p in parts)
        try:
            label = json.loads(text).get("label")
        except ValueError:
            label = "unparseable"
        served = body.get("modelVersion")
        print(
            json.dumps(
                {
                    "model": model,
                    "model_version": served,
                    "usable": served == model,
                    "latency_s": round(latency, 2),
                    "prompt_tokens": usage.get("promptTokenCount"),
                    "output_tokens": usage.get("candidatesTokenCount"),
                    "thoughts_tokens": usage.get("thoughtsTokenCount", 0),
                    "label": label,
                }
            )
        )


if __name__ == "__main__":
    main()
