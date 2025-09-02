# ADR 0002: Priorities to Advance apictx Accuracy and Coverage

Date: 2025-09-02
Status: Proposed

## Context
apictx aims to extract faithful, machine-readable API context for Python libraries. The current implementation parses with LibCST, extracts symbols, links class bases by simple name, validates against a JSON Schema, and indexes for exact and approximate lookup. The test suite currently passes (10/10), indicating a solid baseline. This ADR identifies the highest-impact areas to improve accuracy, portability, and extensibility, with concrete references to current code locations.

## Findings (with references)
- Linking is name-only for class bases; no import/alias resolution or fully-qualified linking:
  - `src/apictx/pipeline.py:72` (`link`) resolves bases by simple name and picks the lexicographically first FQN.
- Public API determination ignores `__all__`:
  - `src/apictx/extract.py:161` (`extract_module`) derives visibility solely from leading underscore.
- Parameter modeling lacks defaults and parameter kind (pos-only, kw-only, varargs, varkw):
  - `src/apictx/extract.py:32` (`_iter_parameters`) enumerates params but does not capture kind/defaults.
  - `src/apictx/models.py:9` (`Parameter`) has only `name`, `type`.
- No source location metadata (file path, line/col) on symbols:
  - All symbol dataclasses in `src/apictx/models.py:16`, `:22`, `:40`, `:56`, `:64` omit location info.
- Docstring “Raises” parsing is heuristic and limited to a narrow header format:
  - `src/apictx/extract.py:52` (`_parse_docstring_raises`) scans for simple "Raises:" patterns, misses Numpy/Google/reST variants and inline references.
- Deprecation detection is decorator-string based and coarse:
  - `src/apictx/extract.py:83`+ in `_function_from_def` flags `deprecated` when a decorator contains "deprecated"; does not consider docstring sections or `warnings.warn` usage.
- Schema lacks fields for richer parameters and locations:
  - `src/apictx/schema.json:1` defines `parameter` with only `name`/`type`; no `default`, `kind`, or location across entities.
- Query capabilities are basic (FQN or grams); no filters by kind/visibility/owner:
  - `src/apictx/pipeline.py:198` (`query_index`) returns raw objects without server-side filtering.
- CLI is functional but minimal; no `--public-only` extraction or version command:
  - `src/apictx/cli.py:1` defines `extract` and `query` subcommands; no filtering flags.

## Priorities (highest impact first)
1) Import Graph & Name Resolution for Linking
- Build per-module import tables and a simple symbol table to resolve bases, owners, and (future) references beyond simple name.
- Replace simple-name linking with module-aware resolution, honoring aliases (`import x as y`, `from a import b as c`).
- Target: robust `base_fqns` resolution across modules and packages.
- Affects: `src/apictx/pipeline.py:72`, `src/apictx/extract.py:161`.

2) Public API via `__all__`
- Parse `__all__` at module/package level. When present, mark symbols not exported as `private` even if they don’t start with `_`.
- Optionally add a flag to record `exported: bool` for clarity.
- Affects: `src/apictx/extract.py:161`, schema additions.

3) Richer Parameter Model
- Extend `Parameter` with `default` (text), `kind` (`posonly`, `pos`, `kwonly`, `vararg`, `kwvar`), and maybe `required` boolean.
- Extract defaults and kinds from `libcst` param nodes.
- Update schema and all emit/validate/index paths.
- Affects: `src/apictx/models.py:9`, `src/apictx/extract.py:32`, `src/apictx/schema.json:1`.

4) Symbol Location Metadata
- Add `location` to all symbols: `{ "path": str, "line": int, "column": int }` (start position).
- Enables traceability, better AI prompts, and dedup/debugging.
- Affects: symbol dataclasses in `src/apictx/models.py` and extraction in `src/apictx/extract.py:161`.

5) Docstring Parsing: Raises/Deprecated/Sections
- Support Google/Numpy/reST styles for `Raises`, and detect `Deprecated` sections.
- Consider lightweight structured parse with regex heuristics and section normalization.
- Optionally link raised exception names using the new name-resolution mechanism.
- Affects: `src/apictx/extract.py:52`, schema if adding fields.

6) Schema Evolution (v0.3)
- Add fields: `parameter.default`, `parameter.kind`, `symbol.location`, maybe `exported`.
- Maintain backward compatibility: bump `x-apictx-schema-version` and keep validators tolerant of older fields.
- Affects: `src/apictx/schema.json:1`, `src/apictx/pipeline.py:110` (validation), emit/index.

7) Query Enhancements
- Extend `query_index` to filter by `kind`, `visibility`, `owner`, and optionally full-text over docstrings.
- Consider SQLite FTS5 virtual table for docstrings (optional, feature-flagged).
- Affects: `src/apictx/pipeline.py:198`.

8) CLI UX
- Add `--public-only` or `--visibility public` in `extract` command to emit only public symbols.
- Add `--kinds function,class,const,type` selector and `--version`/`--verbose` flags.
- Affects: `src/apictx/cli.py:1`.

## Suggested Implementation Sequence
- Phase 1 (Linking & Visibility):
  - Implement import graph + base linking (Priority 1).
  - Add `__all__` export logic (Priority 2).
  - Update tests to cover cross-module base resolution and `__all__` semantics.
- Phase 2 (Schema & Parameters):
  - Extend `Parameter` + schema (Priority 3) and add symbol `location` (Priority 4).
  - Update validation, emit, and index. Add migration note for consumers.
- Phase 3 (Docstrings & Query):
  - Improve raises/deprecation parsing (Priority 5).
  - Add query filters (Priority 7) and CLI options (Priority 8).

## Test Additions
- Cross-module inheritance with aliases (`from base import B as X`) resolves `base_fqns`.
- Packages with `__all__` — ensure visibility/export flags match expectations.
- Defaulted parameters and kinds across all param forms (posonly, varargs, kwonly).
- Location presence and stability (line numbers) across runs.
- Docstring style matrix (Google, Numpy, reST) for `Raises` and `Deprecated`.
- Query filters by kind/visibility and combined predicates.

## Risks and Mitigations
- More complex linking may be slower: use caches and only resolve needed names (e.g., bases and, later, raises).
- Schema bump: document in `docs/USAGE.md`, provide version in manifest (already emitted) to coordinate consumers.
- Line numbers can shift with whitespace: document stability guarantees relate to source snapshot (commit), not across arbitrary edits.

## Decision
Proceed with Phase 1 (linking and `__all__`) immediately; draft schema changes for Phase 2 to socialise before implementation to avoid churn. Maintain deterministic output and strict validation at each step.
