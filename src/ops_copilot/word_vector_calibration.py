"""Calibrate the word-vector backoff on clean golden + dev synonym rows only.

Same calibration rows and safety bar as ``semantic_calibration`` (51 clean
golden queries + the 15 ``dev`` synonym rows; ``calibration_rows`` raises if
a held-out row slips in). The default config (embedding off) is the base.

Grid: ``word_vector_min_similarity`` in ``GRID`` x ``word_vector_max_neighbours``
in ``MAX_NEIGHBOURS`` x scope (``word_vector_known_words`` off / on).
Selection:

1. feasible: clean accuracy 1.000, zero fail-open, zero spurious
   PROPOSE_WRITE and zero raw PII outputs on the calibration rows;
2. highest calibration decision accuracy;
3. narrower scope first (unknown words only), then fewer neighbours;
4. the midpoint of the widest contiguous run of optimal thresholds.

The backoff is switched on by default only if the chosen setting beats the
backoff-off accuracy on the same rows (``recommend_default_on``).

``dev_pair_report`` is a word-level diagnostic on the split's *dev* pairs
only: for each dev replacement word, the corpus substitute the table offers
and whether it is a content word of the key it replaced.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from ops_copilot.config import CopilotConfig
from ops_copilot.pipeline import Copilot
from ops_copilot.semantic_calibration import calibration_rows, score
from ops_copilot.synonym_split import DEFAULT_SPLIT_PATH, load_split
from ops_copilot.text import content_tokens, normalize_text
from ops_copilot.word_vectors import TABLE_FLOOR, load_table

GRID: tuple[float, ...] = tuple(
    round(float(x), 2) for x in np.arange(TABLE_FLOOR, 1.0001, 0.01)
)
MAX_NEIGHBOURS: tuple[int, ...] = (1, 3)
SCOPES: tuple[bool, ...] = (False, True)  # word_vector_known_words


def _feasible(r: dict) -> bool:
    return (
        r["clean_accuracy"] == 1.0
        and r["n_fail_open"] == 0
        and r["n_spurious_write"] == 0
        and r["n_raw_pii_outputs"] == 0
    )


def select(results: list[dict]) -> dict:
    feasible = [r for r in results if _feasible(r)]
    if not feasible:
        raise RuntimeError("no feasible word-vector setting")
    best = max(r["accuracy"] for r in feasible)
    tops = [r for r in feasible if r["accuracy"] == best]
    known = min(r["known_words"] for r in tops)  # False < True: narrower scope
    tops = [r for r in tops if r["known_words"] == known]
    k = min(r["max_neighbours"] for r in tops)
    ok = {r["threshold"] for r in tops if r["max_neighbours"] == k}
    runs: list[list[float]] = []
    for i, th in enumerate(GRID):
        if th in ok:
            if runs and i > 0 and runs[-1][-1] == GRID[i - 1]:
                runs[-1].append(th)
            else:
                runs.append([th])
    widest = max(runs, key=len)
    return {
        "threshold": float(widest[(len(widest) - 1) // 2]),
        "max_neighbours": int(k),
        "known_words": bool(known),
        "accuracy": float(best),
        "optimal_run": [float(widest[0]), float(widest[-1])],
    }


def dev_pair_report(path=DEFAULT_SPLIT_PATH) -> list[dict]:
    """Word-level view of the dev pairs (never the held-out ones)."""
    split = load_split(path)
    dev_words = set(split["dev_words"])
    table = load_table()
    out: list[dict] = []
    for pair in split["dev_pairs"]:
        key, repl = (s.strip() for s in pair.split("->", 1))
        key_toks = set(content_tokens(normalize_text(key)))
        for tok in content_tokens(normalize_text(repl)):
            if tok not in dev_words:
                continue
            rows = table.get(tok)
            top = rows[0] if rows else None
            if top is None:
                kind = "none"
            elif top[0] in key_toks:
                kind = "key"
            elif _same_lemma(tok, top[0]):
                kind = "inflection"
            else:
                kind = "other"
            out.append(
                {
                    "pair": pair,
                    "word": tok,
                    "substitute": top[0] if top else None,
                    "cosine": top[1] if top else None,
                    "is_key_word": kind == "key",
                    "kind": kind,
                    "key_in_table_targets": sorted(
                        k for k in key_toks if k in set(table.meta.get("corpus_words", []))
                    ),
                }
            )
    return out


def _same_lemma(a: str, b: str) -> bool:
    """Crude inflection check: one word is the other plus a short suffix."""
    short, long_ = sorted((a, b), key=len)
    return len(short) >= 3 and long_.startswith(short[:-1]) and len(long_) - len(short) <= 3


def recommend_default_on(baseline: dict, chosen: dict) -> bool:
    return chosen["accuracy"] > baseline["accuracy"]


def calibrate(base: CopilotConfig | None = None) -> dict:
    base = base or CopilotConfig()
    rows = calibration_rows()
    baseline = score(Copilot(config=replace(base, use_word_vector_backoff=False)), rows)
    results: list[dict] = []
    for known in SCOPES:
        for k in MAX_NEIGHBOURS:
            for th in GRID:
                cfg = replace(
                    base,
                    use_word_vector_backoff=True,
                    word_vector_min_similarity=th,
                    word_vector_max_neighbours=k,
                    word_vector_known_words=known,
                )
                results.append(
                    {"threshold": th, "max_neighbours": k, "known_words": known}
                    | score(Copilot(config=cfg), rows)
                )
    chosen = select(results)
    return {
        "calibration_rows": [rid for rid, _, _ in rows],
        "n_clean": sum(1 for _, g, _ in rows if g == "clean"),
        "n_dev": sum(1 for _, g, _ in rows if g == "dev"),
        "grid": list(GRID),
        "max_neighbours": list(MAX_NEIGHBOURS),
        "scopes": ["unknown words", "unknown + known words"],
        "baseline_off": baseline,
        "chosen": chosen,
        "default_on": recommend_default_on(baseline, chosen),
        "dev_pairs": dev_pair_report(),
        "results": results,
    }
