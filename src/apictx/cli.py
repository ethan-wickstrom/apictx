from __future__ import annotations

import json
from pathlib import Path
import ast
import tomllib
import libcst as cst
import libcst.matchers as m
import importlib.util

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
    # Check if root itself is a package directory
    if (root / "__init__.py").exists():
        return root.name
    
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
                try:
                    self.version = ast.literal_eval(value_node.value)
                except (ValueError, SyntaxError):
                    # If the version string is invalid, continue
                    pass

    # Build package_paths tuple including root if it's the package directory
    package_paths: list[Path] = []
    
    # Check if root itself is the package directory
    if (root / "__init__.py").exists() and root.name == package:
        package_paths.append(root)
    
    # Add standard paths
    package_paths.append(root / package)
    package_paths.append(root / "src" / package)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_package_paths = []
    for path in package_paths:
        if path not in seen:
            seen.add(path)
            unique_package_paths.append(path)
    
    package_path: Path
    for package_path in unique_package_paths:
        init_file: Path = package_path / "__init__.py"
        if init_file.is_file():
            try:
                source: str = init_file.read_text(encoding="utf-8")
                module: cst.Module = cst.parse_module(source)
                visitor: _VersionVisitor = _VersionVisitor()
                module.visit(visitor)
                if visitor.version is not None:
                    return visitor.version
            except Exception:
                # If parsing fails, continue to the next path
                continue
    return None


def _resolve_source(source: str) -> tuple[Path, str | None]:
    """
    Resolve a source string to a filesystem path and optional package name.
    
    Args:
        source: Either a filesystem path or a module name
        
    Returns:
        A tuple of (root_path, package_name) where package_name is None
        if it couldn't be determined
        
    Raises:
        typer.BadParameter: If the source cannot be resolved
    """
    # First, try to resolve as a filesystem path
    path = Path(source).resolve()
    if path.exists():
        # If it's a directory with __init__.py, it's a package
        if path.is_dir() and (path / "__init__.py").exists():
            return path, path.name
        # If it's a file, return its parent directory
        if path.is_file():
            return path.parent, None
        # If it's a directory without __init__.py, return it with no package name
        return path, None
    
    # If not a filesystem path, try to resolve as a module name
    try:
        spec = importlib.util.find_spec(source)
        if spec is None:
            raise typer.BadParameter(f"Could not find module or path: {source}")
        
        # Extract the root package name (first part of the module name)
        package_name = source.split('.')[0]
        
        # Determine the root directory of the module
        if spec.origin is not None:
            # For regular modules, use the parent directory
            root_path = Path(spec.origin).parent
        elif spec.submodule_search_locations:
            # For packages, use the first search location
            root_path = Path(spec.submodule_search_locations[0])
        else:
            raise typer.BadParameter(f"Could not determine location of module: {source}")
        
        # Verify that the root path exists
        if not root_path.exists():
            raise typer.BadParameter(f"Module directory does not exist: {root_path}")
        
        return root_path, package_name
    except (ImportError, AttributeError) as e:
        raise typer.BadParameter(f"Could not resolve module or path: {source}") from e


app: typer.Typer = typer.Typer()


@app.command()
def extract(
    source: str,
    package: str | None = None,
    version: str | None = None,
    commit: str = "",
    out: Path = Path("build"),
    workers: int = 4,
) -> None:
    """Run pipeline on a source tree.
    
    SOURCE can be either a filesystem path or a module name.
    """
    try:
        root_path, default_pkg = _resolve_source(source)
    except typer.BadParameter as err:
        typer.echo(str(err), err=True)
        raise typer.Exit(1) from err
    
    # If package is not provided, use the default from resolution
    if package is None:
        if default_pkg is None:
            typer.echo("Could not determine package name, please specify with --package", err=True)
            raise typer.Exit(1)
        package = default_pkg
    
    # If version is not provided, try to detect it
    if version is None:
        try:
            _, version = detect_metadata(root_path, package, None)
        except typer.BadParameter as err:
            typer.echo(f"Could not determine package version: {err}", err=True)
            typer.echo("Please specify with --version", err=True)
            raise typer.Exit(1) from err
    
    result: Result[None, tuple[Error, ...]] = run_pipeline(
        root_path,
        package,
        version,
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
