from __future__ import annotations

import libcst as cst

from apictx.extract import extract_module
from apictx.models import FunctionSymbol, ConstantSymbol, Symbol


def test_module_all_controls_visibility() -> None:
    src = (
        "__all__ = ['exported_fun', 'EXPORTED_CONST']\n"
        "\n"
        "def exported_fun():\n    pass\n"
        "def internal_fun():\n    pass\n"
        "EXPORTED_CONST = 1\n"
        "INTERNAL_CONST = 2\n"
    )
    mod = cst.parse_module(src)
    symbols: tuple[Symbol, ...] = extract_module(mod, "pkg.m")
    ef = next(s for s in symbols if isinstance(s, FunctionSymbol) and s.fqn.endswith(".exported_fun"))
    inf = next(s for s in symbols if isinstance(s, FunctionSymbol) and s.fqn.endswith(".internal_fun"))
    ec = next(s for s in symbols if isinstance(s, ConstantSymbol) and s.fqn.endswith(".EXPORTED_CONST"))
    ic = next(s for s in symbols if isinstance(s, ConstantSymbol) and s.fqn.endswith(".INTERNAL_CONST"))
    assert ef.visibility == "public"
    assert ec.visibility == "public"
    assert inf.visibility == "private"
    assert ic.visibility == "private"
