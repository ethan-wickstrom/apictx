from __future__ import annotations

import json
from pathlib import Path

import typer

from .errors import Error
from .pipeline import query_index, run_pipeline
from .result import Result


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
    result: Result[None, tuple[Error, ...]] = run_pipeline(
        root,
        package or "",
        version or "",
        commit,
        workers,
        out,
    )
    if result.ok:
        return
    errors: tuple[Error, ...] = result.error or ()
    for err in errors:
        typer.echo(f"{err.code}:{err.path}:{err.message}")
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

