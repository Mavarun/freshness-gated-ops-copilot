"""Pre-registered dev2 protocol: grid, rows, safety, selection and confirm rule."""

from ops_copilot import wordnet_dev2 as p
from ops_copilot.synonym_dev2 import half
from ops_copilot.synonym_split import load_split


def test_grid_is_fixed():
    grid = p.grid_settings()
    assert len(grid) == 144
    assert {g["max_fanout"] for g in grid if g["max_path"] < 2} == {0}
    assert {g["max_sense_rank"] for g in grid} == {0, 1, 2}
    assert {g["morphy"] for g in grid} == {False, True}


def test_calibration_rows_exclude_heldout_and_confirm():
    split = load_split()
    rows = p.calibration_rows()
    ids = {r["id"] for r in rows}
    assert not ids & {r["id"] for r in half("confirm")}
    assert all(split["rows"][r["id"]]["split"] == "dev" for r in rows if r["set"] == "dev")
    assert sum(r["set"] == "dev" for r in rows) == 15
    assert sum(r["set"] == "dev2_calib" for r in rows) == 22


def _stats(ok, answer_correct=0, fo=0, sw=0, pii=0):
    return {
        "ok": ok,
        "correct": sum(ok.values()),
        "answer_correct": answer_correct,
        "n_fail_open": fo,
        "n_spurious_write": sw,
        "n_raw_pii": pii,
    }


CLEAN = {"clean_accuracy": 1.0, "n_fail_open": 0, "n_spurious_write": 0}


def test_safe_requires_no_new_error():
    off = _stats({"a": True, "b": False})
    assert p.is_safe(CLEAN, off, _stats({"a": True, "b": True}))
    assert not p.is_safe(CLEAN, off, _stats({"a": False, "b": True}))
    assert not p.is_safe({**CLEAN, "clean_accuracy": 0.98}, off, off)
    assert not p.is_safe(CLEAN, off, _stats({"a": True, "b": True}, fo=1))
    assert p.fixed_rows(off, _stats({"a": True, "b": True})) == ["b"]
    assert p.new_errors(off, _stats({"a": False, "b": False})) == ["a"]


def _row(**kw):
    base = dict(safe=True, calib_correct=10, calib_answer_correct=5, scope="known", max_path=1,
                max_fanout=0, max_neighbours=1, morphy=False, max_sense_rank=1)
    return {**base, **kw}


def test_selection_prefers_safe_then_gain_then_conservative():
    rows = [
        _row(max_sense_rank=0),
        _row(morphy=True),
        _row(scope="lone"),
        _row(),
        _row(safe=False, calib_correct=20),
    ]
    rows.sort(key=p.selection_key)
    assert rows[0] == _row()
    better = _row(scope="all", max_path=2, max_fanout=25, calib_correct=11)
    assert sorted(rows + [better], key=p.selection_key)[0] is better


def _rob(acc=0.5, ans=0, clean=1.0, fo=0):
    return {
        "clean_accuracy": clean,
        "n_fail_open": fo,
        "n_spurious_write": 0,
        "n_raw_pii_outputs": 0,
        "per_synonym_split": {"heldout": {"perturbed_accuracy": acc, "by_gate": {"ANSWER": {"correct": ans}}}},
    }


def test_confirm_rule_needs_a_confirm_gain_and_no_heldout_harm():
    off = _stats({"a": True, "b": False}, answer_correct=1)
    on = _stats({"a": True, "b": True}, answer_correct=2)
    assert p.confirm_decision(off, on, _rob(), _rob())["default_on"]
    assert not p.confirm_decision(off, off, _rob(), _rob())["default_on"]
    assert not p.confirm_decision(off, on, _rob(), _rob(acc=0.4))["default_on"]
    assert not p.confirm_decision(off, on, _rob(), _rob(clean=0.98))["default_on"]
    broke = _stats({"a": False, "b": True}, answer_correct=1)
    d = p.confirm_decision(off, broke, _rob(), _rob())
    assert not d["checks"]["confirm_no_new_error"] and not d["default_on"]
