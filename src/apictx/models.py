from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class Parameter:
    name: str
    type: str


@dataclass(frozen=True, slots=True)
class Symbol:
    kind: str
    fqn: str


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
