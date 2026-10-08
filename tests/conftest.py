from __future__ import annotations

import socket
from datetime import datetime, timedelta, timezone

import pytest

from ops_copilot import Copilot, CopilotConfig, EVAL_CLOCK
from ops_copilot.types import Chunk, Document


_REAL_CONNECT = socket.socket.connect
_REAL_CONNECT_EX = socket.socket.connect_ex


def _offline_only(real):
    def guard(self: socket.socket, address, *args, **kwargs):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            raise RuntimeError(f"tests must stay offline: blocked connect to {address!r}")
        return real(self, address, *args, **kwargs)

    return guard


@pytest.fixture(autouse=True, scope="session")
def _no_network():
    """CI never needs the network: every committed snapshot is read from disk.

    Any IPv4 / IPv6 connect from a test (a fetch script, a model download, an
    API call) fails loudly instead of quietly depending on the network.
    Unix sockets (the event loop's self-pipe) are untouched.
    """
    mp = pytest.MonkeyPatch()
    mp.setattr(socket.socket, "connect", _offline_only(_REAL_CONNECT))
    mp.setattr(socket.socket, "connect_ex", _offline_only(_REAL_CONNECT_EX))
    yield
    mp.undo()


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
