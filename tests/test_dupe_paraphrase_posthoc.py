"""The committed post-hoc reading recomputes, and its helpers behave."""

import json
import subprocess
import sys
from pathlib import Path

from ops_copilot.dupe_paraphrase import DupeParaphraseSense, DupeTable
from ops_copilot.dupe_paraphrase_posthoc import new_swap_passes, pair_coverage, single_word_pairs

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"


def test_single_word_pairs_skip_phrases_and_hyphens():
    assert single_word_pairs(["a->b", "a b->c", "on-call->x", "K->W"]) == [("a", "b"), ("k", "w")]


def _sense():
    table = DupeTable({}, 10, {"wipe": [["erase", 20.0, 5, 0], ["disk", 30.0, 5, 0]],
                                   "erase": [["wipe", 20.0, 5, 0]], "disk": [["wipe", 30.0, 5, 0]]})
    return DupeParaphraseSense(frozenset({"erase", "disk"}), table, min_cross=3, min_g2=10.0, scope="all", max_neighbours=5), table


def test_pair_coverage_counts_gold_and_wrong_tops():
    s, t = _sense()
    cov = pair_coverage({"strict": s}, t, ["erase->wipe", "foo->bar"])
    m = cov["summary"]
    assert m["pairs"] == 2 and m["in_table"] == 1 and m["in_table_key_in_corpus"] == 1
    assert m["strict_gold_passes"] == 1 and m["strict_top_is_wrong"] == 1 and m["strict_top_is_gold"] == 0


def test_new_swap_passes_only_reports_swaps_the_reference_refused():
    s, _ = _sense()
    arm = [{"row": "r", "term": "erase", "word": "wipe"}, {"row": "q", "term": "x", "word": "y"}]
    got = new_swap_passes(arm, [{"row": "q", "term": "x", "word": "y"}], s)
    assert got == [{"row": "r", "term": "erase", "word": "wipe", "mapped": "disk", "mapped_is_term": False}]


def test_committed_reading_recomputes_and_pins_the_facts(tmp_path):
    before = (ART / "dupe_paraphrase_posthoc.json").read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "scripts/run_dupe_paraphrase_posthoc.py")], check=True,
                   capture_output=True)
    assert (ART / "dupe_paraphrase_posthoc.json").read_text(encoding="utf-8") == before
    d = json.loads(before)
    dev, held = d["coverage"]["dev"]["summary"], d["coverage"]["heldout"]["summary"]
    assert (dev["pairs"], dev["in_table"], dev["strict_gold_passes"], dev["strict_top_is_wrong"]) == (54, 6, 2, 15)
    assert (held["pairs"], held["in_table"], held["strict_gold_passes"], held["strict_top_is_wrong"]) == (53, 8, 2, 10)
    w = d["watch"]
    assert w["restart->reboot"]["raw"] == {"g2": 200.913, "cross": 38, "same": 8}
    assert w["restart->reboot"]["key_in_corpus"] is False
    assert all(w[p]["raw"] is None for p in ("restart->bounce", "latency->lag", "status->health", "cadence->frequency"))
    assert [len(d["new_swap_passes"][a]) for a in ("strict_known", "loose_lone", "loose_all")] == [4, 7, 11]
