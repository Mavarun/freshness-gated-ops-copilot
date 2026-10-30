"""attached_digit protocol: fresh seeds, pinned knobs, check rules."""

from __future__ import annotations

from ops_copilot import passphrase_digit_protocol as D


def test_seeds_fresh_and_knobs_pinned() -> None:
    spent = {2910, 2929, 2931, 3010, 3037, 3053, 3061, 999}
    assert not {D.ATTACHED_SEED, D.STANDARD_SEED} & spent and D.ATTACHED_SEED != D.STANDARD_SEED
    s, c = D.shipped_detector(), D.candidate_detector()
    assert (s.attached_digit, c.attached_digit) == (False, True)
    assert all(getattr(s, k) == getattr(c, k) for k in ("tail", "coherence_max", "wordlist_compounds", "wordlist_space", "exempt_identifiers"))
    assert D.ident_budget("train", 1867) == 9 and D.ident_budget("test", 150) == 1 and D.ident_budget("train", 4000) == 20


def test_digit_identifier_regex() -> None:
    got = {m.group() for m in D.IDENT_DIGIT_RE.finditer("apt install python3-pip-wheel and ext4-dir-index, not a1-b2")}
    assert got == {"python3-pip-wheel", "ext4-dir-index"}


def _r(al, ac, sl, sc, so=100, co=100, **kw):
    r = {"attached": {"shipped": {"leak_words": al}, "candidate": {"leak_words": ac}},
         "standard": {"shipped": {"leak_words": sl, "over_words": so, "rows": 10}, "candidate": {"leak_words": sc, "over_words": co}},
         "oct13_leak_words": 0, "repo_query_changes": 0, "data_ident_new_flags": []}
    r.update(kw)
    return r


def test_check_rules() -> None:
    assert all(D.checks(_r(10, 5, 3, 3)).values())
    assert not D.checks(_r(10, 10, 3, 3))["attached_fewer_leaks"]
    assert not D.checks(_r(10, 5, 3, 4))["standard_no_more_leaks"]
    assert not D.checks(_r(10, 5, 3, 3, co=106))["standard_over_budget"]
    se = {"train": {"sent_shipped": 28, "sent_candidate": 44, "ident_new": 0, "n_identifiers": 1900},
          "test": {"sent_shipped": 0, "sent_candidate": 1, "ident_new": 2, "n_identifiers": 150}}
    c = D.checks(_r(10, 5, 3, 3, se=se))
    assert not c["se_train_sentences"] and c["se_test_sentences"] and c["se_train_identifiers"] and not c["se_test_identifiers"]
