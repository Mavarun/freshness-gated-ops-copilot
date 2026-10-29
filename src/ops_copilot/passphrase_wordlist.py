"""Passphrases drawn from a real diceware wordlist, and how many of their words leak.

The Oct 13 probe (``explain_eval`` section 7) used 32 hand-picked words that were
chosen to be *absent* from the ops vocabulary, so it could not see the detector's
documented gap: a passphrase made of words the ops vocabulary knows. Real
passphrase generators do not avoid ops words. The EFF large wordlist (7,776
words, ``data/passphrase``) shares 1,342 words with the ops vocabulary (17%),
so a 5-word EFF passphrase has three or more ops words about 4% of the time and
at least one ops word 61% of the time.

``wordlist_passphrases(seed, n)`` draws ``n`` rows: 4-6 distinct alphabetic EFF
words, a separator from {space, -, ., _}, half Title-Case with a trailing
two-digit number (as in the Oct 13 probe), placed in one of the five Oct 13
templates. ``score_rows`` runs the trace ``query`` redaction (the boundary pass,
fragment pass included) with a given pattern set and counts:

* ``leak_rows`` / ``leak_words``: rows with any passphrase word (4+ letters) left
  in the redacted query, and how many such words;
* ``over_words``: template words (4+ letters, not in the passphrase) that were
  redacted, the price of a wider span;
* ``cause``: a post-hoc label for every leaking row (``no_flag_ops`` when the
  run had too few non-ops words, ``stop_inside`` when a passphrase word is in the
  run stop list, ``tail_trim`` when only trailing words leaked, ``other``).
"""

from __future__ import annotations

import gzip
import random
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence

DATA = Path(__file__).resolve().parents[2] / "data" / "passphrase" / "eff_large_wordlist.txt.gz"
WORDLIST_SHA256 = "addd35536511597a02fa0a9ff1e5284677b8883b83e986e43f15a3db996b903e"
SEPARATORS = (" ", "-", ".", "_")
SEP_NAMES = {" ": "space", "-": "hyphen", ".": "dot", "_": "underscore"}
LENGTHS = (4, 5, 6)


@lru_cache(maxsize=1)
def eff_words() -> tuple[str, ...]:
    """The 7,772 purely alphabetic words of the EFF large list (4 hyphenated ones dropped)."""
    import hashlib

    raw = gzip.decompress(DATA.read_bytes())
    if hashlib.sha256(raw).hexdigest() != WORDLIST_SHA256:
        raise ValueError("EFF wordlist does not match the pinned sha256")
    out = []
    for ln in raw.decode("utf-8").splitlines():
        parts = ln.split("\t")
        if len(parts) == 2 and parts[1].isalpha():
            out.append(parts[1])
    return tuple(out)


@dataclass(frozen=True)
class ProbeRow:
    secret: str
    words: tuple[str, ...]
    separator: str
    context: str
    template: str

    @property
    def text(self) -> str:
        return self.template.format(s=self.secret)


def _templates() -> list[tuple[str, str]]:
    from ops_copilot.explain_eval import PASSPHRASE_TEMPLATES

    return [(ctx, t) for ctx, ts in PASSPHRASE_TEMPLATES.items() for t in ts]


def wordlist_passphrases(seed: int, n: int) -> list[ProbeRow]:
    rng = random.Random(seed)
    words = eff_words()
    tpls = _templates()
    rows: list[ProbeRow] = []
    for i in range(n):
        ws = rng.sample(words, rng.choice(LENGTHS))
        sep = SEPARATORS[i % len(SEPARATORS)]
        ctx, tpl = tpls[rng.randrange(len(tpls))]
        parts = list(ws)
        if rng.random() < 0.5:
            parts = [w.title() for w in parts] + [str(rng.randint(10, 99))]
        rows.append(ProbeRow(sep.join(parts), tuple(ws), SEP_NAMES[sep], ctx, tpl))
    return rows


def _present(blob: str, word: str) -> bool:
    return re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", blob) is not None


def redact_query(text: str, patterns) -> str:
    from ops_copilot.explain_redact import redact_boundary

    out, _ = redact_boundary({"query": text}, query=text, patterns=patterns)
    return str(out["query"])


def _cause(row: ProbeRow, leaked: list[str]) -> str:
    from ops_copilot.passphrase import _SPACE_STOP, ops_vocabulary

    ws = [w.lower() for w in row.words]
    if row.separator == "space" and any(w in _SPACE_STOP for w in ws):
        return "stop_inside"
    if len(leaked) == len([w for w in ws if len(w) >= 4]):
        ops = ops_vocabulary()
        return "no_flag_ops" if sum(w not in ops for w in ws) < max(2, -(-len(ws) // 2)) else "other"
    tail = [w for w in ws if len(w) >= 4][-len(leaked):]
    return "tail_trim" if leaked == tail else "other"


def score_rows(rows: Sequence[ProbeRow], patterns) -> dict[str, Any]:
    tot = {"rows": 0, "words": 0, "leak_rows": 0, "leak_words": 0, "over_words": 0}
    by_sep: dict[str, dict[str, int]] = {}
    cause: dict[str, int] = {}
    examples: list[dict[str, Any]] = []
    for r in rows:
        red = redact_query(r.text, patterns).lower()
        words = [w.lower() for w in r.words if len(w) >= 4]
        leaked = [w for w in words if _present(red, w)]
        tpl_words = [w for w in re.findall(r"[a-z]{4,}", r.template.lower()) if w not in words]
        over = sum(not _present(red, w) for w in dict.fromkeys(tpl_words))
        s = by_sep.setdefault(r.separator, {"rows": 0, "leak_rows": 0, "leak_words": 0})
        s["rows"] += 1
        tot["rows"] += 1
        tot["words"] += len(words)
        tot["over_words"] += over
        if leaked:
            c = _cause(r, leaked)
            cause[c] = cause.get(c, 0) + 1
            s["leak_rows"] += 1
            s["leak_words"] += len(leaked)
            tot["leak_rows"] += 1
            tot["leak_words"] += len(leaked)
            if len(examples) < 8:
                examples.append({"text": r.text, "leaked": leaked, "cause": c})
    return {"total": tot, "by_separator": by_sep, "cause": dict(sorted(cause.items())), "examples": examples}
