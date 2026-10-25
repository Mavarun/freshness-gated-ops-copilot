"""Attribute traps: must-refuse questions about a property no page records.

Why it exists: dev5 calibration (2026-10-24) found the shipped default
answering ``What colour is the checkout_retry feature flag?`` (d5-38) through
the passage-support rescue ``colour <- default``. One row says little about
how wide the hole is, so ``data/eval/attribute_traps.jsonl`` (36 rows) was
written by hand on 2026-10-25, before any config was run on it. Each row asks
a known subject (a flag, pool, deployment, runbook, on-call ...) for a property
that is meaningless for it and absent from the corpus (``shape``, ``flavour``,
``salary``, ``How heavy ...``), in four forms:

- ``what_attr_is``         What <attr> is the <subject>?          (d5-38's form)
- ``what_is_attr_of``      What is the <attr> of the <subject>?
- ``what_is_subject_attr`` What is the <subject> <attr>?
- ``how_adj_is``           How <adj> is the <subject>?

``colour`` itself is not used, so the set measures whether a fix generalises
beyond the one row it was found on. Every row is must-refuse: any refusal
counts as correct, ANSWER or PROPOSE_WRITE is an *open*.

Split (``split_traps``): whole attributes move together (salted hash), so a
word seen while designing a fix never appears in the ``confirm`` half. Only
the ``tune`` half may be looked at before the one-shot confirm.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

from ops_copilot.synonym_dev4 import OPENING

TRAPS_PATH = Path(__file__).resolve().parents[2] / "data" / "eval" / "attribute_traps.jsonl"
SPLIT_SALT = "attribute-traps-2026-10-25"
HALVES = ("tune", "confirm")
FORMS = ("what_attr_is", "what_is_attr_of", "what_is_subject_attr", "how_adj_is")


def load_traps(path: str | Path | None = None) -> list[dict]:
    src = Path(path) if path else TRAPS_PATH
    return [json.loads(ln) for ln in src.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _hash(key: str) -> str:
    return hashlib.sha256(f"{SPLIT_SALT}:{key}".encode()).hexdigest()


def split_traps(rows: list[dict] | None = None) -> dict[str, str]:
    """Row id -> ``tune`` / ``confirm``; whole attributes move together, balanced by rows."""
    rows = load_traps() if rows is None else rows
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["attribute"]].append(r)
    filled = {h: 0 for h in HALVES}
    out: dict[str, str] = {}
    for attr in sorted(groups, key=_hash):
        side = min(HALVES, key=lambda h: (filled[h], HALVES.index(h)))
        filled[side] += len(groups[attr])
        for m in groups[attr]:
            out[m["id"]] = side
    return out


def half(name: str, rows: list[dict] | None = None) -> list[dict]:
    if name not in HALVES:
        raise ValueError(f"unknown half {name!r}")
    rows = load_traps() if rows is None else rows
    sp = split_traps(rows)
    return [r for r in rows if sp[r["id"]] == name]


def score_traps(cfg, rows: list[dict]) -> dict:
    """Decisions, opened ids and opens per form for one config."""
    from ops_copilot.pipeline import Copilot

    bot = Copilot(config=cfg)
    decisions = {r["id"]: bot.ask(r["query"]).decision.value for r in rows}
    opened = sorted(rid for rid, d in decisions.items() if d in OPENING)
    form_of = {r["id"]: r["form"] for r in rows}
    by_form = {f: sum(form_of[i] == f for i in opened) for f in FORMS if any(r["form"] == f for r in rows)}
    return {"n": len(rows), "n_opened": len(opened), "opened": opened, "opened_by_form": by_form,
            "decisions": decisions}
