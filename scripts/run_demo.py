#!/usr/bin/env python3
"""Run a handful of queries that exercise every policy decision."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import Copilot, EVAL_CLOCK  # noqa: E402


DEMO_QUERIES = [
    "What is the current checkout p99 latency?",
    "Who is the primary on-call right now?",
    "What is the Redis maxmemory-policy?",
    "How do we run the blue-green deploy procedure?",
    "How do I reset the SAP payroll connector?",
    "What is the rollback procedure for the checkout_retry feature flag?",
    "What millicore CPU request is configured on checkout-api?",
]


def main() -> None:
    bot = Copilot()
    print(f"clock={EVAL_CLOCK.isoformat()}  sla={bot.config.max_age_hours:g}h")
    print(f"corpus={len(bot.corpus.docs)} docs / {len(bot.corpus.chunks)} chunks")
    print("-" * 78)
    for query in DEMO_QUERIES:
        result = bot.ask(query)
        ids = ", ".join(c.doc_id for c in result.retrieved) or "-"
        ages = ", ".join(f"{c.age_hours:.1f}" for c in result.retrieved) or "-"
        print(f"Q: {query}")
        print(f"   decision={result.decision.value}")
        print(f"   reason={result.reason}")
        print(f"   retrieved=[{ids}] ages_h=[{ages}]")
        print(f"   latency_ms={result.latency_ms:.2f}  cost={result.approx_cost_units:.2f}")
        print(f"   answer={result.answer}")
        print("-" * 78)


if __name__ == "__main__":
    main()
