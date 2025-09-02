from __future__ import annotations

from pathlib import Path

from apictx.pipeline import run_pipeline
from apictx.result import Result
from apictx.errors import Error


def test_symbols_jsonl_deterministic(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    root.mkdir()
    (root / "a.py").write_text("def a():\n    pass\n", encoding="utf-8")
    (root / "b.py").write_text("class B:\n    def m(self):\n        pass\n", encoding="utf-8")

    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"

    r1: Result[None, tuple[Error, ...]] = run_pipeline(root, "lib", "0.0.1", "deadbeef", 1, out1)
    r2: Result[None, tuple[Error, ...]] = run_pipeline(root, "lib", "0.0.1", "deadbeef", 1, out2)
    assert r1.ok and r2.ok

    s1 = (out1 / "symbols.jsonl").read_text(encoding="utf-8")
    s2 = (out2 / "symbols.jsonl").read_text(encoding="utf-8")
    assert s1 == s2
