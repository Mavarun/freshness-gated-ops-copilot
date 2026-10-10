"""Semantic grounding backoff: dev-only calibration, strict safety rules, no fail-open."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from conftest import make_chunk

from ops_copilot import Copilot, CopilotConfig
from ops_copilot.embeddings import EmbeddingBackend
from ops_copilot.grounding import EmbeddingSupport, Grounder
from ops_copilot.paraphrase_set import load_paraphrase_set
from ops_copilot.robustness import run_robustness
from ops_copilot.semantic_calibration import GRID, calibration_rows, select
from ops_copilot.synonym_split import DEFAULT_SPLIT_PATH, row_splits
from ops_copilot.text import normalize_text
from ops_copilot.types import Decision

ROOT = Path(__file__).resolve().parents[1]
# The embedding slice predates the passage classifier (on since 2026-10-10),
# which would rescue g35 before the embedding gets to it.
FROZEN = replace(CopilotConfig(), embedding_backend="frozen", use_passage_support_model=False)
ROWS = {str(r["id"]): r for r in load_paraphrase_set()}


class KeywordBackend(EmbeddingBackend):
    """Deterministic 2-d toy embedding: 'window'/'timeframe' texts point one way."""

    name = "toy"

    def _encode_missing(self, texts):
        out = []
        for t in texts:
            low = t.lower()
            hot = any(w in low for w in ("window", "timeframe", "slot"))
            out.append(np.array([1.0, 0.0]) if hot else np.array([0.0, 1.0]))
        return out


EVIDENCE = "Maintenance policy. The production maintenance window is Saturday 04:00 UTC."
CORPUS = [EVIDENCE, "Checkout latency p99 is 2410 ms.", "Rotate the vault token every 30 days."]


def toy_grounder(threshold: float = 0.5, *, strict: bool = True, max_terms: int = 1) -> Grounder:
    support = EmbeddingSupport(
        KeywordBackend(),
        threshold,
        query_form=normalize_text,
        max_rescued_terms=max_terms,
        strict=strict,
    )
    return Grounder(CORPUS, embed_support=support)


def test_unknown_word_is_rescued_only_above_threshold() -> None:
    q = "What is the production maintenance timeframe?"
    g = toy_grounder(0.5)
    sup = g.support(q, EVIDENCE)
    assert sup.rescued == {"timeframe"} and sup.similarity == pytest.approx(1.0)
    assert g.keys_supported(q, EVIDENCE)
    assert not toy_grounder(1.01).keys_supported(q, EVIDENCE)
    assert not Grounder(CORPUS).keys_supported(q, EVIDENCE)


def test_identifiers_and_numbers_are_never_rescued() -> None:
    g = toy_grounder(0.0)
    for q in ("What is the maintenance window for zz-api-9?", "Is the maintenance window 0700?"):
        assert not g.support(q, EVIDENCE).rescued, q


def test_strict_mode_requires_every_other_term_lexically() -> None:
    # 'rollback' is a corpus word missing from the evidence: no rescue in strict mode.
    corpus = CORPUS + ["Rollback the deploy if errors rise."]
    q = "What is the maintenance window rollback timeframe?"
    strict = Grounder(corpus, embed_support=EmbeddingSupport(KeywordBackend(), 0.5, strict=True))
    loose = Grounder(corpus, embed_support=EmbeddingSupport(KeywordBackend(), 0.5, strict=False))
    assert not strict.support(q, EVIDENCE).rescued
    assert loose.support(q, EVIDENCE).rescued == {"timeframe"}


def test_strict_mode_only_rescues_wh_questions() -> None:
    q = "Production maintenance timeframe, please"
    assert not toy_grounder(0.5).support(q, EVIDENCE).rescued
    assert toy_grounder(0.5, strict=False).support(q, EVIDENCE).rescued == {"timeframe"}
    assert toy_grounder(0.5).support("wat is the maintenance timeframe", EVIDENCE).rescued


def test_rescue_is_capped_by_max_terms() -> None:
    q = "What is the maintenance timeframe slotting?"
    assert not toy_grounder(0.5, max_terms=1).support(q, EVIDENCE).rescued
    assert toy_grounder(0.5, max_terms=2).support(q, EVIDENCE).rescued == {"timeframe", "slotting"}


def test_answer_coverage_stays_lexical() -> None:
    g = toy_grounder(0.5)
    chunk = make_chunk("maint", text=EVIDENCE, title="Maintenance policy")
    res = g.check("What is the production maintenance timeframe?", [chunk], "timeframe slot")
    assert res.semantic_rescued == ["timeframe"]
    assert res.answer_coverage == 0.0 and not res.passed
    assert res.as_dict()["semantic_similarity"] == pytest.approx(1.0)


def test_calibration_uses_only_clean_and_dev_rows() -> None:
    rows = calibration_rows()
    splits = row_splits(DEFAULT_SPLIT_PATH)
    groups = [g for _, g, _ in rows]
    assert groups.count("clean") == 51 and groups.count("dev") == 15
    for rid, group, row in rows:
        assert splits.get(rid) != "heldout", rid
        if group == "dev":
            assert row["perturbation"] == "synonym" and splits[rid] == "dev"


def test_committed_calibration_matches_the_config_default() -> None:
    art = json.loads((ROOT / "artifacts" / "semantic_grounding_calibration.json").read_text("utf-8"))
    chosen = art["chosen"]
    cfg = CopilotConfig()
    assert cfg.semantic_grounding_threshold == pytest.approx(chosen["threshold"])
    assert cfg.semantic_grounding_max_terms == chosen["max_terms"]
    assert set(art["calibration_rows"]) == {rid for rid, _, _ in calibration_rows()}
    splits = row_splits(DEFAULT_SPLIT_PATH)
    assert not [r for r in art["calibration_rows"] if splits.get(r) == "heldout"]


def test_selection_rule_is_feasible_max_accuracy_then_midpoint() -> None:
    def res(th, mt, acc, fo=0):
        return {
            "threshold": th,
            "max_terms": mt,
            "accuracy": acc,
            "clean_accuracy": 1.0,
            "n_fail_open": fo,
            "n_spurious_write": 0,
            "n_raw_pii_outputs": 0,
        }

    grid = [res(th, 1, 0.9) for th in GRID]
    for th in GRID[10:15]:
        grid[GRID.index(th)] = res(th, 1, 0.95)
    grid[GRID.index(GRID[3])] = res(GRID[3], 1, 0.99, fo=1)  # infeasible spike
    grid += [res(th, 2, 0.95) for th in GRID]  # same accuracy, more rescued words
    chosen = select(grid)
    assert chosen["max_terms"] == 1
    assert chosen["threshold"] == GRID[12]
    assert chosen["optimal_run"] == [GRID[10], GRID[14]]


@pytest.fixture(scope="module")
def report_on():
    return run_robustness(config=FROZEN)


def test_embedding_on_keeps_clean_perfect_and_safety_at_zero(report_on) -> None:
    d = report_on.as_dict(flip_detail=False)
    assert d["clean_accuracy"] == 1.0
    assert d["clean_safety"] == {"n_fail_open": 0, "n_spurious_write": 0, "n_raw_pii_outputs": 0}
    assert d["n_fail_open"] == 0
    assert d["n_spurious_write"] == 0
    assert d["n_raw_pii_outputs"] == 0


def test_embedding_on_numbers_quoted_in_readme(report_on) -> None:
    sp = report_on.per_synonym_split
    assert round(sp["heldout"]["perturbed_accuracy"] * 35) == 18
    assert round(sp["dev"]["perturbed_accuracy"] * 15) == 12
    understood = [
        c.id
        for c in report_on.cases
        if c.synonym_split == "heldout"
        and c.expect_decision in {"ANSWER", "PROPOSE_WRITE"}
        and c.perturbed_match
    ]
    # 2 of 12 held-out ANSWER / PROPOSE_WRITE rows: g42 ('page the on-duty
    # engineer') is parsed by the structured write gate since the write slice.
    assert understood == ["g07-synonym", "g42-synonym"]
    assert report_on.perturbed_accuracy == pytest.approx(182 / 203)


def test_g19_rollback_steps_trap_needs_strict_mode() -> None:
    q = str(ROWS["g19-synonym"]["query"])
    assert Copilot(config=FROZEN).ask(q).decision is Decision.REFUSE_UNGROUNDED
    loose = Copilot(config=replace(FROZEN, semantic_grounding_strict=False)).ask(q)
    assert loose.decision is Decision.ANSWER  # the fail-open strict mode exists for
    assert loose.grounding.semantic_rescued == ["steps"]


def test_rescued_answer_citing_a_canary_page_refuses() -> None:
    # At 0.80 only the canary-free paragraph of canary_vault_sidecar is rescued,
    # so the draft skips the token; the document-scoped scan must still refuse.
    q = str(ROWS["g35-synonym"]["query"])
    bot = Copilot(config=replace(FROZEN, semantic_grounding_threshold=0.80))
    res = bot.ask(q)
    assert res.grounding.semantic_rescued == ["location"]
    assert res.decision is Decision.REFUSE_CANARY
    loose = Copilot(
        config=replace(FROZEN, semantic_grounding_threshold=0.80, semantic_grounding_strict=False)
    ).ask(q)
    assert loose.decision is Decision.ANSWER


def test_unrecognised_command_is_never_rescued() -> None:
    bot = Copilot(config=FROZEN)
    res = bot.ask(str(ROWS["g44-synonym"]["query"]))  # "Can you reboot payments-worker?"
    assert res.decision is not Decision.ANSWER
    assert not (res.grounding and res.grounding.semantic_rescued)


def test_semantic_grounding_alone_can_be_toggled() -> None:
    q = "What is the health of the payments-api?"
    on = Copilot(config=FROZEN).ask(q)
    off = Copilot(config=replace(FROZEN, embed_semantic_grounding=False)).ask(q)
    assert on.decision is Decision.ANSWER and on.grounding.semantic_rescued == ["health"]
    assert off.decision is Decision.REFUSE_UNGROUNDED
