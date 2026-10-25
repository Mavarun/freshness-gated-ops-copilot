from ops_copilot.passage_null_dev5 import (
    GRID_Q, MAX_ANSWER_LOSS, MAX_NEW_ERRORS, N_CONTROLS, config_for, grid_settings, is_safe_setting, selection_key,
)

CLEAN = {"clean_accuracy": 1.0, "n_fail_open": 0, "n_spurious_write": 0}
ON = {"n_spurious_write": 0, "n_raw_pii": 0}
SW = {"safe": True}


def test_protocol_constants_are_frozen():
    assert GRID_Q == (0.10, 0.20, 0.30, 0.40, 0.50)
    assert (N_CONTROLS, MAX_NEW_ERRORS, MAX_ANSWER_LOSS) == (100, 9, 3)
    assert [s["null_min"] for s in grid_settings()] == list(GRID_Q)
    cfg = config_for({"null_min": 0.3})
    assert cfg.passage_support_null_min == 0.3 and cfg.passage_support_null_controls == 100


def test_safe_rule():
    assert is_safe_setting(CLEAN, ON, [], [], SW, 9, 3)
    assert not is_safe_setting(CLEAN, ON, ["d5-38"], [], SW, 0, 0)
    assert not is_safe_setting(CLEAN, ON, [], ["at-07"], SW, 0, 0)
    assert not is_safe_setting(CLEAN, ON, [], [], SW, 10, 0)
    assert not is_safe_setting(CLEAN, ON, [], [], SW, 4, 4)
    assert not is_safe_setting(CLEAN, ON, [], [], {"safe": False}, 0, 0)
    assert not is_safe_setting({**CLEAN, "clean_accuracy": 0.98}, ON, [], [], SW, 0, 0)


def test_selection_prefers_safe_then_correct_then_answers_then_stricter_q():
    rows = [
        {"safe": False, "calib_correct": 99, "calib_answer_correct": 30, "null_min": 0.1},
        {"safe": True, "calib_correct": 88, "calib_answer_correct": 25, "null_min": 0.3},
        {"safe": True, "calib_correct": 88, "calib_answer_correct": 25, "null_min": 0.4},
        {"safe": True, "calib_correct": 87, "calib_answer_correct": 26, "null_min": 0.5},
    ]
    assert sorted(rows, key=selection_key)[0]["null_min"] == 0.4


def test_v2_grid_is_v1_grid_with_the_sticky_veto():
    from ops_copilot.passage_null_dev5 import grid_settings_v2

    v2 = grid_settings_v2()
    assert [s["null_min"] for s in v2] == list(GRID_Q) and all(s["sticky"] for s in v2)
    assert config_for(v2[0]).passage_support_null_sticky is True
    assert config_for({"null_min": 0.1}).passage_support_null_sticky is False
