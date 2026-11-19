"""Every number in the README's hazard-scope section comes from the committed artifacts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text()
HEAD = "## Hazard scan scope (2026-11-20, second slice)"
SECTION = README[README.index(HEAD):README.index("## Hazard scan on ungrounded refusals (2026-11-20)")]
A = json.loads((ROOT / "artifacts" / "hazard_scope.json").read_text())
P = json.loads((ROOT / "artifacts" / "hazard_scope_posthoc.json").read_text())


def test_head_and_checks():
    ch = A["checks"]
    assert README.index(HEAD) < README.index("## Hazard scan on ungrounded refusals (2026-11-20)")
    assert f"removes {ch['misfires_all'] - ch['misfires_covered']} of {ch['misfires_all']} hazard misfires" in SECTION
    assert f"loses {ch['lost_fixes']} must-refuse rows" in SECTION
    assert f"| pass ({ch['answer_changes']}) |" in SECTION
    assert f"({ch['misfires_all']} → {ch['misfires_covered']})" in SECTION
    assert f"same {A['n_rows']} rows" in SECTION


def test_posthoc_table_and_prose():
    for r in P["rows"]:
        assert f"| `{r['id']}` | {r['expect']} | {r['kind']} | {r['coverage']:.3f} |" in SECTION
    cov = {r["id"]: r["coverage"] for r in P["rows"]}
    off = [cov[i] for i in ("d2-36", "d3-41", "d5-41")]
    assert f"{min(off):.2f}-{max(off):.2f}" in SECTION
    assert f"{P['min_lost_fix_coverage']:.2f} and {cov['g37-synonym']:.2f}" in SECTION
    assert f"remove {P['removed_below_min_lost']} misfires" in SECTION
    assert f"misfire ({cov['g50-synonym']:.2f})" in SECTION
