"""Oct 30 pre-registered protocol: constants, grid, safety and pick rules."""

from __future__ import annotations

from ops_copilot import passphrase_compound_protocol as P
from ops_copilot import passphrase_tail_protocol as T
from ops_copilot.explain_redact import LOGIN_SECRET_NUM_RE, LOGIN_SECRET_RE, SENSITIVE_PATTERNS


def test_seeds_are_fresh_and_constants_pinned() -> None:
    spent = {T.CALIB_SEED, T.CONFIRM_SEED, T.AMENDED_CONFIRM_SEED, 999}
    assert not {P.CALIB_SEED, P.CONFIRM_SEED, P.OFFLIST_SEED} & spent
    assert len({P.CALIB_SEED, P.CONFIRM_SEED, P.OFFLIST_SEED}) == 3
    assert (P.N_ROWS, P.FP_BUDGET_TRAIN, P.FP_BUDGET_TEST, P.IDENT_BUDGET_TRAIN, P.IDENT_BUDGET_TEST) == (1200, 15, 1, 9, 1)


def test_grid_has_sixteen_arms_and_the_shipped_one_first() -> None:
    a = P.arms()
    assert len(a) == 16 and len(set(map(P.arm_name, a))) == 16 and a[0] == P.SHIPPED


def test_shipped_arm_reproduces_the_shipped_patterns() -> None:
    pats = P.patterns_for(P.SHIPPED)
    assert [k for k, _ in pats] == [k for k, _ in SENSITIVE_PATTERNS]
    assert any(p is LOGIN_SECRET_RE for _, p in pats)
    assert any(p is LOGIN_SECRET_NUM_RE for _, p in P.patterns_for((None, False, True)))
    from ops_copilot.passphrase import CUED_PASSPHRASE

    b = P.detector(P.SHIPPED)
    assert (b.tail, b.coherence_max, b.coherence_compounds) == (CUED_PASSPHRASE.tail, CUED_PASSPHRASE.coherence_max, False)
    d = P.detector(("all4", True, False))
    assert d.exempt_identifiers and d.wordlist_compounds == "all4" and d.wordlist_space


def _res(leak, over, se=0, new_ids=0, **kw):
    r = {"probe": {"total": {"rows": 10, "leak_words": leak, "over_words": over}}, "oct13_leak_words": 0,
         "repo_query_changes": 0, "se": {"flagged": se}, "idents": {"new_flags": new_ids}, "data_ident_new_flags": []}
    r.update(kw)
    return r


def test_pick_prefers_fewest_leaks_among_safe_arms_and_respects_budgets() -> None:
    base = _res(50, 100)
    names = [P.arm_name(a) for a in P.arms()]
    rs = [dict(_res(40, 100, new_ids=10), arm=names[1]), dict(_res(42, 101), arm=names[2]), dict(_res(42, 100), arm=names[3]),
          dict(_res(30, 100, se=16), arm=names[4]), dict(_res(20, 106), arm=names[5])]
    assert P.pick(rs, base)["arm"] == names[3]
    assert P.pick([rs[0], rs[3], rs[4]], base) is None
    ok = P.confirm_passes(_res(49, 100, se=1, new_ids=1), base)
    assert all(ok.values())
    assert not P.confirm_passes(_res(50, 100), base)["fewer_leaked_words"]
