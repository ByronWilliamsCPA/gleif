# Contributing

## Development Setup

```bash
uv sync --all-extras
uv run pre-commit install
```

## Running Tests

```bash
uv run pytest
```

## Code Style

```bash
uv run ruff format .
uv run ruff check --fix .
uv run basedpyright src
```

## Submitting Changes

- Fork the repository and create a feature branch
- Follow conventional commits (feat:, fix:, chore:, docs:, etc.)
- Sign your commits (GPG)
- Open a pull request against main
- Ensure CI Gate and Security Gate pass
- One approving review required

## Pre-commit Hooks

Install hooks before your first commit:

```bash
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```
