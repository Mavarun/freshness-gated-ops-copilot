"""Numbers quoted in the README's verified-rewrites section match the committed artifacts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
HEAD = "## Verified did-you-mean rewrites (2026-11-06)"


def _section() -> str:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    start = text.index(HEAD)
    return text[start: text.index("\n## ", start + 5)]


def _j(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def test_it_is_the_newest_section():
    heads = [h for h in (ROOT / "README.md").read_text(encoding="utf-8").splitlines() if h.startswith("## ")]
    # newest until the 2026-11-07 swap null section went above it
    i = next(k for k, h in enumerate(heads) if h.startswith(HEAD))
    assert i >= 1 and heads[i - 1].startswith("## Random one-word swaps")


def test_calibration_rows_match():
    cal, s = _j("rewrite_suggest_calibration.json"), _section()
    assert cal["picked"] == "context_mc2"
    for name in ("idf", "context", "context_mc2", "context_pairs"):
        r = cal["arms"][name]["rates"]
        cells = f"{r['anchor_hit_1']:.3f} | {r['anchor_hit_3']:.3f} | {r['anchor_precision_1']:.3f} | {r['trap_invitation']:.3f} |"
        assert cells in s, name
    null = cal["arms"]["context"]["rates"]["null_verify_rate"]
    assert f"**{100 * null:.1f}%**" in s


def test_confirm_and_posthoc_match():
    c, p, s = _j("rewrite_suggest_confirm.json"), _j("rewrite_suggest_posthoc.json"), _section()
    assert c["ships"] is False and c["arm"] == "context_mc2"
    pooled = c["pooled"]["rates"]
    assert f"| dev7 + fresh | {c['pooled']['n_rescuable']} | {pooled['anchor_hit_3']:.3f} | " in s
    assert f"**{c['heldout']['anchor_hit_3']} of 9**" in s
    held = p["sets"]["heldout"]
    assert f"**{held['context_mc2']['strict_anchor_hit_3']} of 9**" in s
    assert f"gets {held['context_pairs']['strict_anchor_hit_3']} of 9" in s
