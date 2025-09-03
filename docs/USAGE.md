# Using apictx Outputs with AI Systems

- Generate context:
  - Extract from a package directory: `uv run -m apictx.cli extract src/apictx --package apictx --version 0.1.0 --commit abc123 --out build/apictx-0.1.0`
  - Extract from a module name: `uv run -m apictx.cli extract apictx --package apictx --version 0.1.0 --commit abc123 --out build/apictx-0.1.0`
  - Auto-detect package and version: `uv run -m apictx.cli extract src/apictx --commit abc123 --out build/apictx-0.1.0`
  - Auto-detect from installed module: `uv run -m apictx.cli extract requests --commit abc123 --out build/requests-latest`
  - Artifacts:
    - `symbols.jsonl` — one JSON object per symbol, stable and schema‑validated
    - `index.sqlite3` — exact FQN lookup and approximate name search (grams)
    - `manifest.json` — package, version, commit, extraction time, tool and schema versions
    - `validation.json` — counts and reference checks

- Query the index:
  - Exact: `uv run -m apictx.cli query --db build/apictx-0.1.0/index.sqlite3 --fqn apictx.cli.extract`
  - Approx: `uv run -m apictx.cli query --db build/apictx-0.1.0/index.sqlite3 --approx serializer --limit 10`

- Prompting patterns:
  - Small tasks: Select top‑N relevant symbols via approximate search and include JSON objects directly in the prompt.
  - RAG pipelines: Use the SQLite index to retrieve by FQN/name; feed only symbols required for the user's task.
  - Scope helpers: Prefer class methods over internal helpers; filter by `visibility == "public"`.

- Regeneration guidance:
  - Regenerate on every release or CI build of your library.
  - Keep past manifests and JSONL files; match by `(package, version, commit)`.
  - Merge contexts by concatenating JSONL files and re‑indexing into a combined SQLite database.

- Invariants enforced:
  - Fully qualified names are unique and stable.
  - Class `base_fqns`, function/constant `owner` references resolve inside the corpus.
  - Schema version stored in `manifest.json` (`schema_version`) and enforced via validation.

- Safety notes:
  - apictx does not execute code; it parses sources with LibCST only.
  - Outputs are deterministic for a given input tree and commit.

## CLI Usage

### Extract Command

The `extract` command generates API context from Python packages. It accepts either a filesystem path or a module name as the source:

```bash
# Extract from a package directory (auto-detects name and version)
uv run -m apictx.cli extract src/apictx

# Extract from a module name (auto-detects location and version)
uv run -m apictx.cli extract requests

# Specify package and version explicitly
uv run -m apictx.cli extract src/apictx --package apictx --version 0.1.0

# Specify output directory and commit hash
uv run -m apictx.cli extract src/apictx --out build/apictx-context --commit abc123
```

#### Auto-detection

When you don't specify `--package` or `--version`, `apictx` tries to auto-detect them:

- **Package name**: Detected from:
  - The directory name if it contains `__init__.py`
  - `pyproject.toml` (project.name or tool.poetry.name)
  - The first package directory found in the search path
  
- **Version**: Detected from:
  - `__init__.__version__` in the package directory
  - `pyproject.toml` (project.version or tool.poetry.version)

#### Examples

```bash
# Extract from the apictx source directory
uv run -m apictx.cli extract src/apictx

# Extract from an installed package
uv run -m apictx.cli extract numpy

# Extract with custom output location
uv run -m apictx.cli extract src/mylib --out build/mylib-api

# Extract with explicit package and version
uv run -m apictx.cli extract . --package mylib --version 1.2.3
```
