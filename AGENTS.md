Default to using uv instead of pip, virtualenv, poetry, or pyenv.

- Use `uv run <script.py>` instead of `python <script.py>` or `python3 <script.py>`
- Use `uv pip install` instead of `pip install` or `pip3 install`
- Use `uv add <package>` instead of `pip install <package>` in projects
- Use `uv init` instead of `poetry new` or manual `pyproject.toml` creation
- Use `uv sync` instead of `pip install -r requirements.txt` or `poetry install`
- Use `uv python install` instead of `pyenv install` or manual Python downloads
- Use `uv venv` instead of `python -m venv` or `virtualenv`
- Use `uv build` and `uv publish` instead of `python -m build` and `twine`

## Project Management

uv handles virtual environments automatically. Don't manually activate/deactivate.

Initialize projects:
```bash
uv init --app        # For applications
uv init --lib        # For libraries  
uv init --script     # For single scripts
```

Manage dependencies:
```bash
uv add requests              # Add dependency
uv add --dev pytest         # Add dev dependency
uv remove requests          # Remove dependency
uv sync                     # Sync environment with lockfile
uv lock                     # Update lockfile
```

## Python Management

uv manages Python installations. Don't use pyenv, conda, or system Python.

```bash
uv python install 3.12      # Install Python 3.12
uv python list              # List available Pythons
uv python pin 3.12          # Pin project to Python 3.12
```

## Running Code

Use `uv run` for all script execution:

```bash
uv run script.py                    # Run script with project deps
uv run -m pytest                     # Run module
uv run --with numpy script.py        # Run with additional package
uv run --isolated script.py          # Run in isolated environment
```

## Scripts & Tools

Install and run tools without polluting global environment:

```bash
uv tool install ruff               # Install tool globally
uv tool run --from ruff ruff check # Run without installing
```

For inline script dependencies:
```python
# /// script
# dependencies = ["requests", "pandas"]
# ///

import requests
import pandas as pd
# script code here
```

Then: `uv run script.py` automatically installs dependencies.

## Environment Variables

uv automatically loads `.env` files with `uv run --env-file .env` or by default in projects.

## Performance

- uv is 10-100x faster than pip
- Parallel downloads and installations
- Global cache prevents re-downloads
- Use `--compile-bytecode` for faster imports

For more information, see https://docs.astral.sh/uv/

# Writing Commit Messages

Follow this protocol when preparing to commit code changes.
1. Identify changes: Run `git status`.
2. Validate changes: Apply appropriate syntax checks (e.g., `uv run -m py_compile [file]`, `bash -n [file]`) and run relevant tests (e.g., `uv run pytest`) for all modified files. If validation fails, fix the issues.
3. Review staged changes: Run `git diff --cached`.
4. Create commit message: Follow Conventional Commits pattern ("type(scope): description"). Detail complex changes in the commit body.
5. Verify commit: Run `git log -1 --stat`.

# Analyzing Code and Identifying Patterns

Start by inventorying the codebase using `rg --files` to list all files, filtering by directory or extension as needed. Search for structural patterns, anti-patterns, and repetitive code blocks using precise `rg` queries. Focus on high-impact areas such as core logic, shared utilities, and frequently modified files.

Cross-reference findings with version control history to assess context. Use `git blame` on critical files to identify ownership, change frequency, and potential technical debt hotspots. Check test coverage for impacted components by searching for corresponding test files or test functions.

Use insights for actionable recommendations. Prioritize based on impact, linking each suggestion to specific files, functions, or lines. For example:
- Replace duplicated logic in `utils/data_processing.py` (lines 15-30) with a shared helper function.
- Standardize error handling in `api/endpoints/` by adopting the pattern used in `api/users.py`.
- Break down monolithic functions exceeding 50 lines, starting with `services/report_generator.py:process_data()`.

Document patterns and recommendations in an ADR `.md` file in a `docs/` folder, ensuring traceability to the original code locations. Use these insights to guide refactoring, inform new feature design, and improve maintainability. Validate proposals by verifying consistency with existing conventions and testing strategies.
