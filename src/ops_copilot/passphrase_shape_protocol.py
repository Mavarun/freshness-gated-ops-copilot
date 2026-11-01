"""Pre-registered protocol for the Nov 1 ``shape_guards`` knob (committed before any scored run).

Question: the shipped detector flags 221 of 1,920 Stack Exchange *train*
identifiers (alphabetic plus glued-digit, ``passphrase_digit_protocol.se_material``)
after a credential noun, and 24 of 147 *test* ones. Can guards that recognise
compounds no passphrase generator emits (``passphrase.shape_guard_hits``: a
non-generator letter case, a host name's top-level domain, a non-EFF stop word)
remove those false flags without leaking passphrases that generators or people
do emit?

What was looked at before this file:

* the 221 SE *train* flags of the shipped detector, by shape: 37 all-caps
  constants, 19 CamelCase parts, 142 lower-case names (host names, dotted config
  keys, hyphenated English);
* on those 221 only: the case guard would drop 24, the TLD guard 35 and the stop
  guard 23 (80 together). That is the design data; budgets below were set
  without any probe count.
* which TLD and stop words are EFF-list words (``net``; 13 stop words such as
  ``many``, ``that``, ``very``), which is why both guards exclude list words.

No seed below, no SE test sentence and no SE test identifier was scored by any arm
before this file was committed. All-caps constants (``BTRFS_FIRST_FREE_OBJECTID``)
are deliberately *not* targeted: KeePassXC emits UPPER-CASE passphrases.

Grid: every subset of {case, tld, stop}, 8 arms, smallest first; ``()`` is shipped.
Every other knob is pinned to the shipped value (Oct 31 defaults).

Probes (``N_ROWS`` each): ``standard`` (Oct 29 EFF rows), ``attached`` (Bitwarden
glued digit), ``invented`` (Oct 31 invented-word rows), ``cased`` (KeePassXC UPPER
and xkpasswd alternate / random / inverted case) and ``phrase`` (EFF words with one
inner function word, the stop guard's worst case).

Calibration (``CALIB_SEEDS``, SE *train*). An arm is *safe* when

1. no Oct 13 probe word leaks;
2. no golden / perturbed / phrasal-write trace ``query`` changes;
3. no ``data/`` identifier is newly flagged;
4. no more SE sentences are flagged than shipped;
5. no SE identifier is *newly* flagged;
6. on each probe it over-redacts at most ``OVER_BUDGET_PER_ROW`` more template words per row;
7. on ``standard``, ``attached`` and ``cased`` rows it leaks no more words than shipped;
8. on ``invented`` and ``phrase`` rows it leaks at most ``LEAK_BUDGET`` (share of the
   probe's words) more than shipped.

Pick: the safe arm with the fewest SE train identifiers flagged; ties go to fewer
leaked words over the five probes, then grid order (fewer guards first).

One-shot confirm (``CONFIRM_SEEDS``, SE *test*): the pick ships on only if checks 1-8
hold and it flags strictly fewer SE test identifiers than shipped. Otherwise it
ships off; the confirm seeds are spent either way.

Reported, not gating: both arms on ``OFFLIST_SEED`` rows of off-list words.
"""

from __future__ import annotations

from itertools import combinations
from typing import Any

CALIB_SEEDS = {"standard": 3203, "attached": 3209, "invented": 3217, "cased": 3221, "phrase": 3229}
CONFIRM_SEEDS = {"standard": 3251, "attached": 3253, "invented": 3257, "cased": 3259, "phrase": 3271}
OFFLIST_SEED = 3299
N_ROWS = 1200
OVER_BUDGET_PER_ROW = 0.5
LEAK_BUDGET = 0.005
GUARDS = ("case", "tld", "stop")
SHIPPED: tuple[str, ...] = ()
PROBES = ("standard", "attached", "invented", "cased", "phrase")
STRICT_PROBES = ("standard", "attached", "cased")
BUDGET_PROBES = ("invented", "phrase")


def arms() -> list[tuple[str, ...]]:
    return [c for k in range(len(GUARDS) + 1) for c in combinations(GUARDS, k)]


def arm_name(arm: tuple[str, ...]) -> str:
    return "+".join(arm) if arm else "shipped"


def detector(arm: tuple[str, ...]):
    """Arms pin every knob, so a later change of the module defaults never moves them."""
    from ops_copilot.passphrase import CuedPassphraseDetector

    return CuedPassphraseDetector(
        tail="keep", coherence_max=0.10, coherence_compounds=False,
        wordlist_compounds="all4", wordlist_space=True, exempt_identifiers=True,
        attached_digit=True, digit_guard=True, plain_rule="ops", plain_scope="compounds",
        shape_guards=tuple(arm),
    )


def patterns_for(arm: tuple[str, ...]):
    from ops_copilot import passphrase_compound_protocol as C

    det = detector(arm)
    return tuple((k, det if k == "passphrase" else p) for k, p in C.patterns_for(("all4", True, True)))


def probe_rows(kind: str, seed: int, n: int = N_ROWS):
    from ops_copilot import passphrase_wordlist as W

    if kind == "standard":
        return W.wordlist_passphrases(seed, n)
    if kind == "attached":
        return W.wordlist_passphrases(seed, n, number_style="attached")
    if kind == "invented":
        return W.invented_passphrases(seed, n)
    if kind == "cased":
        return W.cased_passphrases(seed, n)
    if kind == "phrase":
        return W.phrase_passphrases(seed, n)
    raise ValueError(kind)


def leak_total(res: dict) -> int:
    return sum(res["probe"][k]["total"]["leak_words"] for k in PROBES)


def is_safe(res: dict, base: dict) -> dict[str, bool]:
    p, b = res["probe"], base["probe"]
    out = {
        "oct13_no_leak": res["oct13_leak_words"] == 0,
        "repo_queries_unchanged": res["repo_query_changes"] == 0,
        "data_idents": not res["data_ident_new_flags"],
        "se_sentences": res["se"]["sent_flagged"] <= base["se"]["sent_flagged"],
        "se_identifiers": res["se"]["ident_new"] == 0,
        "over_budget": all(
            p[k]["total"]["over_words"] - b[k]["total"]["over_words"] <= OVER_BUDGET_PER_ROW * b[k]["total"]["rows"]
            for k in PROBES
        ),
        "strict_no_more_leaks": all(p[k]["total"]["leak_words"] <= b[k]["total"]["leak_words"] for k in STRICT_PROBES),
        "leak_budget": all(
            p[k]["total"]["leak_words"] - b[k]["total"]["leak_words"] <= LEAK_BUDGET * b[k]["total"]["words"]
            for k in BUDGET_PROBES
        ),
    }
    return out


def pick(results: list[dict], base: dict) -> dict | None:
    safe = [r for r in results if all(is_safe(r, base).values())]
    if not safe:
        return None
    order = {arm_name(a): i for i, a in enumerate(arms())}
    return min(safe, key=lambda r: (r["se"]["ident_flagged"], leak_total(r), order[r["arm"]]))


def confirm_passes(res: dict, base: dict) -> dict[str, Any]:
    chk = is_safe(res, base)
    chk["fewer_test_identifiers"] = res["se"]["ident_flagged"] < base["se"]["ident_flagged"]
    return chk
