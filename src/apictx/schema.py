from __future__ import annotations

import json
from importlib import resources
from typing import Any, Mapping


def load_schema() -> Mapping[str, Any]:
    with resources.files("apictx").joinpath("schema.json").open("r", encoding="utf-8") as handle:
        data: Mapping[str, Any] = json.load(handle)
    return data
