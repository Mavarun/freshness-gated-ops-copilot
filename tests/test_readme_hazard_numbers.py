"""Numbers quoted in the README's Nov 20 hazard-scan section match the committed artifacts."""

import json
from collections import Counter
from pathlib import Path

from ops_copilot.config import CopilotConfig

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
HEAD = "## Hazard scan on ungrounded refusals (2026-11-20)"


def _section() -> str:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    start = text.index(HEAD)
    return text[start: text.index("\n## ", start + 5)]


def _j(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def test_it_directly_precedes_the_nonkey_section():
    heads = [h for h in (ROOT / "README.md").read_text(encoding="utf-8").splitlines() if h.startswith("## ")]
    i = next(k for k, h in enumerate(heads) if h.startswith(HEAD))
    assert heads[i + 1].startswith("## Non-key rule ships on (2026-11-17)")


def test_effect_table_and_ship_call():
    h, s = _j("hazard_scan.json"), _section()
    eff = h["effects"]
    fixed = [c for c in h["changed"] if c["effect"] == "fixed"]
    gates = Counter(c["on"] for c in fixed)
    assert f"({gates['REFUSE_CANARY']} canary, {gates['REFUSE_PII']} PII) | {eff['fixed']} |" in s
    assert f"instead of `REFUSE_UNGROUNDED` | {eff['still wrong']} |" in s
    assert eff.get("broke", 0) == 0 and eff.get("answer change", 0) == 0
    assert h["checks"]["ship"] and "**it ships on**" in s and CopilotConfig().hazard_scan_on_ungrounded
    assert f"({h['n_rows']} rows)" in s.replace("\n   ", " ")
    off_topic = [c["id"] for c in h["changed"] if c["expect"] == "REFUSE_NO_EVIDENCE"]
    assert len(off_topic) == 3 and "three of them" in s
    vault = [c for c in h["changed"] if c["expect"] == "ANSWER" and "vault-transit" in c["query"]]
    assert len(vault) == 7 and "The other seven" in s


def test_live_report_table():
    s = _section()
    rob, d2, d5, d6, d7, fr = (_j("robustness_metrics.json"), _j("synonym_dev2_eval.json"), _j("synonym_dev5_eval.json"),
                               _j("synonym_dev6_eval.json"), _j("synonym_dev7_eval.json"), _j("synonym_fresh_eval.json"))
    assert f"| 0.887 | {rob['perturbed_accuracy']:.3f} |" in s
    held = rob["per_synonym_split"]["heldout"]
    assert f"| 0.486 | {held['perturbed_accuracy']:.3f} |" in s
    assert held["by_gate"]["ANSWER"]["correct"] == 0
    cells = (d2["halves"]["calib"]["default (shipped)"]["correct"], d5["tune_default"]["correct"],
             d6["default"]["correct"], d7["default"]["tune"]["correct"])
    assert f"| 13 / 8 / 19 / 5 | {' / '.join(map(str, cells))} |" in s
    off = fr["configs"]["default (word-vector backoff off; = PR #14)"]
    assert f"| 7 | {off['n'] - len(off['wrong'])} |" in s
