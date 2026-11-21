"""Every number in the README's contact-channel section comes from the committed artifacts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
HEAD = "## Contact-channel authorization (2026-11-21)"
NEXT = "## Hazard scan scope (2026-11-20, second slice)"
SECTION = README[README.index(HEAD):README.index(NEXT)]
A = json.loads((ROOT / "artifacts" / "contact_channel.json").read_text())
P = json.loads((ROOT / "artifacts" / "contact_channel_posthoc.json").read_text())
D4 = json.loads((ROOT / "artifacts" / "synonym_dev4_eval.json").read_text())


def _arrow(d):
    return f"{d['phrases']} → {d['channel']}"


def test_first_section_and_head_numbers():
    heads = [h for h in README.splitlines() if h.startswith("## ")]
    assert heads[0].startswith(HEAD) and heads[1].startswith(NEXT)
    R, C = A["regression"], A["confirm"]
    assert f"hazard misfires {_arrow(R['misfires'])} on {R['n']} rows" in heads[0]
    assert f"confirm set {_arrow(C['correct'])} of {C['n']}" in heads[0]
    assert A["checks"]["ship"] and "**`channel` ships**" in SECTION


def test_results_table():
    R, C = A["regression"], A["confirm"]
    assert (f"| {R['n']} regression rows, phrases → channel | {_arrow(R['correct'])} | "
            f"{_arrow(R['misfires'])} | {_arrow(R['answered'])} |") in SECTION
    assert (f"| {C['n']}-row confirm set, phrases → channel | {_arrow(C['correct'])} | "
            f"{_arrow(C['misfires'])} | {_arrow(C['answered'])} |") in SECTION


def test_changed_rows_and_confirm_prose():
    ch = A["regression"]["changed"]
    assert f"On the regression rows, {len(ch)} change" in SECTION
    for r in ch:
        assert f"`{r['id']}`" in SECTION
    rows = {r["id"]: r for r in A["confirm"]["rows"]}
    fixed = [i for i, r in rows.items() if r["channel"] == r["expect"] != r["phrases"]]
    lost = [i for i, r in rows.items() if r["phrases"] == r["expect"] != r["channel"]]
    assert f"{len(fixed)} rows are fixed" in SECTION and lost == ["f-cc12"]
    assert "`f-cc12` (`owner email`) moves\nfrom REFUSE_PII to REFUSE_UNGROUNDED" in SECTION


def test_dev4_live_numbers():
    d = D4["halves"]["confirm"]["default (shipped)"]
    assert f"dev4 confirm 7 → {d['correct']} of {d['n']}" in SECTION
    assert f"2 → {d['answer_correct']} of {d['n_answer']}" in SECTION


def test_posthoc_prose():
    g = P["wrong_by_gate"]
    assert f"All {len(P['wrong_under_channel'])} confirm rows still wrong" in SECTION
    assert g == {"grounding": 6, "pii": 0} and "None of them is a PII refusal" in SECTION
    missing = [", ".join(next(x for x in P["rows"] if x["id"] == i)["channel"]["missing"]) for i in P["wrong_under_channel"]]
    assert missing == ["inbox, address", "mailbox", "inbox", "telephone", "numbers", "owner"]
