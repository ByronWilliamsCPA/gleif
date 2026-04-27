# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Release workflow (`release.yml`): Sigstore keyless signing and SPDX SBOM
  generation via `anchore/sbom-action` on tagged releases
- OpenSSF Scorecard workflow (`scorecard.yml`) for continuous supply-chain
  health scoring
- `SECURITY.md`, `CONTRIBUTING.md` (OpenSSF required community files)
- `CODEOWNERS`, darglint, and interrogate pre-commit hooks

### Fixed

- Security Analysis: moved `continue-on-error` from job level to step level on
  `codeql-analysis` so real CodeQL failures propagate to the security gate
- Security Analysis: `dorny/paths-filter` silently skipped all jobs on weekly
  `schedule` triggers (no diff to compare); added
  `|| github.event_name != 'pull_request'` to CodeQL, Bandit, and OSV scanner
  job conditions so weekly scans always run
- `_extract_zip()`: added `resolve().is_relative_to()` check before extraction
  to prevent ZIP path traversal via crafted `../../` entry names
- `create_schema()` docstring: corrected to reflect it only creates the
  `load_metadata` tracking table, not all data tables
- `docs/development.md`: corrected BasedPyright mode (`strict`, not
  `standard`), coverage threshold (65%, not 80%), and dependency scanning
  description (dependency-review on PRs, osv-scanner via security workflow)
- `docs/known-vulnerabilities.md`: softened OpenSSF release gate claim to
  reflect a policy requirement rather than automated CI enforcement

### Security

- Fixed ZIP path traversal in `_extract_zip()` (no CVE; internal finding)

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
