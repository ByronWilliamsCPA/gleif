# AGENTS.md

Agent configuration for AI coding assistants (Codex, Gemini CLI, and similar tools).
This file follows the same structure as CLAUDE.md for consistency. For full project
context, architecture decisions, and detailed conventions, see CLAUDE.md.

## Project Overview

This is a CLI tool that downloads GLEIF (Global Legal Entity Identifier Foundation)
golden copy datasets, loads them into a local DuckDB database, and queries LEI
relationship hierarchies: parents, children, siblings, and reporting exceptions.

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
uv run gleif name <QUERY>      # Search entities by legal name (substring)
uv run gleif status            # Show database record counts

# Run tests
uv run pytest                  # All tests with coverage
uv run pytest tests/test_queries.py  # Single file

# Lint and type check
uv run ruff format .
uv run ruff check --fix .
uv run basedpyright src

# Pre-commit hooks
uv run pre-commit install          # First-time setup
uv run pre-commit run --all-files  # Run all hooks manually
```

## Architecture

Data pipeline: GLEIF REST API → ZIP download (httpx async) → CSV extract → DuckDB
bulk load → SQL queries → Rich terminal output.

### Three GLEIF datasets

| Dataset | Table | Key |
| ------- | ----- | --- |
| Level 1 LEI (`lei2`) | `lei_records` | `lei` (PK) |
| Level 2 Relationships (`rr`) | `relationships` | `(start_node_id, end_node_id, relationship_type)` |
| Level 2 Reporting Exceptions (`repex`) | `reporting_exceptions` | `(lei, exception_category)` |

Relationship direction: `start_node_id` is the child, `end_node_id` is the parent.

### Source layout (`src/gleif/`)

- `constants.py`: Dataset URLs, column mappings, `DatasetType` enum
- `download.py`: Async ZIP download with freshness checking
- `db.py`: DuckDB connection, table creation, index management
- `queries.py`: LEI lookup, parent/child traversal, name search
- `models.py`: Frozen dataclasses for all return types
- `isin.py`: ISIN lookup via GLEIF REST API
- `cli.py`: Typer app with Rich terminal rendering

## Testing

Tests use in-memory DuckDB with CSV fixtures in `tests/conftest.py`. The `loaded_db`
fixture provides a pre-populated database with 4 LEI entities forming a hierarchy:
Ultimate Parent → Parent → Child A + Child B. Run `uv run pytest` for the full suite.

## Code Style

- Formatter and linter: Ruff at 88-character line length
- Type checker: BasedPyright in standard mode with strict inference
- No `# noqa`, `# type: ignore`, or CI bypass flags; fix the actual issue
- Conventional commits required; all commits must be GPG-signed
