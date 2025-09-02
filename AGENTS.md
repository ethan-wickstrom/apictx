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
