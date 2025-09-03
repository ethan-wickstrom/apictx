from __future__ import annotations

import libcst as cst

from apictx.extract import extract_module
from apictx.models import ConstantSymbol, FunctionSymbol, Symbol


def test_visibility_and_constants() -> None:
    src = (
        "def _internal():\n    pass\n"
        "def public():\n    pass\n"
        "VAL = 1\n"
        "class K:\n    _X = 2\n    Y: str = 'ok'\n"
    )
    mod = cst.parse_module(src)
    symbols: tuple[Symbol, ...] = extract_module(mod, "pkg.m")

    priv = next(
        s
        for s in symbols
        if isinstance(s, FunctionSymbol) and s.fqn.endswith("._internal")
    )
    pub = next(
        s
        for s in symbols
        if isinstance(s, FunctionSymbol) and s.fqn.endswith(".public")
    )
    assert priv.visibility == "private"
    assert pub.visibility == "public"

    val = next(
        s for s in symbols if isinstance(s, ConstantSymbol) and s.fqn.endswith(".VAL")
    )
    assert val.visibility == "public"
    x = next(
        s for s in symbols if isinstance(s, ConstantSymbol) and s.fqn.endswith(".K._X")
    )
    assert x.visibility == "private"
