# Using apictx Outputs with AI Systems

- Generate context:
  - Extract: `uv run -m apictx.cli extract path/to/pkg --package mylib --version 1.2.3 --commit abc123 --out build/mylib-1.2.3`
  - Artifacts:
    - `symbols.jsonl` — one JSON object per symbol, stable and schema‑validated
    - `index.sqlite3` — exact FQN lookup and approximate name search (grams)
    - `manifest.json` — package, version, commit, extraction time, tool and schema versions
    - `validation.json` — counts and reference checks

- Query the index:
  - Exact: `uv run -m apictx.cli query --db build/mylib-1.2.3/index.sqlite3 --fqn mylib.module.Func`
  - Approx: `uv run -m apictx.cli query --db build/mylib-1.2.3/index.sqlite3 --approx serializer --limit 10`

- Prompting patterns:
  - Small tasks: Select top‑N relevant symbols via approximate search and include JSON objects directly in the prompt.
  - RAG pipelines: Use the SQLite index to retrieve by FQN/name; feed only symbols required for the user’s task.
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

