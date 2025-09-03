from __future__ import annotations

from pathlib import Path

from apictx.pipeline import run_pipeline, query_index
from apictx.result import Result
from apictx.errors import Error


def test_query_index_exact_and_approx(tmp_path: Path) -> None:
    root: Path = tmp_path / "libx"
    root.mkdir()
    (root / "__init__.py").write_text("__all__ = []\n", encoding="utf-8")
    (root / "core.py").write_text(
        "class Thing:\n    def do(self):\n        pass\n\n" "def helper():\n    pass\n",
        encoding="utf-8",
    )
    out: Path = tmp_path / "out"
    res: Result[None, tuple[Error, ...]] = run_pipeline(root, "libx", "0.0.1", "deadbeef", 1, out)
    assert res.ok

    # exact
    exact = query_index(out / "index.sqlite3", fqn="libx.core.Thing")
    assert exact.ok and exact.value is not None
    assert any(obj["fqn"] == "libx.core.Thing" for obj in exact.value)

    # approx
    approx = query_index(out / "index.sqlite3", approx="thing", limit=3)
    assert approx.ok and approx.value is not None
    assert any(obj["fqn"].endswith("Thing") for obj in approx.value)

