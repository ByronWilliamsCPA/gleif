# 01 Dependencies & Supply Chain Audit

Scope: direct/transitive dependency health, lockfile reproducibility, pip-audit, SBOM/renovate config, and runtime version target for /home/user/gleif at HEAD 7fd3cb5 (audited 2026-05-29).

## Assessment

The supply chain is in good shape. Lock is present, complete, and consistent (`uv lock --check` passes, 82 packages, all entries carry sha256 hashes). No migration residue (no requirements*.txt / setup.py / poetry.lock / Pipfile at root). All four runtime deps (duckdb 1.5.2, httpx 0.28.1, typer 0.25.0, rich 15.0.0) are at or near current and actively maintained.

The real findings are dev-only and config-level. Two dev dependencies are abandoned: `darglint` (last release 2021-10-18, repo archived 2022-12-16) and the transitive `py` (maintenance mode, last release 2021-11-04, source of the ignored CVE). The `[tool.pip-audit]` ignore-vuln block in pyproject.toml is dead config: pip-audit 2.10 does not read ignore lists from pyproject, so the markdown advisory PYSEC-2026-89 is not actually being suppressed by that file (it just is not in the current OSV feed for this version), and PYSEC-2022-42969 only stays suppressed if the org reusable workflow passes explicit `--ignore-vuln` flags. Python 3.11 reaches EOL 2026-10-31, roughly five months out, while the project pins 3.11.

## Findings

### DEP-01: `darglint` is abandoned (repo archived 2022, no release in 55 months)
- Severity: Medium | Effort: S (<1 day)
- Affected: `/home/user/gleif/pyproject.toml` (dependency-groups.dev: `"darglint>=1.8.1"`); `/home/user/gleif/uv.lock` (darglint 1.8.1)
- Evidence: uv.lock darglint 1.8.1 `upload-time = "2021-10-18T03:40:35.034Z"`. GitHub terrencepreilly/darglint: "This repository was archived by the owner on Dec 16, 2022. It is now read-only." Maintainer README states maintenance mode, no new features. As of 2026-05-29 the last release is 55 months old.
- Recommendation: Drop darglint and fold docstring linting into ruff (pydocstyle `D` rules), which is already a dev dep; this removes an unmaintained tool and the separate `[tool.darglint]` config.

### DEP-02: `[tool.pip-audit] ignore-vuln` in pyproject.toml is not honored by pip-audit
- Severity: Medium | Effort: S (<1 day)
- Affected: `/home/user/gleif/pyproject.toml` (`[tool.pip-audit]` ignore-vuln, lines ~104-114); `/home/user/gleif/.github/workflows/security-analysis.yml:42-43`
- Evidence: pip-audit 2.10 has no pyproject config support (its `--help` shows only the `--ignore-vuln ID` CLI flag; no `--config`/pyproject option). `uv run pip-audit` (which reads cwd pyproject) still reports `py 1.11.0 PYSEC-2022-42969`, proving the file-level ignore is inert. Suppression only works when flags are passed: `uv run pip-audit --ignore-vuln PYSEC-2022-42969 --ignore-vuln PYSEC-2026-89` -> "No known vulnerabilities found, 1 ignored". The comment at security-analysis.yml:42-43 asserts the reusable `python-ci.yml` "honors [tool.pip-audit] ignore-vuln"; that workflow is org-level and not in this repo, so the claim is unverifiable here and is false for stock pip-audit.
- Recommendation: Confirm the org `python-ci.yml` translates `[tool.pip-audit]` into explicit `--ignore-vuln` flags; if it does not, switch the ignore mechanism to an `.pip-audit.toml`-fed flag list or document that suppression lives in the reusable workflow, not pyproject.

### DEP-03: Python 3.11 reaches EOL 2026-10-31 (~5 months out); project pins 3.11
- Severity: High | Effort: M (few days)
- Affected: `/home/user/gleif/.python-version` (`3.11`); `/home/user/gleif/pyproject.toml` (`requires-python = ">=3.11,<4"`, ruff `target-version = "py311"`, basedpyright `pythonVersion = "3.11"`); `/home/user/gleif/.github/workflows/ci.yml` (`python-version: '3.11'`)
- Evidence: Python 3.11 final security release / EOL is 2026-10-31 (python devguide versions page). Classifiers already list 3.12 and 3.13, so the code targets newer runtimes, but the pinned dev/CI interpreter and the floor stay at 3.11. After EOL no security patches ship for 3.11.
- Recommendation: Move the pinned interpreter and CI default to 3.12 before 2026-10-31, keep the `>=3.11` floor only if 3.11 support is still wanted, and add 3.12 to the matrix as the primary.

### DEP-04: Transitive `py` 1.11.0 is unmaintained and carries the ignored CVE
- Severity: Low | Effort: S (<1 day)
- Affected: `/home/user/gleif/uv.lock` (py 1.11.0, pulled by interrogate); `/home/user/gleif/pyproject.toml` (`interrogate>=1.7.0`); `/home/user/gleif/docs/known-vulnerabilities.md`
- Evidence: uv.lock py 1.11.0 `upload-time = "2021-11-04T17:17:00.152Z"` (54 months old; PyPI metadata: "maintenance mode and should not be used in new code"). `uv run pip-audit` flags `py 1.11.0 PYSEC-2022-42969` (ReDoS in `py.path.svnwc`, no fix). interrogate 1.7.0 (latest, 2024-04-07) still lists `py` as a core dependency, so the dep cannot be removed without dropping interrogate. The ignore in known-vulnerabilities.md is justified: the CLI never touches `py.path.svnwc`, it is dev-only, and there is no upstream fix. CVE: CVE-2022-42969 (PYSEC-2022-42969).
- Recommendation: Keep the documented ignore; revisit when interrogate drops `py` or when DEP-01-style consolidation removes interrogate. The 2026-07-14 review date in known-vulnerabilities.md is appropriate.

### DEP-05: `interrogate` 1.7.0 last released 2024-04-07 (~26 months; over the 18-month flag line)
- Severity: Low | Effort: S (<1 day)
- Affected: `/home/user/gleif/pyproject.toml` (`interrogate>=1.7.0`); `/home/user/gleif/uv.lock` (interrogate 1.7.0)
- Evidence: uv.lock interrogate 1.7.0 `upload-time = "2024-04-07T22:30:44.277Z"`; PyPI confirms 1.7.0 is the latest. As of 2026-05-29 that is 25.7 months with no newer release. Not archived, but slow-moving, and it is the sole reason `py` is in the tree (DEP-04).
- Recommendation: Track upstream; if it stalls further, replace docstring-coverage gating with ruff `D`/docstring rules (pairs with DEP-01) to drop both interrogate and py.

### DEP-06: `httpx` 0.28.1 nearing the 18-month staleness line (informational)
- Severity: Low | Effort: S (<1 day)
- Affected: `/home/user/gleif/uv.lock` (httpx 0.28.1)
- Evidence: uv.lock httpx 0.28.1 `upload-time = "2024-12-06T15:37:21.509Z"` = 17.7 months as of 2026-05-29, just under the 18-month threshold. 0.28.1 is still the current release on PyPI and httpx is actively maintained (pre-1.0 cadence), so this is age of the latest release, not a missed upgrade. Floor `httpx>=0.27.0`.
- Recommendation: No action; note for the next audit. If no 0.29/1.0 ships by the next cycle, re-confirm maintenance status.

## Clean areas

- Lockfile health: `uv lock --check` returns "Resolved 82 packages" exit 0; uv.lock present, complete, consistent with pyproject; 605 sha256 hash entries; lock `requires-python = ">=3.11, <4"` matches pyproject.
- Migration residue: none. No requirements*.txt, setup.py, poetry.lock, or Pipfile at repo root (confirmed).
- Runtime deps duckdb 1.5.2 (2026-04-13), typer 0.25.0 (2026-04-26), rich 15.0.0 (2026-04-12) are current and actively maintained; installed == locked == latest.
- SBOM (`.github/workflows/sbom.yml`): calls org `python-sbom.yml` pinned to commit SHA, CycloneDX + Trivy, `fail-on-vulnerabilities: true`, severity `CRITICAL,HIGH`, triggers on pyproject/uv.lock changes plus weekly cron; `no-build: false` correctly set for the editable source install. Coverage is adequate from config.
- renovate.json: schema-referenced, sane config; SHA-pins GitHub Actions (`pinDigests`), groups/auto-merges actions minor/patch, disables auto Python-version bumps (manual review), enables `vulnerabilityAlerts` + `osvVulnerabilityAlerts` + `transitiveRemediation`, `preserveSemverRanges`. No issues.
