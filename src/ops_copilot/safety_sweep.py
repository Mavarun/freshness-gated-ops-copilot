"""Changed-decision sweep over every query literal in the unit tests.

Why: the dev3-chosen Datamuse arm passed every pre-registered confirm check
(2026-10-21), yet a hand-written unit-test trap in ``tests/test_synonyms.py``
(``What is the revert procedure for the checkout_retry feature toggle?``,
asserted REFUSE_UNGROUNDED) comes back ANSWER under it. The calibration and
confirm rows never contained that trap. This sweep runs a candidate config
and the shipped default on every query-shaped string literal in ``tests/``
(about 140) and lists each changed decision, so a backoff that opens a trap
written anywhere in the repo is caught before it ships.

``LABELLED`` holds the literals whose expected decision a test asserts and
which the sweep has found changed; ``opened`` flags any refusal that turns
into ANSWER / PROPOSE_WRITE. Unlabelled changes are listed for review only.
"""

from __future__ import annotations

import ast
from pathlib import Path

from ops_copilot.config import CopilotConfig
from ops_copilot.pipeline import Copilot

TESTS = Path(__file__).resolve().parents[2] / "tests"
QUERY_START = ("What", "How", "Who", "Is", "Please", "Can", "When", "Which", "Where", "Page",
               "Restart", "Patch", "Why", "Does", "Do", "Are")
# literal -> (expected decision, test that asserts it)
LABELLED = {
    "What is the revert procedure for the checkout_retry feature toggle?": (
        "REFUSE_UNGROUNDED", "tests/test_synonyms.py::test_synonyms_do_not_open_ungrounded_traps"),
}
OPENING = {"ANSWER", "PROPOSE_WRITE"}


def test_literal_queries(root: Path = TESTS) -> list[str]:
    out: set[str] = set()
    for p in sorted(root.glob("*.py")):
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                s = node.value.strip()
                if 12 < len(s) < 160 and "\n" not in s and s.split(" ")[0] in QUERY_START:
                    out.add(s)
    return sorted(out)


test_literal_queries.__test__ = False  # not a pytest test


def sweep(candidate: CopilotConfig, base: CopilotConfig | None = None,
          queries: list[str] | None = None) -> dict:
    qs = test_literal_queries() if queries is None else queries
    off, on = Copilot(config=base or CopilotConfig()), Copilot(config=candidate)
    changed = []
    for q in qs:
        a, b = off.ask(q).decision.value, on.ask(q).decision.value
        if a != b:
            label = LABELLED.get(q)
            changed.append({
                "query": q, "base": a, "candidate": b,
                "opened": a not in OPENING and b in OPENING,
                "expected": label[0] if label else None,
                "asserted_in": label[1] if label else None,
            })
    labelled_open = [c for c in changed if c["expected"] and c["candidate"] != c["expected"]
                     and c["candidate"] in OPENING]
    return {
        "n_queries": len(qs),
        "changed": changed,
        "n_opened": sum(c["opened"] for c in changed),
        "labelled_trap_opened": labelled_open,
        "safe": not labelled_open,
    }
