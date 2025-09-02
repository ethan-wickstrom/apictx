from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, asdict, replace
from datetime import UTC, datetime
from itertools import chain
from pathlib import Path
from typing import Iterator, Mapping, Dict, Tuple

import jsonschema
import libcst as cst

from .errors import Error
from .extract import extract_module
from .models import ClassSymbol, ConstantSymbol, FunctionSymbol, Symbol
from .result import Result
from .schema import load_schema


_EMPTY_MODULE: cst.Module = cst.Module([])

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
            str(path),
        )
        for path, module in parsed.items()
    )
    symbols: tuple[Symbol, ...] = tuple(
        sorted(chain.from_iterable(fragments), key=lambda s: s.fqn)
    )
    return symbols


def _module_fqn_for(path: Path, root: Path, package: str) -> str:
    return ".".join((package, *path.relative_to(root).with_suffix("").parts))


def build_import_tables(parsed: Mapping[Path, cst.Module], root: Path, package: str) -> Dict[str, Dict[str, str]]:
    tables: Dict[str, Dict[str, str]] = {}
    for path, module in parsed.items():
        mod_fqn = _module_fqn_for(path, root, package)
        table: Dict[str, str] = {}
        for stmt in module.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                for small in stmt.body:
                    if isinstance(small, cst.Import):
                        for alias in small.names:
                            full = _EMPTY_MODULE.code_for_node(alias.name)
                            asname = full
                            if alias.asname is not None:
                                asname = alias.asname.name.value
                            else:
                                # expose top-level name as shorthand
                                asname = full.split(".")[-1]
                            table[asname] = full
                    elif isinstance(small, cst.ImportFrom):
                        # compute base module fqn considering relative import dots
                        base_module = ""
                        rel = 0
                        if small.relative:
                            rel = len(tuple(small.relative))
                        # current package parts (drop module leaf)
                        pkg_parts = mod_fqn.split(".")[:-1]
                        if rel > 0:
                            ascend = max(0, rel - 1)
                            pkg_parts = pkg_parts[: max(0, len(pkg_parts) - ascend)]
                        if small.module is not None:
                            mod_part = _EMPTY_MODULE.code_for_node(small.module)
                            base_module = ".".join((*pkg_parts, *mod_part.split(".")))
                        else:
                            base_module = ".".join(pkg_parts)
                        for alias in small.names:
                            name = _EMPTY_MODULE.code_for_node(alias.name)
                            target = f"{base_module}.{name}" if base_module else name
                            local = alias.asname.name.value if alias.asname is not None else name
                            table[local] = target
        tables[mod_fqn] = table
    return tables


def link(symbols: tuple[Symbol, ...], import_tables: Dict[str, Dict[str, str]]) -> tuple[Symbol, ...]:
    # map simple name -> sorted fqns
    name_to_fqns: dict[str, tuple[str, ...]] = {}
    class_fqns: set[str] = {s.fqn for s in symbols if isinstance(s, ClassSymbol)}
    for s in symbols:
        name = s.fqn.split(".")[-1]
        name_to_fqns.setdefault(name, tuple())
    # fill lists deterministically
    for name in tuple(name_to_fqns.keys()):
        vals = sorted([s.fqn for s in symbols if s.fqn.split(".")[-1] == name])
        name_to_fqns[name] = tuple(vals)

    linked: list[Symbol] = []
    def _resolve_base(base_txt: str, current_mod: str) -> str | None:
        txt = base_txt.strip()
        # strip generics like typing.Generic[T]
        head = txt.split("[", 1)[0]
        parts = head.split(".") if head else []
        if not parts:
            return None
        alias_map = import_tables.get(current_mod, {})
        # qualified name
        if len(parts) > 1:
            first = parts[0]
            rest = parts[1:]
            target = alias_map.get(first)
            if target:
                candidate = ".".join((target, *rest)) if rest else target
                return candidate if candidate in class_fqns else None
            # already fully qualified
            if head in class_fqns:
                return head
        else:
            # unqualified: prefer same module first
            simple = parts[0]
            same_mod_candidate = f"{current_mod}.{simple}"
            if same_mod_candidate in class_fqns:
                return same_mod_candidate
            # via import alias mapping
            target = alias_map.get(simple)
            if target and target in class_fqns:
                return target
            # fallback to global name mapping
            matches = name_to_fqns.get(simple, ())
            if matches:
                return matches[0]
        return None

    for s in symbols:
        if isinstance(s, ClassSymbol):
            resolved: list[str] = []
            current_mod = s.fqn.rsplit(".", 1)[0]
            for b in s.bases:
                cand = _resolve_base(b, current_mod)
                if cand:
                    resolved.append(cand)
            linked.append(replace(s, base_fqns=tuple(sorted(set(resolved)))))
        else:
            linked.append(s)
    return tuple(linked)


@dataclass(frozen=True, slots=True)
class ValidationReport:
    symbol_count: int
    missing_references: int


@dataclass(frozen=True, slots=True)
class ValidationOutput:
    objects: tuple[dict[str, object], ...]
    report: ValidationReport


def validate(symbols: tuple[Symbol, ...]) -> Result[ValidationOutput, tuple[Error, ...]]:
    schema: Mapping[str, object] = load_schema()
    objs: list[dict[str, object]] = []
    errors: list[Error] = []
    seen: set[str] = set()
    fqn_set: set[str] = {s.fqn for s in symbols}
    missing_refs_count: int = 0
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
        # Reference closure checks for owners and base_fqns
        if isinstance(symbol, FunctionSymbol) and symbol.owner is not None:
            if symbol.owner not in fqn_set:
                missing_refs_count += 1
                errors.append(Error(code="missing_ref", message="owner not found", path=f"{symbol.fqn} -> {symbol.owner}"))
        if isinstance(symbol, ConstantSymbol):
            if symbol.owner not in fqn_set:
                missing_refs_count += 1
                errors.append(Error(code="missing_ref", message="owner not found", path=f"{symbol.fqn} -> {symbol.owner}"))
        if isinstance(symbol, ClassSymbol):
            for base in symbol.base_fqns:
                if base not in fqn_set:
                    missing_refs_count += 1
                    errors.append(Error(code="missing_ref", message="base not found", path=f"{symbol.fqn} -> {base}"))
    if errors:
        return Result.failure(tuple(errors))
    report: ValidationReport = ValidationReport(symbol_count=len(objs), missing_references=missing_refs_count)
    output: ValidationOutput = ValidationOutput(objects=tuple(objs), report=report)
    return Result.success(output)


def _to_grams(text: str, n: int = 3) -> tuple[str, ...]:
    s = f"^{text.lower()}$"
    return tuple({s[i : i + n] for i in range(max(0, len(s) - n + 1))})


def index(objs: tuple[dict[str, object], ...], db_path: Path) -> Result[None, Error]:
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn: sqlite3.Connection = sqlite3.connect(db_path)
        cur: sqlite3.Cursor = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS symbols (id INTEGER PRIMARY KEY AUTOINCREMENT, fqn TEXT UNIQUE, name TEXT, kind TEXT, data TEXT)"
        )
        cur.execute("CREATE TABLE IF NOT EXISTS grams (gram TEXT, id INTEGER)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_symbols_fqn ON symbols(fqn)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_grams_gram ON grams(gram)")
        for obj in objs:
            fqn: str = str(obj["fqn"])
            kind: str = str(obj["kind"])
            name: str = fqn.split(".")[-1].lower()
            data_str: str = json.dumps(obj, sort_keys=True)
            # upsert symbol
            cur.execute("SELECT id FROM symbols WHERE fqn = ?", (fqn,))
            row = cur.fetchone()
            if row is None:
                cur.execute(
                    "INSERT INTO symbols (fqn, name, kind, data) VALUES (?, ?, ?, ?)",
                    (fqn, name, kind, data_str),
                )
                sid = int(cur.lastrowid)
            else:
                sid = int(row[0])
                cur.execute(
                    "UPDATE symbols SET name = ?, kind = ?, data = ? WHERE id = ?",
                    (name, kind, data_str, sid),
                )
                cur.execute("DELETE FROM grams WHERE id = ?", (sid,))
            grams = set(_to_grams(name)) | set(_to_grams(fqn))
            cur.executemany("INSERT INTO grams (gram, id) VALUES (?, ?)", [(g, sid) for g in sorted(grams)])
        conn.commit()
        conn.close()
        return Result.success(None)
    except Exception as exc:  # noqa: BLE001
        return Result.failure(Error(code="index", message=str(exc), path=str(db_path)))


def query_index(
    db_path: Path,
    *,
    fqn: str | None = None,
    approx: str | None = None,
    limit: int = 10,
    kind: str | None = None,
    visibility: str | None = None,
    owner: str | None = None,
) -> Result[tuple[dict[str, object], ...], Error]:
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        rows: list[tuple[str]] = []
        if fqn:
            row = cur.execute("SELECT data FROM symbols WHERE fqn = ?", (fqn,)).fetchone()
            if row:
                rows = [row]
        elif approx:
            grams = _to_grams(approx)
            if grams:
                placeholders = ",".join(["?"] * len(grams))
                # fetch a larger pool to allow post-filtering
                pool = max(50, int(limit) * 5)
                sql = (
                    "SELECT s.data, COUNT(*) as score FROM grams g JOIN symbols s ON s.id = g.id "
                    f"WHERE g.gram IN ({placeholders}) GROUP BY s.id ORDER BY score DESC, s.fqn ASC LIMIT ?"
                )
                rows = cur.execute(sql, [*grams, pool]).fetchall()
        conn.close()
        objs: list[dict[str, object]] = []
        for row in rows:
            data_str = row[0] if len(row) >= 1 else None
            if not isinstance(data_str, str):
                continue
            try:
                obj = json.loads(data_str)
            except Exception:
                continue
            # Apply filters
            if kind is not None and str(obj.get("kind")) != str(kind):
                continue
            if visibility is not None:
                if str(obj.get("visibility")) != str(visibility):
                    continue
            if owner is not None:
                if str(obj.get("owner")) != str(owner):
                    continue
            objs.append(obj)
            if len(objs) >= int(limit):
                break
        return Result.success(tuple(objs))
    except Exception as exc:  # noqa: BLE001
        return Result.failure(Error(code="query", message=str(exc), path=str(db_path)))


@dataclass(frozen=True, slots=True)
class Manifest:
    package: str
    version: str
    commit: str
    extracted_at: str
    tool: str
    tool_version: str
    schema_version: str


def emit(objs: tuple[dict[str, object], ...], manifest: Manifest, report: ValidationReport, outdir: Path) -> Result[None, Error]:
    try:
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
        return Result.success(None)
    except Exception as exc:  # noqa: BLE001
        return Result.failure(Error(code="emit", message=str(exc), path=str(outdir)))


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
    import_tables = build_import_tables(modules, root, package)
    linked: tuple[Symbol, ...] = link(symbols, import_tables)
    validated: Result[ValidationOutput, tuple[Error, ...]] = validate(linked)
    if not validated.ok or validated.value is None:
        return Result.failure(validated.error if validated.error is not None else tuple())
    output: ValidationOutput = validated.value
    objs: tuple[dict[str, object], ...] = output.objects
    db_path: Path = outdir / "index.sqlite3"
    idx_res = index(objs, db_path)
    if not idx_res.ok:
        return Result.failure((idx_res.error,) if idx_res.error is not None else tuple())
    # derive schema version from schema file if present
    schema_data = load_schema()
    schema_version = str(schema_data.get("x-apictx-schema-version", "unknown"))
    from . import __version__ as TOOL_VERSION  # local import to avoid cycles at load
    manifest: Manifest = Manifest(
        package=package,
        version=version,
        commit=commit,
        extracted_at=datetime.now(UTC).isoformat(),
        tool="apictx",
        tool_version=TOOL_VERSION,
        schema_version=schema_version,
    )
    emit_res = emit(objs, manifest, output.report, outdir)
    if not emit_res.ok:
        return Result.failure((emit_res.error,) if emit_res.error is not None else tuple())
    return Result.success(None)
