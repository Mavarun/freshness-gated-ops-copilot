"""Out-of-sample check of the random-token detector (``secret_entropy``).

Positives: seeded synthetic secrets (never real) of every family in
``secret_entropy.SECRET_FAMILIES`` with a *different* seed from calibration.
Four of the seven families (base64url, password with symbols, prefixed
personal-access-token style, pronounceable) never took part in calibration.
Recall is reported for the PR #16 pattern set (shape detectors plus the
32-character high-entropy regex) and for the pattern set with the detector.

Negatives: every whitespace token of text the character model never saw:
the 47 ops documents, the 51 golden questions, the 203 perturbed questions,
both write-intent evals and the fresh synonym set. A flagged token there is a
false positive (it would be blanked in a trace). Tokens a shape pattern
already redacts (the canary token some golden questions paste) are counted
apart and are not negatives. The canary and PII documents are reported apart:
their planted values *should* be caught.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ops_copilot.secret_entropy import (
    DEFAULT_THRESHOLD,
    DEV_FAMILIES,
    RANDOM_TOKEN,
    TEST_FAMILIES,
    _RUN_RE,
    _strip_span,
    is_candidate,
    synthetic_secrets,
    token_score,
)

ROOT = Path(__file__).resolve().parents[2]
TEST_SEED = 2026
N_PER_FAMILY = 200

NEGATIVE_FILES = {
    "ops documents": ROOT / "data" / "corpus" / "ops_docs.jsonl",
    "golden questions": ROOT / "data" / "golden" / "questions.jsonl",
    "perturbed questions": ROOT / "data" / "golden" / "paraphrase_questions.jsonl",
    "write-intent eval": ROOT / "data" / "golden" / "write_intent_eval.jsonl",
    "phrasal write eval": ROOT / "data" / "eval" / "write_intent_eval_phrasal.jsonl",
    "fresh synonym set": ROOT / "data" / "eval" / "synonym_fresh.jsonl",
}
PLANTED_FILES = {
    "canary documents": ROOT / "data" / "corpus" / "canary_docs.jsonl",
    "PII documents": ROOT / "data" / "corpus" / "pii_docs.jsonl",
}
TEXT_FIELDS = ("title", "body", "query")


def _texts(path: Path) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out.extend(str(row[k]) for k in TEXT_FIELDS if row.get(k))
    return out


def _tokens(texts: list[str]) -> list[str]:
    toks = []
    for t in texts:
        for m in _RUN_RE.finditer(t):
            a, b = _strip_span(t, m.start(), m.end())
            if b > a:
                toks.append(t[a:b])
    return toks


def _pr16_patterns():
    from ops_copilot.explain_redact import PR16_PATTERNS

    return PR16_PATTERNS


def _pr16_hits(secret: str) -> bool:
    from ops_copilot.explain_redact import find_sensitive

    return bool(find_sensitive(f"what is {secret} for", patterns=_pr16_patterns()))


def _shape_hit(token: str) -> bool:
    """Token already caught by a PR #16 shape pattern (canary, key id, ...)."""
    from ops_copilot.explain_redact import find_sensitive

    return bool(find_sensitive(token, patterns=_pr16_patterns()))


def run_secret_entropy_eval(threshold: float = DEFAULT_THRESHOLD) -> dict[str, Any]:
    det = RANDOM_TOKEN if threshold == DEFAULT_THRESHOLD else type(RANDOM_TOKEN)(threshold)
    secrets = synthetic_secrets(TEST_FAMILIES, N_PER_FAMILY, TEST_SEED)
    fam: dict[str, dict[str, Any]] = {}
    for f, s in secrets:
        r = fam.setdefault(f, {"n": 0, "pr16": 0, "detector": 0, "now": 0, "dev_family": f in DEV_FAMILIES})
        old = _pr16_hits(s)
        new = det.is_random(s)
        r["n"] += 1
        r["pr16"] += old
        r["detector"] += new
        r["now"] += old or new
    neg: dict[str, dict[str, Any]] = {}
    for label, path in NEGATIVE_FILES.items():
        toks = _tokens(_texts(path))
        cands = [t for t in toks if is_candidate(t)]
        shaped = [t for t in cands if _shape_hit(t)]
        cands = [t for t in cands if not _shape_hit(t)]
        flagged = sorted({t for t in cands if det.is_random(t)})
        neg[label] = {
            "n_tokens": len(toks),
            "n_candidates": len(cands),
            "n_already_shape_redacted": len(shaped),
            "n_flagged": sum(det.is_random(t) for t in cands),
            "flagged": flagged,
        }
    planted: dict[str, dict[str, Any]] = {}
    for label, path in PLANTED_FILES.items():
        toks = _tokens(_texts(path))
        planted[label] = {
            "n_candidates": sum(is_candidate(t) for t in toks),
            "flagged": sorted({t for t in toks if det.is_random(t)}),
        }
    n_c = sum(v["n_candidates"] for v in neg.values())
    n_f = sum(v["n_flagged"] for v in neg.values())
    n_pos = sum(r["n"] for r in fam.values())
    return {
        "threshold": threshold,
        "seed": TEST_SEED,
        "families": fam,
        "recall": {
            "pr16": sum(r["pr16"] for r in fam.values()) / n_pos,
            "now": sum(r["now"] for r in fam.values()) / n_pos,
        },
        "negatives": neg,
        "false_positive_rate": n_f / n_c if n_c else 0.0,
        "n_negative_candidates": n_c,
        "n_negative_flagged": n_f,
        "planted": planted,
        "score_examples": {
            t: round(token_score(t), 2)
            for t in ("checkout_retry", "payments-worker-heartbeat", "redis.maxmemory-policy", "q7xf2lpz9mkw3t")
        },
    }
