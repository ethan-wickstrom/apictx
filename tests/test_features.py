from __future__ import annotations

import json
from pathlib import Path

import libcst as cst

from apictx.extract import extract_module
from apictx.models import ClassSymbol, ConstantSymbol, FunctionSymbol, Symbol, TypeAliasSymbol
from apictx.pipeline import run_pipeline
from apictx.result import Result
from apictx.errors import Error


def test_extraction_flags_and_aliases() -> None:
    source = (
        "from typing import overload, Protocol, TypeAlias\n"
        "from enum import Enum\n"
        "\n"
        "UserId: TypeAlias = int\n"
        "\n"
        "async def aio(x: int) -> int:\n"
        "    return x\n"
        "\n"
        "class MyErr(Exception):\n"
        "    pass\n\n"
        "class P(Protocol):\n"
        "    pass\n\n"
        "class E(Enum):\n"
        "    A = 1\n\n"
        "PI: float = 3.14\n"
        "_SECRET = 1\n\n"
        "class C:\n"
        "    NAME = 'n'\n\n"
        "    @property\n"
        "    def x(self) -> int:\n"
        "        return 1\n\n"
        "    @classmethod\n"
        "    def c(cls) -> str:\n"
        "        return ''\n\n"
        "    @staticmethod\n"
        "    def s() -> None:\n"
        "        pass\n\n"
        "@overload\n"
        "def f(x: int) -> int: ...\n"
        "@overload\n"
        "def f(x: str) -> str: ...\n"
        "def f(x):\n"
        "    \"\"\"Raises:\n"
        "    MyErr: sometimes\n"
        "    \"\"\"\n"
        "    return x\n"
    )
    mod = cst.parse_module(source)
    symbols: tuple[Symbol, ...] = extract_module(mod, "pkg.mod")

    # Async function
    aio = next(s for s in symbols if isinstance(s, FunctionSymbol) and s.fqn.endswith(".aio"))
    assert aio.is_async is True
    assert aio.returns == "int"

    # Type alias
    alias = next(s for s in symbols if isinstance(s, TypeAliasSymbol))
    assert alias.fqn == "pkg.mod.UserId"
    assert alias.target == "int"

    # Constants and visibility
    pi = next(s for s in symbols if isinstance(s, ConstantSymbol) and s.fqn.endswith(".PI"))
    assert pi.type == "float" and pi.visibility == "public"
    sec = next(s for s in symbols if isinstance(s, ConstantSymbol) and s.fqn.endswith("._SECRET"))
    assert sec.visibility == "private"

    # Class flags
    Csym = next(s for s in symbols if isinstance(s, ClassSymbol) and s.fqn.endswith(".C"))
    assert Csym.is_exception is False and Csym.is_protocol is False and Csym.is_enum is False

    Esym = next(s for s in symbols if isinstance(s, ClassSymbol) and s.fqn.endswith(".E"))
    assert Esym.is_enum is True

    Psym = next(s for s in symbols if isinstance(s, ClassSymbol) and s.fqn.endswith(".P"))
    assert Psym.is_protocol is True

    Err = next(s for s in symbols if isinstance(s, ClassSymbol) and s.fqn.endswith(".MyErr"))
    assert Err.is_exception is True

    # Method flags
    prop = next(s for s in symbols if isinstance(s, FunctionSymbol) and s.is_property)
    assert prop.owner == "pkg.mod.C"
    cmethod = next(s for s in symbols if isinstance(s, FunctionSymbol) and s.is_classmethod)
    assert cmethod.owner == "pkg.mod.C"
    smethod = next(s for s in symbols if isinstance(s, FunctionSymbol) and s.is_staticmethod)
    assert smethod.owner == "pkg.mod.C"

    # Overloads and raises
    overloads = [s for s in symbols if isinstance(s, FunctionSymbol) and s.fqn.endswith(".f")]
    assert any(s.overload_of is not None for s in overloads)
    impl = next(s for s in overloads if s.overload_of is None)
    assert "MyErr" in impl.raises


def test_pipeline_nested_packages(tmp_path: Path) -> None:
    root = tmp_path / "top"
    (root / "pkg" / "sub").mkdir(parents=True)
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "sub" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "sub" / "util.py").write_text("def g():\n    pass\n", encoding="utf-8")

    out = tmp_path / "out"
    res: Result[None, tuple[Error, ...]] = run_pipeline(root / "pkg", "pkg", "1.0.0", "cafebabe", 1, out)
    assert res.ok
    # Ensure submodule function exists
    data = (out / "symbols.jsonl").read_text(encoding="utf-8").splitlines()
    assert any(json.loads(line)["fqn"] == "pkg.sub.util.g" for line in data)
