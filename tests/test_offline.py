"""The test suite and the shipped package run without the network."""

from __future__ import annotations

import ast
import socket
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NETWORK_MODULES = {"urllib.request", "http.client", "requests", "httpx", "socket"}
FETCH_SCRIPTS = {"fetch_stackexchange_qa", "fetch_tag_synonyms"}


def _source(path: Path) -> str:
    # eval.py execs the _eval_part*.py fragments joined; check them that way.
    if path.name == "eval.py" and path.parent.name == "ops_copilot":
        return path.read_text() + "".join(
            path.with_name(f"_eval_part{i}.py").read_text() for i in range(3)
        )
    return path.read_text()


def _python_files(top: str) -> list[Path]:
    return [p for p in (ROOT / top).rglob("*.py") if not p.name.startswith("_eval_part")]


def _imports(path: Path) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(ast.parse(_source(path))):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
    return out


def test_conftest_blocks_internet_connects() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        with pytest.raises(RuntimeError, match="tests must stay offline"):
            s.connect(("127.0.0.1", 9))


def test_package_has_no_network_client() -> None:
    hits = {
        str(p.relative_to(ROOT)): sorted(_imports(p) & NETWORK_MODULES)
        for p in _python_files("src")
        if _imports(p) & NETWORK_MODULES
    }
    assert hits == {}


def test_fetch_scripts_are_never_imported_by_code_or_tests() -> None:
    users = [
        str(p.relative_to(ROOT))
        for top in ("src", "tests", "scripts")
        for p in _python_files(top)
        if any(m.split(".")[-1] in FETCH_SCRIPTS for m in _imports(p))
    ]
    assert users == []


def test_answer_support_model_loads_from_the_committed_table() -> None:
    from ops_copilot.corpus import Corpus
    from ops_copilot.qa_translation import DEFAULT_TABLE, AnswerSupportModel

    assert DEFAULT_TABLE.is_file()
    model = AnswerSupportModel([f"{c.title} {c.text}" for c in Corpus().chunks])
    assert model.candidates("principal")  # read offline, corpus hash verified
