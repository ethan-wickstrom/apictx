from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Result(Generic[T, E]):
    ok: bool
    value: T | None
    error: E | None

    @staticmethod
    def success(value: T) -> "Result[T, E]":
        return Result(True, value, None)

    @staticmethod
    def failure(error: E) -> "Result[T, E]":
        return Result(False, None, error)
