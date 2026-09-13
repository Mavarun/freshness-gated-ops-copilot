"""JSONL request traces: query, ids, ages, decision, latency, cost."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ops_copilot.types import CopilotResult

DEFAULT_TRACE_PATH = Path("artifacts") / "traces.jsonl"


def result_to_trace(result: CopilotResult, *, extra: dict | None = None) -> dict:
    payload = result.as_dict()
    payload["ts"] = datetime.now(timezone.utc).isoformat()
    if extra:
        payload.update(extra)
    return payload


class TraceWriter:
    """Append-only JSONL tracer. Safe to reuse across a golden-set run."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else DEFAULT_TRACE_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, result: CopilotResult, *, extra: dict | None = None) -> dict:
        row = result_to_trace(result, extra=extra)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()
