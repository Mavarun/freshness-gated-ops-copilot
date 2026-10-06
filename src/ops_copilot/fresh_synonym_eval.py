"""Fresh, hand-written general-English synonym set (26 rows), reported separately.

``data/eval/synonym_fresh.jsonl`` paraphrases 26 golden queries with one or two
general-English swaps (``remaining -> residual``, ``status -> condition``,
``password -> passcode``) and keeps the golden label. It was written on
2026-10-06 by the author of the word-vector backoff, *after* the backoff was
built and calibrated, so it is a check of what the external resource is meant
to cover, not an unbiased benchmark. ``vocabulary_overlap`` enforces that no
swapped-in word is a dev or held-out word of the perturbation split or any
word of the eval's synonym map, so the 203-row set and its split stay
untouched and the two sets share no replacement vocabulary.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from ops_copilot.config import CopilotConfig
from ops_copilot.pii import detect_pii
from ops_copilot.pipeline import Copilot
from ops_copilot.text import tokenize

FRESH_PATH = Path(__file__).resolve().parents[2] / "data" / "eval" / "synonym_fresh.jsonl"

CONFIGS: dict[str, dict] = {
    "default (word-vector backoff off; = PR #14)": {"use_word_vector_backoff": False},
    "+ word-vector backoff (calibrated)": {"use_word_vector_backoff": True},
    "+ word-vector backoff, unknown words only": {
        "use_word_vector_backoff": True,
        "word_vector_known_words": False,
    },
    "+ corpus PPMI backoff (PR #11, for comparison)": {"use_semantic_backoff": True},
}


def load_fresh(path: str | Path | None = None) -> list[dict]:
    src = Path(path) if path else FRESH_PATH
    return [json.loads(ln) for ln in src.read_text(encoding="utf-8").splitlines() if ln.strip()]


def swapped_words(row: dict) -> set[str]:
    out: set[str] = set()
    for part in str(row["swap"]).split(","):
        out |= set(tokenize(part.split("->", 1)[1]))
    return out


def vocabulary_overlap(rows: list[dict]) -> dict[str, list[str]]:
    """Swapped-in words shared with the perturbation split / synonym map (must be empty)."""
    from ops_copilot.perturb import synonym_pairs
    from ops_copilot.synonym_split import load_split

    split = load_split()
    eval_vocab = set(split["dev_words"]) | set(split["heldout_words"])
    for _, repl in synonym_pairs():
        eval_vocab |= set(tokenize(repl))
    hits = {r["id"]: sorted(swapped_words(r) & eval_vocab) for r in rows}
    return {k: v for k, v in hits.items() if v}


def score(config: CopilotConfig, rows: list[dict]) -> dict:
    bot = Copilot(config=config)
    per_row: dict[str, str] = {}
    wrong: list[str] = []
    fail_open = spurious = raw_pii = 0
    by_gate: dict[str, dict[str, int]] = {}
    for row in rows:
        res = bot.ask(row["query"])
        got, want = res.decision.value, row["expect_decision"]
        per_row[row["id"]] = got
        g = by_gate.setdefault(want, {"n": 0, "correct": 0})
        g["n"] += 1
        g["correct"] += got == want
        raw_pii += bool(detect_pii(res.answer or ""))
        if got != want:
            wrong.append(f"{row['id']}:{want}->{got}")
            fail_open += got == "ANSWER"
            spurious += got == "PROPOSE_WRITE"
    n = len(rows)
    ans = by_gate.get("ANSWER", {"n": 0, "correct": 0})
    return {
        "n": n,
        "accuracy": (n - len(wrong)) / n if n else 0.0,
        "answer_correct": f"{ans['correct']}/{ans['n']}",
        "n_fail_open": fail_open,
        "n_spurious_write": spurious,
        "n_raw_pii_outputs": raw_pii,
        "by_gate": by_gate,
        "wrong": wrong,
        "decisions": per_row,
    }


def run_fresh_eval(base: CopilotConfig | None = None) -> dict:
    base = base or CopilotConfig()
    rows = load_fresh()
    return {
        "n_rows": len(rows),
        "vocabulary_overlap": vocabulary_overlap(rows),
        "configs": {label: score(replace(base, **knobs), rows) for label, knobs in CONFIGS.items()},
    }
