"""Real multi-part identifiers from Stack Exchange posts, as a false-positive set.

The Oct 29 identifier check used the 51 names in the repo's own ``data/``. Any
exemption list built from ``data/`` passes that check by construction, so it
cannot say what an arm does to a service name the repo has never seen. This
module harvests the ``-`` / ``.`` / ``_`` joined names that real ops posts
contain (``xserver-xorg-input-libinput``, ``innodb_buffer_pool``,
``mysignins.microsoft.com``) from the same Stack Exchange snapshot as the QA
table, split by the same question-level train / test hash
(``qa_translation.is_test``). Each name is put after a credential noun
(``token <name>``, the detector ignores which cue it is) and counted as a false
positive when the detector flags it. Hostnames, package names, config keys and
hyphenated English ("less-than-ideal") are all non-secrets, so every flag is
wrong.

Nothing harvested is committed: the raw pages stay outside the repo (as for the
QA table), and the scripts take ``--raw-dir``. Only counts and a few examples
reach ``artifacts/``.
"""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path
from typing import Any, Iterable

IDENT_RE = re.compile(r"(?<![\w./-])[A-Za-z]{3,12}(?:([-._])[A-Za-z]{3,12})(?:\1[A-Za-z]{3,12}){1,4}(?![\w-])")
CUE = "token"


def harvest(texts: Iterable[str]) -> set[str]:
    out: set[str] = set()
    for t in texts:
        out.update(m.group() for m in IDENT_RE.finditer(t or ""))
    return out


def se_identifiers(raw_dir: Path) -> dict[str, list[str]]:
    """3-6 part identifiers in question titles and the top two answers, by split.

    A name seen in both splits is kept in train only, so the test set is disjoint.
    """
    from ops_copilot.qa_translation import clean_markdown, is_test

    by: dict[str, set[str]] = {"train": set(), "test": set()}
    for f in sorted(Path(raw_dir).glob("*.json.gz")):
        site = f.name.split("-")[0]
        for q in json.loads(gzip.decompress(f.read_bytes())).get("items", []):
            split = "test" if is_test(site, int(q["question_id"])) else "train"
            texts = [q.get("title", "")] + [clean_markdown(a.get("body_markdown", "")) for a in (q.get("answers") or [])[:2]]
            by[split] |= harvest(texts)
    by["test"] -= by["train"]
    return {k: sorted(v) for k, v in by.items()}


def identifier_flags(det, names: Iterable[str]) -> list[str]:
    """Names the detector flags right after a credential noun."""
    return [n for n in names if det.search(f"{CUE} {n}") is not None]


def score_identifiers(det, names: list[str], *, base: set[str] | None = None) -> dict[str, Any]:
    flagged = identifier_flags(det, names)
    out: dict[str, Any] = {"n": len(names), "flagged": len(flagged), "examples": flagged[:10]}
    if base is not None:
        new = [n for n in flagged if n not in base]
        out["new_flags"] = len(new)
        out["new_examples"] = new[:12]
    return out
