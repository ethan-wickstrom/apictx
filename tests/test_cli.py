from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from apictx.cli import app, _detect_package_name, _detect_package_version, _resolve_source
from apictx.pipeline import run_pipeline
from apictx.result import Result
from apictx.errors import Error


class TestDetectPackageName:
    def test_detect_package_name_from_package_directory(self, tmp_path: Path) -> None:
        """Test that package name is detected from a directory with __init__.py."""
        pkg_dir = tmp_path / "mypackage"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
        
        result = _detect_package_name(tmp_path)
        assert result == "mypackage"

    def test_detect_package_name_from_pyproject(self, tmp_path: Path) -> None:
        """Test that package name is detected from pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "testpkg"\n',
            encoding="utf-8"
        )
        
        result = _detect_package_name(tmp_path)
        assert result == "testpkg"

    def test_detect_package_name_from_poetry(self, tmp_path: Path) -> None:
        """Test that package name is detected from poetry configuration."""
        (tmp_path / "pyproject.toml").write_text(
            '[tool.poetry]\nname = "poetry_pkg"\n',
            encoding="utf-8"
        )
        
        result = _detect_package_name(tmp_path)
        assert result == "poetry_pkg"

    def test_detect_package_name_from_child_directory(self, tmp_path: Path) -> None:
        """Test that package name is detected from child directory."""
        pkg_dir = tmp_path / "src" / "childpkg"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
        
        result = _detect_package_name(tmp_path)
        assert result == "childpkg"

    def test_detect_package_name_multiple_candidates(self, tmp_path: Path) -> None:
        """Test that None is returned when multiple package candidates exist."""
        (tmp_path / "pkg1").mkdir()
        (tmp_path / "pkg1" / "__init__.py").write_text("", encoding="utf-8")
        (tmp_path / "pkg2").mkdir()
        (tmp_path / "pkg2" / "__init__.py").write_text("", encoding="utf-8")
        
        result = _detect_package_name(tmp_path)
        assert result is None

    def test_detect_package_name_no_candidates(self, tmp_path: Path) -> None:
        """Test that None is returned when no package candidates exist."""
        result = _detect_package_name(tmp_path)
        assert result is None


class TestDetectPackageVersion:
    def test_detect_package_version_from_package_directory(self, tmp_path: Path) -> None:
        """Test that version is detected from package directory __init__.py."""
        pkg_dir = tmp_path / "mypackage"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text('__version__ = "1.2.3"', encoding="utf-8")
        
        result = _detect_package_version(tmp_path, "mypackage")
        assert result == "1.2.3"

    def test_detect_package_version_from_child_directory(self, tmp_path: Path) -> None:
        """Test that version is detected from child directory."""
        pkg_dir = tmp_path / "src" / "mypackage"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text('__version__ = "0.1.0"', encoding="utf-8")
        
        result = _detect_package_version(tmp_path, "mypackage")
        assert result == "0.1.0"

    def test_detect_package_version_invalid_version(self, tmp_path: Path) -> None:
        """Test that invalid version strings are handled gracefully."""
        pkg_dir = tmp_path / "mypackage"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text('__version__ = "invalid.version"', encoding="utf-8")
        
        result = _detect_package_version(tmp_path, "mypackage")
        assert result is None

    def test_detect_package_version_no_version(self, tmp_path: Path) -> None:
        """Test that None is returned when no version is found."""
        pkg_dir = tmp_path / "mypackage"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("# No version here', encoding="utf-8")
        
        result = _detect_package_version(tmp_path, "mypackage")
        assert result is None


class TestResolveSource:
    def test_resolve_source_package_directory(self, tmp_path: Path) -> None:
        """Test resolving a package directory."""
        pkg_dir = tmp_path / "mypackage"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
        
        root_path, package_name = _resolve_source(str(pkg_dir))
        assert root_path == pkg_dir
        assert package_name == "mypackage"

    def test_resolve_source_file(self, tmp_path: Path) -> None:
        """Test resolving a file path."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')", encoding="utf-8")
        
        root_path, package_name = _resolve_source(str(test_file))
        assert root_path == tmp_path
        assert package_name is None

    def test_resolve_source_directory_no_init(self, tmp_path: Path) -> None:
        """Test resolving a directory without __init__.py."""
        root_path, package_name = _resolve_source(str(tmp_path))
        assert root_path == tmp_path
        assert package_name is None

    def test_resolve_source_nonexistent_path(self, tmp_path: Path) -> None:
        """Test resolving a non-existent path."""
        with pytest.raises(typer.BadParameter, match="Could not find module or path"):
            _resolve_source(str(tmp_path / "nonexistent"))

    @patch('importlib.util.find_spec')
    def test_resolve_source_module_name(self, mock_find_spec, tmp_path: Path) -> None:
        """Test resolving a module name."""
        # Mock the spec
        mock_spec = mock_find_spec.return_value
        mock_spec.origin = str(tmp_path / "mymodule" / "__init__.py")
        mock_spec.submodule_search_locations = None
        
        root_path, package_name = _resolve_source("mymodule")
        assert root_path == tmp_path / "mymodule"
        assert package_name == "mymodule"
        mock_find_spec.assert_called_once_with("mymodule")

    @patch('importlib.util.find_spec')
    def test_resolve_source_module_name_with_submodule_locations(self, mock_find_spec, tmp_path: Path) -> None:
        """Test resolving a module name with submodule search locations."""
        # Mock the spec
        mock_spec = mock_find_spec.return_value
        mock_spec.origin = None
        mock_spec.submodule_search_locations = [str(tmp_path / "mymodule")]
        
        root_path, package_name = _resolve_source("mymodule.submodule")
        assert root_path == tmp_path / "mymodule"
        assert package_name == "mymodule"
        mock_find_spec.assert_called_once_with("mymodule.submodule")

    @patch('importlib.util.find_spec')
    def test_resolve_source_module_not_found(self, mock_find_spec) -> None:
        """Test resolving a non-existent module name."""
        mock_find_spec.return_value = None
        
        with pytest.raises(typer.BadParameter, match="Could not find module or path"):
            _resolve_source("nonexistent_module")

    @patch('importlib.util.find_spec')
    def test_resolve_source_module_no_origin_or_locations(self, mock_find_spec) -> None:
        """Test resolving a module with no origin or search locations."""
        mock_spec = mock_find_spec.return_value
        mock_spec.origin = None
        mock_spec.submodule_search_locations = None
        
        with pytest.raises(typer.BadParameter, match="Could not determine location of module"):
            _resolve_source("problematic_module")


class TestExtractCommand:
    def setup_method(self) -> None:
        self.runner = CliRunner()

    def test_extract_package_directory_auto_detect(self, tmp_path: Path) -> None:
        """Test extracting from a package directory with auto-detection."""
        # Create a simple package
        pkg_dir = tmp_path / "testpkg"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text('__version__ = "1.0.0"', encoding="utf-8")
        (pkg_dir / "module.py").write_text('def test_func(): pass', encoding="utf-8")
        
        out_dir = tmp_path / "out"
        
        result = self.runner.invoke(app, [
            "extract", str(pkg_dir), "--out", str(out_dir), "--commit", "abc123"
        ])
        
        assert result.exit_code == 0
        assert (out_dir / "symbols.jsonl").exists()
        assert (out_dir / "manifest.json").exists()
        assert (out_dir / "validation.json").exists()
        
        # Check manifest
        manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["package"] == "testpkg"
        assert manifest["version"] == "1.0.0"

    def test_extract_package_directory_explicit_params(self, tmp_path: Path) -> None:
        """Test extracting from a package directory with explicit parameters."""
        # Create a simple package
        pkg_dir = tmp_path / "testpkg"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text('', encoding="utf-8")
        (pkg_dir / "module.py").write_text('def test_func(): pass', encoding="utf-8")
        
        out_dir = tmp_path / "out"
        
        result = self.runner.invoke(app, [
            "extract", str(pkg_dir), "--package", "testpkg", "--version", "2.0.0",
            "--out", str(out_dir), "--commit", "abc123"
        ])
        
        assert result.exit_code == 0
        assert (out_dir / "symbols.jsonl").exists()
        
        # Check manifest
        manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["package"] == "testpkg"
        assert manifest["version"] == "2.0.0"

    def test_extract_package_directory_missing_package(self, tmp_path: Path) -> None:
        """Test extracting from a directory without auto-detectable package name."""
        # Create a directory without a package
        pkg_dir = tmp_path / "not_a_package"
        pkg_dir.mkdir()
        (pkg_dir / "file.py").write_text('print("hello")', encoding="utf-8")
        
        out_dir = tmp_path / "out"
        
        result = self.runner.invoke(app, [
            "extract", str(pkg_dir), "--out", str(out_dir), "--commit", "abc123"
        ])
        
        assert result.exit_code == 1
        assert "Could not determine package name" in result.stdout

    def test_extract_package_directory_missing_version(self, tmp_path: Path) -> None:
        """Test extracting from a package without auto-detectable version."""
        # Create a package without version
        pkg_dir = tmp_path / "testpkg"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text('', encoding="utf-8")
        (pkg_dir / "module.py").write_text('def test_func(): pass', encoding="utf-8")
        
        out_dir = tmp_path / "out"
        
        result = self.runner.invoke(app, [
            "extract", str(pkg_dir), "--out", str(out_dir), "--commit", "abc123"
        ])
        
        assert result.exit_code == 1
        assert "Could not determine package version" in result.stdout

    @patch('apictx.cli._resolve_source')
    @patch('apictx.cli.run_pipeline')
    def test_extract_nonexistent_path(self, mock_run_pipeline, mock_resolve_source) -> None:
        """Test extracting from a non-existent path."""
        mock_resolve_source.side_effect = typer.BadParameter("Could not find module or path: nonexistent")
        
        result = self.runner.invoke(app, ["extract", "nonexistent"])
        
        assert result.exit_code == 1
        assert "Could not find module or path: nonexistent" in result.stdout
        mock_run_pipeline.assert_not_called()

    @patch('apictx.cli._resolve_source')
    @patch('apictx.cli.detect_metadata')
    @patch('apictx.cli.run_pipeline')
    def test_extract_pipeline_error(self, mock_run_pipeline, mock_detect_metadata, mock_resolve_source, tmp_path: Path) -> None:
        """Test handling pipeline errors."""
        mock_resolve_source.return_value = (tmp_path, "testpkg")
        mock_detect_metadata.return_value = ("testpkg", "1.0.0")
        mock_run_pipeline.return_value = Result.failure((
            Error("pipeline", "Pipeline error", "test"),
        ))
        
        result = self.runner.invoke(app, ["extract", str(tmp_path)])
        
        assert result.exit_code == 1
        assert "pipeline:test:Pipeline error" in result.stdout