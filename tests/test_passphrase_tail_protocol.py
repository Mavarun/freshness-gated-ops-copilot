"""Pre-registered Oct 29 protocol: grid, budgets, safety checks and the pick rule."""

from __future__ import annotations

from ops_copilot import passphrase_tail_protocol as P


def _res(arm, leak, over, fp, oct13=0, changes=0, rows=100):
    return {
        "arm": arm,
        "probe": {"total": {"rows": rows, "leak_words": leak, "over_words": over}},
        "oct13_leak_words": oct13,
        "repo_query_changes": changes,
        "se": {"flagged": fp},
    }


def test_grid_and_budgets_are_frozen() -> None:
    assert len(P.arms()) == 14 and P.arms()[0] == P.SHIPPED == ("trim", None)
    assert (P.CALIB_SEED, P.CONFIRM_SEED, P.N_ROWS) == (2910, 2929, 1200)
    assert (P.FP_BUDGET_TRAIN, P.FP_BUDGET_TEST, P.OVER_BUDGET_PER_ROW) == (15, 1, 0.5)
    assert P.arm_name(("keep", 0.1)) == "keep/0.10" and P.arm_name(("trim", None)) == "trim/none"


def test_safety_checks_each_rule() -> None:
    base = _res("trim/none", 50, 10, 17)
    assert all(P.is_safe(_res("x", 40, 60, 32), base, fp_budget=15).values())
    assert not P.is_safe(_res("x", 40, 61, 17), base, fp_budget=15)["over_budget"]
    assert not P.is_safe(_res("x", 40, 10, 33), base, fp_budget=15)["fp_budget"]
    assert not P.is_safe(_res("x", 40, 10, 17, oct13=1), base, fp_budget=15)["oct13_no_leak"]
    assert not P.is_safe(_res("x", 40, 10, 17, changes=1), base, fp_budget=15)["repo_queries_unchanged"]


def test_pick_prefers_fewest_leaks_then_over_redaction_then_grid_order() -> None:
    base = _res("trim/none", 50, 10, 17)
    rs = [base, _res("keep/none", 30, 40, 17), _res("trim/0.05", 30, 12, 20), _res("keep/0.15", 20, 10, 40)]
    assert P.pick(rs, base)["arm"] == "trim/0.05"
    assert P.pick([_res("keep/0.15", 20, 10, 40)], base) is None


def test_detectors_and_patterns_follow_the_arm() -> None:
    from ops_copilot.explain_redact import SENSITIVE_PATTERNS

    d = P.detector(("keep", 0.08))
    assert d.tail == "keep" and d.coherence_max == 0.08
    pats = P.patterns_for(("keep", None))
    assert [k for k, _ in pats] == [k for k, _ in SENSITIVE_PATTERNS]
    assert dict(pats)["passphrase"].tail == "keep"


def test_repo_queries_cover_golden_perturbed_and_write_rows() -> None:
    assert len(P.repo_queries()) == 51 + 203 + 39
    assert len(P.oct13_probe_texts()) == 80


def test_amendment_is_frozen_and_space_only() -> None:
    assert P.AMENDED == ("keep", 0.10, "space-only") and P.AMENDED_CONFIRM_SEED == 2931
    assert P.AMENDED_CONFIRM_SEED not in (P.CALIB_SEED, P.CONFIRM_SEED)
    assert P.arm_name(P.AMENDED) == "keep/0.10/space-only"
    d = P.detector(P.AMENDED)
    assert (d.tail, d.coherence_max, d.coherence_compounds) == ("keep", 0.10, False)
    assert P.detector(("keep", 0.10)).coherence_compounds is True


def test_identifier_check_sees_the_compound_false_positive() -> None:
    ids = P.data_identifiers()
    assert "sidecar-mesh-mtls-handshake-budget" in ids
    base = set(P.identifier_flags(P.SHIPPED))
    assert set(P.identifier_flags(("keep", 0.10))) - base
    assert not set(P.identifier_flags(P.AMENDED)) - base
