"""Prompt-injection canary farm for retrieved evidence.

Plant unique canary tokens in a subset of corpus docs. After an extractive
draft is built, scan it: if a registered canary appears in the answer but
is *not* justified by the query (token absent from the query text), treat
that as an exfiltration signal and refuse with REFUSE_CANARY.

Offline only — no network, no LLM. Tokens are synthetic lab probes, not
production secrets.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_REGISTRY = (
    Path(__file__).resolve().parents[2] / "data" / "canaries" / "registry.json"
)

# Canaries look like CNRY-<ALNUM> so they never collide with normal ops prose.
_CANARY_RE = re.compile(r"\bCNRY-[A-Z0-9]{6,}\b")


@dataclass(frozen=True)
class CanaryRecord:
    token: str
    doc_ids: tuple[str, ...]
    note: str = ""


@dataclass
class CanaryRegistry:
    """In-memory map of planted canary tokens → corpus doc ids."""

    records: tuple[CanaryRecord, ...] = ()

    @classmethod
    def load(cls, path: str | Path | None = None) -> "CanaryRegistry":
        src = Path(path) if path else DEFAULT_REGISTRY
        if not src.is_file():
            return cls(records=())
        payload = json.loads(src.read_text(encoding="utf-8"))
        rows = payload.get("canaries", payload if isinstance(payload, list) else [])
        records: list[CanaryRecord] = []
        for row in rows:
            token = str(row["token"]).strip()
            if not token:
                continue
            doc_ids = tuple(str(d) for d in row.get("doc_ids", ()))
            records.append(
                CanaryRecord(
                    token=token,
                    doc_ids=doc_ids,
                    note=str(row.get("note", "")),
                )
            )
        return cls(records=tuple(records))

    @property
    def tokens(self) -> tuple[str, ...]:
        return tuple(r.token for r in self.records)

    def by_token(self, token: str) -> CanaryRecord | None:
        for rec in self.records:
            if rec.token == token:
                return rec
        return None

    def doc_ids_for(self, token: str) -> tuple[str, ...]:
        rec = self.by_token(token)
        return rec.doc_ids if rec else ()


@dataclass
class CanaryScanResult:
    """Outcome of scanning an answer draft for unjustified canary echoes."""

    found: tuple[str, ...] = ()
    leaked: tuple[str, ...] = ()  # found in answer, absent from query
    justified: tuple[str, ...] = ()  # found in answer AND present in query
    registry_size: int = 0

    @property
    def has_leak(self) -> bool:
        return bool(self.leaked)

    def as_dict(self) -> dict:
        return {
            "found": list(self.found),
            "leaked": list(self.leaked),
            "justified": list(self.justified),
            "registry_size": self.registry_size,
            "has_leak": self.has_leak,
        }


def find_canary_tokens(text: str, registry: CanaryRegistry | None = None) -> tuple[str, ...]:
    """Return registered canary tokens present in ``text`` (stable order)."""
    if not text:
        return ()
    hits = _CANARY_RE.findall(text)
    if registry is None or not registry.tokens:
        return tuple(dict.fromkeys(hits))
    known = set(registry.tokens)
    return tuple(dict.fromkeys(t for t in hits if t in known))


def scan_answer(
    answer: str,
    query: str,
    registry: CanaryRegistry,
) -> CanaryScanResult:
    """Detect canary tokens echoed in ``answer`` that the query did not justify.

    A token is *justified* when it appears literally in the query (operator is
    deliberately asking about the probe). Otherwise a hit is a leak.
    """
    found = find_canary_tokens(answer, registry)
    justified = tuple(t for t in found if t in query)
    leaked = tuple(t for t in found if t not in query)
    return CanaryScanResult(
        found=found,
        leaked=leaked,
        justified=justified,
        registry_size=len(registry.tokens),
    )


def canary_detection_metrics(
    cases: list[dict],
) -> dict[str, float | int]:
    """Precision/recall for canary-leak detection over labeled golden cases.

    Each case may carry:
    - ``expect_canary_leak`` (bool): whether the draft *would* leak a canary
    - ``actual_canary_leak`` (bool): whether the scan reported a leak
    """
    labeled = [c for c in cases if "expect_canary_leak" in c]
    if not labeled:
        return {
            "n_labeled": 0,
            "canary_precision": 0.0,
            "canary_recall": 0.0,
            "canary_f1": 0.0,
            "true_positives": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "true_negatives": 0,
        }
    tp = fp = fn = tn = 0
    for c in labeled:
        expect = bool(c["expect_canary_leak"])
        actual = bool(c.get("actual_canary_leak", False))
        if expect and actual:
            tp += 1
        elif not expect and actual:
            fp += 1
        elif expect and not actual:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall)
        else 0.0
    )
    return {
        "n_labeled": len(labeled),
        "canary_precision": round(precision, 4),
        "canary_recall": round(recall, 4),
        "canary_f1": round(f1, 4),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
    }
