from __future__ import annotations

from pathlib import Path
import json

from apictx.pipeline import run_pipeline
from apictx.result import Result
from apictx.errors import Error


def test_pipeline_emits_validation(tmp_path: Path) -> None:
    pkg: Path = tmp_path / "mathx"
    pkg.mkdir()
    mod: Path = pkg / "add.py"
    mod.write_text("def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8")
    outdir: Path = tmp_path / "out"
    res: Result[None, tuple[Error, ...]] = run_pipeline(pkg, "mathx", "0.1.0", "", 1, outdir)
    assert res.ok
    report_path: Path = outdir / "validation.json"
    data: dict[str, object] = json.loads(report_path.read_text(encoding="utf-8"))
    assert data["symbol_count"] == 2
