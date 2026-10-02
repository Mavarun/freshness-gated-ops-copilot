"""Write ontology, registry and prototypes: structure and no held-out leakage."""

from __future__ import annotations

import json
import re

import pytest

from ops_copilot.synonym_split import load_split
from ops_copilot.text import fold_token, tokenize
from ops_copilot.write_mood import INFORMATIONAL_CUES
from ops_copilot.write_ontology import (
    ONTOLOGY,
    READ_VERBS,
    UNSUPPORTED_VERBS,
    WriteActionType,
    action_verbs,
    lexicon_words,
    verb_index,
)
from ops_copilot.write_prototypes import (
    load_dev_set,
    prototype_texts,
)
from ops_copilot.write_targets import (
    CORPUS_DIR,
    CORPUS_FILES,
    default_registry,
    shape_kind,
)

_SUFFIXES = ("s", "es", "ed", "d", "ing", "er", "ers")


def _held() -> set[str]:
    return {fold_token(w) for w in load_split()["heldout_words"]}


def _forms(word: str) -> set[str]:
    """``word`` and its regular inflections (turn -> turned, cycle -> cycling)."""
    out = {word}
    for suf in _SUFFIXES:
        out.add(word + suf)
        if word.endswith("e"):
            out.add(word[:-1] + suf)
    return out


def _leaks(words) -> list[str]:
    held = _held()
    return sorted({w for w in words if any(fold_token(f) in held for f in _forms(w))})


def test_no_heldout_word_or_inflection_in_any_write_lexicon() -> None:
    words = set(lexicon_words())
    assert len(words) > 100
    assert _leaks(words) == []


def test_documented_exclusions_are_really_absent() -> None:
    excluded = {
        "bounce", "reboot", "recycle", "reinitialize", "kick", "cycle", "ping", "set",
        "modify", "config", "configuration", "configure", "rollout", "rollover",
        "credential", "passphrase", "down", "capacity", "count", "turn", "flush",
        "purge", "create", "list", "engineer",
    }
    assert excluded & lexicon_words() == set()


def test_informational_cues_hold_no_heldout_word() -> None:
    words = set(re.findall(r"[a-z]{2,}", INFORMATIONAL_CUES.pattern))
    assert {"how", "what", "procedure", "safe"} <= words
    assert _leaks(words) == []
    assert "steps" not in words  # PR #12 had it; it is a held-out word


def test_prototypes_and_dev_calibration_verbs_hold_no_heldout_word() -> None:
    proto_words = {t for texts in prototype_texts().values() for s in texts for t in tokenize(s)}
    assert _leaks(proto_words) == []
    dev = load_dev_set()
    assert len(dev) >= 40
    assert _leaks({r["verb"] for r in dev}) == []
    # Dev verbs are not lexicon verbs (the backoff never sees those).
    assert {r["verb"] for r in dev} & action_verbs() == set()


def test_prototypes_come_from_lexicon_verbs_only() -> None:
    lex = lexicon_words()
    for cls, texts in prototype_texts().items():
        assert texts, cls
        for text in texts:
            verb = text.split(" the ")[0]
            assert all(v in lex for v in verb.split()), (cls, text)


def test_every_action_has_verbs_and_target_kinds() -> None:
    assert {s.action for s in ONTOLOGY} == set(WriteActionType)
    for spec in ONTOLOGY:
        assert spec.verbs and spec.target_kinds, spec.action
        assert spec.anchor in spec.verbs or spec.anchor == "rollback", spec.action


def test_verb_clusters_are_disjoint_from_read_and_unsupported() -> None:
    verbs = set(verb_index())
    assert verbs & READ_VERBS == set()
    assert verbs & UNSUPPORTED_VERBS == set()
    assert READ_VERBS & UNSUPPORTED_VERBS == set()
    assert all(len(actions) == 1 for actions in verb_index().values())


def test_registry_is_built_from_the_corpus() -> None:
    reg = default_registry()
    corpus = " ".join(
        (CORPUS_DIR / name).read_text(encoding="utf-8").lower() for name in CORPUS_FILES
    )
    for name in reg.kinds:
        assert name in corpus, name
    assert reg.kind("checkout-api") == "service"
    assert reg.kind("payments-worker") == "service"
    assert reg.kind("checkout_retry") == "flag"
    assert reg.kind("vault-transit") == "secret"
    assert reg.kind("cache-oncall") == "recipient"
    assert reg.kind("checkout-primary") == "recipient"  # follows "pager" in the corpus
    assert reg.kind("maxmemory-policy") == "config_key"
    for never in ("inc-4821", "p99", "2026-09-12", "cnry-vault7f3a", "us-east-1", "5xx"):
        assert reg.kind(never) is None, never


@pytest.mark.parametrize(
    ("token", "kind"),
    [
        ("billing-api", "service"),
        ("search-worker", "service"),
        ("redis.maxmemory-policy", "config_key"),
        ("edge-cache", "cache"),
        ("signing-key", "secret"),
        ("inc-1234", None),
        ("us-west-2", None),
        ("400ms", None),
    ],
)
def test_shape_kind(token: str, kind: str | None) -> None:
    assert shape_kind(token) == kind


def test_dev_set_labels_are_actions_or_none() -> None:
    labels = {r["label"] for r in load_dev_set()}
    assert labels <= {a.value for a in WriteActionType} | {"none"}
    assert "none" in labels and len(labels) >= 8
    raw = json.dumps(load_dev_set())
    assert "heldout" not in raw
