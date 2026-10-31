"""The Oct 31 protocol is fixed before any scored run: seeds, budgets, grid and pick rule."""

from __future__ import annotations

from ops_copilot import passphrase_dictionary_protocol as P
from ops_copilot import passphrase_compound_protocol as C
from ops_copilot import passphrase_digit_protocol as D
from ops_copilot import passphrase_tail_protocol as T


def test_seeds_are_fresh_and_distinct() -> None:
    seeds = [*P.calib_seeds().values(), *P.confirm_seeds().values(), P.OFFLIST_SEED]
    spent = {T.CALIB_SEED, T.CONFIRM_SEED, T.AMENDED_CONFIRM_SEED, C.CALIB_SEED, C.CONFIRM_SEED,
             C.OFFLIST_SEED, D.ATTACHED_SEED, D.STANDARD_SEED, 3061, 997, 998, 999}
    assert len(set(seeds)) == len(seeds) == 7
    assert not set(seeds) & spent
    # invented rows use seed and seed + 1
    assert not {s + 1 for s in (P.CALIB_INVENTED_SEED, P.CONFIRM_INVENTED_SEED)} & (set(seeds) | spent)


def test_grid_and_shipped_arm() -> None:
    arms = P.arms()
    assert len(arms) == 15 and arms[0] == P.SHIPPED
    names = [P.arm_name(a) for a in arms]
    assert len(set(names)) == 15 and names[0] == "ops/compounds/off"
    d = P.detector(P.SHIPPED)
    assert (d.plain_rule, d.attached_digit, d.digit_guard) == ("ops", False, False)
    g = P.detector((("dict_cv", "all"), "guard"))
    assert (g.plain_rule, g.plain_scope, g.attached_digit, g.digit_guard) == ("dict_cv", "all", True, True)


def test_budgets() -> None:
    assert (P.FP_BUDGET_TRAIN, P.FP_BUDGET_TEST, P.IDENT_BUDGET_TRAIN, P.IDENT_BUDGET_TEST) == (15, 1, 9, 1)
    assert P.OVER_BUDGET_PER_ROW == 0.5 and P.INVENTED_BUDGET == 0.005 and P.N_ROWS == 1200


def _res(arm, std, att, inv, ids=100, sent=20, new_ids=0, over=0):
    tot = lambda lw: {"total": {"rows": 1200, "words": 6000, "leak_words": lw, "over_words": 500 + over}}
    return {"arm": P.arm_name(arm), "probe": {"standard": tot(std), "attached": tot(att), "invented": tot(inv)},
            "oct13_leak_words": 0, "repo_query_changes": 0, "data_ident_new_flags": [],
            "se": {"sent_flagged": sent, "ident_flagged": ids, "ident_new": new_ids}}


def test_pick_prefers_fewer_leaks_then_fewer_identifier_flags() -> None:
    base = _res(P.SHIPPED, 20, 2000, 0)
    a = _res((("ops", "compounds"), "guard"), 20, 10, 0)
    b = _res((("dict", "compounds"), "guard"), 20, 10, 0, ids=20)
    c = _res((("dict", "compounds"), "off"), 20, 2000, 600, ids=20)  # invented leaks: unsafe
    assert P.pick([base, a, b, c], base)["arm"] == "dict/compounds/guard"
    assert not P.is_safe(c, base, fp_budget=15, ident_budget=9)["invented_budget"]
    noisy = _res((("ops", "compounds"), "raw"), 20, 5, 0, new_ids=12)
    assert P.pick([base, noisy], base)["arm"] == "ops/compounds/off"


def test_confirm_gain_rule() -> None:
    base = _res(P.SHIPPED, 20, 2000, 0)
    assert P.confirm_passes(_res((("ops", "compounds"), "guard"), 20, 10, 0), base)["gain"]
    assert P.confirm_passes(_res((("dict", "compounds"), "off"), 20, 2000, 0, ids=50), base)["gain"]
    assert not P.confirm_passes(base, base)["gain"]
