"""Every number in the README's Nov 23 section comes from the committed artifacts."""

import json
from pathlib import Path

from ops_copilot.dupe_paraphrase import DEFAULT_TABLE, load_table

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
HEAD = "## Hazard scan floor and duplicate-question paraphrases (2026-11-23)"
NEXT = "## Contact-channel authorization (2026-11-21)"
SECTION = README[README.index(HEAD):README.index(NEXT)]
FLAT = " ".join(SECTION.split())  # prose wraps across lines
F = json.loads((ROOT / "artifacts" / "hazard_floor.json").read_text())
D = json.loads((ROOT / "artifacts" / "dupe_paraphrase_calibration.json").read_text())
P = json.loads((ROOT / "artifacts" / "dupe_paraphrase_posthoc.json").read_text())


def test_first_section_and_headline():
    heads = [h for h in README.splitlines() if h.startswith("## ")]
    assert heads[3].startswith(HEAD) and heads[4].startswith(NEXT)
    r, c = F["decision"]["regression"], F["decision"]["confirm"]
    assert f"hazard misfires {r['misfires_all']} → {r['misfires_floor']} on {F['regression']['n_rows']} rows" in heads[3]
    assert f"{c['misfires_all']} → {c['misfires_floor']} on a {F['confirm']['n_rows']}-row fresh confirm" in heads[3]
    assert F["decision"]["ship"] and "**`floor` ships**" in SECTION
    assert D["picked"] is None and "**No arm is eligible.**" in SECTION


def test_floor_table():
    for part, label in (("regression", "751 regression rows"), ("confirm", "28-row fresh confirm")):
        d, rows = F["decision"][part], F[part]["rows"]
        n = sum(x["expect"] == x["floor"] for x in rows)
        assert n == sum(x["expect"] == x["all"] for x in rows)
        assert (f"| {label} | {d['misfires_all']} → {d['misfires_floor']} | {d['lost_fixes']} | "
                f"{d['answer_changes']} | {n} → {n} |") in SECTION
    changed = sorted(x["id"] for x in F["regression"]["notable"] if x["all"] != x["floor"])
    assert all(f"`{i}`" in SECTION for i in changed)


def test_dupe_table_and_data_numbers():
    arms = D["arms"]
    for name in ("shipped", "strict_known", "loose_lone", "loose_all"):
        a = arms[name]
        assert f"| {name} | {a['passed']} | {a['answered']} | {a['refuse_opened']} |" in SECTION
    assert arms["strict_lone"]["passed"] == arms["strict_all"]["passed"]
    assert arms["strict_lone"]["answered"] == arms["strict_all"]["answered"]
    a = arms["strict_lone"]
    assert f"| strict_lone / strict_all | {a['passed']} | {a['answered']} | {a['refuse_opened']} |" in SECTION
    assert f"on {D['rows']} rows" in SECTION and f"{D['swaps']} swaps" in SECTION
    t = load_table()
    assert f"{t.n_pairs:,} duplicate title pairs" in SECTION and f"{len(t.rows):,} words" in SECTION
    assert f"({round(DEFAULT_TABLE.stat().st_size / 1024)} KB," in SECTION


def test_posthoc_coverage_numbers():
    dev, held = P["coverage"]["dev"]["summary"], P["coverage"]["heldout"]["summary"]
    assert f"{dev['in_table']} of {dev['pairs']} dev" in FLAT
    assert f"{held['in_table']} of {held['pairs']} held-out" in FLAT
    assert (f"wrong {dev['strict_top_is_wrong']} / {held['strict_top_is_wrong']} times for every "
            f"{dev['strict_gold_passes']} gold hits") in FLAT and dev["strict_gold_passes"] == held["strict_gold_passes"]
