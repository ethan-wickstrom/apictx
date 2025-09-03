from __future__ import annotations

from pathlib import Path
import libcst as cst

from apictx.extract import extract_module
from apictx.models import FunctionSymbol, Symbol
from apictx.pipeline import run_pipeline, query_index
from apictx.result import Result
from apictx.errors import Error


def test_docstring_parsing_numpy_and_rest() -> None:
    doc = (
        "def f(x):\n"
        "    \"\"\"Summary.\n\n"
        "    Raises\n"
        "    ------\n"
        "    MyErr: some details\n\n"
        "    Also see: :raises OtherErr: more details\n\n"
        "    Deprecated: use g() instead.\n"
        "    \"\"\"\n"
        "    pass\n"
    )
    mod = cst.parse_module(doc)
    syms: tuple[Symbol, ...] = extract_module(mod, "pkg.m")
    f = next(s for s in syms if isinstance(s, FunctionSymbol) and s.fqn.endswith(".f"))
    assert any(name in f.raises for name in ("MyErr", "OtherErr"))
    assert f.deprecated is True


def test_query_filters(tmp_path: Path) -> None:
    root = tmp_path / "lib"
    root.mkdir()
    (root / "a.py").write_text(
        "class C:\n    def pub(self):\n        pass\n\n    def _priv(self):\n        pass\n\n\n@staticmethod\ndef util():\n    pass\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    res: Result[None, tuple[Error, ...]] = run_pipeline(root, "lib", "0.0.1", "deadbeef", 1, out)
    assert res.ok

    # approx query for "pub" functions, filter by kind and visibility
    got = query_index(out / "index.sqlite3", approx="pub", limit=5, kind="function", visibility="public")
    assert got.ok and got.value is not None
    assert all(obj["kind"] == "function" for obj in got.value)
    assert all(obj.get("visibility") == "public" for obj in got.value)
