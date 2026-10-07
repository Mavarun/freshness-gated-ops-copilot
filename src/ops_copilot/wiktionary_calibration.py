"""Calibrate the Wiktionary computing-sense backoff on clean + dev rows only.

Rows, safety bar and the held-out go / no-go rule are those of
``tag_synonym_calibration`` (51 clean golden + 15 dev synonym rows; the
held-out synonym rows run once, after this choice is committed, and the
backoff becomes a default only if held-out accuracy does not drop and no
fail-open, spurious write or raw PII appears).

Grid: ``wiktionary_min_score`` in ``MIN_SCORES`` (2 = listed synonyms and
pointer glosses only, 1 = also the gloss head word) x
``wiktionary_max_neighbours`` in ``MAX_NEIGHBOURS`` x scope (unknown words /
unknown + known). Base: default config (tag synonyms, word vectors and
embeddings off). Selection, fixed before any run: feasible, then highest
accuracy, then ties by the higher min_score, the narrower scope, then fewer
neighbours.

``dev_word_report`` is the word-level view on the *dev* pairs only.
"""

from __future__ import annotations

from dataclasses import replace

from ops_copilot.config import CopilotConfig
from ops_copilot.corpus import Corpus
from ops_copilot.pipeline import Copilot
from ops_copilot.semantic_calibration import calibration_rows, score
from ops_copilot.synonym_split import DEFAULT_SPLIT_PATH, load_split
from ops_copilot.tag_synonym_calibration import _feasible, recommend_default_on
from ops_copilot.text import content_tokens, normalize_text
from ops_copilot.wiktionary_senses import WiktionarySenseBackoff

MIN_SCORES: tuple[int, ...] = (2, 1)
MAX_NEIGHBOURS: tuple[int, ...] = (1, 3)
SCOPES: tuple[bool, ...] = (False, True)


def _tie_key(r: dict) -> tuple:
    return (-int(r["min_score"]), bool(r["known_words"]), int(r["max_neighbours"]))


def select(results: list[dict]) -> dict:
    feasible = [r for r in results if _feasible(r)]
    if not feasible:
        raise RuntimeError("no feasible Wiktionary setting")
    best = max(r["accuracy"] for r in feasible)
    pick = min((r for r in feasible if r["accuracy"] == best), key=_tie_key)
    return {
        "min_score": int(pick["min_score"]),
        "max_neighbours": int(pick["max_neighbours"]),
        "known_words": bool(pick["known_words"]),
        "accuracy": float(best),
        "n_optimal": sum(1 for r in feasible if r["accuracy"] == best),
    }


def dev_word_report(path=DEFAULT_SPLIT_PATH, *, min_score: int = 1) -> list[dict]:
    split = load_split(path)
    dev_words = set(split["dev_words"])
    texts = [f"{c.title} {c.text}" for c in Corpus().chunks]
    bk = WiktionarySenseBackoff(texts, max_neighbours=3, min_score=min_score)
    out: list[dict] = []
    for pair in split["dev_pairs"]:
        key, repl = (s.strip() for s in pair.split("->", 1))
        key_toks = set(content_tokens(normalize_text(key)))
        for tok in content_tokens(normalize_text(repl)):
            if tok not in dev_words:
                continue
            nb = bk.neighbours(tok)
            subs = [n.word for n in nb]
            if not subs:
                kind = "none"
            elif subs[0] in key_toks:
                kind = "key"
            elif key_toks & set(subs):
                kind = "key (not top)"
            else:
                kind = "other"
            out.append(
                {
                    "pair": pair,
                    "word": tok,
                    "substitutes": subs,
                    "scores": [int(n.similarity) for n in nb],
                    "kind": kind,
                }
            )
    return out


def calibrate(base: CopilotConfig | None = None) -> dict:
    base = replace(
        base or CopilotConfig(), use_word_vector_backoff=False, use_tag_synonym_backoff=False
    )
    rows = calibration_rows()
    baseline = score(Copilot(config=replace(base, use_wiktionary_backoff=False)), rows)
    results: list[dict] = []
    for m in MIN_SCORES:
        for known in SCOPES:
            for k in MAX_NEIGHBOURS:
                cfg = replace(
                    base,
                    use_wiktionary_backoff=True,
                    wiktionary_min_score=m,
                    wiktionary_max_neighbours=k,
                    wiktionary_known_words=known,
                )
                results.append(
                    {"min_score": m, "max_neighbours": k, "known_words": known}
                    | score(Copilot(config=cfg), rows)
                )
    chosen = select(results)
    return {
        "calibration_rows": [rid for rid, _, _ in rows],
        "n_clean": sum(1 for _, g, _ in rows if g == "clean"),
        "n_dev": sum(1 for _, g, _ in rows if g == "dev"),
        "baseline_off": baseline,
        "chosen": chosen,
        "default_on": recommend_default_on(baseline, chosen),
        "dev_words": dev_word_report(),
        "results": results,
    }
