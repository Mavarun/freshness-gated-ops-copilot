"""Random-token secret detector: calibration rule, behaviour and out-of-sample numbers."""

from __future__ import annotations

import pytest

from ops_copilot import secret_entropy as se
from ops_copilot.secret_entropy_eval import run_secret_entropy_eval


def test_default_threshold_is_calibrated():
    cal = se.calibrate_threshold()
    assert cal["threshold"] == se.DEFAULT_THRESHOLD
    assert cal["lo"] <= cal["threshold"] <= cal["hi"]


def test_calibration_negatives_are_not_training_words():
    train, calib = se.vocabulary_split()
    assert not set(train) & set(calib)
    assert 0.10 < len(calib) / (len(train) + len(calib)) < 0.20


def test_training_words_exclude_corpus_identifiers():
    train, calib = se.vocabulary_split()
    words = set(train) | set(calib)
    for ident in ("checkout_retry", "payments-worker", "inc-4821", "cnry-vault7f3a"):
        assert ident not in words


@pytest.mark.parametrize(
    "token",
    ["q7xf2lpz9mkw3t", "9f3c1ab07e4d2c88", "ZmFrZS1rZXktMDE", "deploy-key-Qm8zLx2Vt9Kp", "Xk7#mQ2!pL9zR4"],
)
def test_flags_random_tokens(token):
    assert se.RANDOM_TOKEN.is_random(token)


@pytest.mark.parametrize(
    "token",
    [
        "checkout_retry",
        "payments-worker-heartbeat",
        "kubernetes-controller-manager",
        "redis.maxmemory-policy",
        "reinitialization",
        "2026-09-13T12:00:00Z",
        "inc-4821-postmortem",
        "10.0.3.17:6379",
        "1696512345678",
    ],
)
def test_keeps_natural_tokens(token):
    assert not se.RANDOM_TOKEN.is_random(token)


def test_short_and_shaped_tokens_are_not_candidates():
    assert not se.is_candidate("q7xf2lpz9")  # under MIN_LEN
    assert not se.is_candidate("jane.doe.oncall@example.org")
    assert not se.is_candidate("https://q7xf2lpz9mkw3t.example")
    assert not se.is_candidate("[redacted:random_token]")


def test_system_minted_tokens_are_never_redacted():
    # HITL write ids are what an operator approves; timestamps stamp writes.
    assert not se.RANDOM_TOKEN.is_random("wrt_3226d392e4a1")
    assert not se.RANDOM_TOKEN.is_random("2026-10-10T06:03:38.241432+00:00")
    # a user secret that merely starts like one is still caught
    assert se.RANDOM_TOKEN.is_random("wrt_3226d392e4a1q7xf2lpz")


def test_regex_like_interface():
    text = "why does q7xf2lpz9mkw3t get a 401 on checkout-api?"
    hits = [m.group(0) for m in se.RANDOM_TOKEN.finditer(text)]
    assert hits == ["q7xf2lpz9mkw3t"]
    out, n = se.RANDOM_TOKEN.subn("[redacted:random_token]", text)
    assert n == 1 and out == "why does [redacted:random_token] get a 401 on checkout-api?"
    # idempotent: the placeholder is never a candidate
    assert se.RANDOM_TOKEN.subn("[x]", out) == (out, 0)
    assert se.RANDOM_TOKEN.search("restart checkout-api") is None


def test_edge_punctuation_is_stripped_from_the_span():
    out, n = se.RANDOM_TOKEN.subn("<S>", "use (q7xf2lpz9mkw3t).")
    assert n == 1 and out == "use (<S>)."


def test_synthetic_secrets_are_seeded():
    a = se.synthetic_secrets(se.TEST_FAMILIES, 5, 11)
    assert a == se.synthetic_secrets(se.TEST_FAMILIES, 5, 11)
    assert a != se.synthetic_secrets(se.TEST_FAMILIES, 5, 12)


def test_out_of_sample_numbers():
    ev = run_secret_entropy_eval()
    for fam in se.DEV_FAMILIES:
        assert ev["families"][fam]["now"] == ev["families"][fam]["n"]
    assert ev["recall"]["pr16"] == 0.0
    assert ev["recall"]["now"] >= 0.90
    # repo text the model never saw: no false positive
    assert ev["n_negative_flagged"] == 0
    assert ev["n_negative_candidates"] > 250
    # the known hard family stays visibly weak (reported, not hidden)
    assert ev["families"]["pronounceable"]["detector"] < ev["families"]["pronounceable"]["n"]
