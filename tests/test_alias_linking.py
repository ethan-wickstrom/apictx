from __future__ import annotations

from pathlib import Path

from apictx.pipeline import run_pipeline
from apictx.result import Result
from apictx.errors import Error


def test_alias_based_class_linking(tmp_path: Path) -> None:
    root: Path = tmp_path / "pkg"
    root.mkdir()
    (root / "base.py").write_text("class Base:\n    pass\n", encoding="utf-8")
    (root / "sub.py").write_text(
        "from base import Base as Alias\n\nclass Sub(Alias):\n    pass\n",
        encoding="utf-8",
    )

    out: Path = tmp_path / "out"
    res: Result[None, tuple[Error, ...]] = run_pipeline(
        root, "pkg", "0.0.1", "abc", 1, out
    )
    assert res.ok

    # validate that subclass links to the base via alias
    import json

    data = [
        json.loads(line)
        for line in (out / "symbols.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    sub = next(obj for obj in data if obj["fqn"] == "pkg.sub.Sub")
    assert "pkg.base.Base" in tuple(sub.get("base_fqns", []))
