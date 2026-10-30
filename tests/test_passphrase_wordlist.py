"""Real-wordlist passphrase probe: data pin, seeded rows, leak and over-redaction counts."""

from __future__ import annotations

from ops_copilot.explain_redact import PR19_PATTERNS, SENSITIVE_PATTERNS
from ops_copilot.passphrase_wordlist import (
    ProbeRow,
    eff_words,
    redact_query,
    score_rows,
    wordlist_passphrases,
)


def test_wordlist_is_pinned_and_alphabetic() -> None:
    w = eff_words()
    assert len(w) == 7772 and len(set(w)) == 7772
    assert all(x.isalpha() and x.islower() for x in w)
    assert w[0] == "abacus" and w[-1] == "zoom"


def test_rows_are_seeded_and_cover_every_separator() -> None:
    a, b = wordlist_passphrases(7, 40), wordlist_passphrases(7, 40)
    assert a == b and a != wordlist_passphrases(8, 40)
    assert {r.separator for r in a} == {"space", "hyphen", "dot", "underscore"}
    assert all(4 <= len(r.words) <= 6 and len(set(r.words)) == len(r.words) for r in a)
    assert all("{s}" not in r.text and r.secret in r.text for r in a)


def test_score_counts_leaks_over_redaction_and_causes() -> None:
    tpl = "the deploy token {s} stopped working, who rotates it?"
    rows = [
        # ops words only: no rule flags it, every word leaks
        ProbeRow("plastic vanilla twitter atlas", ("plastic", "vanilla", "twitter", "atlas"), "space", "no_copula", tpl),
        # trailing ops word trimmed with "stopped working"
        ProbeRow("syrup prowling uplifted component", ("syrup", "prowling", "uplifted", "component"), "space", "no_copula", tpl),
        # flagged whole
        ProbeRow("marble meadow lagoon badger", ("marble", "meadow", "lagoon", "badger"), "space", "no_copula", tpl),
    ]
    from ops_copilot.passphrase_tail_protocol import SHIPPED, patterns_for

    out = score_rows(rows, patterns_for(SHIPPED))  # the Oct 13 detector, explicit
    assert out["total"]["rows"] == 3 and out["total"]["words"] == 12
    assert out["total"]["leak_rows"] == 2 and out["total"]["leak_words"] == 5
    assert out["cause"] == {"no_flag_ops": 1, "tail_trim": 1}
    assert out["total"]["over_words"] == 0


def test_shipped_patterns_beat_pr19_on_the_wordlist_probe() -> None:
    rows = wordlist_passphrases(5, 60)
    now = score_rows(rows, SENSITIVE_PATTERNS)["total"]
    pr19 = score_rows(rows, PR19_PATTERNS)["total"]
    assert now["leak_words"] < pr19["leak_words"]


def test_redact_query_uses_the_given_patterns() -> None:
    q = "the deploy token marble meadow lagoon badger stopped working"
    assert "marble" not in redact_query(q, SENSITIVE_PATTERNS)
    assert "marble" in redact_query(q, PR19_PATTERNS)


def test_offlist_control_words_are_disjoint_from_the_eff_list() -> None:
    from ops_copilot.passphrase_wordlist import offlist_words

    off = offlist_words()
    assert len(off) == 6872 and not set(off) & set(eff_words())
    assert all(w.isalpha() and w.islower() and 4 <= len(w) <= 9 for w in off)
    rows = wordlist_passphrases(5, 20, words=off)
    assert all(set(r.words) <= set(off) for r in rows)
    # the default source is unchanged, so every spent seed reproduces
    assert wordlist_passphrases(5, 20) == wordlist_passphrases(5, 20, words=eff_words())
