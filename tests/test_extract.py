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


def test_extract_module_with_version() -> None:
    """Test that __version__ is extracted as a constant."""
    source: str = (
        "__version__ = \"1.2.3\"\n\n"
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n"
    )
    module: cst.Module = cst.parse_module(source)
    symbols: tuple[Symbol, ...] = extract_module(module, "mypkg")
    
    # Check that __version__ is extracted as a constant
    version_symbols = [s for s in symbols if s.kind == "constant" and s.fqn.endswith(".__version__")]
    assert len(version_symbols) == 1
    version_symbol = version_symbols[0]
    assert version_symbol.value == "1.2.3"
    assert version_symbol.visibility == "public"
