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

Tests use in-memory DuckDB with CSV fixtures defined in `tests/conftest.py`. They do not require downloading GLEIF data.

```bash
# Run all tests with coverage
uv run pytest

# Single file
uv run pytest tests/test_queries.py

# Single test
uv run pytest tests/test_queries.py::TestGetEntity::test_finds_existing_entity

# Show coverage report
uv run pytest --cov-report=html && open htmlcov/index.html
```

### Test fixtures

The `loaded_db` fixture in `conftest.py` provides a pre-populated in-memory DuckDB with four entities forming a hierarchy:

```
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
# Format code
uv run ruff format .

# Lint and auto-fix
uv run ruff check --fix .

# Type check
uv run basedpyright src
```

Ruff is configured with the PyStrict-aligned rule set at 88-character line length. BasedPyright runs in `standard` mode with strict inference for lists, dicts, and sets.

## Pre-commit hooks

Pre-commit runs automatically on every commit. To run all hooks manually:

```bash
uv run pre-commit run --all-files
```

Configured hooks:

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
# Install docs dependencies (if not already installed)
uv sync --all-extras

# Serve locally with live reload
uv run mkdocs serve

# Build static site
uv run mkdocs build

# Deploy to GitHub Pages
uv run mkdocs gh-deploy
```

The site is built into `site/` (gitignored).

## CI/CD

Three GitHub Actions workflows run on every PR and push to `main`:

### CI (`ci.yml`)

Runs on PRs and pushes to `main` and `develop`.

1. **Test suite**: pytest with 80% coverage gate
2. **Quality checks**: `ruff format --check`, `ruff check`, `basedpyright`
3. **CI gate**: blocks merge if any step fails

All action steps are pinned to commit SHAs.

### Security (`security-analysis.yml`)

Runs on PRs and weekly on a schedule (separate from CI to save ~5-8 min per PR).

1. **CodeQL**: static analysis for Python vulnerabilities
2. **Dependency review**: license compliance (GPL denied) and known CVEs
3. **Bandit**: Python security linting
4. **OSV scanner**: dependency vulnerability scanning

### Qlty (`qlty.yml`)

Triggered after CI succeeds. Uploads `coverage.xml` to [Qlty Cloud](https://qlty.sh/) for coverage trend tracking and code quality analysis.

Qlty also runs locally via pre-commit hooks:
- `qlty fmt` on pre-commit (auto-formats staged files)
- `qlty check` on pre-push (runs the full plugin suite)

## Security

Dependencies are scanned by `pip-audit` and OSV scanner on every CI run. Any unfixed CVEs must be documented in `docs/known-vulnerabilities.md` following the template in `docs/known-vulnerabilities-template.md`.

Never suppress `pip-audit` output without a documented entry. Entries age out after 60 days and block releases if unaddressed.

## Release checklist

Before tagging a release:

- [ ] `CHANGELOG.md` updated with the release version and date
- [ ] All tests pass above coverage thresholds
- [ ] No vulnerabilities older than 60 days in `docs/known-vulnerabilities.md`
- [ ] Version tag follows SemVer (`v0.1.0`, `v1.0.0`, etc.)
- [ ] `uv run pre-commit run --all-files` passes cleanly
