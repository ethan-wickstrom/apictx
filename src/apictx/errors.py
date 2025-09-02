from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Error:
    code: str
    message: str
    path: str
