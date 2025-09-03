from __future__ import annotations

from pathlib import Path
import json
from hypothesis import given, strategies as st, settings, HealthCheck

from apictx.pipeline import run_pipeline, query_index
from apictx.result import Result
from apictx.errors import Error


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
@given(base_name=st.from_regex(r"[A-Z][A-Za-z0-9_]{0,8}", fullmatch=True))
def test_class_linkage_base_resolution(base_name: str, tmp_path: Path) -> None:
    root: Path = tmp_path / f"pkg_{base_name}"
    root.mkdir()
    (root / "base.py").write_text(f"class {base_name}:\n    pass\n", encoding="utf-8")
    (root / "sub.py").write_text(
        f"class Sub{base_name}({base_name}):\n    pass\n",
        encoding="utf-8",
    )
    out: Path = tmp_path / "out"
    res: Result[None, tuple[Error, ...]] = run_pipeline(
        root, "pkg", "0.0.1", "abc", 1, out
    )
    assert res.ok

    # validation report should have zero missing references
    report: dict[str, object] = json.loads(
        (out / "validation.json").read_text(encoding="utf-8")
    )
    assert int(report.get("missing_references", 0)) == 0

    # query subclass and assert its base_fqns includes the base class fqn
    subclass_fqn = f"pkg.sub.Sub{base_name}"
    got = query_index(out / "index.sqlite3", fqn=subclass_fqn)
    assert got.ok and got.value is not None and len(got.value) == 1
    subclass = got.value[0]
    assert subclass["kind"] == "class"
    base_fqns = tuple(subclass.get("base_fqns", []))
    assert f"pkg.base.{base_name}" in base_fqns
