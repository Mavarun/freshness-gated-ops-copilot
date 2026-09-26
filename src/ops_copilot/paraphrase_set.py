"""Build / load the perturbed golden set used by the robustness eval.

Each golden case yields one row per perturbation type, keeping the *same*
``expect_decision`` (labels are never re-tuned to recover accuracy) and any
session fields the budget-trap cases need. Perturbations that leave the query
unchanged (e.g. no synonym-map hit) are skipped rather than counted as free
passes. ``source_index`` is the 0-based line of the clean case in
``data/golden/questions.jsonl``.
"""

from __future__ import annotations

import json
from pathlib import Path

from ops_copilot.perturb import DEFAULT_SEED, PERTURBATION_TYPES, perturb

DEFAULT_PARAPHRASE = (
    Path(__file__).resolve().parents[2] / "data" / "golden" / "paraphrase_questions.jsonl"
)
# Golden fields carried verbatim so perturbed rows replay the same scenario.
CARRY_FIELDS: tuple[str, ...] = ("session_id", "seed_session_spent")


def build_paraphrase_set(
    cases: list[dict],
    *,
    seed: int = DEFAULT_SEED,
    kinds: tuple[str, ...] = PERTURBATION_TYPES,
) -> list[dict]:
    rows: list[dict] = []
    for idx, case in enumerate(cases):
        clean = str(case["query"])
        for kind in kinds:
            query = perturb(clean, kind, seed=seed)
            if query == clean:
                continue
            row = {
                "id": f"g{idx:02d}-{kind}",
                "source_index": idx,
                "perturbation": kind,
                "query": query,
                "expect_decision": case["expect_decision"],
            }
            for key in CARRY_FIELDS:
                if key in case:
                    row[key] = case[key]
            rows.append(row)
    return rows


def dump_jsonl(rows: list[dict], path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    out.write_text(text, encoding="utf-8")
    return out


def load_paraphrase_set(path: str | Path | None = None) -> list[dict]:
    src = Path(path) if path else DEFAULT_PARAPHRASE
    rows: list[dict] = []
    with src.open(encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            if not raw.strip():
                continue
            row = json.loads(raw)
            missing = {"query", "expect_decision", "perturbation", "source_index"} - set(row)
            if missing:
                raise ValueError(f"{src}:{line_no}: missing {sorted(missing)}")
            rows.append(row)
    if not rows:
        raise ValueError(f"paraphrase set is empty: {src}")
    return rows
