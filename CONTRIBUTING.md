# Contributing

## Development Setup

```bash
git clone https://github.com/ByronWilliamsCPA/gleif.git
cd gleif
uv sync --all-extras
uv run pre-commit install
```

## Running Tests

```bash
uv run pytest                           # full suite with coverage
uv run pytest tests/test_queries.py     # single file
uv run pytest -k test_finds_existing    # single test by name
```

Tests use an in-memory DuckDB instance; no external services are required.

## Code Style

```bash
uv run ruff format .        # auto-format
uv run ruff check --fix .   # lint with auto-fix
uv run basedpyright src     # type checking
```

These run automatically on every commit via pre-commit hooks.

## Submitting a Pull Request

1. Fork the repo and create a branch from `main`.
2. Write tests for any new behavior.
3. Ensure `uv run pre-commit run --all-files` passes cleanly.
4. Open a PR with a clear description of the change and why it is needed.

Follow [Conventional Commits](https://www.conventionalcommits.org/):
`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`.

## Reporting Bugs

Open a [GitHub Issue](https://github.com/ByronWilliamsCPA/gleif/issues) with:

- The command you ran and the full error output
- Your Python version (`python --version`) and OS

For security vulnerabilities, see [SECURITY.md](SECURITY.md) instead.
