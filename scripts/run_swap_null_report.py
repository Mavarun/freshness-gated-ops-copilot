#!/usr/bin/env python3
"""Swap null control on the shipped default (CI step) -> artifacts/swap_null_report.{json,md}.

Gating: exits non-zero if the shipped default answers more of the calibration swaps
(golden + dev2-dev6, seed 1107) than the last confirmed arm did, or if any mechanism other
than lexical / unsupported reappears. The ceiling was 42 of 384 (known_off, Nov 7); since
the non-key rule shipped on 2026-11-17 it is the all_hyphen calibration count (14 of 384,
artifacts/nonkey_citation_calibration.json). The swap set stays the protocol's 384: it is
drawn with the pre-Nov 17 default, so the rule cannot shrink the set it is scored on.
The residual breakdown (key half, same sentence) is post-hoc and selects nothing.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import swap_null_protocol as P  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402
from ops_copilot.swap_null import build_swaps, file_rows, golden_rows, residual, score  # noqa: E402

ART = ROOT / "artifacts"


def main() -> int:
    cal = json.loads((ART / "nonkey_citation_calibration.json").read_text(encoding="utf-8"))
    ceiling = cal["arms"][cal["picked"]]["passed"]
    bot = Copilot()
    rows = golden_rows() + file_rows(P.CAL_FILES)
    # the swap set is the protocol's: drawn on the rows the pre-flip default answered, with
    # the non-key rule off as in the protocol, so a later default cannot shrink the set
    from ops_copilot.config import pre_nonkey_config

    ref = Copilot(config=pre_nonkey_config(passage_support_known_words=True))
    swaps = build_swaps(rows, ref, draws=P.CAL_DRAWS, seed=P.CAL_SEED)
    sc = score(bot, rows, swaps)
    res = residual(bot, sc.passes)
    cells = Counter((("key" if r["key"] else "non-key"), r["mechanism"],
                     ("same sentence" if r["same_sentence"] else "apart")) for r in res)
    problems = []
    if sc.passed > ceiling:
        problems.append(f"{sc.passed} swaps answered > {ceiling} (Nov 17 non-key calibration record)")
    extra = {m: n for m, n in sc.by_mechanism.items() if n and m not in ("lexical", "unsupported")}
    if extra:
        problems.append(f"rescue mechanisms reappeared: {extra}")
    out = {"swaps": sc.n_swaps, "passed": sc.passed, "ceiling": ceiling, "by_mechanism": sc.by_mechanism,
           "residual": {" / ".join(k): v for k, v in sorted(cells.items())}, "problems": problems,
           "passes": res}
    (ART / "swap_null_report.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    md = ["# Swap null control, shipped default (golden + dev2-dev6, seed 1107)", "",
          f"{sc.passed} of {sc.n_swaps} random one-word swaps answered (ceiling {ceiling}).", "",
          "| swapped word | support | evidence | swaps |", "| :--- | :--- | :--- | ---: |",
          *[f"| {a} | {b} | {c} | {n} |" for (a, b, c), n in sorted(cells.items())], "",
          "Post-hoc reading (selects nothing): `key` = the word is in the key half the gate checks; "
          "`same sentence` = a cited sentence holds it next to another query term.", "",
          "Problems: " + ("; ".join(problems) if problems else "none")]
    (ART / "swap_null_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
