from __future__ import annotations

from pathlib import Path
import json
import sqlite3

from apictx.pipeline import run_pipeline, _to_grams
from apictx.result import Result
from apictx.errors import Error


def _write(pkg: Path, rel: str, content: str) -> None:
    path = pkg / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_link_and_index(tmp_path: Path) -> None:
    pkg: Path = tmp_path / "data_processor"
    pkg.mkdir()
    _write(
        pkg,
        "processor.py",
        (
            "class Processor:\n"
            "    def process(self, path: str) -> None:\n"
            "        pass\n"
        ),
    )
    _write(
        pkg,
        "csvproc.py",
        (
            "class ValidationError(Exception):\n"
            "    pass\n\n"
            "class CSVProcessor(Processor):\n"
            "    def process(self, path: str) -> None:\n"
            "        pass\n\n"
            "    def validate_schema(self) -> None:\n"
            "        \"\"\"Raises:\n"
            "        ValidationError: when schema invalid\n"
            "        \"\"\"\n"
            "        raise ValidationError('boom')\n"
        ),
    )
    outdir: Path = tmp_path / "out"
    res: Result[None, tuple[Error, ...]] = run_pipeline(pkg, "data_processor", "0.1.0", "abcdef", 1, outdir)
    assert res.ok

    # Validation report asserts closure
    report_path: Path = outdir / "validation.json"
    report: dict[str, object] = json.loads(report_path.read_text(encoding="utf-8"))
    assert int(report["symbol_count"]) >= 3
    assert int(report.get("missing_references", 0)) == 0

    # Manifest includes required metadata
    manifest_path: Path = outdir / "manifest.json"
    manifest: dict[str, object] = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["package"] == "data_processor"
    assert manifest["version"] == "0.1.0"
    assert manifest["tool"] == "apictx"
    assert isinstance(manifest["tool_version"], str)
    assert isinstance(manifest["schema_version"], str)

    # Index lookups by FQN and approximate name
    db_path: Path = outdir / "index.sqlite3"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    fqn = "data_processor.csvproc.CSVProcessor"
    row = cur.execute("SELECT fqn FROM symbols WHERE fqn = ?", (fqn,)).fetchone()
    assert row and row[0] == fqn

    # Approximate name search using grams
    query = "csvprocesor"  # missing an 's'
    grams = _to_grams(query)
    placeholders = ",".join(["?"] * len(grams))
    sql = (
        "SELECT s.fqn, COUNT(*) as score FROM grams g JOIN symbols s ON s.id = g.id "
        f"WHERE g.gram IN ({placeholders}) GROUP BY s.id ORDER BY score DESC, s.fqn ASC LIMIT 1"
    )
    best = cur.execute(sql, list(grams)).fetchone()
    conn.close()
    assert best is not None
    assert best[0].endswith("CSVProcessor")

