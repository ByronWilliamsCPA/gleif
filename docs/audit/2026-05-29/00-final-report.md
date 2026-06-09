# 00 Final Report: Holistic Legacy & Architecture Audit

Repo: `ByronWilliamsCPA/gleif`. Commit `7fd3cb5`. Audited 2026-05-29 (UTC). Read-only.

This synthesizes seven domain reports (01-07 in this directory). It resolves overlaps between them rather than restating each. Where subagents produced the same finding twice, the merge is noted inline.

## 1. Repo map

- Purpose: a CLI that downloads GLEIF golden-copy datasets, loads them into local DuckDB, and queries LEI relationship hierarchies.
- Language / build: Python only. Build backend hatchling, package manager uv, `uv.lock` present (82 packages, all sha256-hashed, `uv lock --check` passes). No migration residue (no `requirements*.txt`, `setup.py`, `setup.cfg`, `poetry.lock`, or `Pipfile`).
- Runtime target: `requires-python = ">=3.11,<4"`; `.python-version` pins 3.11; ruff and basedpyright target 3.11. Python 3.11 reaches EOL 2026-10-31, about five months out.
- Size: 79 tracked files. 3,856 lines of Python (src ~1,530 LOC across 9 modules, tests ~1,330 LOC across 6 files). Largest modules: `queries.py` 642, `db.py` 472, `cli.py` 326, `download.py` 315, `rendering.py` 268, `models.py` 227.
- Tests: pytest with branch coverage, 67 tests, 0 skipped, 0 xfail, 67.30% coverage, `fail_under = 65`.
- Static analysis: Ruff (wide select set incl. C901), basedpyright strict, bandit, semgrep, detect-secrets, trufflehog, darglint, interrogate, plus Qlty (radarlint/SonarQube rules), CodeQL, Scorecard, Trivy, OSV, pip-audit, dependency-review, REUSE.
- CI: GitHub Actions, 15 workflow files, ~930 lines of YAML, 38 `uses:` references all 40-char SHA-pinned. Several reusable workflows were migrated to an org-level repo (commit `d538fbf`).
- Churn: the 15 most-churned files are all workflows and tool config (`security-analysis.yml` 19 edits, `ci.yml` 14, `scorecard.yml` 11). No application source file appears in the top churn list.
- Age: first commit 2026-04-24, latest 2026-05-24. The whole repo is about one month old; there is no aged code stratum.

Subagents run: all seven domains. Each had real substance here; none was skipped. The architecture and legacy domains came back near-clean (expected for new, tooled code); dependencies, security, CI/CD, code-quality, and docs carried the findings.

## 2. Code quality

The application code is the healthy part of this repo. basedpyright strict passes with 0 errors / 0 warnings / 0 notes. Zero `# type: ignore`, zero `cast(`, zero `Any` annotations, zero `TODO`/`FIXME`/`HACK`/`XXX` markers, zero ruff complexity violations (no function over the C901 threshold of 10). Modern idioms throughout: `from __future__ import annotations` in every code module, no legacy `typing.List/Optional`, no `%`/`.format`, pathlib everywhere, no dead or commented-out code. The legacy-patterns sweep found exactly one nit.

The weak spot is test coverage concentration, not code shape. Coverage is 67.30% but unevenly: `download.py` is 21% (the entire HTTP download, ZIP extract, and the zip-slip guard are unexercised), and the CLI `download`/`load`/`refresh` commands and both `--isin` branches have no tests. `rendering.py` is 62%. The pure query and parse logic is well-covered (`queries.py` 94%, `isin.py` 93%). So the untested surface is precisely the I/O and command-wiring layer, which is also where a regression would be most visible to a user. Three small duplications exist (a `RelatedEntity` row-mapping comprehension repeated four times in `queries.py`, an ISIN-extraction comprehension twice in `isin.py`, and `get_status` returning a loosely-typed `fetchall()` against a precise declared signature). These are minor and the fixes are mechanical.

Verdict on code quality: strong, with one real gap (download/CLI test coverage) that also blocks raising the coverage gate.

## 3. Architecture

Sound for a CLI this size. The module dependency graph is a one-way DAG with no cycles: `cli -> {rendering, queries, db, download, isin, constants}`, `queries -> {models, constants}`, `db -> {constants, download(TYPE_CHECKING only)}`, `rendering -> models`. Verified at runtime, not just by grep: importing the persistence/query layer does not pull in `cli` or `rendering`. `models.py` depends on nothing internal. Cohesion is good and the public API in `__init__.py` matches the layout.

Where the structure works against maintainers is narrow and worth fixing. `db.py` instantiates its own `rich.console.Console` and prints progress from `load_all` (db.py:68, 433-443), which is a layering leak the codebase otherwise avoids: `rendering.py` exists specifically to keep presentation out of the other layers, yet there are now two independent `Console()` instances and any library caller of `load_all` gets unsolicited stdout. The rest are config-centralization slips: the `'ACTIVE'` status literal is inlined in six query bodies, the ISIN base URL lives in `isin.py` rather than `constants.py`, and the download timeout / chunk size are unnamed magic numbers while `isin.py` names its equivalent. These point to modules authored in separate passes without a cross-module consistency sweep.

Verdict on architecture: the structure does not fight maintainers; the constant-scattering and the one persistence/UI leak are the only structural debts, all small.

## 4. Cross-cutting themes

Four root causes recur across domains and explain most findings better than any single report does.

The scaffolding-to-code ratio is inverted. 930 lines of workflow YAML and a nine-tool static-analysis stack sit on top of 1,530 lines of source. The most-churned files are all CI and tool config; no source file is in the top churn list. The compliance apparatus, not the application, is the thing this repo spends its effort on. For 1,530 LOC, SAST runs four ways (CodeQL, semgrep, bandit, radarlint), dependency scanning runs five ways (Trivy, OSV, pip-audit, dependency-review, Renovate alerts), and bandit alone runs in three places.

Dead or inert config is the single most common defect class. The `[tool.pip-audit]` ignore block in `pyproject.toml` is not read by pip-audit and suppresses nothing (SEC-01, also reported as DEP-02). `.codecov.yml` demands 80% but nothing uploads to Codecov (CICD-03). The SLSA provenance workflow triggers on a workflow named "Semantic Release" that does not exist, so it never auto-fires (CICD-01). A `# noqa: PLC0415` guards a Ruff preview rule the project does not enable, so it is inert (ARCH-05, also reported as LEG-01). Four `.gitkeep` dirs duplicate same-named pages (DOC-04). The pattern: config added speculatively or copied from a template, never wired to the thing it claims to govern, never re-checked.

Documentation and config drift from reality. The coverage threshold is stated five ways: 65 in `pyproject.toml`, 65 in `ci.yml`, 65 in `copilot-instructions.md`, but 80 in `.codecov.yml` and 80 in `docs/development.md`. The CHANGELOG records fixes ("coverage threshold corrected to 65%, basedpyright corrected to strict") that are not present in HEAD, so the doc claims work that did not land (DOC-01). The CHANGELOG `[Unreleased]` block both adds SPDX SBOM generation and replaces it with CycloneDX (DOC-06). The README tells users to `uv tool install gleif` and renders a PyPI badge for a package that is private and unpublished (DOC-05). Internal process essays and an audit retrospective listing unremediated defects are published into the user docs site (DOC-03).

The Python version is governed inconsistently. The floor is 3.11 and 3.11 hits EOL in five months (DEP-03), yet the compatibility matrix still spends macOS/Windows/Linux minutes testing 3.10, which the metadata forbids installing (CICD-05), and the SBOM/SLSA/docs build jobs run on 3.12 while everything else runs 3.11 (CICD-06).

On age stratification: there is none. The repo is one month old and uniformly new, so the "legacy" here is not aged code; it is config that accreted faster than anyone reconciled it. On AI-generated divergence: the same comprehension duplicated four times instead of a helper (CQ-05), one module naming a timeout constant while a sibling inlines it (ARCH-04), two `Console()` instances (ARCH-01), and a CHANGELOG describing changes that were never applied (DOC-01) all point to modules and commits generated in separate passes without a final cross-repo consistency check.

Two duplicate findings were merged. DEP-02 (dependencies) and SEC-01 (security) are the same pip-audit issue; kept as SEC-01 at High. LEG-01 (legacy) and ARCH-05 (architecture) are the same `cli.py:105` noqa; kept as ARCH-05 at Low. The code-quality report's addendum on the same noqa line folds into ARCH-05.

## 5. Prioritized remediation backlog

Sorted by severity, then effort. Effort: S < 1 day, M a few days, L a week or more.

| ID | Finding | Domain | Severity | Effort | Files |
|----|---------|--------|----------|--------|-------|
| SEC-01 | pip-audit `[tool.pip-audit] ignore-vuln` block is inert; CLI ignores it, releases may block on accepted vulns (merges DEP-02) | security | High | S | pyproject.toml; .github/workflows/security-analysis.yml; docs/known-vulnerabilities.md |
| CICD-01 | SLSA provenance never auto-fires; triggers on a non-existent "Semantic Release" workflow | cicd | High | S | .github/workflows/slsa-provenance.yml; .github/workflows/release.yml |
| DOC-01 | development.md states 80% coverage and basedpyright "standard"; actual is 65 and strict; CHANGELOG claims a fix not in HEAD | docs | High | S | docs/development.md; pyproject.toml; CHANGELOG.md |
| DEP-03 | Python 3.11 EOL 2026-10-31 (~5 months); floor, pin, ruff, basedpyright, CI all target 3.11 | dependencies | High | M | .python-version; pyproject.toml; .github/workflows/ci.yml |
| CICD-02 | basedpyright (strict) and semgrep never run in CI; both are local/advisory only | cicd | High | M | .pre-commit-config.yaml; .semgrep.yaml; .github/workflows/ |
| DEP-01 | `darglint` abandoned: repo archived 2022-12-16, last release 2021-10-18 (55 months) | dependencies | Medium | S | pyproject.toml; uv.lock |
| ARCH-01 | Persistence layer writes terminal output; `load_all` prints via its own Console; library callers get stdout | architecture | Medium | S | src/gleif/db.py |
| SEC-02 | detect-secrets absent from deps/venv; baseline enforced only via contributor pre-commit, no CI path | security | Medium | S | pyproject.toml; .secrets.baseline; .pre-commit-config.yaml |
| CICD-03 | Coverage threshold drift; `.codecov.yml` targets 80% but is orphaned (no Codecov upload) | cicd | Medium | S | .codecov.yml; pyproject.toml; .github/workflows/ci.yml |
| CICD-05 | Python 3.10 in compat matrix across 3 OS but forbidden by `requires-python >=3.11` | cicd | Medium | S | .github/workflows/python-compatibility.yml; pyproject.toml |
| DOC-02 | Five published doc files absent from mkdocs nav; orphan pages, fatal under `--strict` | docs | Medium | S | mkdocs.yml; docs/known-vulnerabilities.md; docs/known-vulnerabilities-template.md; docs/response-aware-development.md; docs/compliance-reports/lessons-learned/2026-04-25.md; docs/reusable-workflow-jobs.yaml |
| DOC-03 | Internal process/retrospective files published in the user docs site | docs | Medium | S | docs/response-aware-development.md; docs/compliance-reports/lessons-learned/2026-04-25.md; docs/reusable-workflow-jobs.yaml |
| DOC-05 | README `uv tool install gleif` + PyPI badge assume a published package; repo is private, unpublished | docs | Medium | S | README.md |
| CQ-01 | `download.py` 21% covered; download/extract path and zip-slip guard untested | code-quality | Medium | M | src/gleif/download.py; tests/ |
| CQ-02 | CLI `download`/`load`/`refresh` and `--isin` branches have no tests | code-quality | Medium | M | src/gleif/cli.py; tests/test_cli.py |
| CICD-04 | Scanner overlap with no authoritative-gate matrix: SAST x4, dep-scan x5, bandit x3 | cicd | Medium | M | .qlty/qlty.toml; .github/workflows/codeql.yml; .github/workflows/security-analysis.yml; .github/workflows/dependency-review.yml |
| DEP-04 | Transitive `py` 1.11.0 unmaintained (54 months), carries the accepted CVE | dependencies | Low | S | uv.lock; pyproject.toml; docs/known-vulnerabilities.md |
| DEP-05 | `interrogate` 1.7.0 stale (~26 months); sole reason `py` is in the tree | dependencies | Low | S | pyproject.toml; uv.lock |
| DEP-06 | `httpx` 0.28.1 latest release is 17.7 months old; nearing 18-month line (informational) | dependencies | Low | S | uv.lock |
| CQ-03 | `fail_under = 65` with stale "raise to 80" comment; oldest deferred note (2026-04-25) | code-quality | Low | S | pyproject.toml |
| CQ-04 | `rendering.py` 62% covered; pure formatting branches untested | code-quality | Low | S | src/gleif/rendering.py |
| CQ-05 | `RelatedEntity` row-mapping comprehension duplicated four times | code-quality | Low | S | src/gleif/queries.py |
| CQ-06 | ISIN-extraction comprehension duplicated between `fetch_isins` and `fetch_isins_batch` | code-quality | Low | S | src/gleif/isin.py |
| CQ-07 | `get_status` declares a precise tuple return but returns raw `fetchall()`; unchecked promise | code-quality | Low | S | src/gleif/db.py |
| ARCH-02 | `'ACTIVE'` status literal hardcoded in six SQL bodies | architecture | Low | S | src/gleif/queries.py |
| ARCH-03 | ISIN endpoint URL defined in `isin.py`, not `constants.py` | architecture | Low | S | src/gleif/isin.py; src/gleif/constants.py |
| ARCH-04 | Network magic numbers inline (timeout 600.0, chunk 65536, lei_length 20) | architecture | Low | S | src/gleif/download.py; src/gleif/cli.py |
| ARCH-05 | `# noqa: PLC0415` on a function-local import despite the documented noqa ban; rule is inert and import is redundant (merges LEG-01) | architecture | Low | S | src/gleif/cli.py; AGENTS.md |
| ARCH-06 | RAD doc code example uses `?` placeholders and a non-existent `table_exists` helper; contradicts actual `$1` + catalog-exception style | architecture | Low | S | docs/response-aware-development.md |
| SEC-03 | detect-secrets baseline `generated_at` 2026-04-27 predates later hook changes; regen due, unverifiable here | security | Low | S | .secrets.baseline; .pre-commit-config.yaml |
| CICD-06 | Build/scan jobs split between Python 3.11 and 3.12 with no stated reason | cicd | Low | S | .github/workflows/sbom.yml; .github/workflows/slsa-provenance.yml; .github/workflows/docs.yml |
| CICD-07 | `darglint` and `interrogate` pre-commit revs SHA-pinned without version comments, unlike every other hook | cicd | Low | S | .pre-commit-config.yaml |
| CICD-08 | Conventional-commit enforcement split (PR title vs local commit-msg); `dependency-standards-validation` job does no dependency check | cicd | Low | S | .github/workflows/pr-validation.yml; .pre-commit-config.yaml |
| DOC-04 | Four empty `.gitkeep` dirs collide with same-named `.md` pages | docs | Low | S | docs/architecture/.gitkeep; docs/development/.gitkeep; docs/getting-started/.gitkeep; docs/reference/.gitkeep |
| DOC-06 | CHANGELOG `[Unreleased]` self-contradicts on SBOM format; still version 0.1.0; duplicate `Changed` sections | docs | Low | S | CHANGELOG.md; pyproject.toml |
| DOC-07 | No ADR directory for design decisions documented inline in architecture/index.md | docs | Low | M | docs/architecture/index.md |

## 6. Verdict

Drifting. The application code is healthy: typed, modern, well-structured, well-tested except for the download/CLI I/O layer. Nothing here is at-risk in the security or data-loss sense; the only CVE is dev-only, accepted, and unreachable at runtime, and the GitHub Actions posture is strong (every action SHA-pinned, least-privilege permissions, harden-runner, working zip-slip guard, fully parameterized SQL). What is drifting is the compliance and CI apparatus, which has outgrown the 1,530-line program it wraps: overlapping scanners with no authoritative gate, config that governs nothing (pip-audit ignore, codecov, SLSA trigger), quality gates (basedpyright, semgrep) that exist but never run in CI, and documentation that states numbers and fixes that do not match the code.

Three changes move it most:

1. Make the gates real and singular. Run basedpyright strict and semgrep in a blocking CI job, fix the pip-audit ignore mechanism (pass `--ignore-vuln` flags or confirm the org workflow does), and collapse the four SAST and five dependency-scan tools to one authoritative tool per finding class. (SEC-01, CICD-02, CICD-04)

2. Fix the release chain and Python-version governance. Repoint the SLSA trigger to the real release event, move the pinned interpreter and CI default to 3.12 before 3.11 EOL on 2026-10-31, and drop 3.10 from the compatibility matrix. (CICD-01, DEP-03, CICD-05)

3. Reconcile one source of truth for numbers and docs. Resolve the 65-vs-80 coverage value across `pyproject.toml`, `.codecov.yml`, and `docs/development.md`; fix the CHANGELOG that records unapplied fixes and self-contradicts on SBOM; and either publish to PyPI or remove the install instructions and badge that assume it. (DOC-01, CICD-03, CQ-03, DOC-05, DOC-06)

After those, raise the coverage gate by closing the `download.py` and CLI test gap (CQ-01, CQ-02), which is the one substantive hole in otherwise solid code.
