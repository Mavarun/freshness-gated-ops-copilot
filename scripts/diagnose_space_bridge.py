"""Post-hoc: which SE *train* sentences does each space-bridge arm newly flag, and why? (Nov 4)

    python scripts/diagnose_space_bridge.py --raw-dir /tmp/se_qa_raw

Reads only SE train sentences (the calibration split); the SE test split is never opened here. For
every sentence flagged by an arm but not by the shipped detector it records the cue noun, the redacted
span, the bridge words used, and a coarse label. Labels are assigned by rule, not by hand:

* ``all_eff_4plus`` / ``all_eff_3``: every content word (the span minus its bridge words and any number) is on
  the EFF large list, and there are 4+ / exactly 3 of them: the shape a list-based generator emits;
* ``not_all_eff``: at least one content word is off the list (``managers``, ``outcomes``): prose.

Writes ``artifacts/space_bridge_diagnosis.{json,md}``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import passphrase_space_protocol as F  # noqa: E402
from ops_copilot.passphrase import FUNCTION_WORDS, generator_words  # noqa: E402

ART = ROOT / "artifacts"


def new_flags(raw_dir: Path) -> dict:
    from ops_copilot import passphrase_digit_protocol as D

    sents = D.se_material(raw_dir)["train"]["sentences"]
    base = F.detector(F.SHIPPED)
    out: dict = {"sentences": len(sents), "arms": {}}
    for arm in F.arms()[1:]:
        det = F.detector(arm)
        rows, labels, bridges = [], Counter(), Counter()
        for s in sents:
            if base.search(s) is not None:
                continue
            m = det.search(s)
            if m is None:
                continue
            span = m.group()
            toks = [w for w in re.findall(r"[A-Za-z]+", span.lower())]
            used = [w for w in toks if w in FUNCTION_WORDS]
            content = [w for w in toks if w not in FUNCTION_WORDS]
            gen = generator_words()
            if content and all(w in gen for w in content):
                label = "all_eff_4plus" if len(content) >= 4 else "all_eff_3" if len(content) == 3 else "not_all_eff"
            else:
                label = "not_all_eff"
            labels[label] += 1
            bridges.update(used)
            rows.append({"span": span, "label": label, "bridge_words": used})
        out["arms"][F.arm_name(arm)] = {
            "new_sentence_flags": len(rows), "labels": dict(labels),
            "bridge_words": dict(bridges.most_common(12)), "examples": rows[:15],
        }
    return out


def render(out: dict) -> str:
    lines = [f"# Space-bridge: SE train sentences newly flagged ({out['sentences']:,} sentences)", "",
             "Post-hoc, SE train only. `all_eff_*` means every non-bridge word is on the EFF list.", ""]
    for arm, d in out["arms"].items():
        lines += [f"## `{arm}`: {d['new_sentence_flags']} new flags", "",
                  "labels: " + ", ".join(f"{k} {v}" for k, v in sorted(d["labels"].items())),
                  "", "bridge words used: " + ", ".join(f"{k} {v}" for k, v in d["bridge_words"].items()), ""]
        lines += [f"- `{r['span']}` ({r['label']})" for r in d["examples"]] + [""]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, required=True)
    out = new_flags(ap.parse_args().raw_dir)
    (ART / "space_bridge_diagnosis.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (ART / "space_bridge_diagnosis.md").write_text(render(out))
    print(render(out))


if __name__ == "__main__":
    main()
