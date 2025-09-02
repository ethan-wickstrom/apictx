from __future__ import annotations

from typing import Iterator, Literal, Set
from itertools import chain

import libcst as cst

from .models import (
    ClassSymbol,
    ConstantSymbol,
    FunctionSymbol,
    ModuleSymbol,
    Parameter,
    Symbol,
    TypeAliasSymbol,
)

_EMPTY_MODULE: cst.Module = cst.Module([])


def _determine_visibility(name: str, exported: Set[str] | None = None) -> Literal["public", "private"]:
    if exported is not None:
        return "public" if name in exported else "private"
    return "private" if name.startswith("_") else "public"


def _parameter_from_node(param: cst.Param) -> Parameter:
    annotation: str = ""
    if param.annotation is not None:
        annotation = _EMPTY_MODULE.code_for_node(param.annotation.annotation)
    return Parameter(name=param.name.value, type=annotation)


def _iter_parameters(func: cst.FunctionDef) -> Iterator[cst.Param]:
    posonly = func.params.posonly_params
    params = func.params.params
    kwonly = func.params.kwonly_params
    star = func.params.star_arg
    dstar = func.params.star_kwarg
    parts: tuple[cst.Param, ...] = tuple(
        p for p in chain(posonly, params, kwonly) if isinstance(p, cst.Param)
    )
    if isinstance(star, cst.Param):
        parts += (star,)
    if isinstance(dstar, cst.Param):
        parts += (dstar,)
    return parts


def _decorator_to_str(deco: cst.Decorator) -> str:
    return _EMPTY_MODULE.code_for_node(deco.decorator)


def _parse_docstring_raises(doc: str | None) -> tuple[str, ...]:
    if not doc:
        return tuple()
    names: list[str] = []
    lines = [ln.rstrip() for ln in doc.splitlines()]
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.lower().startswith("raises:") or ln.lower().startswith("raise:"):
            i += 1
            while i < len(lines):
                sub = lines[i]
                stripped = sub.strip()
                if stripped == "":
                    i += 1
                    continue
                # Stop if we hit another section header like "Args:" or similar
                if stripped.endswith(":") and " " not in stripped:
                    break
                # Accept bullets, indented or not
                text = stripped.lstrip("- ")
                # Expect formats like "ValueError: details" or just "ValueError"
                name = text.split(":", 1)[0].split()[0]
                if name:
                    names.append(name)
                i += 1
            continue
        i += 1
    return tuple(dict.fromkeys(names))


def _function_from_def(defn: cst.FunctionDef, parent_fqn: str | None, module_fqn: str, exported: Set[str] | None) -> FunctionSymbol:
    owner: str | None = parent_fqn
    base_fqn: str = f"{module_fqn}.{defn.name.value}" if owner is None else f"{owner}.{defn.name.value}"
    params: tuple[Parameter, ...] = tuple(map(_parameter_from_node, _iter_parameters(defn)))
    returns: str | None = None
    if defn.returns is not None:
        returns = _EMPTY_MODULE.code_for_node(defn.returns.annotation)
    doc: str | None = defn.get_docstring()
    decorators: tuple[str, ...] = tuple(map(_decorator_to_str, defn.decorators))
    visibility: Literal["public", "private"] = _determine_visibility(defn.name.value, None if owner is not None else exported)
    deprecated: bool = any("deprecated" in deco for deco in decorators)
    is_property: bool = any(d.split("(")[0].endswith("property") for d in decorators)
    is_classmethod: bool = any(d.split("(")[0].endswith("classmethod") for d in decorators)
    is_staticmethod: bool = any(d.split("(")[0].endswith("staticmethod") for d in decorators)
    is_async: bool = defn.asynchronous is not None
    raises: tuple[str, ...] = _parse_docstring_raises(doc)
    overload_of: str | None = base_fqn if any(d.split("(")[0].endswith("overload") for d in decorators) else None
    return FunctionSymbol(
        kind="function",
        fqn=base_fqn,
        parameters=params,
        returns=returns,
        docstring=doc,
        decorators=decorators,
        visibility=visibility,
        deprecated=deprecated,
        is_async=is_async,
        owner=owner,
        is_classmethod=is_classmethod,
        is_staticmethod=is_staticmethod,
        is_property=is_property,
        raises=raises,
        overload_of=overload_of,
    )


def _bases_from_class(defn: cst.ClassDef) -> tuple[str, ...]:
    bases: list[str] = []
    for arg in defn.bases:
        try:
            bases.append(_EMPTY_MODULE.code_for_node(arg.value))
        except Exception:
            bases.append("")
    return tuple(bases)


def _decorators_from_class(defn: cst.ClassDef) -> tuple[str, ...]:
    return tuple(map(_decorator_to_str, defn.decorators))


def _is_exception_class(bases: tuple[str, ...]) -> bool:
    lowered = tuple(b.lower() for b in bases)
    return any("exception" in b or b.endswith("baseexception") for b in lowered)


def _is_enum_class(bases: tuple[str, ...]) -> bool:
    lowered = tuple(b.lower() for b in bases)
    return any(b.endswith("enum.enum") or b.endswith("enum") for b in lowered)


def _is_protocol_class(bases: tuple[str, ...]) -> bool:
    lowered = tuple(b.lower() for b in bases)
    return any(b.endswith("typing.protocol") or b.endswith("protocol") for b in lowered)


def _constant_from_assign(name: str, owner_fqn: str, type_str: str | None, value_str: str | None, visibility: Literal["public", "private"]) -> ConstantSymbol:
    fqn: str = f"{owner_fqn}.{name}"
    return ConstantSymbol(
        kind="constant",
        fqn=fqn,
        owner=owner_fqn,
        type=type_str,
        value=value_str,
        visibility=visibility,
        deprecated=False,
    )


def extract_module(module: cst.Module, module_fqn: str) -> tuple[Symbol, ...]:
    module_doc: str | None = module.get_docstring()
    mod_symbol: ModuleSymbol = ModuleSymbol(kind="module", fqn=module_fqn, docstring=module_doc)

    # collect __all__ if present: only literal list/tuple of string constants
    def _collect_exports(mod: cst.Module) -> Set[str] | None:
        exports: set[str] = set()
        found: bool = False
        for stmt in mod.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                for small in stmt.body:
                    if isinstance(small, cst.Assign):
                        # handle "__all__ = ["a", "b"]" or tuple
                        for target in small.targets:
                            if isinstance(target.target, cst.Name) and target.target.value == "__all__":
                                value = small.value
                                elements: list[cst.Element] | None = None
                                if isinstance(value, cst.List):
                                    elements = value.elements
                                elif isinstance(value, cst.Tuple):
                                    elements = value.elements
                                if elements is not None:
                                    for elt in elements:
                                        node = elt.value
                                        if isinstance(node, cst.SimpleString):
                                            text = node.value
                                            # strip quotes for simple cases
                                            if len(text) >= 2 and text[0] in {'"', "'"} and text[-1] == text[0]:
                                                exports.add(text[1:-1])
                                    found = True
        return exports if found else None

    exported_names: Set[str] | None = _collect_exports(module)

    out: list[Symbol] = [mod_symbol]

    def handle_function(defn: cst.FunctionDef, parent_fqn: str | None) -> None:
        out.append(_function_from_def(defn, parent_fqn, module_fqn, exported_names))

    def handle_simple_stmt(stmt: cst.SimpleStatementLine, owner_fqn: str) -> None:
        for small in stmt.body:
            if isinstance(small, cst.AnnAssign):
                if isinstance(small.target, cst.Name):
                    name = small.target.value
                    ann_str = _EMPTY_MODULE.code_for_node(small.annotation.annotation)
                    # Detect typing TypeAlias via annotation (PEP 613 style): Name or qualified Name ending with TypeAlias
                    if ann_str.split(".")[-1] == "TypeAlias" and small.value is not None:
                        target = _EMPTY_MODULE.code_for_node(small.value)
                        out.append(TypeAliasSymbol(kind="type_alias", fqn=f"{owner_fqn}.{name}", target=target))
                    else:
                        type_str = ann_str
                        value_str = _EMPTY_MODULE.code_for_node(small.value) if small.value is not None else None
                        vis = _determine_visibility(name, exported_names if owner_fqn == module_fqn else None)
                        out.append(_constant_from_assign(name, owner_fqn, type_str, value_str, vis))
            elif isinstance(small, cst.Assign):
                # Only handle single-target simple names for constants
                if len(small.targets) == 1 and isinstance(small.targets[0].target, cst.Name):
                    name = small.targets[0].target.value
                    value_str = _EMPTY_MODULE.code_for_node(small.value)
                    vis = _determine_visibility(name, exported_names if owner_fqn == module_fqn else None)
                    out.append(_constant_from_assign(name, owner_fqn, None, value_str, vis))

    for stmt in module.body:
        if isinstance(stmt, cst.FunctionDef):
            handle_function(stmt, None)
        elif isinstance(stmt, cst.ClassDef):
            cls_fqn: str = f"{module_fqn}.{stmt.name.value}"
            bases: tuple[str, ...] = _bases_from_class(stmt)
            decorators: tuple[str, ...] = _decorators_from_class(stmt)
            cls = ClassSymbol(
                kind="class",
                fqn=cls_fqn,
                docstring=stmt.get_docstring(),
                decorators=decorators,
                visibility=_determine_visibility(stmt.name.value),
                deprecated=any("deprecated" in d for d in decorators),
                bases=bases,
                base_fqns=tuple(),
                is_exception=_is_exception_class(bases),
                is_enum=_is_enum_class(bases),
                is_protocol=_is_protocol_class(bases),
            )
            out.append(cls)
            # Inspect class body for methods and constants
            for cstmt in stmt.body.body:
                if isinstance(cstmt, cst.FunctionDef):
                    handle_function(cstmt, cls_fqn)
                elif isinstance(cstmt, cst.SimpleStatementLine):
                    handle_simple_stmt(cstmt, cls_fqn)
        elif isinstance(stmt, cst.SimpleStatementLine):
            handle_simple_stmt(stmt, module_fqn)
        elif isinstance(stmt, cst.TypeAlias):
            alias_name = stmt.name.value
            target = _EMPTY_MODULE.code_for_node(stmt.value)
            out.append(
                TypeAliasSymbol(kind="type_alias", fqn=f"{module_fqn}.{alias_name}", target=target)
            )

    symbols: tuple[Symbol, ...] = tuple(sorted(out, key=lambda s: s.fqn))
    return symbols
