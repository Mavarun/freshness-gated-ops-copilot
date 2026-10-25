from collections import Counter

from ops_copilot.attribute_traps import FORMS, half, load_traps, split_traps
from ops_copilot.corpus import Corpus
from ops_copilot.resource_audit import audit
from ops_copilot.synonym_dev4 import OPENING
from ops_copilot.text import fold_token
from ops_copilot.word_vectors import corpus_words

TUNE_ATTRS = ["birthday", "expensive", "flavour", "friendly", "height", "price", "spicy", "texture", "weight"]


def test_shape_and_labels():
    rows = load_traps()
    assert len(rows) == 36
    assert len({r["id"] for r in rows}) == 36
    assert all(r["expect_decision"] not in OPENING for r in rows)
    assert Counter(r["form"] for r in rows) == {"what_attr_is": 10, "what_is_attr_of": 10,
                                                 "what_is_subject_attr": 10, "how_adj_is": 6}
    assert set(r["form"] for r in rows) == set(FORMS)


def test_attribute_words_are_absent_from_the_corpus_and_colour_is_not_reused():
    vocab = {fold_token(w) for w in corpus_words(f"{c.title} {c.text}" for c in Corpus().chunks)}
    attrs = {r["attribute"] for r in load_traps()}
    assert not {fold_token(a) for a in attrs} & vocab
    assert not {"colour", "color"} & attrs


def test_no_heldout_word():
    assert audit(("data/eval/attribute_traps.jsonl",)) == {"data/eval/attribute_traps.jsonl": []}


def test_split_keeps_attributes_together_and_is_frozen():
    rows = load_traps()
    sp = split_traps(rows)
    by_attr = {}
    for r in rows:
        by_attr.setdefault(r["attribute"], set()).add(sp[r["id"]])
    assert all(len(v) == 1 for v in by_attr.values())
    tune, conf = half("tune"), half("confirm")
    assert len(tune) + len(conf) == 36 and abs(len(tune) - len(conf)) <= 3
    assert sorted({r["attribute"] for r in tune}) == TUNE_ATTRS
