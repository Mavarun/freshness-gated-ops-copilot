"""Wiktionary computing-sense extract and its substitute table."""

from __future__ import annotations

from ops_copilot.corpus import Corpus
from ops_copilot.wiktionary_senses import (
    EXTRACT_N_SENSES,
    EXTRACT_SHA256,
    OPS_TOPICS,
    SCORE_GLOSS_HEAD,
    SCORE_SYNONYM,
    WiktionarySenseBackoff,
    build_sense_table,
    dump_extract,
    extract_senses,
    gloss_head,
    load_extract,
)


def test_extract_is_the_pinned_build() -> None:
    ext = load_extract()
    assert ext["sha256"] == EXTRACT_SHA256
    assert len(ext["senses"]) == EXTRACT_N_SENSES == ext["meta"]["n_senses"]
    assert ext["meta"]["topics"] == list(OPS_TOPICS)
    assert "CC BY-SA" in ext["meta"]["license"]
    assert len(ext["meta"]["source_sha256"]) == 64


def test_extract_rows_are_plain_english_domain_senses() -> None:
    for s in load_extract()["senses"]:
        assert s["topic"] in OPS_TOPICS
        assert s["word"].isalpha() and s["word"] == s["word"].lower() and len(s["word"]) >= 3
        assert s["gloss"] and len(s["gloss"]) <= 200
        assert all(w.isalpha() for w in s["synonyms"])


def test_extract_senses_filters_language_topic_and_headword() -> None:
    entry = {
        "lang_code": "en",
        "word": "bounce",
        "pos": "verb",
        "senses": [
            {"glosses": ["To rebound."], "topics": []},
            {"glosses": ["To restart a device."], "topics": ["computing"], "synonyms": [{"word": "Reboot"}, {"word": "power cycle"}]},
            {"glosses": ["To bounce a ball."], "topics": ["sports"]},
        ],
    }
    got = extract_senses(entry)
    assert got == [{"word": "bounce", "pos": "verb", "topic": "computing", "synonyms": ["reboot"], "gloss": "To restart a device."}]
    assert extract_senses(entry | {"lang_code": "fr"}) == []
    assert extract_senses(entry | {"word": "Bounce"}) == []  # proper-noun casing
    assert extract_senses(entry | {"word": "re-bounce"}) == []


def test_gloss_head_and_pointer_glosses() -> None:
    assert gloss_head("To restart (a device or program).") == ("restart", False)
    assert gloss_head("A delay in network traffic.") == ("delay", False)
    assert gloss_head("Abbreviation of configuration.") == ("configuration", True)
    assert gloss_head("Short for application.") == ("application", True)
    assert gloss_head("") == (None, False)


def test_table_scores_and_never_maps_to_self_or_inflection() -> None:
    senses = [
        {"word": "bounce", "pos": "verb", "topic": "computing", "synonyms": ["reboot"], "gloss": "To restart a device."},
        {"word": "conf", "pos": "noun", "topic": "computing", "synonyms": [], "gloss": "Abbreviation of config."},
        {"word": "hooks", "pos": "noun", "topic": "computing", "synonyms": ["hook"], "gloss": "Plural of hook."},
    ]
    table = build_sense_table(senses, {"restart", "reboot", "config", "hook"})
    assert table["bounce"] == (("reboot", SCORE_SYNONYM), ("restart", SCORE_GLOSS_HEAD))
    assert table["conf"] == (("config", SCORE_SYNONYM),)
    assert "hooks" not in table
    no_heads = build_sense_table(senses, {"restart", "config"}, use_gloss_heads=False)
    assert "bounce" not in no_heads and no_heads["conf"] == (("config", SCORE_SYNONYM),)


def test_dump_is_byte_stable(tmp_path) -> None:
    ext = load_extract()
    meta = {k: v for k, v in ext["meta"].items() if k not in ("n_senses", "n_words")}
    sha = dump_extract(list(reversed(ext["senses"])), meta, tmp_path / "x.json.gz")
    assert sha == EXTRACT_SHA256


def _texts() -> list[str]:
    return [f"{c.title} {c.text}" for c in Corpus().chunks]


def test_backoff_is_corpus_bound_and_respects_min_score() -> None:
    lo = WiktionarySenseBackoff(_texts(), max_neighbours=5)
    hi = WiktionarySenseBackoff(_texts(), max_neighbours=5, min_score=SCORE_SYNONYM)
    assert lo.table and set(hi.table) <= set(lo.table)
    for word, rows in lo.table.items():
        assert all(t in lo.corpus_words and t != word for t, _ in rows)
        assert all(n.similarity >= SCORE_SYNONYM for n in hi.neighbours(word))
        assert all(n.source == "wiktionary" for n in lo.neighbours(word))
    for tok in ("p99", "checkout-api", "2410", "db"):
        assert lo.neighbours(tok) == ()
