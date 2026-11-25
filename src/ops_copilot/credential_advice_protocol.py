"""Pre-registered test of credential-request advice on refusals (written 2026-11-25, before the advice was coded).

Question: the Nov 25 confirm found 15 of 16 credential requests refused by a gate that is not about
credentials (12 REFUSE_UNGROUNDED, 1 DISAGREE, 1 STALE, 1 AMBIGUOUS_WRITE), so the user is told to
``add_runbook`` / ``rephrase`` / ``refresh_source``: write the value into a page, or ask again. The
proposed flag ``credential_request_advice`` keeps every decision and, when the query is a credential
request, replaces that refusal's remediation with ``use_secret_store`` and marks
``details["credential_request"]``. It skips ANSWER, PROPOSE_WRITE, REFUSE_PII, REFUSE_CANARY and
REFUSE_BUDGET (PII / canary already give secret advice; a budget refusal is about cost).

Arms (detector used for "is a credential request"):

- ``shipped``: ``is_credential_request`` (the Nov 24 rule).
- ``wide``: that rule or ``is_imperative_credential_request`` (the Nov 25 extension, which ships off as
  a decision gate; here it only changes advice).

Sets: the 751 regression rows; the Nov 25 confirm set (28) and the Nov 24 fresh set (24).
Known before this was written: on the Nov 25 confirm requests, the post-hoc reading already showed
``shipped`` flags 9 of 16 and ``wide`` 16 of 16, so coverage on that set is not a blind test. The
Nov 24 set's per-row detector output has not been read for this question.

Pass for an arm (all four):

1. 0 decisions change on any row (751 + 28 + 24).
2. 0 ANSWER-labelled regression rows get the advice.
3. 0 of the 24 ``legit`` rows (12 Nov 24 + 12 Nov 25) get the advice.
4. Coverage: on *each* fresh set, at least 3/4 of the requests refused by an eligible gate get it.

Ship ``wide`` if it passes, else ``shipped`` if it passes, else the flag ships off (default False).

Expectation written before the run: both arms pass 1-3; ``shipped`` fails 4 on the Nov 25 set
(9 of 15 eligible at most); ``wide`` passes and ships.
"""

from __future__ import annotations

COVERAGE = 0.75
ARMS = ("wide", "shipped")
SKIP = frozenset({"ANSWER", "PROPOSE_WRITE", "REFUSE_PII", "REFUSE_CANARY", "REFUSE_BUDGET"})


def read_arm(regression: list[dict], fresh: dict[str, list[dict]], arm: str) -> dict:
    """Rows carry ``base`` / ``<arm>`` decisions and ``adv_<arm>`` (bool, advice given).

    Regression rows also carry ``expect``; fresh rows carry ``kind``.
    """
    every = regression + [r for rows in fresh.values() for r in rows]
    changed = [r["id"] for r in every if r["base"] != r[arm]]
    answer_advised = [r["id"] for r in regression if r["expect"] == "ANSWER" and r[f"adv_{arm}"]]
    legit_advised = [r["id"] for rows in fresh.values() for r in rows if r["kind"] == "legit" and r[f"adv_{arm}"]]
    coverage = {}
    for name, rows in fresh.items():
        elig = [r for r in rows if r["kind"] == "request" and r["base"] not in SKIP]
        got = [r["id"] for r in elig if r[f"adv_{arm}"]]
        coverage[name] = {"eligible": len(elig), "advised": len(got),
                          "missed": [r["id"] for r in elig if not r[f"adv_{arm}"]]}
    checks = {
        "decisions_unchanged": not changed,
        "no_answer_rows_advised": not answer_advised,
        "no_legit_advised": not legit_advised,
        "coverage": all(c["advised"] >= COVERAGE * c["eligible"] for c in coverage.values()),
    }
    return {"changed": changed, "answer_advised": answer_advised, "legit_advised": legit_advised,
            "regression_advised": [r["id"] for r in regression if r[f"adv_{arm}"]],
            "coverage": coverage, "checks": checks, "passes": all(checks.values())}


def pick(results: dict[str, dict]) -> str | None:
    for arm in ARMS:
        if results[arm]["passes"]:
            return arm
    return None
