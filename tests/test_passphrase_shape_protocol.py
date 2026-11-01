"""The Nov 1 protocol is fixed before any scored run: seeds, budgets, grid and pick rule."""

from __future__ import annotations

from ops_copilot import passphrase_compound_protocol as C
from ops_copilot import passphrase_dictionary_protocol as P
from ops_copilot import passphrase_digit_protocol as D
from ops_copilot import passphrase_shape_protocol as S
from ops_copilot import passphrase_tail_protocol as T
from ops_copilot.passphrase import CUED_PASSPHRASE


def _spent() -> set[int]:
    return {T.CALIB_SEED, T.CONFIRM_SEED, T.AMENDED_CONFIRM_SEED, C.CALIB_SEED, C.CONFIRM_SEED, C.OFFLIST_SEED,
            D.ATTACHED_SEED, D.STANDARD_SEED, 3061, 997, 998, 999, P.OFFLIST_SEED,
            *P.calib_seeds().values(), *P.confirm_seeds().values()}


def test_seeds_are_fresh_and_distinct() -> None:
    seeds = [*S.CALIB_SEEDS.values(), *S.CONFIRM_SEEDS.values(), S.OFFLIST_SEED]
    assert len(set(seeds)) == len(seeds) == 11
    spent = _spent()
    assert not set(seeds) & spent
    # invented rows also use seed + 1
    plus = {S.CALIB_SEEDS["invented"] + 1, S.CONFIRM_SEEDS["invented"] + 1}
    assert not plus & (set(seeds) | spent)
    assert set(S.CALIB_SEEDS) == set(S.CONFIRM_SEEDS) == set(S.PROBES)


def test_grid_is_every_subset_smallest_first() -> None:
    arms = S.arms()
    assert len(arms) == 8 and arms[0] == S.SHIPPED == ()
    assert arms[-1] == ("case", "tld", "stop")
    assert [S.arm_name(a) for a in arms][:4] == ["shipped", "case", "tld", "stop"]


def test_shipped_arm_is_the_current_default_detector() -> None:
    d = S.detector(S.SHIPPED)
    keys = ("tail", "coherence_max", "coherence_compounds", "exempt_identifiers", "wordlist_compounds",
            "wordlist_space", "attached_digit", "digit_guard", "plain_rule", "plain_scope", "shape_guards")
    assert {k: getattr(d, k) for k in keys} == {k: getattr(CUED_PASSPHRASE, k) for k in keys}
    assert S.detector(("case", "stop")).shape_guards == ("case", "stop")


def test_budgets() -> None:
    assert (S.N_ROWS, S.OVER_BUDGET_PER_ROW, S.LEAK_BUDGET) == (1200, 0.5, 0.005)
    assert set(S.STRICT_PROBES) | set(S.BUDGET_PROBES) == set(S.PROBES)
    assert not set(S.STRICT_PROBES) & set(S.BUDGET_PROBES)


def _res(arm, leaks=None, ids=221, sent=28, new_ids=0, over=0):
    leaks = leaks or {}
    tot = lambda k: {"total": {"rows": 1200, "words": 6000, "leak_words": leaks.get(k, 10), "over_words": 500 + over}}
    return {"arm": S.arm_name(arm), "probe": {k: tot(k) for k in S.PROBES},
            "oct13_leak_words": 0, "repo_query_changes": 0, "data_ident_new_flags": [],
            "se": {"sent_flagged": sent, "ident_flagged": ids, "ident_new": new_ids}}


def test_pick_minimises_identifier_flags_among_safe_arms() -> None:
    base = _res(())
    a = _res(("case",), ids=200)
    b = _res(("case", "stop"), ids=150, leaks={"phrase": 10 + 31})  # 31 > 0.5% of 6000: unsafe
    c = _res(("tld",), ids=190)
    assert not S.is_safe(b, base)["leak_budget"]
    assert S.pick([base, a, b, c], base)["arm"] == "tld"
    strict = _res(("case", "tld"), ids=100, leaks={"cased": 11})
    assert not S.is_safe(strict, base)["strict_no_more_leaks"]
    within = _res(("case", "tld", "stop"), ids=120, leaks={"phrase": 40})
    assert S.is_safe(within, base)["leak_budget"]
    assert S.pick([base, a, c, strict, within], base)["arm"] == "case+tld+stop"


def test_pick_falls_back_to_shipped_and_confirm_needs_fewer_test_flags() -> None:
    base = _res(())
    worse = _res(("stop",), ids=150, new_ids=1)
    assert S.pick([base, worse], base)["arm"] == "shipped"
    assert S.confirm_passes(_res(("case",), ids=20), _res((), ids=24))["fewer_test_identifiers"]
    assert not S.confirm_passes(_res(("case",), ids=24), _res((), ids=24))["fewer_test_identifiers"]


def test_probe_rows_dispatch() -> None:
    for k in S.PROBES:
        rows = S.probe_rows(k, 1, 8)
        assert len(rows) == 8


def test_evaluate_arm_on_a_small_offline_set() -> None:
    from ops_copilot.passphrase_identifiers import identifier_flags
    from ops_copilot.passphrase_shape_eval import evaluate_arm, table

    se = {"sentences": ["reset the token marble-meadow-lagoon-badger now"],
          "identifiers": ["csrc.nist.gov", "chicken-and-egg", "Windows.System.UserProfile.LockScreen", "kube-state-metrics"]}
    probes = {k: S.probe_rows(k, 11, 20) for k in S.PROBES}
    base_ids = set(identifier_flags(S.detector(S.SHIPPED), se["identifiers"]))
    base = evaluate_arm(S.SHIPPED, probes, se, base_queries={}, base_ident_flags=base_ids)
    arm = evaluate_arm(("case", "tld", "stop"), probes, se, base_queries={}, base_ident_flags=base_ids)
    assert base["se"]["ident_unflagged"] == 0
    assert arm["se"]["ident_new"] == 0
    assert arm["se"]["ident_flagged"] <= base["se"]["ident_flagged"]
    assert sum(arm["se"]["ident_unflagged_by_guard"].values()) >= arm["se"]["ident_unflagged"]
    lines = table([base, arm], "safe")
    assert len(lines) == 4 and lines[2].startswith("| shipped |")
