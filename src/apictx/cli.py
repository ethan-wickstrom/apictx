from __future__ import annotations

import json
from pathlib import Path
import ast
import tomllib
import libcst as cst
import libcst.matchers as m

import typer

from .errors import Error
from .pipeline import query_index, run_pipeline
from .result import Result


def detect_metadata(root: Path, package: str | None, version: str | None) -> tuple[str, str]:
    pkg: str
    ver: str
    if package is None:
        name: str | None = _detect_package_name(root)
        if name is None:
            raise typer.BadParameter("could not determine package name")
        pkg = name
    else:
        pkg = package
    if version is None:
        ver_detected: str | None = _detect_package_version(root, pkg)
        if ver_detected is None:
            raise typer.BadParameter("could not determine package version")
        ver = ver_detected
    else:
        ver = version
    return pkg, ver


def _detect_package_name(root: Path) -> str | None:
    pyproject_path: Path = root / "pyproject.toml"
    if pyproject_path.is_file():
        data: dict[str, object]
        with pyproject_path.open("rb") as file:
            data = tomllib.load(file)
        project_obj: object | None = data.get("project")
        project: dict[str, object] | None = project_obj if isinstance(project_obj, dict) else None
        name_obj: object | None = None
        if project is not None:
            name_obj = project.get("name")
        if not isinstance(name_obj, str):
            tool_obj: object | None = data.get("tool")
            tool: dict[str, object] | None = tool_obj if isinstance(tool_obj, dict) else None
            if tool is not None:
                poetry_obj: object | None = tool.get("poetry")
                poetry: dict[str, object] | None = poetry_obj if isinstance(poetry_obj, dict) else None
                if poetry is not None:
                    name_obj = poetry.get("name")
        if isinstance(name_obj, str):
            return name_obj
    candidates: set[str] = set()
    search_dirs: tuple[Path, ...] = (root, root / "src")
    search_dir: Path
    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue
        entries: list[Path] = [entry for entry in search_dir.iterdir() if entry.is_dir()]
        entry: Path
        for entry in entries:
            init_path: Path = entry / "__init__.py"
            if init_path.is_file():
                candidates.add(entry.name)
    if len(candidates) == 1:
        return next(iter(candidates))
    return None


def _detect_package_version(root: Path, package: str) -> str | None:
    class _VersionVisitor(cst.CSTVisitor):
        version: str | None

        def __init__(self) -> None:
            self.version = None

        def visit_Assign(self, node: cst.Assign) -> None:
            if self.version is not None:
                return
            if (
                len(node.targets) == 1
                and m.matches(node.targets[0].target, m.Name("__version__"))
                and m.matches(node.value, m.SimpleString())
            ):
                value_node: cst.SimpleString = cst.ensure_type(node.value, cst.SimpleString)
                self.version = ast.literal_eval(value_node.value)

    package_paths: tuple[Path, ...] = (root / package, root / "src" / package)
    package_path: Path
    for package_path in package_paths:
        init_file: Path = package_path / "__init__.py"
        if init_file.is_file():
            source: str = init_file.read_text(encoding="utf-8")
            module: cst.Module = cst.parse_module(source)
            visitor: _VersionVisitor = _VersionVisitor()
            module.visit(visitor)
            return visitor.version
    return None


app: typer.Typer = typer.Typer()


@app.command()
def extract(
    root: Path,
    package: str | None = None,
    version: str | None = None,
    commit: str = "",
    out: Path = Path("build"),
    workers: int = 4,
) -> None:
    """Run pipeline on a source tree."""
    pkg: str = package if package is not None else ""
    ver: str = version if version is not None else ""
    if package is None or version is None:
        try:
            pkg, ver = detect_metadata(root, package, version)
        except typer.BadParameter as err:
            typer.echo(str(err), err=True)
            raise typer.Exit(1) from err
    result: Result[None, tuple[Error, ...]] = run_pipeline(
        root,
        pkg,
        ver,
        commit,
        workers,
        out,
    )
    if result.ok:
        return
    errors: tuple[Error, ...] = result.error or ()
    for error in errors:
        typer.echo(f"{error.code}:{error.path}:{error.message}")
    raise typer.Exit(1)


@app.command()
def query(
    db: Path,
    fqn: str | None = None,
    approx: str | None = None,
    limit: int = 5,
    kind: str | None = None,
    visibility: str | None = None,
    owner: str | None = None,
) -> None:
    """Query the SQLite index."""
    if (fqn is None) == (approx is None):
        typer.echo("Provide either --fqn or --approx", err=True)
        raise typer.Exit(2)
    res: Result[tuple[dict[str, object], ...], Error] = query_index(
        db,
        fqn=fqn,
        approx=approx,
        limit=limit,
        kind=kind,
        visibility=visibility,
        owner=owner,
    )
    if not res.ok or res.value is None:
        err: Error | None = res.error
        if err is not None:
            typer.echo(f"{err.code}:{err.path}:{err.message}")
        raise typer.Exit(1)
    objs: tuple[dict[str, object], ...] = res.value
    for obj in objs:
        typer.echo(json.dumps(obj, sort_keys=True))


if __name__ == "__main__":
    app()

