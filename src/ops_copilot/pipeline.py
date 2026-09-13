"""Compose retrieve → support filter → freshness → extractive draft → policy."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from ops_copilot.answer import extractive_answer, render_refusal
from ops_copilot.config import CopilotConfig, parse_clock
from ops_copilot.corpus import Corpus
from ops_copilot.freshness import annotate, fresh_only
from ops_copilot.grounding import Grounder
from ops_copilot.policy import decide
from ops_copilot.retrieve import Retriever
from ops_copilot.source_slas import SourceSlaTable, load_source_slas, resolve_max_age
from ops_copilot.types import Chunk, CopilotResult, Decision


def _cost_units(n_retrieved: int, use_dense: bool) -> float:
    # Synthetic accounting units — no paid LLM in this path.
    return 1.0 + 0.15 * n_retrieved + (0.40 if use_dense else 0.0)


def supporting_chunks(
    query: str,
    chunks: list[Chunk],
    grounder: Grounder,
    threshold: float,
) -> tuple[list[Chunk], float]:
    """Keep chunks whose IDF-weighted query coverage clears ``threshold``."""
    kept: list[Chunk] = []
    best = 0.0
    for chunk in chunks:
        text = f"{chunk.title} {chunk.text}"
        cov, _ = grounder.coverage(query, text)
        keys_ok = grounder.keys_supported(query, text)
        if cov > best:
            best = cov
        if cov >= threshold and keys_ok:
            kept.append(chunk)
    return kept, best


class Copilot:
    """Offline ops copilot with freshness as a first-class gate."""

    def __init__(
        self,
        corpus: Corpus | None = None,
        config: CopilotConfig | None = None,
        *,
        path: str | Path | None = None,
        now: datetime | str | None = None,
        sla_table: SourceSlaTable | None = None,
    ) -> None:
        self.config = config or CopilotConfig()
        self.corpus = corpus or Corpus(path=path, now=now)
        self.retriever = Retriever(self.corpus.chunks, self.config)
        texts = [f"{c.title} {c.text}" for c in self.corpus.chunks]
        self.grounder = Grounder(texts, threshold=self.config.grounding_threshold)
        if sla_table is not None:
            self.sla_table = sla_table
        elif self.config.use_source_slas:
            self.sla_table = load_source_slas(self.config.source_sla_path)
        else:
            self.sla_table = None

    def sla_for(self, source_system: str) -> float:
        """Resolve the max_age_hours that applies to a source_system."""
        return resolve_max_age(
            source_system,
            table=self.sla_table,
            global_default_hours=self.config.max_age_hours,
            use_source_slas=self.config.use_source_slas,
        )

    def ask(self, query: str) -> CopilotResult:
        started = time.perf_counter()
        retrieved = self.retriever.search(query)
        sla_lookup = self.sla_for if self.config.use_source_slas else None
        freshness = annotate(
            retrieved,
            None if sla_lookup else self.config.max_age_hours,
            sla_lookup=sla_lookup,
        )
        supporting, best_support = supporting_chunks(
            query,
            retrieved,
            self.grounder,
            self.config.grounding_threshold,
        )
        fresh_hits = fresh_only(
            supporting,
            None if sla_lookup else self.config.max_age_hours,
            sla_lookup=sla_lookup,
        )

        draft = ""
        grounding = None
        if fresh_hits:
            draft = extractive_answer(
                query,
                fresh_hits,
                max_sentences=self.config.max_answer_sentences,
            )
            grounding = self.grounder.check(query, fresh_hits, draft)
        elif supporting or retrieved:
            # Coverage against whatever we have so the refusal reason is inspectable.
            grounding = self.grounder.check(query, supporting or retrieved, draft)

        policy = decide(
            retrieved,
            freshness,
            supporting,
            fresh_hits,
            grounding,
            max_age_hours=self.config.max_age_hours,
            best_support=best_support,
            support_floor=self.config.support_floor,
            use_source_slas=self.config.use_source_slas,
        )

        if policy.decision is Decision.ANSWER:
            answer = draft
            cited = list(dict.fromkeys(c.doc_id for c in fresh_hits))
        else:
            answer = render_refusal(policy.decision, policy.reason)
            cited = []

        latency_ms = (time.perf_counter() - started) * 1000.0
        return CopilotResult(
            query=query,
            decision=policy.decision,
            reason=policy.reason,
            answer=answer,
            retrieved=retrieved,
            fresh_hits=fresh_hits,
            freshness=freshness,
            grounding=grounding,
            latency_ms=latency_ms,
            approx_cost_units=_cost_units(len(retrieved), self.config.use_dense),
            cited_ids=cited,
        )


def run_query(
    query: str,
    *,
    config: CopilotConfig | None = None,
    path: str | Path | None = None,
    now: datetime | str | None = None,
) -> CopilotResult:
    """Convenience wrapper used by scripts and tests."""
    cfg = config or CopilotConfig()
    copilot = Copilot(config=cfg, path=path, now=parse_clock(now))
    return copilot.ask(query)
