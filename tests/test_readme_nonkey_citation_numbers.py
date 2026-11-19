"""Numbers quoted in the README's Nov 17 non-key ship section match the committed artifacts."""

import json
from pathlib import Path

from ops_copilot.config import CopilotConfig

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
HEAD = "## Non-key rule ships on (2026-11-17)"


def _section() -> str:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    start = text.index(HEAD)
    return text[start: text.index("\n## ", start + 5)]


def _j(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def test_it_follows_the_hazard_section():
    heads = [h for h in (ROOT / "README.md").read_text(encoding="utf-8").splitlines() if h.startswith("## ")]
    assert heads[0].startswith("## Hazard scan on ungrounded refusals (2026-11-20)")
    assert heads[1].startswith(HEAD)


def test_headline_and_ship_call():
    c, s = _j("nonkey_citation_confirm.json"), _section()
    first = s.splitlines()[0]
    sh, a = c["arms"]["shipped"], c["arms"]["all_hyphen"]
    assert f"{sh['rates']['null_pass_rate']:.3f} → {a['rates']['null_pass_rate']:.3f}" in first
    assert f"{c['citation']['all_hyphen']['budget_lost']} right-evidence answer lost (budget 2)" in first
    assert c["ships"] is True and "now ships on" in first and "held-out ANSWER stays 0 of 9" in first
    cfg = CopilotConfig()
    assert (cfg.grounding_nonkey_rule, cfg.grounding_nonkey_parts) == ("all", "hyphen")


def test_calibration_table():
    cal, s = _j("nonkey_citation_calibration.json"), _section()
    arms, cit = cal["arms"], cal["citation"]
    ref = arms["shipped"]
    assert f"| rule off | {ref['passed']} | {ref['rates']['null_pass_rate']:.3f} | 0 | 0 | 0 | 0 |" in s
    for label, n in (("`all_hyphen` (picked)", "all_hyphen"), ("`all` (Nov 9, reference)", "all")):
        a, c = arms[n], cit[n]
        row = (f"| {label} | {a['passed']} | {a['rates']['null_pass_rate']:.3f} | {ref['answered'] - a['answered']} | "
               f"{len(c['fixed'])} | {c['budget_lost']} | {len(c['new_wrong'])} |")
        assert row in s, n
    assert cal["picked"] == "all_hyphen"


def test_confirm_table_and_text():
    c, s = _j("nonkey_citation_confirm.json"), _section()
    for label, n in (("rule off", "shipped"), ("`all_hyphen`", "all_hyphen")):
        a = c["arms"][n]
        rate = f"{a['rates']['null_pass_rate']:.3f}" if n == "shipped" else f"**{a['rates']['null_pass_rate']:.3f}**"
        traps = f"{len(c['topic_trap_opens'][n])} of 16"
        traps = traps if n == "shipped" else f"**{traps}**"
        budget = c["citation"][n]["budget_lost"] if n in c["citation"] else 0
        wrong = len(c["citation"][n]["new_wrong"]) if n in c["citation"] else 0
        row = (f"| {label} | {c['swaps']} | {a['passed']} | {rate} | {a['answered']} of {a['n_answer_rows']} | "
               f"{budget} | {wrong} | {traps} | {len(c['attribute_trap_opens'][n])} of 114 |")
        assert row in s, n
    sh, a = c["arms"]["shipped"]["rates"]["null_pass_rate"], c["arms"]["all_hyphen"]["rates"]["null_pass_rate"]
    assert f"drops by {sh - a:.3f} ({round(100 * (sh - a) / sh)}% relative" in s
    assert c["citation"]["all_hyphen"]["lost"] == ["d9-15"] and "`d9-15`" in s
    assert f"from {c['dev9_answered']['shipped']} to\n{c['dev9_answered']['all_hyphen']} of 32" in s


def test_live_report_table():
    # The "after" column is the Nov 17 shipped default. The 2026-11-20 hazard scan moved
    # the dev2 / dev5 / dev6 / 203-row reports again (README "Hazard scan" section), so
    # those cells are pinned to the Nov 17 values, re-scored here with the scan off.
    s = _section()
    d8, rep = _j("dev8_eval.json"), _j("swap_null_report.json")
    assert f"| 42 of 384 | {rep['passed']} of {rep['swaps']} |" in s
    sh, pre = d8["arms"]["shipped"], d8["arms"]["rule off (pre-Nov 17)"]
    assert (f"| {len(pre['traps_open'])} of 16 / {pre['answered']} of 32 | "
            f"{len(sh['traps_open'])} of 16 / {sh['answered']} of 32 |") in s
    from ops_copilot.config import pre_hazard_config
    from ops_copilot.robustness import run_robustness
    from ops_copilot.synonym_dev2 import half as dev2_half
    from ops_copilot.synonym_dev5 import half as dev5_half
    from ops_copilot.synonym_dev6 import load_dev6
    from ops_copilot.wordnet_dev2 import score_rows

    cfg = pre_hazard_config()
    assert f"| 9 of 24 | {score_rows(cfg, dev5_half('tune'))['correct']} of 24 |" in s
    assert f"| 20 of 45 | {score_rows(cfg, load_dev6())['correct']} of 45 |" in s
    assert f"| 14 of 22 | {score_rows(cfg, dev2_half('calib'))['correct']} of 22 |" in s
    rob = run_robustness(config=cfg)
    assert f"| 0.892 | {rob.perturbed_accuracy:.3f} |" in s
    assert f"| 0.514 | {rob.per_synonym_split['heldout']['perturbed_accuracy']:.3f} |" in s

def test_posthoc_numbers():
    p, s = _j("nonkey_citation_posthoc.json"), _section()
    assert f"{len(p['changed'])} of {p['n_rows']} eval rows change decision" in s
    e = p["effects"]
    assert f"**fixed {e['fixed'] + e['wrong-evidence answer refused']}**" in s
    assert f"**lost {e['lost answer'] + e['lost answer (no evidence label)']}**" in s
    assert f"**refused under another gate {e['refused under another gate']}**" in s
    g = p["dev9_wordy_gates"]["shipped"]
    assert f"Of the {32 - g['ANSWER']} dev9 wordy rows" in s
    assert f"{g['REFUSE_DISAGREE']}\nretriever disagreements, {g['REFUSE_STALE']} stale sources and {g['REFUSE_UNGROUNDED'] - 1} key-gate refusals" in s
