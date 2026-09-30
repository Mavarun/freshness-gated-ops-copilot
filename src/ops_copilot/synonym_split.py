"""Leakage-free dev / held-out split of the robustness eval's synonym pairs.

PR #10 measured that the corpus-side synonym map (``synonyms.OPS_EQUIVALENTS``)
resolved 39 of the eval's 122 synonym pairs, so the 0.620 synonym accuracy
partly measured the map's overlap with ``perturb.OPS_SYNONYMS``. This module
splits the eval vocabulary so one half can be used for development and the
other half is never seen by product code.

Split unit: a *novel replacement word*, i.e. a content token of a replacement
that is not already a content token of its key ("feature switch" for "feature
flag" contributes only ``switch``). The sorted novel words are shuffled with
``random.Random(f"{seed}|{SPLIT_SALT}")`` and the first ``HELDOUT_FRACTION``
of them are held out. A pair is held-out when any of its novel words is
held-out, otherwise dev (a pair with no novel content word, e.g. ``config ->
setting`` where ``setting`` is a stopword, is dev with an empty word list).
So the dev and held-out pair sets are disjoint, and so are their novel
vocabularies.

A synonym row of the committed paraphrase set is held-out when any pair its
perturbation applied is held-out. The applied pairs are recovered by replaying
``perturb.synonym_swap_trace`` with the row's seed; the replay must reproduce
the committed query exactly, otherwise ``tag_rows`` raises (no silent drift).
The 203-row set and the golden labels are not regenerated or edited.

Only eval code (this module, ``robustness``, scripts, tests) may import
``perturb``. Product code never imports this module either: the held-out
words were removed from ``synonyms.py`` by hand and
``tests/test_heldout_leakage.py`` asserts none of them is in any product
lexicon.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from ops_copilot.perturb import DEFAULT_SEED, _rng, synonym_pairs, synonym_swap_trace
from ops_copilot.text import content_tokens

SPLIT_SEED = 42
HELDOUT_FRACTION = 0.5
SPLIT_SALT = "synonym-heldout-split"
DEFAULT_SPLIT_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "golden" / "synonym_split.json"
)
DEV = "dev"
HELDOUT = "heldout"
PAIR_SEP = "->"


def novel_words(key: str, replacement: str) -> list[str]:
    """Content tokens of ``replacement`` that are not content tokens of ``key``."""
    key_toks = set(content_tokens(key))
    return sorted(set(content_tokens(replacement)) - key_toks)


def build_split(
    *,
    seed: int = SPLIT_SEED,
    fraction: float = HELDOUT_FRACTION,
) -> dict:
    """Deterministic word-level partition of the eval's synonym pairs."""
    if not 0.0 < fraction < 1.0:
        raise ValueError("fraction must be in (0, 1)")
    pairs = synonym_pairs()
    words = sorted({w for key, repl in pairs for w in novel_words(key, repl)})
    order = list(words)
    random.Random(f"{seed}|{SPLIT_SALT}").shuffle(order)
    n_held = round(len(order) * fraction)
    held = set(order[:n_held])
    by_split: dict[str, list[str]] = {DEV: [], HELDOUT: []}
    for key, repl in pairs:  # a pair is held out if any of its novel words is
        label = HELDOUT if set(novel_words(key, repl)) & held else DEV
        by_split[label].append(f"{key}{PAIR_SEP}{repl}")
    return {
        "seed": seed,
        "fraction": fraction,
        "salt": SPLIT_SALT,
        "n_words": len(words),
        "dev_words": sorted(set(words) - held),
        "heldout_words": sorted(held),
        "n_dev_pairs": len(by_split[DEV]),
        "n_heldout_pairs": len(by_split[HELDOUT]),
        "dev_pairs": by_split[DEV],
        "heldout_pairs": by_split[HELDOUT],
    }


def pair_split_map(split: dict) -> dict[tuple[str, str], str]:
    """``{(key, replacement): "dev" | "heldout"}`` from a split dict."""
    out: dict[tuple[str, str], str] = {}
    for label in (DEV, HELDOUT):
        for pair in split[f"{label}_pairs"]:
            key, repl = pair.split(PAIR_SEP)
            out[(key, repl)] = label
    return out


def applied_pairs(clean_query: str, *, seed: int = DEFAULT_SEED) -> tuple[str, list[tuple[str, str]]]:
    """Replay the synonym perturbation of ``clean_query``: (query, applied pairs)."""
    return synonym_swap_trace(clean_query, _rng(seed, "synonym", clean_query))


def tag_rows(
    rows: list[dict],
    golden: list[dict],
    split: dict,
    *,
    seed: int = DEFAULT_SEED,
) -> dict[str, dict]:
    """``{row_id: {"split", "pairs"}}`` for every synonym row of the paraphrase set."""
    by_pair = pair_split_map(split)
    out: dict[str, dict] = {}
    for row in rows:
        if row["perturbation"] != "synonym":
            continue
        clean = str(golden[int(row["source_index"])]["query"])
        replayed, pairs = applied_pairs(clean, seed=seed)
        if replayed != row["query"]:
            raise ValueError(f"{row['id']}: synonym replay drifted from the committed row")
        labels = {by_pair[p] for p in pairs}
        out[str(row["id"])] = {
            "split": HELDOUT if HELDOUT in labels else DEV,
            "pairs": [f"{k}{PAIR_SEP}{r}" for k, r in pairs],
        }
    return out


def build_split_file(rows: list[dict], golden: list[dict], *, seed: int = SPLIT_SEED) -> dict:
    split = build_split(seed=seed)
    tagged = tag_rows(rows, golden, split)
    split["n_dev_rows"] = sum(1 for t in tagged.values() if t["split"] == DEV)
    split["n_heldout_rows"] = sum(1 for t in tagged.values() if t["split"] == HELDOUT)
    split["rows"] = tagged
    return split


def _render(split: dict) -> str:
    """Reviewable JSON: scalars and lists inline, one row per line."""

    def one(obj: object) -> str:
        return json.dumps(obj, ensure_ascii=False)

    lines = ["{"]
    items = list(split.items())
    for i, (key, value) in enumerate(items):
        tail = "," if i < len(items) - 1 else ""
        if key == "rows":
            body = ",\n".join(f"  {one(k)}: {one(v)}" for k, v in value.items())
            lines.append(f' "rows": {{\n{body}\n }}{tail}')
        else:
            lines.append(f" {one(key)}: {one(value)}{tail}")
    return "\n".join(lines) + "\n}\n"


def dump_split(split: dict, path: str | Path | None = None) -> Path:
    out = Path(path) if path else DEFAULT_SPLIT_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_render(split), encoding="utf-8")
    return out


def load_split(path: str | Path | None = None) -> dict:
    src = Path(path) if path else DEFAULT_SPLIT_PATH
    return json.loads(src.read_text(encoding="utf-8"))


def row_splits(path: str | Path | None = None) -> dict[str, str]:
    """``{row_id: "dev" | "heldout"}`` from the committed split file."""
    return {rid: t["split"] for rid, t in load_split(path)["rows"].items()}
