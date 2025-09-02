from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class Parameter:
    name: str
    type: str
    kind: Literal["posonly", "pos", "kwonly", "vararg", "kwvar"]
    default: str | None
    required: bool


@dataclass(frozen=True, slots=True)
class Location:
    path: str
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class Symbol:
    kind: str
    fqn: str
    location: Location


@dataclass(frozen=True, slots=True)
class ModuleSymbol(Symbol):
    docstring: str | None


@dataclass(frozen=True, slots=True)
class FunctionSymbol(Symbol):
    parameters: tuple[Parameter, ...]
    returns: str | None
    docstring: str | None
    decorators: tuple[str, ...]
    visibility: Literal["public", "private"]
    deprecated: bool
    is_async: bool
    owner: str | None  # class FQN if method/property
    is_classmethod: bool
    is_staticmethod: bool
    is_property: bool
    raises: tuple[str, ...]
    overload_of: str | None  # base FQN without overload index


@dataclass(frozen=True, slots=True)
class ClassSymbol(Symbol):
    docstring: str | None
    decorators: tuple[str, ...]
    visibility: Literal["public", "private"]
    deprecated: bool
    bases: tuple[str, ...]               # textual base expressions
    base_fqns: tuple[str, ...]           # linked FQNs when resolvable
    is_exception: bool
    is_enum: bool
    is_protocol: bool


@dataclass(frozen=True, slots=True)
class ConstantSymbol(Symbol):
    owner: str  # module or class FQN holding the constant
    type: str | None
    value: str | None
    visibility: Literal["public", "private"]
    deprecated: bool


@dataclass(frozen=True, slots=True)
class TypeAliasSymbol(Symbol):
    target: str
