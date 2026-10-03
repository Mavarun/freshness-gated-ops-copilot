"""Redaction for refusal explanations.

An explanation is built from things the copilot already holds: doc ids,
source systems, SLA numbers, registry names and *query terms* (missing
salient terms, the parsed write target, the verb). Query text is user input,
so it can carry an e-mail address, a phone number, an access key, a chat
token, a pasted password or a canary token copied out of a document. None of
that may come back in an explanation, in the API response or in a trace.

Two passes, applied to every string anywhere in the explanation dict:

1. Pattern pass. Case-insensitive versions of the PII detectors (queries are
   lower-cased before parsing, so ``AKIA...`` arrives as ``akia...`` and
   ``CNRY-...`` as ``cnry-...``), plus canary tokens, ``key=value`` secret
   assignments and long high-entropy strings. Each hit becomes
   ``[redacted:<kind>]``.
2. Fragment pass. The tokenizer splits ``alice.smith@example.com`` into
   ``alice``, ``smith``, ``example``, ``com``, so a missing-terms list can hold
   the pieces of an address without any single piece matching a pattern. The
   sensitive spans found in the *context* (the raw query) are tokenized the
   same way and any whole-word occurrence of a fragment is replaced with
   ``[redacted]``. Over-redaction is accepted; a leak is not.

``redact_explanation`` is idempotent (a second pass finds nothing) and
reports how many replacements it made. It runs when the explanation is built
and again at the API and trace boundaries.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import Any

from ops_copilot.pii import EMAIL_RE, PHONE_RE
from ops_copilot.text import STOPWORDS, tokenize

CANARY_ANY_CASE_RE = re.compile(r"(?i)\bcnry-[a-z0-9]{6,}\b")
AWS_KEY_ANY_CASE_RE = re.compile(r"(?i)\b(?:akia|asia)[0-9a-z]{16}\b")
SLACK_TOKEN_ANY_CASE_RE = re.compile(r"(?i)\bxox[baprs]-[0-9a-z-]{10,}\b")
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key)"
    r"\s*[:=]\s*[^\s,;'\"]+"
)
# >= 32 chars of key-ish alphabet with both letters and digits; doc ids use
# underscores/hyphens and no long digit runs, so they never match.
HIGH_ENTROPY_RE = re.compile(r"\b(?=[A-Za-z0-9+/=]*\d)(?=[A-Za-z0-9+/=]*[A-Za-z])[A-Za-z0-9+/=]{32,}")

SENSITIVE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("canary", CANARY_ANY_CASE_RE),
    ("secret", SECRET_ASSIGNMENT_RE),
    ("aws_key", AWS_KEY_ANY_CASE_RE),
    ("slack_token", SLACK_TOKEN_ANY_CASE_RE),
    ("email", EMAIL_RE),
    ("phone", PHONE_RE),
    ("high_entropy", HIGH_ENTROPY_RE),
)

_MIN_FRAGMENT = 2


def find_sensitive(text: str) -> list[tuple[str, str]]:
    """Return ``(kind, value)`` for every sensitive span in ``text``."""
    out: list[tuple[str, str]] = []
    if not text:
        return out
    for kind, pat in SENSITIVE_PATTERNS:
        out.extend((kind, m.group(0)) for m in pat.finditer(text))
    return out


def sensitive_fragments(texts: Iterable[str]) -> set[str]:
    """Tokenizer fragments of every sensitive span in ``texts`` (lower-cased).

    For an e-mail address only the local part is fragmented: the domain
    (``example``, ``com``) identifies nobody and would otherwise blank out
    ordinary words like "for example".
    """
    frags: set[str] = set()
    for text in texts:
        for kind, value in find_sensitive(text or ""):
            frags.add(value.lower())
            part = value.split("@", 1)[0] if kind == "email" else value
            frags.update(
                t for t in tokenize(part) if len(t) >= _MIN_FRAGMENT and t not in STOPWORDS
            )
    return frags


def _redact_str(s: str, frag_re: re.Pattern[str] | None) -> tuple[str, int]:
    n = 0
    for kind, pat in SENSITIVE_PATTERNS:
        s, k = pat.subn(f"[redacted:{kind}]", s)
        n += k
    if frag_re is not None:
        s, k = frag_re.subn("[redacted]", s)
        n += k
    return s, n


def _walk(obj: Any, frag_re: re.Pattern[str] | None) -> tuple[Any, int]:
    if isinstance(obj, str):
        return _redact_str(obj, frag_re)
    if isinstance(obj, dict):
        total = 0
        out = {}
        for k, v in obj.items():
            nv, n = _walk(v, frag_re)
            out[k] = nv
            total += n
        return out, total
    if isinstance(obj, (list, tuple)):
        total = 0
        items = []
        for v in obj:
            nv, n = _walk(v, frag_re)
            items.append(nv)
            total += n
        return items, total
    return obj, 0


def _fragment_re(context: Sequence[str]) -> re.Pattern[str] | None:
    frags = sorted(sensitive_fragments(context), key=len, reverse=True)
    if not frags:
        return None
    return re.compile(r"(?i)(?<![\w\[])(?:" + "|".join(re.escape(f) for f in frags) + r")(?![\w\]])")


def redact_string(text: str, *, context: Sequence[str] = ()) -> tuple[str, int]:
    """Both passes on one string (used for refusal ``reason`` lines)."""
    return _redact_str(text or "", _fragment_re(context))


def redact_explanation(
    explanation: dict[str, Any] | None, *, context: Sequence[str] = ()
) -> tuple[dict[str, Any] | None, int]:
    """Redact every string in ``explanation``; return ``(copy, n_replacements)``.

    ``context`` holds raw texts the explanation was derived from (the query);
    their sensitive spans are tokenized so split fragments are caught too.
    The ``redactions_count`` key accumulates across passes.
    """
    if explanation is None:
        return None, 0
    frag_re = _fragment_re(context)
    body = {k: v for k, v in explanation.items() if k != "redactions_count"}
    out, n = _walk(body, frag_re)
    out["redactions_count"] = int(explanation.get("redactions_count", 0) or 0) + n
    return out, n


def explanation_leaks(explanation: dict[str, Any] | None, secrets: Iterable[str] = ()) -> list[str]:
    """Return the sensitive kinds / literal secrets still present (for tests and evals)."""
    if not explanation:
        return []
    flat: list[str] = []

    def _collect(o: Any) -> None:
        if isinstance(o, str):
            flat.append(o)
        elif isinstance(o, dict):
            for v in o.values():
                _collect(v)
        elif isinstance(o, (list, tuple)):
            for v in o:
                _collect(v)

    _collect(explanation)
    blob = "\n".join(flat)
    leaks = [kind for kind, _ in find_sensitive(blob)]
    low = blob.lower()
    leaks.extend(f"literal:{s[:4]}…" for s in secrets if s and s.lower() in low)
    return leaks
