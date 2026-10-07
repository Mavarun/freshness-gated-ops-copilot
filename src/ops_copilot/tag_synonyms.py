"""Stack Exchange tag synonyms: an external, ops-domain synonym resource.

The word-vector backoff (``word_vectors.py``) showed that a general-English
resource does not carry ops senses: ``latency`` and ``credential`` are not in
its vocabulary, and nothing in it says that *bounce* is a restart. The README
named the next honest step as an ops-domain resource that is also external.

Stack Exchange tag synonyms are that. On each site a synonym (``from_tag`` ->
``to_tag``) is proposed by a user and needs approval from users who hold
answer score in the target tag, so every pair was judged by practitioners of
that site's domain, years before this repo existed. ``SITES`` are the sites
whose subject is running systems (Server Fault, Super User, Unix & Linux,
Ask Ubuntu, DevOps, Database Administrators, Network Engineering, Information
Security) plus Stack Overflow. ``scripts/fetch_tag_synonyms.py`` snapshots
*every* synonym of those sites into ``data/tagsyn/`` with no eval-driven or
corpus-driven filtering; tests and CI only read the snapshot (offline).

Content is CC BY-SA 4.0 (Stack Exchange Inc. and each site's contributors).
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "tagsyn"
DEFAULT_SNAPSHOT = DATA_DIR / "stackexchange_tag_synonyms.json.gz"
API_URL = "https://api.stackexchange.com/2.3/tags/synonyms"
OPS_SITES: tuple[str, ...] = (
    "serverfault",
    "superuser",
    "unix",
    "askubuntu",
    "devops",
    "dba",
    "networkengineering",
    "security",
)
SITES: tuple[str, ...] = (*OPS_SITES, "stackoverflow")
# SHA-256 of the uncompressed snapshot payload fetched on 2026-10-07 (4,560
# synonyms; Stack Overflow cut to its 2,500 most-applied by the anonymous
# 25-page API limit). Applied counts drift daily, so a re-fetch will differ.
SNAPSHOT_SHA256 = "e1cff66cc42f02967d9121b6335ce0bd1e17b8230e12dd27d2b9c2417a230c44"
SNAPSHOT_N_PAIRS = 4560


def _payload(pairs: list[dict], meta: dict) -> bytes:
    rows = sorted(
        ({k: p[k] for k in ("site", "from_tag", "to_tag", "applied_count")} for p in pairs),
        key=lambda p: (p["site"], p["from_tag"], p["to_tag"]),
    )
    meta = dict(meta) | {
        "n_pairs": len(rows),
        "per_site": {s: sum(1 for r in rows if r["site"] == s) for s in meta.get("sites", [])},
    }
    return json.dumps(
        {"meta": meta, "pairs": rows}, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def dump_snapshot(pairs: list[dict], meta: dict, path: str | Path) -> str:
    """Write a byte-stable gzip snapshot (zero mtime); returns its payload SHA-256."""
    payload = _payload(pairs, meta)
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, compresslevel=9) as gz:
        gz.write(payload)
    Path(path).write_bytes(buf.getvalue())
    return hashlib.sha256(payload).hexdigest()


def load_snapshot(path: str | Path | None = None) -> dict:
    """``{"meta": ..., "pairs": [{site, from_tag, to_tag, applied_count}, ...]}``."""
    with gzip.open(Path(path) if path else DEFAULT_SNAPSHOT, "rb") as fh:
        raw = fh.read()
    data = json.loads(raw)
    data["sha256"] = hashlib.sha256(raw).hexdigest()
    return data


# --- substitute table -------------------------------------------------------

MIN_WORD_LEN = 3
_SUFFIXES = ("ing", "ed", "es", "s")


def _stem(word: str) -> str:
    for suf in _SUFFIXES:
        if word.endswith(suf) and len(word) - len(suf) >= MIN_WORD_LEN:
            return word[: -len(suf)]
    return word


def is_inflection(a: str, b: str) -> bool:
    """Crude same-lemma test (``index``/``indexes``, ``debug``/``debugging``,
    ``cache``/``cached``, ``rotate``/``rotating``).

    Tag clusters are full of singular/plural and gerund pairs. Those carry no
    synonym information (``text.match_tokens`` already matches plurals) and
    would take the only substitute slot, so the table drops them.
    """
    from ops_copilot.text import fold_token

    sa, sb = _stem(a), _stem(b)
    if sa.rstrip("e") == sb.rstrip("e") or fold_token(a) == fold_token(b) or sa in (b, fold_token(b)) or sb in (a, fold_token(a)):
        return True
    short, long_ = sorted((sa, sb), key=len)
    # doubled final consonant before -ing / -ed: debugg(ing) ~ debug
    return long_[:-1] == short and long_[-1] == short[-1]


def tag_word(tag: str) -> str | None:
    """The plain word a single-word tag stands for (``None`` for compounds/ids)."""
    t = tag.strip().lower()
    if len(t) >= MIN_WORD_LEN and t.isascii() and t.isalpha():
        return t
    return None


def site_clusters(
    pairs: list[dict], *, sites: tuple[str, ...] = SITES, min_applied: int = 0
) -> list[tuple[str, frozenset[str]]]:
    """``(site, {to_tag, from_tag...})`` per master tag; stable order.

    Each site keeps synonyms star-shaped (a tag that is a synonym cannot have
    synonyms of its own), so a master tag and its synonyms are one cluster.
    Clusters never merge across sites: two sites' communities each vouch only
    for their own pairs.
    """
    groups: dict[tuple[str, str], set[str]] = {}
    for p in pairs:
        if p["site"] not in sites or int(p["applied_count"]) < min_applied:
            continue
        groups.setdefault((p["site"], p["to_tag"]), {p["to_tag"]}).add(p["from_tag"])
    return [(site, frozenset(tags)) for (site, _), tags in sorted(groups.items())]


def build_substitute_table(
    pairs: list[dict],
    targets: set[str] | frozenset[str],
    *,
    sites: tuple[str, ...] = SITES,
    min_applied: int = 0,
) -> dict[str, tuple[tuple[str, int], ...]]:
    """word -> ((corpus word, n_sites vouching), ...), most-vouched first.

    For every single-word tag of every cluster, the *other* single-word tags of
    that cluster that are corpus words (``targets``; plural folds count, so
    ``servers`` reaches ``server``), minus inflections of the word itself
    (``is_inflection``). The table depends only on the snapshot
    and the corpus. Ties break by spelling, so it is deterministic.
    """
    from ops_copilot.text import fold_token

    def target_of(word: str) -> str | None:
        if word in targets:
            return word
        folded = fold_token(word)
        if folded in targets:
            return folded
        if word + "s" in targets:
            return word + "s"
        return None

    votes: dict[str, dict[str, set[str]]] = {}
    for site, tags in site_clusters(pairs, sites=sites, min_applied=min_applied):
        words = sorted({w for w in (tag_word(t) for t in tags) if w})
        for a in words:
            for b in words:
                tb = target_of(b)
                if a == b or tb is None or tb == a or is_inflection(a, tb):
                    continue
                votes.setdefault(a, {}).setdefault(tb, set()).add(site)
    return {
        a: tuple(sorted(((t, len(s)) for t, s in subs.items()), key=lambda ts: (-ts[1], ts[0])))
        for a, subs in sorted(votes.items())
    }


_TABLE_CACHE: dict[tuple, dict] = {}


class TagSynonymBackoff:
    """Map a query word onto corpus words its tag cluster vouches for (or none).

    ``neighbours`` has the ``semantic.SemanticBackoff`` interface. A neighbour's
    score is the number of sites whose community linked the two tags; only
    neighbours with at least ``min_sites`` are returned, at most
    ``max_neighbours`` of them. Identifiers, numbers and short tokens are never
    looked up, and returning nothing is the safe answer (the word stays an
    unknown, high-weight term and grounding refuses as before).
    """

    def __init__(
        self,
        corpus_texts: list[str],
        *,
        sites: tuple[str, ...] = SITES,
        min_sites: int = 1,
        max_neighbours: int = 1,
        min_applied: int = 0,
        snapshot: dict | None = None,
    ) -> None:
        from ops_copilot.word_vectors import corpus_words, words_fingerprint

        unknown = set(sites) - set(SITES)
        if unknown:
            raise ValueError(f"sites not in the snapshot: {sorted(unknown)}")
        self.corpus_words: frozenset[str] = frozenset(corpus_words(corpus_texts))
        self.sites = tuple(sites)
        self.min_sites = int(min_sites)
        self.max_neighbours = int(max_neighbours)
        key = (words_fingerprint(sorted(self.corpus_words)), self.sites, int(min_applied))
        if snapshot is not None:
            self.table = build_substitute_table(
                snapshot["pairs"], self.corpus_words, sites=self.sites, min_applied=min_applied
            )
        else:
            if key not in _TABLE_CACHE:
                _TABLE_CACHE[key] = build_substitute_table(
                    load_snapshot()["pairs"],
                    self.corpus_words,
                    sites=self.sites,
                    min_applied=min_applied,
                )
            self.table = _TABLE_CACHE[key]
        self._cache: dict[str, tuple] = {}

    @staticmethod
    def lookupable(token: str) -> bool:
        from ops_copilot.text import is_identifier

        return token.isalpha() and not is_identifier(token) and len(token) >= MIN_WORD_LEN

    def neighbours(self, token: str) -> tuple:
        """Corpus words a tag cluster makes interchangeable with ``token``."""
        from ops_copilot.semantic import Neighbour
        from ops_copilot.text import fold_token

        tok = token.lower()
        if tok in self._cache:
            return self._cache[tok]
        found: tuple = ()
        if self.lookupable(tok):
            rows = self.table.get(tok) or self.table.get(fold_token(tok), ())
            picked = [
                Neighbour(w, float(n), "tagsyn")
                for w, n in rows
                if n >= self.min_sites and w in self.corpus_words and w != tok
            ]
            found = tuple(picked[: self.max_neighbours])
        self._cache[tok] = found
        return found
