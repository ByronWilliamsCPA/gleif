# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Release workflow (`release.yml`): Sigstore keyless signing on tagged releases
- OpenSSF Scorecard workflow (`scorecard.yml`) for continuous supply-chain
  health scoring
- `SECURITY.md`, `CONTRIBUTING.md` (OpenSSF required community files)
- `CODEOWNERS` and interrogate pre-commit hooks

### Changed

- CI workflows (`ci.yml`, `release.yml`, `scorecard.yml`, `security-analysis.yml`)
  migrated from local reusable workflows to org-level reusables in
  `ByronWilliamsCPA/.github`, pinned to SHA
  `4e0fd54428d6745b04e2316f85d585109d7db02b` (closes #28). Local
  `reusable-codeql.yml` is retained because the org repo does not publish a
  `python-codeql.yml` equivalent.
- Release SBOM format changes from SPDX-JSON (`gleif-sbom.spdx.json`,
  produced by `anchore/sbom-action`) to CycloneDX-JSON (`dist/sbom.json`,
  produced by `cyclonedx-py` inside the org `python-release.yml`).
  Downstream consumers expecting SPDX should switch to CycloneDX or
  generate SPDX out of band.
- GitHub Actions bumped to major versions: `actions/checkout` v4→v6,
  `actions/setup-python` v5→v6, `sigstore/cosign-installer` v3→v4,
  `actions/attest-build-provenance` v1→v4, `fsfe/reuse-action` v4→v6,
  `actions/dependency-review-action` v4→v5; all now run Node 24 runtimes
- `release-sign.yml`: `cosign sign-blob` updated to use `--bundle` flag
  (cosign v3 deprecated `--output-signature`/`--output-certificate`); `.sig`
  and `.pem` outputs removed; only `.bundle` uploaded to release assets
- `slsa-provenance.yml`: moved all write permissions from workflow level to
  `build` job level (least-privilege, resolves S8233); added
  `persist-credentials: false` to checkout step; SHA-pinned org-level reusable
  workflow ref to replace mutable `@main` tag
- `reusable-security-analysis.yml`: corrected `deny-license-types` parameter
  to `deny-licenses`; GPL-2.0 and GPL-3.0 blocking now active

### Added

- Qlty workflow (`qlty.yml`): a `qlty-gate` job that runs `qlty check` in diff
  mode on pull requests and blocks merges introducing medium or higher severity
  issues, plus a weekly `qlty-health` job (Mondays 07:00 UTC) that runs a
  full-codebase scan in informational-only mode. Both delegate to the org-level
  reusable `ByronWilliamsCPA/.github/.github/workflows/python-qlty-gate.yml`.
- Release workflow (`release.yml`): Sigstore keyless signing and SPDX SBOM
  generation via `anchore/sbom-action` on tagged releases
- OpenSSF Scorecard workflow (`scorecard.yml`) for continuous supply-chain
  health scoring
- `SECURITY.md`, `CONTRIBUTING.md` (OpenSSF required community files)
- `CODEOWNERS`, darglint, and interrogate pre-commit hooks

### Fixed

- `.pre-commit-config.yaml`: moved TruffleHog `- repo: local` block before the
  top-level `exclude:` key; the block scalar was absorbing the entire hook
  definition as regex text, causing `InvalidConfigError` on every pre-commit run
- `.pre-commit-config.yaml`: replaced `command -v trufflehog && scan || skip`
  pattern with explicit `if/else`; the prior form silently exited 0 when
  TruffleHog was installed but the scan found secrets
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
- `docs/development.md`: corrected BasedPyright mode to `strict` and the
  dependency-scanning description (dependency-review on PRs, osv-scanner via
  security workflow) to match enforced settings
- `docs/known-vulnerabilities.md`: softened OpenSSF release gate claim to
  reflect a policy requirement rather than automated CI enforcement
- `reusable-scorecard.yml`: wired `SCORECARD_TOKEN` through the
  `workflow_call` secrets declaration and the `scorecard.yml` caller so the
  secret reaches the `ossf/scorecard-action` step; without this wiring the
  secret resolved to an empty string and the Branch-Protection check
  continued to score 0 despite the token being provisioned

### Security

- Fixed script injection in `reusable-python-quality.yml` (`githubactions:S7630`):
  `inputs.source-dir` was interpolated directly in a `run` block and is now routed
  through a `SOURCE_DIR` environment variable before shell expansion
- Replaced `permissions: read-all` with least-privilege permission blocks in all
  top-level workflow files (`githubactions:S8234`): `ci.yml`, `codeql.yml`,
  `qlty.yml`, `release.yml`, `scorecard.yml`, `security-analysis.yml`
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
