from __future__ import annotations

from typing import Iterator, Literal
from itertools import chain

import libcst as cst

from .models import FunctionSymbol, ModuleSymbol, Parameter, Symbol

_EMPTY_MODULE: cst.Module = cst.Module([])


def _determine_visibility(name: str) -> Literal["public", "private"]:
    return "private" if name.startswith("_") else "public"


def _parameter_from_node(param: cst.Param) -> Parameter:
    annotation: str = ""
    if param.annotation is not None:
        annotation = _EMPTY_MODULE.code_for_node(param.annotation.annotation)
    return Parameter(name=param.name.value, type=annotation)


def _iter_parameters(func: cst.FunctionDef) -> Iterator[cst.Param]:
    return chain(func.params.params, func.params.kwonly_params)


def _decorator_to_str(deco: cst.Decorator) -> str:
    return _EMPTY_MODULE.code_for_node(deco.decorator)


def _function_from_def(defn: cst.FunctionDef, module_fqn: str) -> FunctionSymbol:
    func_fqn: str = f"{module_fqn}.{defn.name.value}"
    params: tuple[Parameter, ...] = tuple(map(_parameter_from_node, _iter_parameters(defn)))
    returns: str | None = None
    if defn.returns is not None:
        returns = _EMPTY_MODULE.code_for_node(defn.returns.annotation)
    doc: str | None = defn.get_docstring()
    decorators: tuple[str, ...] = tuple(map(_decorator_to_str, defn.decorators))
    visibility: Literal["public", "private"] = _determine_visibility(defn.name.value)
    deprecated: bool = any("deprecated" in deco for deco in decorators)
    return FunctionSymbol(
        kind="function",
        fqn=func_fqn,
        parameters=params,
        returns=returns,
        docstring=doc,
        decorators=decorators,
        visibility=visibility,
        deprecated=deprecated,
    )


def extract_module(module: cst.Module, module_fqn: str) -> tuple[Symbol, ...]:
    module_doc: str | None = module.get_docstring()
    mod_symbol: ModuleSymbol = ModuleSymbol(kind="module", fqn=module_fqn, docstring=module_doc)
    functions: tuple[FunctionSymbol, ...] = tuple(
        sorted(
            (
                _function_from_def(stmt, module_fqn)
                for stmt in module.body
                if isinstance(stmt, cst.FunctionDef)
            ),
            key=lambda s: s.fqn,
        )
    )
    symbols: tuple[Symbol, ...] = (mod_symbol, *functions)
    return symbols
