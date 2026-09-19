"""Load the synthetic ops corpus and attach age relative to a clock."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import pandas as pd

from ops_copilot.config import EVAL_CLOCK, parse_clock
from ops_copilot.types import Chunk, Document

DEFAULT_CORPUS = (
    Path(__file__).resolve().parents[2] / "data" / "corpus" / "ops_docs.jsonl"
)
CANARY_CORPUS = (
    Path(__file__).resolve().parents[2] / "data" / "corpus" / "canary_docs.jsonl"
)


def age_hours(updated_at: datetime, now: datetime) -> float:
    """Hours between document ``updated_at`` and the evaluation clock."""
    delta = now - updated_at
    return delta.total_seconds() / 3600.0


def parse_updated_at(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return parse_clock(value)
    return parse_clock(str(value))


def load_documents(path: str | Path | None = None) -> list[Document]:
    """Load JSONL documents. Each line needs doc_id, title, body, updated_at, source_system."""
    src = Path(path) if path else DEFAULT_CORPUS
    docs: list[Document] = []
    with src.open(encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{src}:{line_no}: invalid JSON") from exc
            missing = {"doc_id", "title", "body", "updated_at", "source_system"} - set(row)
            if missing:
                raise ValueError(f"{src}:{line_no}: missing fields {sorted(missing)}")
            docs.append(
                Document(
                    doc_id=str(row["doc_id"]),
                    title=str(row["title"]),
                    body=str(row["body"]),
                    updated_at=parse_updated_at(row["updated_at"]),
                    source_system=str(row["source_system"]),
                )
            )
    if not docs:
        raise ValueError(f"corpus is empty: {src}")
    canary_src = CANARY_CORPUS if path is None else None
    if (
        canary_src is not None
        and canary_src.is_file()
        and Path(src).resolve() == DEFAULT_CORPUS.resolve()
    ):
        with canary_src.open(encoding="utf-8") as handle:
            for line_no, raw in enumerate(handle, start=1):
                line = raw.strip()
                if not line:
                    continue
                row = json.loads(line)
                missing = {"doc_id", "title", "body", "updated_at", "source_system"} - set(row)
                if missing:
                    raise ValueError(
                        f"{canary_src}:{line_no}: missing fields {sorted(missing)}"
                    )
                docs.append(
                    Document(
                        doc_id=str(row["doc_id"]),
                        title=str(row["title"]),
                        body=str(row["body"]),
                        updated_at=parse_updated_at(row["updated_at"]),
                        source_system=str(row["source_system"]),
                    )
                )
    return docs


def chunk_document(doc: Document, now: datetime = EVAL_CLOCK) -> list[Chunk]:
    """Split a document on blank lines so retrieval returns scored chunks + metadata."""
    paragraphs = [p.strip() for p in doc.body.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [doc.body.strip() or doc.title]
    age = age_hours(doc.updated_at, now)
    chunks: list[Chunk] = []
    for idx, para in enumerate(paragraphs):
        chunks.append(
            Chunk(
                chunk_id=f"{doc.doc_id}::p{idx}",
                doc_id=doc.doc_id,
                title=doc.title,
                text=para,
                updated_at=doc.updated_at,
                source_system=doc.source_system,
                age_hours=age,
            )
        )
    return chunks


class Corpus:
    """In-memory corpus with ages computed against a single clock."""

    def __init__(
        self,
        docs: list[Document] | None = None,
        *,
        path: str | Path | None = None,
        now: datetime | str | None = None,
    ) -> None:
        self.now = parse_clock(now)
        self.docs = docs if docs is not None else load_documents(path)
        self.chunks: list[Chunk] = []
        for doc in self.docs:
            self.chunks.extend(chunk_document(doc, self.now))

    def documents_frame(self) -> pd.DataFrame:
        rows = []
        for doc in self.docs:
            rows.append(
                {
                    "doc_id": doc.doc_id,
                    "title": doc.title,
                    "source_system": doc.source_system,
                    "updated_at": doc.updated_at.isoformat(),
                    "age_hours": age_hours(doc.updated_at, self.now),
                    "chars": len(doc.body),
                }
            )
        return pd.DataFrame(rows)

    def chunks_frame(self) -> pd.DataFrame:
        return pd.DataFrame([asdict(c) for c in self.chunks])

    def by_id(self, doc_id: str) -> Document:
        for doc in self.docs:
            if doc.doc_id == doc_id:
                return doc
        raise KeyError(doc_id)
