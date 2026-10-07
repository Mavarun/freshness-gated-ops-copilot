"""Calibrate the tag-synonym backoff on clean golden + dev synonym rows only.

Same calibration rows and safety bar as ``word_vector_calibration`` (51 clean
golden queries + the 15 ``dev`` synonym rows; ``calibration_rows`` raises if
a held-out row slips in). The default config (embedding off, word-vector
backoff off) is the base.

Grid: ``tag_synonym_sites`` in ``SITE_GRID`` x ``tag_synonym_min_sites`` in
``MIN_SITES`` x ``tag_synonym_max_neighbours`` in ``MAX_NEIGHBOURS`` x scope
(``tag_synonym_known_words`` off / on). Selection, fixed before any run:

1. feasible: clean accuracy 1.000, zero fail-open, zero spurious
   PROPOSE_WRITE and zero raw PII outputs on the calibration rows;
2. highest calibration decision accuracy;
3. ties: ops sites before all sites, then more sites required, then the
   narrower scope (unknown words only), then fewer neighbours.

Go / no-go, also fixed before the held-out run: the chosen setting becomes the
default only if (a) it beats backoff-off accuracy on the calibration rows
(``recommend_default_on``) and (b) on the held-out synonym rows it does not
lower accuracy and adds no fail-open, spurious write or raw PII (checked by
``scripts/run_robustness.py``, reported in the README). The held-out rows are
run once, after this file's choice is committed.

``dev_word_report`` is a word-level diagnostic on the split's *dev* pairs
only: for each dev replacement word, the corpus substitute the tag table
offers (all sites, 1 site, top 3) and whether it is a word of the key it
replaced.
"""

from __future__ import annotations

from dataclasses import replace

from ops_copilot.config import CopilotConfig
from ops_copilot.corpus import Corpus
from ops_copilot.pipeline import Copilot
from ops_copilot.semantic_calibration import calibration_rows, score
from ops_copilot.synonym_split import DEFAULT_SPLIT_PATH, load_split
from ops_copilot.tag_synonyms import TagSynonymBackoff
from ops_copilot.text import content_tokens, normalize_text

SITE_GRID: tuple[str, ...] = ("ops", "all")
MIN_SITES: tuple[int, ...] = (1, 2, 3)
MAX_NEIGHBOURS: tuple[int, ...] = (1, 3)
SCOPES: tuple[bool, ...] = (False, True)  # tag_synonym_known_words


def _feasible(r: dict) -> bool:
    return (
        r["clean_accuracy"] == 1.0
        and r["n_fail_open"] == 0
        and r["n_spurious_write"] == 0
        and r["n_raw_pii_outputs"] == 0
    )


def _tie_key(r: dict) -> tuple:
    return (
        SITE_GRID.index(r["sites"]),
        -int(r["min_sites"]),
        bool(r["known_words"]),
        int(r["max_neighbours"]),
    )


def select(results: list[dict]) -> dict:
    feasible = [r for r in results if _feasible(r)]
    if not feasible:
        raise RuntimeError("no feasible tag-synonym setting")
    best = max(r["accuracy"] for r in feasible)
    pick = min((r for r in feasible if r["accuracy"] == best), key=_tie_key)
    return {
        "sites": pick["sites"],
        "min_sites": int(pick["min_sites"]),
        "max_neighbours": int(pick["max_neighbours"]),
        "known_words": bool(pick["known_words"]),
        "accuracy": float(best),
        "n_optimal": sum(1 for r in feasible if r["accuracy"] == best),
    }


def recommend_default_on(baseline: dict, chosen: dict) -> bool:
    return chosen["accuracy"] > baseline["accuracy"]


def dev_word_report(path=DEFAULT_SPLIT_PATH) -> list[dict]:
    """Word-level view of the dev pairs (never the held-out ones)."""
    split = load_split(path)
    dev_words = set(split["dev_words"])
    texts = [f"{c.title} {c.text}" for c in Corpus().chunks]
    bk = TagSynonymBackoff(texts, max_neighbours=3)
    out: list[dict] = []
    for pair in split["dev_pairs"]:
        key, repl = (s.strip() for s in pair.split("->", 1))
        key_toks = set(content_tokens(normalize_text(key)))
        for tok in content_tokens(normalize_text(repl)):
            if tok not in dev_words:
                continue
            subs = [n.word for n in bk.neighbours(tok)]
            if not subs:
                kind = "none"
            elif subs[0] in key_toks:
                kind = "key"
            elif key_toks & set(subs):
                kind = "key (not top)"
            else:
                kind = "other"
            out.append({"pair": pair, "word": tok, "substitutes": subs, "kind": kind})
    return out


def calibrate(base: CopilotConfig | None = None) -> dict:
    base = replace(base or CopilotConfig(), use_word_vector_backoff=False)
    rows = calibration_rows()
    baseline = score(Copilot(config=replace(base, use_tag_synonym_backoff=False)), rows)
    results: list[dict] = []
    for sites in SITE_GRID:
        for m in MIN_SITES:
            for known in SCOPES:
                for k in MAX_NEIGHBOURS:
                    cfg = replace(
                        base,
                        use_tag_synonym_backoff=True,
                        tag_synonym_sites=sites,
                        tag_synonym_min_sites=m,
                        tag_synonym_max_neighbours=k,
                        tag_synonym_known_words=known,
                    )
                    results.append(
                        {"sites": sites, "min_sites": m, "max_neighbours": k, "known_words": known}
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
