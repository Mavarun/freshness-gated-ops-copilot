#!/usr/bin/env python3
"""One-shot held-out go / no-go for the noun gloss-sense read backoff.

Pre-registered rule (set before this run, see README): turn the flag on by
default only if held-out accuracy and held-out ANSWER rows do not fall, there
are no fail-open / spurious-write / raw-PII outputs, and clean stays 1.000.
Writes artifacts/noun_gloss_sense_heldout.json.
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.robustness import run_robustness  # noqa: E402


def summarise(cfg: CopilotConfig) -> dict:
    d = run_robustness(config=cfg).as_dict(flip_detail=False)
    return {
        "clean_accuracy": d["clean_accuracy"],
        "perturbed_accuracy": d["perturbed_accuracy"],
        "per_synonym_split": {k: v for k, v in d["per_synonym_split"].items()},
        "n_fail_open": d["n_fail_open"],
        "n_spurious_write": d["n_spurious_write"],
        "n_raw_pii_outputs": d["n_raw_pii_outputs"],
    }


def _use_seed(path: Path) -> None:
    """Point the noun sense graph at another seed file (clears the caches)."""
    import ops_copilot.noun_gloss_sense as ngs

    ngs.DEFAULT_OPS_NOUN_SEED = path
    ngs.all_senses.cache_clear()
    ngs.build_sense_graph.cache_clear()
    ngs._senses_by_word.cache_clear()


def main() -> int:
    base = CopilotConfig()
    leaky = ROOT / "data" / "wiktionary" / "ops_noun_senses_leaky_reference.json"
    clean = ROOT / "data" / "wiktionary" / "ops_noun_senses.json"
    out = {"off": summarise(replace(base, use_noun_gloss_sense=False))}
    _use_seed(clean)
    out["on_clean_seed"] = summarise(replace(base, use_noun_gloss_sense=True))
    # Reference only: seed that authors the held-out words lag / health / state.
    _use_seed(leaky)
    out["on_leaky_seed_reference_only"] = summarise(replace(base, use_noun_gloss_sense=True))
    p = ROOT / "artifacts" / "noun_gloss_sense_heldout.json"
    p.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
