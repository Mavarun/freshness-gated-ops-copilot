"""Deterministic, seeded query perturbations for the robustness eval.

Four perturbation types, all offline (no LLM):

- ``synonym``: swap 1-2 words using a small hand-written ops synonym map.
- ``word_order``: a few adjacent-token swaps inside each clause (first token
  of the clause stays put, so the question/imperative cue survives).
- ``typo``: 1-2 character edits (transpose / drop / double / keyboard
  neighbour) on plain alphabetic words of length >= 4.
- ``polite``: a polite rephrasing prefix ("could you please tell me ...").

Identifier-like tokens (``checkout-api``, ``p99``, ``INC-4821``,
``CNRY-VAULT7F3A``, ``redis.maxmemory-policy``) are never typo'd or
reordered away from their clause, because users copy-paste those.

Every call derives its RNG from ``(seed, kind, query)`` via a string seed,
so output is stable across processes and independent of case order.
"""

from __future__ import annotations

import random
import re

DEFAULT_SEED = 42
PERTURBATION_TYPES: tuple[str, ...] = ("synonym", "word_order", "typo", "polite")

# Hand-written, deliberately small. Keys are lowercase; multi-word keys match
# as phrases. Values are what an on-call engineer might plausibly type instead.
OPS_SYNONYMS: dict[str, tuple[str, ...]] = {
    "restart": ("reboot", "bounce", "recycle"),
    "page": ("alert", "ping"),
    "patch": ("update", "modify"),
    "latency": ("response time", "lag"),
    "replicas": ("pods", "instances"),
    "status": ("health", "state"),
    "enabled": ("turned on", "switched on"),
    "utilization": ("usage", "saturation"),
    "mitigation": ("remediation", "workaround"),
    "recommend": ("suggest", "advise"),
    "runbook": ("playbook", "guide"),
    "procedure": ("process", "steps"),
    "email": ("e-mail", "mail address"),
    "contact": ("point of contact", "owner"),
    "token": ("credential", "secret"),
    "rotation": ("rollover", "cycling"),
    "schedule": ("timetable", "calendar"),
    "window": ("timeframe", "period"),
    "oncall": ("on-duty engineer", "pager holder"),
    "on-call": ("on-duty", "pager"),
    "primary": ("main", "lead"),
    "outage": ("incident", "downtime"),
    "config": ("configuration", "setting"),
    "deploy": ("release", "rollout"),
    "remaining": ("left", "leftover"),
    "current": ("present", "latest"),
    "cadence": ("frequency", "interval"),
    "interval": ("period", "frequency"),
    "freeze": ("lockdown", "moratorium"),
    "production": ("prod", "live"),
    "maintenance": ("upkeep", "servicing"),
    "database": ("db", "datastore"),
    "password": ("passphrase", "credential"),
    "feature flag": ("feature toggle", "feature switch"),
    "flag": ("toggle", "switch"),
    "rollback": ("revert", "undo"),
    "owner": ("maintainer", "steward"),
    "owns": ("maintains", "is responsible for"),
    "directory": ("listing", "roster"),
    "reset": ("reinitialize", "clear"),
    "drain": ("burn down", "clear"),
    "target": ("goal", "objective"),
    "request rate": ("traffic", "throughput"),
    "endpoint": ("URL", "address"),
    "key": ("secret", "credential"),
    "path": ("route", "location"),
    "route": ("path", "URL"),
    "provision": ("create", "set up"),
    "gateway": ("proxy", "edge"),
    "start": ("begin", "kick off"),
    "error budget": ("SLO headroom", "error allowance"),
    "service": ("app", "system"),
    "flush": ("purge", "clear"),
    "webhook": ("callback", "hook"),
    "allowlist": ("whitelist", "permit list"),
    "chargeback": ("dispute", "refund"),
    "playbook": ("runbook", "guide"),
    "checkpoint": ("snapshot", "flush point"),
    "handshake": ("negotiation", "setup"),
    "size": ("capacity", "count"),
    "setting": ("config value", "parameter"),
    "request": ("reservation", "allocation"),
    "qps": ("throughput", "requests per second"),
    "salt": ("seed", "nonce"),
    "stickiness": ("affinity", "pinning"),
}

_QUESTION_STARTS = frozenset(
    {"what", "who", "how", "is", "are", "when", "where", "which", "why", "do", "does"}
)
_REQUEST_LEADS = re.compile(r"^\s*(please|can you|could you|would you)\s+", re.I)
_QUESTION_PREFIXES = (
    "Could you please tell me",
    "Quick question:",
    "Hey team, sorry to bother you, but",
    "I was wondering,",
)
_IMPERATIVE_PREFIXES = (
    "Could you please",
    "Would you kindly",
    "Hey, when you get a chance,",
    "I need you to",
)
_KEYBOARD = {
    "a": "sqz", "b": "vn", "c": "xv", "d": "sf", "e": "wr", "f": "dg", "g": "fh",
    "h": "gj", "i": "uo", "j": "hk", "k": "jl", "l": "k", "m": "n", "n": "bm",
    "o": "ip", "p": "o", "q": "w", "r": "et", "s": "ad", "t": "ry", "u": "yi",
    "v": "cb", "w": "qe", "x": "zc", "y": "tu", "z": "x",
}
_PLAIN_WORD = re.compile(r"^[A-Za-z]{4,}$")
_EDGE_PUNCT = re.compile(r"^(\W*)(.*?)(\W*)$")


def _rng(seed: int, kind: str, query: str) -> random.Random:
    return random.Random(f"{seed}|{kind}|{query}")


def _match_case(src: str, repl: str) -> str:
    return repl[:1].upper() + repl[1:] if src[:1].isupper() else repl


def synonym_swap_trace(
    query: str, rng: random.Random, max_swaps: int = 2
) -> tuple[str, list[tuple[str, str]]]:
    """``synonym_swap`` plus the ``(key, replacement)`` pairs it applied.

    Consumes the RNG exactly like the original swap, so replaying it with
    ``_rng(seed, "synonym", query)`` recovers which pairs produced a committed
    paraphrase row (``synonym_split`` uses this to tag dev / held-out rows).
    """
    spans: list[tuple[int, int, str]] = []
    taken: set[int] = set()
    # Longest keys first so "feature flag" wins over "flag".
    for key in sorted(OPS_SYNONYMS, key=len, reverse=True):
        for m in re.finditer(rf"(?<![\w.-]){re.escape(key)}(?![\w-])", query, re.I):
            idx = set(range(m.start(), m.end()))
            if idx & taken:
                continue
            taken |= idx
            spans.append((m.start(), m.end(), key))
    if not spans:
        return query, []
    spans.sort()
    chosen = rng.sample(spans, k=min(max_swaps, len(spans)))
    out = query
    applied: list[tuple[str, str]] = []
    for start, end, key in sorted(chosen, reverse=True):
        repl = rng.choice(OPS_SYNONYMS[key])
        out = out[:start] + _match_case(out[start:end], repl) + out[end:]
        applied.append((key, repl))
    return out, applied[::-1]


def synonym_swap(query: str, rng: random.Random, max_swaps: int = 2) -> str:
    return synonym_swap_trace(query, rng, max_swaps)[0]


def synonym_pairs() -> list[tuple[str, str]]:
    """Every ``(key, replacement)`` pair of ``OPS_SYNONYMS`` in map order."""
    return [(key, repl) for key, repls in OPS_SYNONYMS.items() for repl in repls]


def shuffle_word_order(query: str, rng: random.Random) -> str:
    clauses = re.split(r"([,;:])", query)
    out: list[str] = []
    for clause in clauses:
        if clause in {",", ";", ":"}:
            out.append(clause)
            continue
        m = re.match(r"^(\s*)(.*?)([?.!]*\s*)$", clause, re.S)
        lead, body, tail = m.group(1), m.group(2), m.group(3)
        toks = body.split()
        if len(toks) < 3:
            out.append(clause)
            continue
        # Disjoint adjacent swaps (never undo each other, never a no-op swap).
        slots = [i for i in range(1, len(toks) - 1) if toks[i].lower() != toks[i + 1].lower()]
        rng.shuffle(slots)
        want, used = max(1, (len(toks) - 1) // 3), set()
        for i in slots:
            if want == 0:
                break
            if {i, i + 1} & used:
                continue
            toks[i], toks[i + 1] = toks[i + 1], toks[i]
            used |= {i, i + 1}
            want -= 1
        out.append(lead + " ".join(toks) + tail)
    return "".join(out)


def _typo_word(word: str, rng: random.Random) -> str:
    op = rng.choice(("transpose", "drop", "double", "neighbour"))
    i = rng.randrange(1, len(word) - 1)  # never touch the first/last char
    if op == "transpose":
        return word[:i] + word[i + 1] + word[i] + word[i + 2 :]
    if op == "drop":
        return word[:i] + word[i + 1 :]
    if op == "double":
        return word[:i] + word[i] + word[i:]
    near = _KEYBOARD.get(word[i].lower(), word[i])
    return word[:i] + rng.choice(near) + word[i + 1 :]


def inject_typos(query: str, rng: random.Random) -> str:
    toks = query.split(" ")
    eligible = []
    for idx, tok in enumerate(toks):
        core = _EDGE_PUNCT.match(tok).group(2)
        if _PLAIN_WORD.match(core) and not core.isupper():
            eligible.append(idx)
    if not eligible:
        return query
    n = 1 if len(toks) <= 6 else 2
    for idx in sorted(rng.sample(eligible, k=min(n, len(eligible)))):
        pre, core, post = _EDGE_PUNCT.match(toks[idx]).groups()
        toks[idx] = pre + _typo_word(core, rng) + post
    return " ".join(toks)


def _lower_first(text: str) -> str:
    first = text.split(" ", 1)[0]
    if first.isupper() or any(ch.isdigit() or ch in "-_." for ch in first):
        return text
    return text[:1].lower() + text[1:]


def polite_rephrase(query: str, rng: random.Random) -> str:
    q = query.strip()
    first = q.split(" ", 1)[0].lower()
    lead = _REQUEST_LEADS.match(q)
    if lead is None and first in _QUESTION_STARTS:
        return f"{rng.choice(_QUESTION_PREFIXES)} {_lower_first(q)}"
    body = q[lead.end() :] if lead else q
    return f"{rng.choice(_IMPERATIVE_PREFIXES)} {_lower_first(body)}"


_DISPATCH = {
    "synonym": synonym_swap,
    "word_order": shuffle_word_order,
    "typo": inject_typos,
    "polite": polite_rephrase,
}


def perturb(query: str, kind: str, *, seed: int = DEFAULT_SEED) -> str:
    """Return a deterministic perturbation of ``query`` (may equal it if n/a)."""
    if kind not in _DISPATCH:
        raise ValueError(f"unknown perturbation {kind!r}; expected {PERTURBATION_TYPES}")
    return _DISPATCH[kind](query, _rng(seed, kind, query))


def perturb_all(query: str, *, seed: int = DEFAULT_SEED) -> dict[str, str]:
    return {kind: perturb(query, kind, seed=seed) for kind in PERTURBATION_TYPES}
