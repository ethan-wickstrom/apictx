from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from itertools import chain
from pathlib import Path
from typing import Iterator, Mapping

import jsonschema
import libcst as cst

from .errors import Error
from .extract import extract_module
from .models import Symbol
from .result import Result
from .schema import load_schema


STAGES: tuple[str, ...] = (
    "Discover",
    "Parse",
    "Extract",
    "Link",
    "Validate",
    "Index",
    "Emit",
)


def discover(root: Path) -> tuple[Path, ...]:
    files: tuple[Path, ...] = tuple(sorted(root.rglob("*.py")))
    return files


def _parse_worker(path_str: str) -> tuple[str, Result[cst.Module, Error]]:
    path: Path = Path(path_str)
    try:
        source: str = path.read_text(encoding="utf-8")
        module: cst.Module = cst.parse_module(source)
        return path_str, Result.success(module)
    except Exception as exc:  # noqa: BLE001
        err: Error = Error(code="parse", message=str(exc), path=path_str)
        return path_str, Result.failure(err)


def parse(paths: tuple[Path, ...], workers: int) -> Mapping[Path, Result[cst.Module, Error]]:
    path_strings: tuple[str, ...] = tuple(str(p) for p in paths)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        pairs_iter: Iterator[tuple[str, Result[cst.Module, Error]]] = pool.map(
            _parse_worker, path_strings
        )
        return {Path(p): res for p, res in pairs_iter}


def extract(parsed: Mapping[Path, cst.Module], root: Path, package: str) -> tuple[Symbol, ...]:
    fragments: Iterator[tuple[Symbol, ...]] = (
        extract_module(
            module,
            ".".join((package, *path.relative_to(root).with_suffix("").parts)),
        )
        for path, module in parsed.items()
    )
    symbols: tuple[Symbol, ...] = tuple(
        sorted(chain.from_iterable(fragments), key=lambda s: s.fqn)
    )
    return symbols


def link(symbols: tuple[Symbol, ...]) -> tuple[Symbol, ...]:
    return symbols


@dataclass(frozen=True, slots=True)
class ValidationReport:
    symbol_count: int


@dataclass(frozen=True, slots=True)
class ValidationOutput:
    objects: tuple[dict[str, object], ...]
    report: ValidationReport


def validate(symbols: tuple[Symbol, ...]) -> Result[ValidationOutput, tuple[Error, ...]]:
    schema: Mapping[str, object] = load_schema()
    objs: list[dict[str, object]] = []
    errors: list[Error] = []
    seen: set[str] = set()
    for symbol in symbols:
        if symbol.fqn in seen:
            errors.append(Error(code="duplicate", message="duplicate fqn", path=symbol.fqn))
            continue
        seen.add(symbol.fqn)
        raw: dict[str, object] = asdict(symbol)
        obj: dict[str, object] = json.loads(json.dumps(raw, sort_keys=True))
        try:
            jsonschema.validate(obj, schema)
            objs.append(obj)
        except jsonschema.ValidationError as exc:
            error: Error = Error(code="schema", message=str(exc), path=symbol.fqn)
            errors.append(error)
    if errors:
        return Result.failure(tuple(errors))
    report: ValidationReport = ValidationReport(symbol_count=len(objs))
    output: ValidationOutput = ValidationOutput(objects=tuple(objs), report=report)
    return Result.success(output)


def index(objs: tuple[dict[str, object], ...], db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn: sqlite3.Connection = sqlite3.connect(db_path)
    cur: sqlite3.Cursor = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS symbols (fqn TEXT PRIMARY KEY, kind TEXT, data TEXT)")
    cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS symbols_fts USING fts5(fqn)")
    for obj in objs:
        fqn: str = str(obj["fqn"])
        kind: str = str(obj["kind"])
        data_str: str = json.dumps(obj, sort_keys=True)
        cur.execute("INSERT OR REPLACE INTO symbols (fqn, kind, data) VALUES (?, ?, ?)", (fqn, kind, data_str))
        rowid_val: int | None = cur.lastrowid
        rowid: int = 0 if rowid_val is None else rowid_val
        cur.execute("INSERT OR REPLACE INTO symbols_fts(rowid, fqn) VALUES (?, ?)", (rowid, fqn))
    conn.commit()
    conn.close()


@dataclass(frozen=True, slots=True)
class Manifest:
    package: str
    version: str
    commit: str
    extracted_at: str
    tool: str
    schema: str


def emit(objs: tuple[dict[str, object], ...], manifest: Manifest, report: ValidationReport, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    jsonl_path: Path = outdir / "symbols.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for obj in objs:
            line: str = json.dumps(obj, sort_keys=True)
            handle.write(line + "\n")
    manifest_path: Path = outdir / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(manifest), sort_keys=True))
    report_path: Path = outdir / "validation.json"
    with report_path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(report), sort_keys=True))


def run_pipeline(root: Path, package: str, version: str, commit: str, workers: int, outdir: Path) -> Result[None, tuple[Error, ...]]:
    paths: tuple[Path, ...] = discover(root)
    parsed_map: Mapping[Path, Result[cst.Module, Error]] = parse(paths, workers)
    modules: dict[Path, cst.Module] = {}
    parse_errors: list[Error] = []
    for path, res in parsed_map.items():
        if res.ok and res.value is not None:
            modules[path] = res.value
        elif res.error is not None:
            parse_errors.append(res.error)
    if parse_errors:
        return Result.failure(tuple(parse_errors))
    symbols: tuple[Symbol, ...] = extract(modules, root, package)
    linked: tuple[Symbol, ...] = link(symbols)
    validated: Result[ValidationOutput, tuple[Error, ...]] = validate(linked)
    if not validated.ok or validated.value is None:
        return Result.failure(validated.error if validated.error is not None else tuple())
    output: ValidationOutput = validated.value
    objs: tuple[dict[str, object], ...] = output.objects
    db_path: Path = outdir / "index.sqlite3"
    index(objs, db_path)
    manifest: Manifest = Manifest(
        package=package,
        version=version,
        commit=commit,
        extracted_at=datetime.now(UTC).isoformat(),
        tool="apictx",
        schema="1.0",
    )
    emit(objs, manifest, output.report, outdir)
    return Result.success(None)
