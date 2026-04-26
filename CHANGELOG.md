# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-26

### Added

- `gleif download`: async download of Level 1 LEI, Level 2 Relationships, and
  Level 2 Reporting Exceptions ZIP files from the GLEIF golden copy API, with
  freshness checking via publish-date markers
- `gleif load`: bulk CSV-to-DuckDB load with column selection, renaming, index
  creation, and load-metadata tracking
- `gleif refresh`: combined download + load in one step
- `gleif lei <LEI>`: full relationship report including direct parent, ultimate
  parent, children, siblings, and reporting exceptions; optional `--isin` flag
  fetches ISIN mappings from the GLEIF REST API
- `gleif name <QUERY>`: substring search across legal entity names with optional
  `--limit` and `--isin` flags
- `gleif status`: record counts for all three database tables
- Rich terminal output with tables and color for all report views
- Local DuckDB database at `~/.local/share/gleif/gleif.duckdb`
- GitHub Actions CI: pytest (65% coverage gate), ruff, basedpyright
- GitHub Actions Security Analysis: CodeQL, Bandit, OSV Scanner, Dependency Review
- Sigstore keyless signing and SPDX SBOM generation on tagged releases
- Pre-commit hooks: ruff, basedpyright, bandit, detect-secrets, markdownlint,
  yamllint, darglint, interrogate

[Unreleased]: https://github.com/ByronWilliamsCPA/gleif/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ByronWilliamsCPA/gleif/releases/tag/v0.1.0
