"""Calibrate and evaluate the random-token secret detector; write its artifacts.

    python scripts/run_secret_entropy_eval.py

Writes ``artifacts/secret_entropy_eval.{json,md}``. Offline and seeded: the
character model is trained on committed outside word lists only.

Gating (exit 1): any repo-text negative flagged, any dev-family secret missed,
or the re-run calibration landing on a threshold other than the committed
default. Out-of-calibration families (e.g. pronounceable) are report-only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.secret_entropy import (  # noqa: E402
    DEFAULT_THRESHOLD,
    MAX_CALIB_FPR,
    calibrate_threshold,
    vocabulary_split,
)
from ops_copilot.secret_entropy_eval import run_secret_entropy_eval  # noqa: E402

ART = ROOT / "artifacts"


def render_md(cal: dict, ev: dict, n_train: int, n_calib: int) -> str:
    lines = [
        "# Random-token secret detector (no recognisable format)",
        "",
        f"Character trigram model trained on {n_train:,} committed outside words (counter-fitted "
        "table, Stack Exchange QA question words, Wiktionary computing senses, Stack Exchange tag "
        f"names); {n_calib:,} held-out words (salted hash) are calibration negatives together with "
        "identifier-style compounds of them. Score = bits per character of the worst `-_./:` piece "
        "of a token of 12+ characters.",
        "",
        "## Calibration (dev families base62 / hex / lower_alnum, seed 7)",
        "",
        f"- lowest threshold with calibration FPR <= {MAX_CALIB_FPR}: **{cal['lo']}**",
        f"- highest threshold that still catches every dev secret: **{cal['hi']}**",
        f"- chosen (midpoint, rule fixed before the test run): **{cal['threshold']}** "
        f"(committed default {DEFAULT_THRESHOLD})",
        f"- {cal['n_negatives']:,} calibration negatives, {cal['n_positives']} dev secrets",
        "",
        f"## Test: synthetic secrets (seed {ev['seed']}, never real)",
        "",
        "| family | in calibration | n | PR #16 patterns | detector | PR #16 + detector |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for f, r in ev["families"].items():
        lines.append(
            f"| {f} | {'yes' if r['dev_family'] else 'no'} | {r['n']} | {r['pr16']} | {r['detector']} | {r['now']} |"
        )
    lines += [
        "",
        f"Recall over all families: PR #16 {ev['recall']['pr16']:.3f} -> now {ev['recall']['now']:.3f}.",
        "",
        "## Test: false positives on repo text the model never saw",
        "",
        "| text | tokens | candidates (12+ chars) | already shape-redacted | flagged | flagged tokens |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for label, r in ev["negatives"].items():
        flagged = ", ".join(f"`{t}`" for t in r["flagged"]) or "-"
        lines.append(
            f"| {label} | {r['n_tokens']} | {r['n_candidates']} | {r['n_already_shape_redacted']} | {r['n_flagged']} | {flagged} |"
        )
    lines += [
        "",
        f"False-positive rate on candidates: {ev['n_negative_flagged']}/{ev['n_negative_candidates']} "
        f"({ev['false_positive_rate']:.3f}).",
        "",
        "## Planted documents (should be caught)",
        "",
    ]
    for label, r in ev["planted"].items():
        flagged = ", ".join(f"`{t}`" for t in r["flagged"]) or "-"
        lines.append(f"- {label}: {r['n_candidates']} candidates; flagged by the detector: {flagged}")
    lines += ["", "Score examples (bits/char): " + ", ".join(f"`{k}` {v}" for k, v in ev["score_examples"].items()), ""]
    return "\n".join(lines)


def gate_failures(cal: dict, ev: dict) -> list[str]:
    """Reasons this run should fail CI (empty list = pass)."""
    out: list[str] = []
    if ev["n_negative_flagged"]:
        out.append(f"{ev['n_negative_flagged']} repo-text negative(s) flagged as random tokens")
    for fam, r in ev["families"].items():
        if r["dev_family"] and r["now"] < r["n"]:
            out.append(f"dev family {fam}: {r['now']}/{r['n']} secrets redacted")
    if abs(cal["threshold"] - DEFAULT_THRESHOLD) > 1e-9:
        out.append(f"calibrated threshold {cal['threshold']} != committed default {DEFAULT_THRESHOLD}")
    return out


def main() -> int:
    cal = calibrate_threshold()
    ev = run_secret_entropy_eval()
    train, calib = vocabulary_split()
    ART.mkdir(exist_ok=True)
    (ART / "secret_entropy_eval.json").write_text(
        json.dumps({"calibration": cal, "eval": ev, "n_train_words": len(train), "n_calib_words": len(calib)}, indent=2)
        + "\n"
    )
    (ART / "secret_entropy_eval.md").write_text(render_md(cal, ev, len(train), len(calib)))
    print(f"threshold {cal['threshold']} | recall {ev['recall']['pr16']:.3f} -> {ev['recall']['now']:.3f} | "
          f"FPR {ev['n_negative_flagged']}/{ev['n_negative_candidates']}")
    failures = gate_failures(cal, ev)
    for reason in failures:
        print(f"GATE FAIL: {reason}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
