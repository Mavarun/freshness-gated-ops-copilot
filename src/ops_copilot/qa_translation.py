"""Question-answer translation model: does this *evidence* answer the question?

PR #14-#16 tried three word lists (general-English word vectors, Stack
Exchange tag synonyms, Wiktionary computing senses) and none moved a held-out
row: the senses the held-out rows need (``lag`` ~ latency, ``health`` ~
status, ``bounce`` ~ restart) are either absent or not phrased with the
corpus word. A word list substitutes a query word *before* looking at the
evidence. This module instead scores a (query word, evidence) pair: how likely
is it that a question containing ``lag`` is answered by text containing
``latency``?

Model. IBM Model 1 (Brown et al. 1993) trained in the question <- answer
direction, as in answer retrieval for Q&A archives (Berger et al. 2000; Xue,
Jeon & Croft 2008). The training data is *outside* data written by
practitioners who never saw this repo: the titles of the most-voted questions
of eight ops Stack Exchange sites and the accepted / top-voted answers to them
(``scripts/fetch_stackexchange_qa.py``; CC BY-SA, attribution in the table's
``meta``). ``T(q | a)`` is the probability that answer word ``a`` "generates"
question word ``q``; an empty (NULL) answer word absorbs title words that no
answer word explains. The support score of query word ``q`` given an evidence
word ``a`` is the lift

    score(q, a) = log( T(q | a) / P_title(q) )

i.e. how much more likely ``q`` is in the question when ``a`` is in its
answer than in a random title. It is evidence-conditioned, so it applies to a
*known* corpus word used in another sense (``lag`` is a corpus word via
"consumer lag"; a latency page lacks it, yet ``latency`` answers ``lag``
questions) as well as to unknown words.

Leakage. Nothing is filtered by eval words. Pairs are split train / test by a
salted hash of (site, question id) before training; the committed table is the
*train* model, and ``rank_eval`` reports answer-ranking quality on the test
questions (out of sample). The committed table keeps, for every *corpus*
content word ``a`` (the evidence side), its top question words; the corpus
vocabulary hash is pinned so a corpus change without a rebuild fails a test.
The question side is the whole title vocabulary (min document frequency
``MIN_Q_DF``), not the eval's words.

Tokens: ``text.content_tokens`` of the normalised text, plain alphabetic words
only (identifiers and numbers are exact-only everywhere in this repo), plural
folded with ``text.fold_token``. Answers drop fenced / indented code, inline
code, URLs and HTML, and keep the first ``MAX_ANSWER_TOKENS`` distinct words.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from ops_copilot.text import content_tokens, fold_token, is_identifier

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "qa"
DEFAULT_TABLE = DATA_DIR / "se_qa_translation.json.gz"
SPLIT_SALT = "se-qa-translation-split"
VALID_SALT = "se-qa-translation-valid"
TEST_FRACTION = 0.10
VALID_FRACTION = 0.10  # of the train questions; picks the EM iteration count
ITERATION_GRID: tuple[int, ...] = (1, 2, 3, 5, 8)
MAX_TITLE_TOKENS = 12
MAX_ANSWER_TOKENS = 80
MAX_ANSWERS_PER_QUESTION = 2
MIN_Q_DF = 3
MIN_A_DF = 5
EM_ITERATIONS = 8  # upper end of ITERATION_GRID; the build picks on validation
SHRINK_ALPHA = 5.0
TABLE_TOP_Q = 300
TABLE_MIN_LIFT = 1.0  # keep pairs at least e x background; the gate threshold is calibrated above it
NULL = "<null>"

_FENCE = re.compile(r"```.*?```|~~~.*?~~~", re.S)
_INDENTED = re.compile(r"(?m)^(?: {4}|\t).*$")
_INLINE_CODE = re.compile(r"`[^`\n]*`")
_URL = re.compile(r"https?://\S+|www\.\S+")
_HTML = re.compile(r"<[^>]+>")
_ENTITY = re.compile(r"&[a-z]+;|&#\d+;")
_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def clean_markdown(text: str) -> str:
    """Prose of a Stack Exchange markdown body (code, links and HTML removed)."""
    t = _FENCE.sub(" ", text or "")
    t = _INDENTED.sub(" ", t)
    t = _INLINE_CODE.sub(" ", t)
    t = _MD_LINK.sub(r"\1", t)
    t = _URL.sub(" ", t)
    t = _HTML.sub(" ", t)
    t = _ENTITY.sub(" ", t)
    return t


def words(text: str) -> list[str]:
    """Plain alphabetic content words, plural-folded, in order (with repeats)."""
    out: list[str] = []
    for tok in content_tokens(text):
        if not tok.isalpha() or is_identifier(tok):
            continue
        out.append(fold_token(tok))
    return out


def distinct(seq: Iterable[str], limit: int) -> list[str]:
    seen: dict[str, None] = {}
    for w in seq:
        if w not in seen:
            seen[w] = None
            if len(seen) >= limit:
                break
    return list(seen)


def _hash_unit(salt: str, site: str, question_id: int) -> float:
    h = hashlib.sha1(f"{salt}|{site}|{int(question_id)}".encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def is_test(site: str, question_id: int, fraction: float = TEST_FRACTION) -> bool:
    """Deterministic train / test assignment of one question (salted SHA-1)."""
    return _hash_unit(SPLIT_SALT, site, question_id) < fraction


def is_valid(site: str, question_id: int, fraction: float = VALID_FRACTION) -> bool:
    """Validation questions inside train (independent salt); never test ones."""
    return not is_test(site, question_id) and _hash_unit(VALID_SALT, site, question_id) < fraction


def pairs_from_page(site: str, body: dict) -> list[dict]:
    """(title words, answer words) pairs of one raw API page.

    Up to ``MAX_ANSWERS_PER_QUESTION`` answers per question with score >= 1,
    the accepted one first, then by score. Licences are kept for attribution.
    """
    out: list[dict] = []
    for q in body.get("items", []):
        title = words(q.get("title", ""))
        title = distinct(title, MAX_TITLE_TOKENS)
        if not title:
            continue
        answers = [a for a in q.get("answers") or [] if int(a.get("score", 0)) >= 1]
        answers.sort(key=lambda a: (not a.get("is_accepted", False), -int(a.get("score", 0)), int(a["answer_id"])))
        for a in answers[:MAX_ANSWERS_PER_QUESTION]:
            aw = distinct(words(clean_markdown(a.get("body_markdown", ""))), MAX_ANSWER_TOKENS)
            if not aw:
                continue
            out.append(
                {
                    "site": site,
                    "qid": int(q["question_id"]),
                    "aid": int(a["answer_id"]),
                    "license": a.get("content_license", "CC BY-SA"),
                    "q": title,
                    "a": aw,
                }
            )
    return out
