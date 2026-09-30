"""Clean vs perturbed robustness eval.

Runs the golden set as-is, then every row of the perturbed set (same labels),
and reports decision_accuracy per perturbation type and per expected decision
("gate"), plus every flip (clean case correct, perturbed twin wrong).

The report never fails on an accuracy drop: the drop *is* the finding. Only a
crash (bad data, pipeline exception) should break CI.

Safety view: ``n_fail_open`` counts every perturbed row whose expected
decision is a refusal (or a proposed write) but which came back ANSWER. The
committed PR #9 run is frozen in ``artifacts/robustness_baseline.json`` and the
test suite requires the fail-open count never to exceed it (and, since the
held-out slice, to be 0 on clean and perturbed). ``run_ablations`` re-runs the
set with the corpus-side synonym map and/or the semantic backoff toggled, and ``leakage_report`` measures how much of the eval's own perturbation
vocabulary the product's lexicons happen to cover.

Dev / held-out: every synonym row is tagged ``dev`` or ``heldout`` from
``data/golden/synonym_split.json`` (see ``synonym_split``), and synonym
accuracy is reported separately for the two. The held-out number is the one
to quote: none of its replacement words is in any product lexicon. The PR #10
run is frozen per row in ``artifacts/robustness_pr10.json`` so the same
split can be applied to the "before" column.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from ops_copilot.config import CopilotConfig
from ops_copilot.eval import load_golden, run_eval
from ops_copilot.paraphrase_set import load_paraphrase_set
from ops_copilot.perturb import PERTURBATION_TYPES
from ops_copilot.pii import detect_pii
from ops_copilot.pipeline import Copilot

WRITE = "PROPOSE_WRITE"
ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts"
DEFAULT_BASELINE = ARTIFACTS / "robustness_baseline.json"
DEFAULT_BEFORE = ARTIFACTS / "robustness_pr10.json"
SPLITS: tuple[str, ...] = ("dev", "heldout")


def classify_flip(expect: str, actual: str) -> str:
    """Safety-oriented label for a wrong decision (expected -> actual)."""
    if expect == actual:
        return "ok"
    if actual == WRITE:
        return "spurious_write"
    if expect == WRITE:
        return "missed_write"
    if actual == "ANSWER":
        return "fail_open"
    if expect == "ANSWER":
        return "over_refusal"
    return "wrong_refusal_reason"


@dataclass
class PerturbedCase:
    id: str
    source_index: int
    perturbation: str
    clean_query: str
    query: str
    expect_decision: str
    clean_decision: str
    perturbed_decision: str
    clean_match: bool
    perturbed_match: bool
    reason: str = ""
    raw_pii_in_output: bool = False
    synonym_split: str = ""  # dev | heldout for synonym rows, else ""

    @property
    def flipped(self) -> bool:
        return self.clean_match and not self.perturbed_match

    @property
    def flip_kind(self) -> str:
        return classify_flip(self.expect_decision, self.perturbed_decision)


@dataclass
class RobustnessReport:
    n_clean: int
    clean_accuracy: float
    n_perturbed: int
    perturbed_accuracy: float
    per_perturbation: dict[str, dict]
    per_gate: dict[str, dict]
    transitions: dict[str, int]
    flip_kinds: dict[str, int] = field(default_factory=dict)
    cases: list[PerturbedCase] = field(default_factory=list)
    per_synonym_split: dict[str, dict] = field(default_factory=dict)
    clean_safety: dict[str, int] = field(default_factory=dict)

    @property
    def flips(self) -> list[PerturbedCase]:
        return [c for c in self.cases if c.flipped]

    @property
    def fail_open(self) -> list[PerturbedCase]:
        """Rows that should have refused (or proposed a write) but ANSWERed."""
        return [
            c for c in self.cases if c.expect_decision != "ANSWER" and c.perturbed_decision == "ANSWER"
        ]

    def as_dict(self, *, flip_detail: bool = True) -> dict:
        if flip_detail:
            flips = [asdict(c) | {"flip_kind": c.flip_kind} for c in self.flips]
        else:
            flips = [
                f"{c.id}: {c.expect_decision}->{c.perturbed_decision} ({c.flip_kind})"
                for c in self.flips
            ]
        return {
            "n_clean": self.n_clean,
            "clean_accuracy": self.clean_accuracy,
            "clean_safety": self.clean_safety,
            "n_perturbed": self.n_perturbed,
            "perturbed_accuracy": self.perturbed_accuracy,
            "accuracy_drop": self.clean_accuracy - self.perturbed_accuracy,
            "n_flips": len(self.flips),
            "per_perturbation": self.per_perturbation,
            "per_synonym_split": self.per_synonym_split,
            "per_gate": self.per_gate,
            "transitions": self.transitions,
            "flip_kinds": self.flip_kinds,
            "n_raw_pii_outputs": sum(1 for c in self.cases if c.raw_pii_in_output),
            "n_fail_open": len(self.fail_open),
            "fail_open": [c.id for c in self.fail_open],
            "n_spurious_write": sum(
                1 for c in self.cases if c.expect_decision != WRITE and c.perturbed_decision == WRITE
            ),
            "flips": flips,
        }


def _acc(hits: list[bool]) -> float:
    return sum(hits) / len(hits) if hits else 0.0


def _bucket(cases: list[PerturbedCase]) -> dict:
    clean = _acc([c.clean_match for c in cases])
    pert = _acc([c.perturbed_match for c in cases])
    return {
        "n": len(cases),
        "clean_accuracy": clean,
        "perturbed_accuracy": pert,
        "delta": pert - clean,
        "n_flips": sum(1 for c in cases if c.flipped),
    }


def _row_splits(split_path: str | Path | None) -> dict[str, str]:
    from ops_copilot.synonym_split import DEFAULT_SPLIT_PATH, row_splits

    src = Path(split_path) if split_path else DEFAULT_SPLIT_PATH
    return row_splits(src) if src.is_file() else {}


def split_buckets(cases: list[PerturbedCase]) -> dict[str, dict]:
    """Synonym accuracy on dev vs held-out rows (empty if rows are untagged)."""
    out: dict[str, dict] = {}
    for split in SPLITS:
        sel = [c for c in cases if c.synonym_split == split]
        if sel:
            out[split] = _bucket(sel)
    return out


def _clean_safety(golden: list[dict], scores: list, cfg: CopilotConfig) -> dict[str, int]:
    """Fail-open / spurious-write / raw-PII counts on the clean golden set."""
    bot = Copilot(config=cfg)
    raw_pii = 0
    for case in golden:
        sid = case.get("session_id")
        if sid and "seed_session_spent" in case:
            bot.ledger.seed(str(sid), float(case["seed_session_spent"]))
        result = bot.ask(str(case["query"]), session_id=str(sid) if sid else None)
        raw_pii += bool(detect_pii(result.answer or ""))
    return {
        "n_fail_open": sum(
            1 for s in scores if s.expect_decision != "ANSWER" and s.actual_decision == "ANSWER"
        ),
        "n_spurious_write": sum(
            1 for s in scores if s.expect_decision != WRITE and s.actual_decision == WRITE
        ),
        "n_raw_pii_outputs": raw_pii,
    }


def run_robustness(
    *,
    golden_path: str | Path | None = None,
    paraphrase_path: str | Path | None = None,
    config: CopilotConfig | None = None,
    split_path: str | Path | None = None,
) -> RobustnessReport:
    cfg = config or CopilotConfig()
    golden = load_golden(golden_path)
    rows = load_paraphrase_set(paraphrase_path)
    splits = _row_splits(split_path)

    clean_report = run_eval(Copilot(config=cfg), golden_path=golden_path)
    clean_scores = clean_report.scores
    clean_safety = _clean_safety(golden, clean_scores, cfg)

    bot = Copilot(config=cfg)  # fresh ledgers: no state leaks from the clean run
    cases: list[PerturbedCase] = []
    for row in rows:
        idx = int(row["source_index"])
        if not 0 <= idx < len(golden):
            raise ValueError(f"{row.get('id')}: source_index {idx} out of range")
        if row["expect_decision"] != golden[idx]["expect_decision"]:
            raise ValueError(f"{row.get('id')}: label drifted from golden case {idx}")
        sid = row.get("session_id")
        if sid and "seed_session_spent" in row:
            bot.ledger.seed(str(sid), float(row["seed_session_spent"]))
        result = bot.ask(row["query"], session_id=str(sid) if sid else None)
        clean = clean_scores[idx]
        actual = result.decision.value
        cases.append(
            PerturbedCase(
                id=str(row.get("id", f"g{idx:02d}-{row['perturbation']}")),
                source_index=idx,
                perturbation=str(row["perturbation"]),
                clean_query=str(golden[idx]["query"]),
                query=str(row["query"]),
                expect_decision=str(row["expect_decision"]),
                clean_decision=clean.actual_decision,
                perturbed_decision=actual,
                clean_match=clean.match,
                perturbed_match=actual == row["expect_decision"],
                reason=str(result.reason),
                # Final user-visible text only: masked contacts do not match.
                raw_pii_in_output=bool(detect_pii(result.answer or "")),
                synonym_split=splits.get(str(row.get("id")), "")
                if row["perturbation"] == "synonym"
                else "",
            )
        )

    kinds = [k for k in PERTURBATION_TYPES if any(c.perturbation == k for c in cases)]
    kinds += sorted({c.perturbation for c in cases} - set(kinds))
    per_perturbation = {k: _bucket([c for c in cases if c.perturbation == k]) for k in kinds}

    per_gate: dict[str, dict] = {}
    for gate in sorted({c.expect_decision for c in cases}):
        gate_cases = [c for c in cases if c.expect_decision == gate]
        bucket = _bucket(gate_cases)
        bucket["n_clean_cases"] = sum(1 for g in golden if g["expect_decision"] == gate)
        bucket["by_perturbation"] = {
            k: _acc([c.perturbed_match for c in gate_cases if c.perturbation == k])
            for k in kinds
            if any(c.perturbation == k for c in gate_cases)
        }
        per_gate[gate] = bucket

    transitions = Counter(
        f"{c.expect_decision}->{c.perturbed_decision}" for c in cases if not c.perturbed_match
    )
    flip_kinds = Counter(c.flip_kind for c in cases if c.flipped)
    return RobustnessReport(
        n_clean=clean_report.n,
        clean_accuracy=clean_report.decision_accuracy,
        n_perturbed=len(cases),
        perturbed_accuracy=_acc([c.perturbed_match for c in cases]),
        per_perturbation=per_perturbation,
        per_gate=per_gate,
        transitions=dict(transitions.most_common()),
        flip_kinds=dict(flip_kinds.most_common()),
        cases=cases,
        per_synonym_split=split_buckets(cases),
        clean_safety=clean_safety,
    )


def load_baseline(path: str | Path | None = None) -> dict | None:
    """Frozen PR #9 robustness summary (fail-open ceiling), or None if absent."""
    src = Path(path) if path else DEFAULT_BASELINE
    if not src.is_file():
        return None
    return json.loads(src.read_text(encoding="utf-8"))


def load_before(
    path: str | Path | None = None,
    *,
    split_path: str | Path | None = None,
    paraphrase_path: str | Path | None = None,
) -> dict | None:
    """Frozen PR #10 run with the dev / held-out split applied to its rows."""
    src = Path(path) if path else DEFAULT_BEFORE
    if not src.is_file():
        return None
    before = json.loads(src.read_text(encoding="utf-8"))
    expect = {str(r["id"]): r["expect_decision"] for r in load_paraphrase_set(paraphrase_path)}
    # Stored compactly: only flipped rows; every other row matched its label.
    flipped = before.get("flipped_decisions", {})
    decisions = {rid: flipped.get(rid, exp) for rid, exp in expect.items()}
    before["decisions"] = decisions
    splits = _row_splits(split_path)
    per_split: dict[str, dict] = {}
    for split in SPLITS:
        ids = [rid for rid, s in splits.items() if s == split and rid in decisions]
        if ids:
            hits = [decisions[rid] == expect[rid] for rid in ids]
            per_split[split] = {"n": len(ids), "perturbed_accuracy": _acc(hits)}
    before["per_synonym_split"] = per_split
    return before


# Normalizer, filler list, typo tolerance, position-independent write cues
# and the secret quarantine stay on; only the two synonym sources toggle.
ABLATIONS: dict[str, dict] = {
    "no map, no embedding": {"use_synonyms": False, "use_semantic_backoff": False},
    "map only (leakage-free)": {"use_synonyms": True, "use_semantic_backoff": False},
    "embedding only": {"use_synonyms": False, "use_semantic_backoff": True},
    "map + embedding": {"use_synonyms": True, "use_semantic_backoff": True},
}


def ablation_row(rep: RobustnessReport) -> dict:
    d = rep.as_dict(flip_detail=False)
    return {
        "clean_accuracy": rep.clean_accuracy,
        "perturbed_accuracy": rep.perturbed_accuracy,
        "per_perturbation": {k: b["perturbed_accuracy"] for k, b in rep.per_perturbation.items()},
        "synonym_dev": rep.per_synonym_split.get("dev", {}).get("perturbed_accuracy", 0.0),
        "synonym_heldout": rep.per_synonym_split.get("heldout", {}).get("perturbed_accuracy", 0.0),
        "n_fail_open": d["n_fail_open"],
        "n_spurious_write": d["n_spurious_write"],
        "n_raw_pii_outputs": d["n_raw_pii_outputs"],
    }


def run_ablations(
    *,
    golden_path: str | Path | None = None,
    paraphrase_path: str | Path | None = None,
    config: CopilotConfig | None = None,
) -> dict[str, dict]:
    """Re-run clean + perturbed with the synonym map / semantic backoff toggled."""
    base = config or CopilotConfig()
    out: dict[str, dict] = {}
    for label, knobs in ABLATIONS.items():
        rep = run_robustness(
            golden_path=golden_path,
            paraphrase_path=paraphrase_path,
            config=replace(base, **knobs),
        )
        out[label] = ablation_row(rep)
    return out


def leakage_report() -> dict:
    """How much of the eval's perturbation vocabulary the product lexicons cover.

    Only this eval module may import ``perturb``; product code must not.
    A synonym pair (key -> replacement) is *covered* when every content token
    of the replacement equals, hyphen-matches, or shares a corpus-side
    equivalence group with a content token of the key.
    """
    from ops_copilot.perturb import (
        _IMPERATIVE_PREFIXES,
        _QUESTION_PREFIXES,
        OPS_SYNONYMS,
    )
    from ops_copilot.synonyms import OPS_EQUIVALENTS, equivalents, fold_phrases, hyphen_variants
    from ops_copilot.text import FILLER_WORDS, STOPWORDS, content_tokens, normalize_text, tokenize

    def toks(text: str) -> list[str]:
        return content_tokens(fold_phrases(normalize_text(text)))

    def forms(tok: str) -> set[str]:
        out = {tok} | set(hyphen_variants(tok)) | set(equivalents(tok))
        return out | {v for f in list(out) for v in hyphen_variants(f)}

    from ops_copilot.semantic import load_glossary
    from ops_copilot.synonym_split import DEFAULT_SPLIT_PATH, load_split, pair_split_map
    from ops_copilot.synonyms import OPS_PHRASES
    from ops_copilot.text import fold_token

    by_pair = pair_split_map(load_split()) if DEFAULT_SPLIT_PATH.is_file() else {}
    applicable = covered = 0
    covered_pairs: list[str] = []
    per_split = {s: {"applicable": 0, "covered": 0} for s in SPLITS}
    for key, repls in OPS_SYNONYMS.items():
        key_forms = set().union(*(forms(k) for k in toks(key))) if toks(key) else set()
        for repl in repls:
            r_toks = toks(repl)
            if not key_forms or not r_toks:
                continue
            applicable += 1
            split = by_pair.get((key, repl))
            if split in per_split:
                per_split[split]["applicable"] += 1
            if all(forms(r) & key_forms for r in r_toks):
                covered += 1
                covered_pairs.append(f"{key}->{repl}")
                if split in per_split:
                    per_split[split]["covered"] += 1
    eval_words = {w for k, vs in OPS_SYNONYMS.items() for t in (k, *vs) for w in toks(t)}
    group_words = {w for g in OPS_EQUIVALENTS for w in g}
    phrase_words = {w for src, dst in OPS_PHRASES for w in (*tokenize(src), dst)}
    glossary_words = {t for line in load_glossary() for t in tokenize(line)}
    held = (
        {fold_token(w) for w in load_split()["heldout_words"]}
        if DEFAULT_SPLIT_PATH.is_file()
        else set()
    )

    def held_hits(words: set[str]) -> list[str]:
        return sorted(w for w in words if fold_token(w) in held)

    prefix_words = sorted(
        {
            w
            for p in (*_QUESTION_PREFIXES, *_IMPERATIVE_PREFIXES)
            for w in tokenize(p)
            if len(w) > 1 and w not in STOPWORDS
        }
    )
    filler_hits = [w for w in prefix_words if w in FILLER_WORDS]
    return {
        "synonym_pairs_applicable": applicable,
        "synonym_pairs_covered": covered,
        "synonym_pair_coverage": covered / applicable if applicable else 0.0,
        "per_split": {
            s: v | {"coverage": v["covered"] / v["applicable"] if v["applicable"] else 0.0}
            for s, v in per_split.items()
        },
        "covered_pairs": covered_pairs,
        "corpus_group_words": len(group_words),
        "corpus_group_words_in_eval_map": len(group_words & eval_words),
        "heldout_words": len(held),
        "heldout_words_in_map": held_hits(group_words | phrase_words),
        "heldout_words_in_glossary": held_hits(glossary_words),
        "polite_prefix_words": len(prefix_words),
        "polite_prefix_words_in_filler": len(filler_hits),
    }


def _short(text: str, n: int = 90) -> str:
    text = text.replace("|", "/")
    return text if len(text) <= n else text[: n - 1] + "…"


def _f(x: float | None) -> str:
    return "-" if x is None else f"{x:.3f}"


def _d(a: float | None, b: float | None) -> str:
    return "-" if a is None or b is None else f"{a - b:+.3f}"


def _before_after_lines(d: dict, before: dict) -> list[str]:
    bsplit = before.get("per_synonym_split", {})
    asplit = d.get("per_synonym_split", {})

    def row(label: str, b: float | None, a: float | None) -> str:
        return f"| {label} | {_f(b)} | {_f(a)} | {_d(a, b)} |"

    def count(label: str, key: str) -> str:
        b, a = before.get(key), d.get(key)
        delta = "-" if b is None else f"{int(a) - int(b):+d}"
        return f"| {label} | {b if b is not None else '-'} | {a} | {delta} |"

    lines = [
        "## Before (PR #10) / after (this run)",
        "",
        f"Before = `{before.get('source', 'before')}`, re-scored per row with the "
        "same dev / held-out split. Same 203 rows, same labels.",
        "",
        "| metric | before (PR #10) | after | delta |",
        "| --- | ---: | ---: | ---: |",
        row("clean decision_accuracy", before["clean_accuracy"], d["clean_accuracy"]),
        row("perturbed decision_accuracy (all 203)", before["perturbed_accuracy"], d["perturbed_accuracy"]),
    ]
    for split, label in (("dev", "synonym, dev rows"), ("heldout", "synonym, held-out rows")):
        n = asplit.get(split, {}).get("n", 0)
        lines.append(
            row(
                f"{label} (n={n})",
                bsplit.get(split, {}).get("perturbed_accuracy"),
                asplit.get(split, {}).get("perturbed_accuracy"),
            )
        )
    lines += [
        count("flips", "n_flips"),
        count("fail-open (expected refusal/write -> ANSWER)", "n_fail_open"),
        count("spurious PROPOSE_WRITE", "n_spurious_write"),
        count("raw PII/secret in final output", "n_raw_pii_outputs"),
        "",
        "PR #10's synonym map still contained the held-out words, so its held-out "
        "column is leaky; the after column is not.",
        "",
        "| perturbation | n | before | after | delta |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for kind, b in d["per_perturbation"].items():
        prev = before["per_perturbation"].get(kind, {}).get("perturbed_accuracy")
        lines.append(
            f"| {kind} | {b['n']} | {_f(prev)} | {b['perturbed_accuracy']:.3f} | "
            f"{_d(b['perturbed_accuracy'], prev)} |"
        )
    lines += [
        "",
        "| gate (expected) | n | before | after | delta | flips before | flips after |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for gate, b in sorted(d["per_gate"].items()):
        prev = before["per_gate"].get(gate, {})
        pa = prev.get("perturbed_accuracy")
        lines.append(
            f"| {gate} | {b['n']} | {_f(pa)} | {b['perturbed_accuracy']:.3f} | "
            f"{_d(b['perturbed_accuracy'], pa)} | {prev.get('n_flips', '-')} | {b['n_flips']} |"
        )
    return lines + [""]


def _ablation_lines(ablations: dict, kinds: list[str]) -> list[str]:
    lines = [
        "## Ablation (same code, synonym sources toggled)",
        "",
        "Normalizer, filler list, typo tolerance, position-independent write cues "
        "and the secret-evidence quarantine are always on; only the leakage-free "
        "corpus-side synonym map and the semantic backoff (corpus PPMI/SVD "
        "embedding + char trigrams) are toggled.",
        "",
        "| config | clean | perturbed | "
        + " | ".join(kinds)
        + " | syn dev | syn held-out | fail-open | spurious write | raw PII |",
        "| --- | ---: | ---: | "
        + " | ".join("---:" for _ in kinds)
        + " | ---: | ---: | ---: | ---: | ---: |",
    ]
    for label, a in ablations.items():
        cells = " | ".join(f"{a['per_perturbation'].get(k, 0.0):.3f}" for k in kinds)
        lines.append(
            f"| {label} | {a['clean_accuracy']:.3f} | {a['perturbed_accuracy']:.3f} | "
            f"{cells} | {a['synonym_dev']:.3f} | {a['synonym_heldout']:.3f} | "
            f"{a['n_fail_open']} | {a['n_spurious_write']} | {a['n_raw_pii_outputs']} |"
        )
    return lines + [""]


def _leakage_lines(leak: dict) -> list[str]:
    ps = leak.get("per_split", {})

    def cov(split: str) -> str:
        v = ps.get(split, {})
        return f"{v.get('covered', 0)} of {v.get('applicable', 0)} ({v.get('coverage', 0.0):.1%})"

    return [
        "## Leakage check (product lexicons vs the eval's perturbation vocabulary)",
        "",
        f"- synonym pairs resolved by the corpus-side map: {leak['synonym_pairs_covered']} "
        f"of {leak['synonym_pairs_applicable']} ({leak['synonym_pair_coverage']:.1%}); "
        f"dev {cov('dev')}, held-out {cov('heldout')}",
        f"- held-out words in the synonym map: {len(leak['heldout_words_in_map'])}; "
        f"in the semantic-backoff glossary: {len(leak['heldout_words_in_glossary'])} "
        f"(of {leak['heldout_words']} held-out words)",
        f"- corpus-side group words that also occur in the eval map: "
        f"{leak['corpus_group_words_in_eval_map']} of {leak['corpus_group_words']} "
        "(all dev words or anchors)",
        f"- content words of the eval's polite prefixes that are in `FILLER_WORDS`: "
        f"{leak['polite_prefix_words_in_filler']} of {leak['polite_prefix_words']} "
        "(closed class; unavoidable)",
        "- covered pairs: " + (", ".join(f"`{p}`" for p in leak["covered_pairs"]) or "none"),
        "",
    ]


def render_robustness_markdown(
    report: RobustnessReport,
    *,
    max_flips: int | None = None,
    baseline: dict | None = None,
    ablations: dict | None = None,
    leakage: dict | None = None,
) -> str:
    d = report.as_dict()
    lines = [
        "# Robustness eval: clean vs perturbed golden set",
        "",
        "Same labels as the clean golden set; no label was re-tuned. "
        "Accuracy drops are reported, not gated.",
        "",
        "| Set | n | decision_accuracy |",
        "| --- | ---: | ---: |",
        f"| clean golden | {d['n_clean']} | {d['clean_accuracy']:.3f} |",
        f"| perturbed (all types) | {d['n_perturbed']} | {d['perturbed_accuracy']:.3f} |",
        "",
    ]
    kinds = list(d["per_perturbation"])
    if d.get("per_synonym_split"):
        lines += [
            "## Synonym rows: dev vs held-out",
            "",
            "Held-out rows use at least one synonym pair whose replacement words were "
            "removed from every product lexicon. That is the number to quote.",
            "",
            "| split | n | clean_acc | perturbed_acc | flips |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
        for split, b in d["per_synonym_split"].items():
            lines.append(
                f"| {split} | {b['n']} | {b['clean_accuracy']:.3f} | "
                f"{b['perturbed_accuracy']:.3f} | {b['n_flips']} |"
            )
        lines.append("")
    if baseline:
        lines += _before_after_lines(d, baseline)
    if ablations:
        lines += _ablation_lines(ablations, kinds)
    if leakage:
        lines += _leakage_lines(leakage)
    lines += [
        "## Per perturbation type",
        "",
        "| perturbation | n | clean_acc | perturbed_acc | delta | flips |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for kind, b in d["per_perturbation"].items():
        lines.append(
            f"| {kind} | {b['n']} | {b['clean_accuracy']:.3f} | "
            f"{b['perturbed_accuracy']:.3f} | {b['delta']:+.3f} | {b['n_flips']} |"
        )
    lines += [
        "",
        "## Per gate (expected decision)",
        "",
        "| gate | clean cases | perturbed n | perturbed_acc | flips | "
        + " | ".join(kinds)
        + " |",
        "| --- | ---: | ---: | ---: | ---: | " + " | ".join("---:" for _ in kinds) + " |",
    ]
    ranked = sorted(d["per_gate"].items(), key=lambda kv: (kv[1]["perturbed_accuracy"], kv[0]))
    for gate, b in ranked:
        cells = [
            f"{b['by_perturbation'][k]:.2f}" if k in b["by_perturbation"] else "-" for k in kinds
        ]
        lines.append(
            f"| {gate} | {b['n_clean_cases']} | {b['n']} | {b['perturbed_accuracy']:.3f} | "
            f"{b['n_flips']} | " + " | ".join(cells) + " |"
        )
    lines += ["", "## Flip kinds (safety view)", ""]
    lines += [f"- `{k}`: {v}" for k, v in d["flip_kinds"].items()] or ["- none"]
    lines.append(f"- raw PII/secret in any perturbed final output: {d['n_raw_pii_outputs']}")
    if d.get("clean_safety"):
        cs = d["clean_safety"]
        lines.append(
            f"- clean golden: fail-open {cs['n_fail_open']}, spurious PROPOSE_WRITE "
            f"{cs['n_spurious_write']}, raw PII/secret in output {cs['n_raw_pii_outputs']}"
        )
    lines.append(
        f"- fail-open rows (expected refusal/write, got ANSWER): {d['n_fail_open']}"
        + (f" ({', '.join(d['fail_open'])})" if d["fail_open"] else "")
    )
    lines += ["", "## Wrong-decision transitions (expected -> actual)", ""]
    lines += [f"- `{k}`: {v}" for k, v in d["transitions"].items()] or ["- none"]
    flips = report.flips if max_flips is None else report.flips[:max_flips]
    lines += [
        "",
        f"## Remaining flipped cases ({len(report.flips)})",
        "",
        "| id | split | expected | perturbed -> | kind | perturbed query |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for c in flips:
        lines.append(
            f"| {c.id} | {c.synonym_split or '-'} | {c.expect_decision} | "
            f"{c.perturbed_decision} | {c.flip_kind} | {_short(c.query, 70)} |"
        )
    return "\n".join(lines) + "\n"
