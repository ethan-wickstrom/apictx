from __future__ import annotations

import argparse
from pathlib import Path
import json

from .pipeline import run_pipeline, query_index
from .result import Result
from .errors import Error


def main() -> int:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="apictx")
    subs = parser.add_subparsers(dest="cmd", required=True)

    p_extract = subs.add_parser("extract", help="Run pipeline on a source tree")
    p_extract.add_argument("root")
    p_extract.add_argument("--package", required=True)
    p_extract.add_argument("--version", required=True)
    p_extract.add_argument("--commit", default="")
    p_extract.add_argument("--out", type=Path, default=Path("build"))
    p_extract.add_argument("--workers", type=int, default=4)

    p_query = subs.add_parser("query", help="Query the SQLite index")
    p_query.add_argument("--db", type=Path, required=True)
    grp = p_query.add_mutually_exclusive_group(required=True)
    grp.add_argument("--fqn", help="Exact fully qualified name")
    grp.add_argument("--approx", help="Approximate name or FQN")
    p_query.add_argument("--limit", type=int, default=5)
    p_query.add_argument("--kind", choices=["module","function","class","constant","type_alias"], help="Filter by kind")
    p_query.add_argument("--visibility", choices=["public","private"], help="Filter by visibility")
    p_query.add_argument("--owner", help="Filter by owner FQN")

    args: argparse.Namespace = parser.parse_args()

    if args.cmd == "extract":
        result: Result[None, tuple[Error, ...]] = run_pipeline(
            Path(args.root), args.package, args.version, args.commit, args.workers, args.out
        )
        if result.ok:
            return 0
        for err in result.error or ():
            print(f"{err.code}:{err.path}:{err.message}")
        return 1
    elif args.cmd == "query":
        res = query_index(
            Path(args.db),
            fqn=args.fqn,
            approx=args.approx,
            limit=int(args.limit),
            kind=args.kind,
            visibility=args.visibility,
            owner=args.owner,
        )
        if not res.ok or res.value is None:
            err = res.error
            if err is not None:
                print(f"{err.code}:{err.path}:{err.message}")
            return 1
        for obj in res.value:
            print(json.dumps(obj, sort_keys=True))
        return 0
    else:
        parser.print_help()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
