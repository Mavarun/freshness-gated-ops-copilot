"""Reading rules of the Nov 25 credential-advice protocol, fixed before the advice was coded."""

from ops_copilot import credential_advice_protocol as P


def _f(i, kind, base, adv):
    return {"id": i, "kind": kind, "base": base, "wide": base, "shipped": base, "adv_wide": adv, "adv_shipped": adv}


def test_arm_passes_and_fails():
    reg = [{"id": "g1", "expect": "ANSWER", "base": "ANSWER", "wide": "ANSWER", "shipped": "ANSWER",
            "adv_wide": False, "adv_shipped": False}]
    fresh = {"a": [_f("r1", "request", "REFUSE_UNGROUNDED", True), _f("r2", "request", "REFUSE_PII", False),
                   _f("l1", "legit", "REFUSE_UNGROUNDED", False)]}
    assert P.read_arm(reg, fresh, "wide")["passes"]
    fresh["a"][0]["adv_wide"] = False  # 0 of 1 eligible advised
    assert not P.read_arm(reg, fresh, "wide")["checks"]["coverage"]
    fresh["a"][0]["adv_wide"] = True
    fresh["a"][2]["adv_wide"] = True
    assert not P.read_arm(reg, fresh, "wide")["checks"]["no_legit_advised"]


def test_pick_prefers_wide():
    assert P.pick({"wide": {"passes": True}, "shipped": {"passes": True}}) == "wide"
    assert P.pick({"wide": {"passes": False}, "shipped": {"passes": True}}) == "shipped"
    assert P.pick({"wide": {"passes": False}, "shipped": {"passes": False}}) is None
