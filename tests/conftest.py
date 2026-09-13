from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ops_copilot import Copilot, CopilotConfig, EVAL_CLOCK
from ops_copilot.types import Chunk, Document


@pytest.fixture(scope="session")
def copilot() -> Copilot:
    return Copilot(config=CopilotConfig())


def make_chunk(
    doc_id: str = "doc",
    *,
    hours_old: float = 1.0,
    text: str = "checkout p99 latency is 2410 milliseconds.",
    title: str = "fixture",
    source_system: str = "test",
) -> Chunk:
    updated = EVAL_CLOCK - timedelta(hours=hours_old)
    return Chunk(
        chunk_id=f"{doc_id}::p0",
        doc_id=doc_id,
        title=title,
        text=text,
        updated_at=updated,
        source_system=source_system,
        age_hours=hours_old,
    )


def make_doc(doc_id: str, hours_old: float, body: str, title: str = "doc") -> Document:
    return Document(
        doc_id=doc_id,
        title=title,
        body=body,
        updated_at=EVAL_CLOCK - timedelta(hours=hours_old),
        source_system="test",
    )


def assert_utc(ts: datetime) -> None:
    assert ts.tzinfo is not None
    assert ts.utcoffset() == timezone.utc.utcoffset(ts)
