"""dev9 CI gate (spent 2026-11-17): runs clean and agrees with the one-shot confirm."""

import dataclasses
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def test_step_is_in_the_workflow():
    wf = (ROOT / ".github" / "workflows" / "eval.yml").read_text(encoding="utf-8")
    assert "python scripts/run_dev9_eval.py" in wf and "artifacts/dev9_eval.json" in wf


def test_dev9_report_runs_clean_and_matches_the_confirm():
    r = subprocess.run([sys.executable, str(ROOT / "scripts/run_dev9_eval.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    rep = json.loads((ROOT / "artifacts/dev9_eval.json").read_text(encoding="utf-8"))
    conf = json.loads((ROOT / "artifacts/nonkey_citation_confirm.json").read_text(encoding="utf-8"))
    assert rep["problems"] == [] and rep["heldout_words_in_file"] == [] and rep["rows"] == 48
    sh, pre = rep["arms"]["shipped"], rep["arms"]["rule off (pre-Nov 17)"]
    # the shipped default is the confirm's all_hyphen arm; rule off is its shipped arm
    assert sh["answered"] == conf["dev9_answered"]["all_hyphen"] == 12
    assert pre["answered"] == conf["dev9_answered"]["shipped"] == 13
    assert sh["traps_open"] == conf["topic_trap_opens"]["all_hyphen"] == []
    assert pre["traps_open"] == conf["topic_trap_opens"]["shipped"] == ["d9-t02"]
    assert sh["wrong_evidence"] == pre["wrong_evidence"] == []
    changed = {i for i, d in sh["decisions"].items() if d != pre["decisions"][i]}
    assert changed == {"d9-15", "d9-t02"}


def test_gate_flags_a_trap_open_and_a_wrong_evidence_answer(monkeypatch, tmp_path):
    import run_dev9_eval as G
    from ops_copilot import pipeline
    from ops_copilot.types import Decision

    real_ask = pipeline.Copilot.ask

    def fake_ask(self, query, *a, **k):
        res = real_ask(self, query, *a, **k)
        if query == "Who is the secondary on-call for payments right now?":  # d9-t02
            return dataclasses.replace(res, decision=Decision.ANSWER, cited_ids=["wiki_oncall_now"])
        if query == "Who is the secondary on-call right now?":  # d9-04, labelled wiki_oncall_now
            return dataclasses.replace(res, cited_ids=["rb_checkout_latency"])
        return res

    monkeypatch.setattr(pipeline.Copilot, "ask", fake_ask)
    monkeypatch.setattr(G, "ART", tmp_path)
    assert G.main() == 1
    probs = json.loads((tmp_path / "dev9_eval.json").read_text())["problems"]
    assert any("opens topic traps" in p for p in probs)
    assert any("wrong evidence" in p and "d9-04" in p for p in probs)
