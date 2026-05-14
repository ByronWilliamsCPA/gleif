# GEMINI.md

Gemini CLI configuration for this project.

## Project Overview

CLI tool that downloads GLEIF golden copy datasets, loads them into a local DuckDB
database, and queries LEI relationship hierarchies (parents, children, siblings,
reporting exceptions).

## Essential Commands

```bash
# Install dependencies
uv sync --all-extras

# Run the CLI
uv run gleif --help
uv run gleif download          # Download GLEIF datasets
uv run gleif load              # Load CSVs into DuckDB
uv run gleif refresh           # Download + load in one step
uv run gleif lei <LEI>         # Look up an LEI and display related entities
uv run gleif lei <LEI> --isin  # Include ISIN mappings from GLEIF API
uv run gleif name <QUERY>      # Search entities by legal name (substring)
uv run gleif name <QUERY> --isin --limit 20  # With ISIN data and result limit
uv run gleif status            # Show database record counts

# Run tests
uv run pytest

# Lint and type check
uv run ruff format .
uv run ruff check --fix .
uv run basedpyright src

# Pre-commit
uv run pre-commit run --all-files
```

## Code Style

- Ruff at 88-character line length for formatting and linting
- BasedPyright in strict mode for type checking
- Conventional commits; GPG-signed commits required

## Architecture

Data pipeline: GLEIF REST API → ZIP download → CSV extract → DuckDB bulk load →
SQL queries → Rich terminal output. Source lives in `src/gleif/`; tests use
in-memory DuckDB with fixtures in `tests/conftest.py`.

For full architecture details, dataset schemas, and CI/CD configuration, see AGENTS.md.
