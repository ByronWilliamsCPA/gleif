# Development

## Local setup

```bash
# Clone and install all dependencies (runtime + dev)
git clone https://github.com/ByronWilliamsCPA/gleif.git
cd gleif
uv sync --all-extras

# Install pre-commit hooks (one-time)
uv run pre-commit install
```

## Running tests

Tests use in-memory DuckDB with CSV fixtures in `tests/conftest.py`. No downloaded GLEIF data is required.

```bash
# Run all tests with coverage
uv run pytest

# Single file
uv run pytest tests/test_queries.py

# Single test
uv run pytest tests/test_queries.py::TestGetEntity::test_finds_existing_entity

# Open HTML coverage report
uv run pytest --cov-report=html && open htmlcov/index.html
```

### Test fixture hierarchy

The `loaded_db` fixture provides a pre-populated in-memory DuckDB with four entities:

```text
Ultimate Parent
    └── Parent
            ├── Child A
            └── Child B
```

CLI tests use `typer.testing.CliRunner` with on-disk DuckDB files in `tmp_path`.

### Coverage thresholds

| Scope | Threshold |
| ----- | --------- |
| Line coverage | 80% |
| Branch coverage | 70% |
| Critical paths | 90% |
| New patches | 90% |

## Linting and type checking

```bash
uv run ruff format .            # Format code
uv run ruff check --fix .       # Lint and auto-fix
uv run basedpyright src         # Type check
```

Ruff uses the PyStrict-aligned rule set at 88-character line length. BasedPyright runs in `standard` mode with strict inference for lists, dicts, and sets.

## Pre-commit hooks

Pre-commit runs automatically on every commit. To run manually:

```bash
uv run pre-commit run --all-files
```

| Hook | Purpose |
| ---- | ------- |
| `trailing-whitespace` | Remove trailing whitespace |
| `end-of-file-fixer` | Ensure files end with a newline |
| `check-yaml` / `check-json` / `check-toml` | Validate config files |
| `detect-private-key` | Block accidental key commits |
| `ruff` (format + lint) | Python formatting and linting |
| `markdownlint` | Markdown style enforcement |
| `yamllint` | YAML style enforcement |
| `bandit` | Python security scanning |

## Building the documentation

```bash
uv run mkdocs serve     # Live-reload local preview
uv run mkdocs build     # Build static site to site/
uv run mkdocs gh-deploy # Deploy to GitHub Pages
```

The `site/` output directory is gitignored.

## CI/CD

Three GitHub Actions workflows run on every PR and push to `main`:

### CI (`ci.yml`)

1. Test suite with 80% coverage gate
2. Quality checks: `ruff format --check`, `ruff check`, `basedpyright`
3. CI gate that blocks merge on any failure

All action steps are pinned to commit SHAs.

### Security (`security-analysis.yml`)

Runs on PRs and weekly on a schedule (separate workflow to save ~5-8 min per PR):

1. CodeQL static analysis
2. Dependency review (GPL denied, known CVEs blocked)
3. Bandit security linting
4. OSV dependency vulnerability scanning

### Qlty (`qlty.yml`)

Triggered after CI succeeds. Uploads `coverage.xml` to Qlty Cloud for coverage trend tracking.

Qlty also runs locally via pre-commit: `qlty fmt` on pre-commit (auto-format staged files), `qlty check` on pre-push.

## Release checklist

- [ ] `CHANGELOG.md` updated with version and date
- [ ] All tests pass above coverage thresholds
- [ ] No vulnerabilities older than 60 days
- [ ] `uv run pre-commit run --all-files` passes cleanly
- [ ] Version tag follows SemVer (`v0.1.0`, `v1.0.0`, etc.)
