from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import run_pipeline
from .result import Result
from .errors import Error


def main() -> int:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("--package", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", default="")
    parser.add_argument("--out", type=Path, default=Path("build"))
    parser.add_argument("--workers", type=int, default=4)
    args: argparse.Namespace = parser.parse_args()
    result: Result[None, tuple[Error, ...]] = run_pipeline(Path(args.root), args.package, args.version, args.commit, args.workers, args.out)
    if result.ok:
        return 0
    for err in result.error or ():
        print(f"{err.code}:{err.path}:{err.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
