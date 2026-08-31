from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from urllib import request
from urllib.error import HTTPError, URLError


ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a minimal Gemini API request to verify connectivity.")
    parser.add_argument("--model", default=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"))
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument(
        "--env-file",
        action="append",
        default=[],
        help="Optional extra .env file. Values do not override existing environment variables.",
    )
    parser.add_argument(
        "--prompt",
        default='Return JSON {"status":"ok","reply":"gemini connection works"} and nothing else.',
    )
    return parser.parse_args()


def main() -> int:
    _load_dotenv(ROOT / ".env")
    args = parse_args()
    for env_file in args.env_file:
        _load_dotenv(Path(env_file))

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to the environment or .env before running this test.")

    payload = {
        "contents": [{"role": "user", "parts": [{"text": args.prompt}]}],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 64,
            "thinkingConfig": {"thinkingBudget": 0},
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "status": {"type": "STRING"},
                    "reply": {"type": "STRING"},
                },
                "required": ["status", "reply"],
            },
        },
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{args.model}:generateContent"
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )

    started = time.perf_counter()
    try:
        with request.urlopen(req, timeout=args.timeout) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(
            json.dumps(
                {
                    "ok": False,
                    "status_code": exc.code,
                    "reason": exc.reason,
                    "error_body": body,
                    "model": args.model,
                },
                indent=2,
            )
        )
        return 1
    except URLError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "reason": str(exc.reason),
                    "model": args.model,
                },
                indent=2,
            )
        )
        return 1

    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    candidates = response_payload.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"Gemini returned no candidates: {response_payload}")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(str(part.get("text", "")) for part in parts).strip()
    if not text:
        raise RuntimeError(f"Gemini returned empty text: {response_payload}")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = {"raw_text": text}

    print(
        json.dumps(
            {
                "ok": True,
                "model": args.model,
                "latency_ms": latency_ms,
                "usage": response_payload.get("usageMetadata") or {},
                "response": parsed,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
