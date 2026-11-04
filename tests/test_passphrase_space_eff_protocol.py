"""The second Nov 4 space-bridge protocol (list-only reading) is fixed before any scored run."""

from __future__ import annotations

from ops_copilot import passphrase_phrase_protocol as P
from ops_copilot import passphrase_shape_protocol as S
from ops_copilot import passphrase_space_eff_protocol as E
from ops_copilot import passphrase_space_protocol as V1
from ops_copilot.passphrase import CUED_PASSPHRASE


def test_seeds_are_fresh_distinct_and_leave_the_first_protocols_confirm_unspent() -> None:
    seeds = [*E.CALIB_SEEDS.values(), *E.CONFIRM_SEEDS.values()]
    assert len(set(seeds)) == len(seeds) == 14
    used = {*S.CALIB_SEEDS.values(), *S.CONFIRM_SEEDS.values(), S.OFFLIST_SEED,
            *P.CALIB_SEEDS.values(), *P.CONFIRM_SEEDS.values(), *V1.CALIB_SEEDS.values(), *V1.CONFIRM_SEEDS.values()}
    assert not set(seeds) & (used | {s + 1 for s in used})
    assert not {E.CALIB_SEEDS["invented"] + 1, E.CONFIRM_SEEDS["invented"] + 1} & set(seeds)
    assert set(E.CALIB_SEEDS) == set(E.CONFIRM_SEEDS) == set(E.PROBES)


def test_arms_pin_the_nov1_detector_and_name_themselves() -> None:
    assert [E.arm_name(a) for a in E.arms()] == ["shipped", "prep/2/eff3", "prep/2/eff4", "func/2/eff3", "func/2/eff4"]
    keys = ("tail", "coherence_max", "exempt_identifiers", "wordlist_compounds", "attached_digit",
            "digit_guard", "plain_rule", "shape_guards", "function_parts")
    d = E.detector(E.SHIPPED)
    assert {k: getattr(d, k) for k in keys} == {k: getattr(CUED_PASSPHRASE, k) for k in keys}
    assert (d.space_bridge, d.space_bridge_rule) == (None, "plain")
    f = E.detector(("func", 2, "eff4"))
    assert (f.space_bridge, f.space_bridge_max, f.space_bridge_rule) == ("func", 2, "eff4")


def test_probe_rows_include_the_off_list_control() -> None:
    from ops_copilot.passphrase import generator_words

    rows = E.probe_rows("offlist_phrase", E.CALIB_SEEDS["offlist_phrase"], 30)
    assert len(rows) == 30 and not any(w in generator_words() for r in rows for w in r.words)
    assert [r.text for r in E.probe_rows("phrase", 5, 10)] == [r.text for r in V1.probe_rows("phrase", 5, 10)]


def _res(arm, phrase=100, other=10, ids_new=0, sent=28, off=None):
    tot = lambda k: {"total": {"rows": 1200, "words": 6000, "over_words": 500,
                               "leak_words": phrase if k == "phrase" else (off if off is not None and k == "offlist_phrase" else other)}}
    return {"arm": E.arm_name(arm), "probe": {k: tot(k) for k in E.PROBES}, "oct13_leak_words": 0,
            "repo_query_changes": 0, "data_ident_new_flags": [],
            "se": {"sent_flagged": sent, "ident_flagged": 166, "ident_new": ids_new}}


def test_checks_cover_the_seventh_probe_and_pick_prefers_fewest_phrase_leaks() -> None:
    base = _res(E.SHIPPED, phrase=500)
    assert all(E.calibration_passes(_res(("func", 2, "eff3"), phrase=100), base).values())
    assert not E.calibration_passes(_res(("func", 2, "eff3"), phrase=100, off=11), base)["no_more_leaks"]
    assert not E.confirm_passes(_res(("func", 2, "eff3"), phrase=100, sent=30), base)["se_sentences"]
    rs = [base, _res(("prep", 2, "eff3"), phrase=300), _res(("func", 2, "eff3"), phrase=100),
          _res(("func", 2, "eff4"), phrase=100)]
    assert E.pick(rs, base)["arm"] == "func/2/eff3"
    assert E.pick([base, _res(("prep", 2, "eff3"), phrase=500)], base) is None
