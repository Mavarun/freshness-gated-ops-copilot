"""Score verified did-you-mean rewrites on rescuable rows, traps and a null control.

Rows come from the synonym sets that carry the clean golden query they were made from
(``source_index``):

- **rescuable**: expected ``ANSWER`` but the shipped default refuses ``REFUSE_UNGROUNDED``.
  A suggestion is a *doc hit* when the rewritten query's answer cites a document the
  clean golden query's answer cites, and an *anchor hit* when the rewrite puts the gold
  anchor word (the left side of the swap, e.g. ``latency`` for ``latency -> lag``) back.
- **traps**: expected ``REFUSE_UNGROUNDED`` and refused so by the default. Any
  suggestion is an *invitation*: the user is offered a different, answerable question.
- **null control**: for each rescuable row, the missing term is swapped for seeded random
  corpus words instead of ranked candidates. Its verify rate says how lenient the gates
  are on arbitrary one-word swaps, i.e. how much of a doc hit is the ranking and how much
  is the gate accepting almost anything near the right document.

Nothing here changes a decision on the original query.
"""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ops_copilot.eval import load_golden
from ops_copilot.paraphrase_set import load_paraphrase_set
from ops_copilot.pipeline import Copilot
from ops_copilot.rewrite_suggest import SuggestConfig, _eligible, suggest_rewrites, swap_word
from ops_copilot.synonym_split import load_split
from ops_copilot.text import fold_token, tokenize

ROOT = Path(__file__).resolve().parents[2]
CALIBRATION_FILES = tuple(f"data/eval/synonym_dev{i}.jsonl" for i in range(2, 7))
CONFIRM_FILES = ("data/eval/synonym_dev7.jsonl", "data/eval/synonym_fresh.jsonl")


@dataclass
class EvalRow:
    id: str
    query: str
    source_index: int
    expect: str
    anchors: tuple[str, ...]
    source: str


def _doc(chunk_id: str) -> str:
    return chunk_id.split("::", 1)[0]


def _anchors_from_swap(swap: str) -> tuple[str, ...]:
    out: list[str] = []
    for part in swap.split(","):
        if "->" in part:
            out.extend(tokenize(part.split("->", 1)[0]))
    return tuple(out)


def load_rows(files: tuple[str, ...], root: Path = ROOT) -> list[EvalRow]:
    rows: list[EvalRow] = []
    for rel in files:
        for line in (root / rel).read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                rows.append(
                    EvalRow(r["id"], r["query"], int(r.get("source_index", -1)), r["expect_decision"],
                            _anchors_from_swap(r.get("swap", "")), rel)
                )
    return rows


def load_heldout_rows() -> list[EvalRow]:
    """The held-out synonym rows of the robustness set (golden paraphrases)."""
    split = load_split()["rows"]
    out: list[EvalRow] = []
    for r in load_paraphrase_set():
        rid = str(r.get("id"))
        if r["perturbation"] != "synonym" or split.get(rid, {}).get("split") != "heldout":
            continue
        pairs = split[rid].get("pairs", [])
        anchors = tuple(t for p in pairs for t in tokenize(p.split("->", 1)[0]))
        out.append(EvalRow(rid, r["query"], int(r.get("source_index", -1)), r["expect_decision"], anchors,
                           "heldout"))
    return out


@dataclass
class ArmScore:
    n_rescuable: int = 0
    n_covered: int = 0
    doc_hit_1: int = 0
    doc_hit_3: int = 0
    anchor_hit_3: int = 0
    n_traps: int = 0
    trap_invitations: int = 0
    null_verified: int = 0
    null_tried: int = 0
    rows: list[dict] = field(default_factory=list)

    def rates(self) -> dict:
        n, t = max(self.n_rescuable, 1), max(self.n_traps, 1)
        return {
            "coverage": self.n_covered / n,
            "doc_hit_1": self.doc_hit_1 / n,
            "doc_hit_3": self.doc_hit_3 / n,
            "anchor_hit_3": self.anchor_hit_3 / n,
            "trap_invitation": self.trap_invitations / t,
            "null_verify_rate": self.null_verified / max(self.null_tried, 1),
        }

    def as_dict(self) -> dict:
        d = asdict(self)
        d["rates"] = self.rates()
        return d


def _corpus_words(bot: Copilot) -> list[str]:
    chunks = getattr(bot, "chunks", None) or getattr(bot.retriever, "chunks", [])
    return sorted({t for c in chunks for t in tokenize(c.text) if _eligible(t, set())})


def score_arm(
    rows: list[EvalRow],
    cfg: SuggestConfig,
    *,
    bot: Copilot | None = None,
    null_draws: int = 0,
    seed: int = 1106,
) -> ArmScore:
    bot = bot or Copilot()
    verifier = Copilot(config=bot.config)
    golden = load_golden()
    clean_docs: dict[int, set[str]] = {}
    words = _corpus_words(bot) if null_draws else []
    rng = random.Random(seed)
    sc = ArmScore()
    for row in rows:
        res = bot.ask(row.query)
        if res.decision.value != "REFUSE_UNGROUNDED":
            continue
        if row.expect == "REFUSE_UNGROUNDED":
            sc.n_traps += 1
            rws = suggest_rewrites(res, bot, cfg, verifier=verifier)
            sc.trap_invitations += bool(rws)
            sc.rows.append({"id": row.id, "kind": "trap", "suggestions": [r.query for r in rws]})
            continue
        if row.expect != "ANSWER":
            continue
        sc.n_rescuable += 1
        if row.source_index not in clean_docs:
            clean = verifier.ask(golden[row.source_index]["query"])
            clean_docs[row.source_index] = {_doc(c) for c in clean.cited_ids}
        want = clean_docs[row.source_index]
        rws = suggest_rewrites(res, bot, cfg, verifier=verifier)
        hits = [bool({_doc(c) for c in r.cited_ids} & want) for r in rws]
        anchors = {fold_token(a) for a in row.anchors}
        anchor = any(fold_token(rep) in anchors for r in rws for _, rep in r.swaps if rep)
        sc.n_covered += bool(rws)
        sc.doc_hit_1 += bool(hits[:1] and hits[0])
        sc.doc_hit_3 += any(hits[:3])
        sc.anchor_hit_3 += anchor
        sc.rows.append({"id": row.id, "kind": "rescuable", "suggestions": [r.query for r in rws],
                        "doc_hits": hits, "anchor_hit": anchor})
        missing = (res.explanation or {}).get("missing_terms") or []
        for _ in range(null_draws if missing else 0):
            q = swap_word(res.query, missing[0], rng.choice(words))
            if q is None:
                break
            sc.null_tried += 1
            sc.null_verified += verifier.ask(q).decision.value == "ANSWER"
    return sc
