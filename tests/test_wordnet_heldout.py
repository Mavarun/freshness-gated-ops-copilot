"""Pins the WordNet held-out decision and the build's independence from the eval."""

import ast
import json
from pathlib import Path

from ops_copilot.config import CopilotConfig

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "wordnet_sense_heldout.json"
EVAL_MODULES = {"synonym_split", "paraphrase_set", "perturb", "robustness", "eval"}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module.split(".")[-1])
        elif isinstance(node, ast.Import):
            out.update(a.name.split(".")[-1] for a in node.names)
    return out


def test_table_build_never_reads_eval_modules():
    for p in (ROOT / "src" / "ops_copilot" / "wordnet_senses.py",
              ROOT / "scripts" / "build_wordnet_neighbours.py"):
        assert not (_imports(p) & EVAL_MODULES), p.name


def test_decision_ships_off_and_chosen_equals_off():
    d = json.loads(ART.read_text())
    assert d["decision"] == {
        "decided_on": "chosen",
        "no_harm_rule_passed": True,
        "heldout_gain": False,
        "default_on": False,
    }
    assert d["chosen"]["changed_vs_off"] == []
    assert d["chosen"]["flips"] == d["off"]["flips"]
    assert CopilotConfig().use_wordnet_noun_sense is False


def test_chosen_arm_matches_the_calibration_and_config_defaults():
    d = json.loads(ART.read_text())
    cal = json.loads((ROOT / "artifacts" / "wordnet_sense_calibration.json").read_text())["chosen"]
    cfg = CopilotConfig()
    assert d["chosen"]["setting"] == {
        "scope": cal["scope"], "path": cal["max_path"], "fan": cal["max_fanout"], "n": cal["max_neighbours"]
    }
    assert (cfg.wordnet_scope, cfg.wordnet_max_path, cfg.wordnet_max_neighbours) == (
        cal["scope"], cal["max_path"], cal["max_neighbours"]
    )


def test_no_arm_fails_open_or_leaks():
    d = json.loads(ART.read_text())
    for name, arm in d.items():
        if name == "decision":
            continue
        assert arm["clean_accuracy"] == 1.0, name
        assert (arm["n_fail_open"], arm["n_spurious_write"], arm["n_raw_pii_outputs"]) == (0, 0, 0), name
