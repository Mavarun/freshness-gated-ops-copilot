"""WordNet calibration: grid shape, selection rule, and no held-out rows scored."""

from ops_copilot import wordnet_sense_calibration as cal


def test_grid_is_fixed_and_fanout_only_varies_for_siblings():
    grid = cal.grid_settings()
    assert len(grid) == 20
    assert {g["max_fanout"] for g in grid if g["max_path"] < 2} == {0}
    assert {g["scope"] for g in grid} == {"known", "all"}


def test_selection_prefers_safe_then_dev_then_most_conservative():
    base = {"dev_synonym_accuracy": 0.8, "dev_answer_correct": 3}
    rows = [
        {**base, "safe": True, "scope": "known", "max_path": 2, "max_fanout": 25, "max_neighbours": 1},
        {**base, "safe": True, "scope": "known", "max_path": 0, "max_fanout": 0, "max_neighbours": 1},
        {**base, "safe": False, "scope": "all", "max_path": 0, "max_fanout": 0, "max_neighbours": 1,
         "dev_synonym_accuracy": 0.9},
    ]
    rows.sort(key=cal.selection_key)
    assert rows[0]["max_path"] == 0 and rows[0]["safe"]
    better = {**rows[0], "max_path": 2, "dev_synonym_accuracy": 0.9}
    assert sorted([rows[0], better], key=cal.selection_key)[0] is better


def test_dev_scoring_never_touches_heldout_rows(monkeypatch):
    seen = []
    from ops_copilot import noun_gloss_sense_calibration as ngc
    from ops_copilot.synonym_split import load_split

    split = load_split()

    class Bot:
        def __init__(self, config=None):
            pass

        def ask(self, q):
            seen.append(q)

            class D:
                value = "ANSWER"

            class R:
                decision = D

            return R

    monkeypatch.setattr(ngc, "Copilot", Bot)
    out = ngc._dev_synonym_accuracy(None)
    assert out["n_dev"] == 15
    dev_queries = {
        r["query"]
        for r in ngc.load_paraphrase_set()
        if r["perturbation"] == "synonym" and split["rows"][r["id"]]["split"] == "dev"
    }
    assert set(seen) == dev_queries
