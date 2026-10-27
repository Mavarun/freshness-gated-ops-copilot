"""The second attribute-trap set: fresh attributes, no held-out word, frozen split."""

from collections import Counter

from ops_copilot.attribute_traps import load_traps
from ops_copilot.attribute_traps_v2 import FORMS, half_v2, load_traps_v2, split_traps_v2
from ops_copilot.corpus import Corpus
from ops_copilot.resource_audit import audit
from ops_copilot.synonym_dev4 import OPENING
from ops_copilot.text import fold_token
from ops_copilot.word_vectors import corpus_words

TUNE_ATTRS = ["accent", "bitter", "brave", "fluffy", "hobby", "juicy", "melody", "sweet", "wingspan", "zodiac"]


def test_shape_forms_and_labels():
    rows = load_traps_v2()
    assert len(rows) == 40 and len({r["id"] for r in rows}) == 40
    assert len({r["query"] for r in rows}) == 40
    assert all(r["expect_decision"] not in OPENING for r in rows)
    assert Counter(r["form"] for r in rows) == {"what_attr_is": 11, "what_is_attr_of": 11,
                                                 "what_is_subject_attr": 11, "how_adj_is": 7}
    assert set(r["form"] for r in rows) == set(FORMS)


def test_attributes_are_new_absent_from_the_corpus_and_not_colour():
    vocab = {fold_token(w) for w in corpus_words(f"{c.title} {c.text}" for c in Corpus().chunks)}
    attrs = {r["attribute"] for r in load_traps_v2()}
    assert len(attrs) == 18
    assert not {fold_token(a) for a in attrs} & vocab
    assert not attrs & {r["attribute"] for r in load_traps()}
    assert not {"colour", "color"} & attrs
    # no query of the first set is repeated
    assert not {r["query"] for r in load_traps_v2()} & {r["query"] for r in load_traps()}


def test_no_heldout_word():
    rel = "data/eval/attribute_traps_v2.jsonl"
    assert audit((rel,)) == {rel: []}


def test_split_keeps_attributes_together_and_is_frozen():
    rows = load_traps_v2()
    sp = split_traps_v2(rows)
    by_attr = {}
    for r in rows:
        by_attr.setdefault(r["attribute"], set()).add(sp[r["id"]])
    assert all(len(v) == 1 for v in by_attr.values())
    tune, conf = half_v2("tune"), half_v2("confirm")
    assert len(tune) == len(conf) == 20
    assert sorted({r["attribute"] for r in tune}) == TUNE_ATTRS
    assert {r["form"] for r in conf} == set(FORMS)
