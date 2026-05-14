# GitHub Copilot Code Review Instructions

Focus on: business logic correctness, error handling completeness, edge cases,
concurrency issues, and security logic flaws.

Exclude from review: code style, formatting, and whitespace. These are enforced
by pre-commit hooks and ruff; do not flag them.

## Project context

- Type: Python CLI tool
- Language: Python 3.11+
- Key libraries: Typer (CLI), DuckDB (local SQL database), httpx (async HTTP), Rich (terminal output)

## Code style

- Formatter and linter: ruff (88-character line length)
- Type checker: basedpyright in strict mode
- Do NOT suggest black, mypy, or safety as alternatives

## Testing

- Framework: pytest
- Database fixtures: in-memory DuckDB populated via tests/conftest.py
- Coverage target: 65% line (interim; will be raised to 80% once download.py and CLI command tests are added), 70% branch

## Patterns to reinforce

- Use async httpx for all HTTP downloads
- Use parameterized DuckDB queries in queries.py (never string-interpolated SQL)
- Use Rich console/tables for all terminal output in cli.py

## Patterns to avoid

- Do not add `# type: ignore` comments; fix the underlying type error instead
- Do not use subprocess or os.system for external commands
- Do not introduce synchronous HTTP calls in async download paths
