"""Purpose pattern with one extra trailing-number token (off by default)."""

from __future__ import annotations

import pytest

from ops_copilot.explain_redact import LOGIN_SECRET_NUM_RE, LOGIN_SECRET_RE, SENSITIVE_PATTERNS

SEVEN = "use Sprig Detonate Italicize Domestic Stallion Mammal 43 to log in to vault"


def test_seven_token_passphrase_leaked_on_oct29_and_the_shipped_form_matches() -> None:
    assert LOGIN_SECRET_RE.search(SEVEN) is None
    m = LOGIN_SECRET_NUM_RE.search(SEVEN)
    assert m is not None and m.group("val") == "Sprig Detonate Italicize Domestic Stallion Mammal 43"
    assert any(p is LOGIN_SECRET_NUM_RE for _, p in SENSITIVE_PATTERNS)
    assert all(p is not LOGIN_SECRET_RE for _, p in SENSITIVE_PATTERNS)


@pytest.mark.parametrize(
    "text",
    [
        "use violet harbor zebra to log in",
        "use Lagoon Mosaic Velvet Sonnet 83 to sign in",
        "how do I use kubectl to authenticate?",
        "use the bastion to log in",
        "use sso to sign in",
        "use alpha beta gamma delta epsilon zeta eta to log in",
    ],
)
def test_same_answer_as_today_up_to_six_tokens(text: str) -> None:
    a, b = LOGIN_SECRET_RE.search(text), LOGIN_SECRET_NUM_RE.search(text)
    assert (a is None) == (b is None)
    if a is not None:
        assert a.group("val") == b.group("val")


def test_only_a_number_may_be_the_seventh_token() -> None:
    assert LOGIN_SECRET_NUM_RE.search("use a1 b2 c3 d4 e5 f6 g7 to log in") is None
    assert LOGIN_SECRET_NUM_RE.search("use a1 b2 c3 d4 e5 f6 77 to log in") is not None
