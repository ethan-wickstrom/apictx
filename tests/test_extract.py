from __future__ import annotations

import libcst as cst
from hypothesis import given, strategies as st

from apictx.extract import extract_module
from apictx.models import FunctionSymbol, Symbol


def test_extract_simple_function() -> None:
    source: str = (
        "def add(a: int, b: int) -> int:\n"
        "    \"Return the sum of a and b.\"\n"
        "    return a + b\n"
    )
    module: cst.Module = cst.parse_module(source)
    symbols: tuple[Symbol, ...] = extract_module(module, "mathx.add")
    selected: Symbol = next(s for s in symbols if s.kind == "function")
    assert isinstance(selected, FunctionSymbol)
    func: FunctionSymbol = selected
    assert func.fqn == "mathx.add.add"
    assert len(func.parameters) == 2
    assert func.returns == "int"


@given(st.lists(st.from_regex(r"[A-Za-z][A-Za-z0-9_]*", fullmatch=True), unique=True))
def test_unique_fqn(names: list[str]) -> None:
    body: str = "\n\n".join(f"def {n}():\n    pass" for n in names)
    module: cst.Module = cst.parse_module(body)
    symbols: tuple[Symbol, ...] = extract_module(module, "pkg.mod")
    fqn_set: set[str] = {s.fqn for s in symbols if s.kind == "function"}
    assert len(fqn_set) == len(names)
