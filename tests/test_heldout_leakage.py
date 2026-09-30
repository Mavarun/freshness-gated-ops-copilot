"""Held-out synonym split: deterministic, disjoint, and absent from product lexicons."""

from __future__ import annotations

from ops_copilot.eval import load_golden
from ops_copilot.paraphrase_set import load_paraphrase_set
from ops_copilot.perturb import synonym_pairs
from ops_copilot.robustness import leakage_report
from ops_copilot.semantic import load_glossary
from ops_copilot.synonym_split import (
    DEFAULT_SPLIT_PATH,
    DEV,
    HELDOUT,
    _render,
    build_split,
    build_split_file,
    load_split,
    novel_words,
    pair_split_map,
)
from ops_copilot.synonyms import OPS_EQUIVALENTS, OPS_PHRASES
from ops_copilot.text import fold_token, tokenize


def _folded_heldout() -> set[str]:
    return {fold_token(w) for w in load_split()["heldout_words"]}


def test_committed_split_file_matches_generator() -> None:
    fresh = build_split_file(load_paraphrase_set(), load_golden())
    assert DEFAULT_SPLIT_PATH.read_text(encoding="utf-8") == _render(fresh)


def test_split_is_deterministic_and_seeded() -> None:
    assert build_split() == build_split()
    assert build_split(seed=7)["heldout_words"] != build_split()["heldout_words"]


def test_words_and_pairs_are_disjoint_and_complete() -> None:
    split = load_split()
    dev, held = set(split["dev_words"]), set(split["heldout_words"])
    assert dev and held and not dev & held
    assert len(held) == round(split["n_words"] * split["fraction"])
    pairs = pair_split_map(split)
    assert len(pairs) == split["n_dev_pairs"] + split["n_heldout_pairs"]
    assert set(pairs) == set(synonym_pairs())
    for (key, repl), label in pairs.items():
        novel = set(novel_words(key, repl))
        assert (label == HELDOUT) == bool(novel & held), (key, repl)
        if label == DEV:
            assert novel <= dev


def test_every_synonym_row_is_tagged_from_its_replayed_pairs() -> None:
    split = load_split()
    rows = [r for r in load_paraphrase_set() if r["perturbation"] == "synonym"]
    assert set(split["rows"]) == {r["id"] for r in rows}
    by_pair = {f"{k}->{r}": label for (k, r), label in pair_split_map(split).items()}
    for rid, tag in split["rows"].items():
        assert tag["pairs"], rid
        labels = {by_pair[p] for p in tag["pairs"]}
        assert tag["split"] == (HELDOUT if HELDOUT in labels else DEV), rid
    assert split["n_dev_rows"] + split["n_heldout_rows"] == len(rows)


def test_no_heldout_word_in_the_synonym_map() -> None:
    held = _folded_heldout()
    map_words = {w for group in OPS_EQUIVALENTS for w in group}
    map_words |= {t for src, dst in OPS_PHRASES for t in (*tokenize(src), dst)}
    leaked = sorted(w for w in map_words if fold_token(w) in held)
    assert leaked == [], leaked


def test_no_heldout_word_in_the_semantic_glossary() -> None:
    held = _folded_heldout()
    lines = load_glossary()
    assert len(lines) >= 20
    leaked = sorted({t for ln in lines for t in tokenize(ln) if fold_token(t) in held})
    assert leaked == [], leaked


def test_leakage_report_shows_zero_heldout_coverage() -> None:
    leak = leakage_report()
    assert leak["per_split"]["heldout"]["covered"] == 0
    assert leak["per_split"]["heldout"]["applicable"] > 50
    assert leak["per_split"]["dev"]["covered"] > 0
    assert leak["heldout_words_in_map"] == []
    assert leak["heldout_words_in_glossary"] == []
