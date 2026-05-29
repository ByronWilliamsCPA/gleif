# 05 - Security & Secrets

Scope: hardcoded secrets / baseline drift, vulnerable deps (pip-audit), insecure code patterns in `src/gleif/`, GitHub Actions posture. Repo HEAD 7fd3cb5. Read-only audit.

## Assessment

Code-level posture is strong. Bandit (`uv run bandit -r src -c pyproject.toml`) reports zero issues across 2,115 LOC. All SQL user-supplied values are bound via DuckDB `$1/$2` parameters; the only f-string interpolated into a query is an internal table-name constant. No broad exception swallowing, no bare `except`, no `except ... pass`, no `shell=True`, no `pickle`/`eval`/`exec`, no `verify=False`. Zip extraction in `download.py` has a working zip-slip guard. Workflows have top-level `permissions:`, SHA-pinned third-party actions, harden-runner, and no `pull_request_target`.

Two real findings: the `[tool.pip-audit]` ignore block in `pyproject.toml` is **not honored** by the pip-audit CLI, so the supposedly-accepted py vuln re-surfaces and would fail any CLI gate; and the detect-secrets baseline could not be re-validated because detect-secrets is absent from the project's dependency set and venv.

## Findings

### SEC-01 pip-audit pyproject ignore-vuln block is silently not honored by the CLI
Severity: High. Effort: S.
Files: `pyproject.toml:99-109`, `docs/known-vulnerabilities.md`.
Evidence: `uv run pip-audit` returns exit 1 and reports `py 1.11.0 PYSEC-2022-42969` despite that ID being listed in `[tool.pip-audit] ignore-vuln`. pip-audit does not read `[tool.pip-audit]` from pyproject; only the `--ignore-vuln` CLI flag works: `uv run pip-audit --ignore-vuln PYSEC-2022-42969` returns exit 0, "1 ignored". So the documented suppressions (PYSEC-2022-42969, PYSEC-2026-89) take effect only if every invocation passes the flags. `security-analysis.yml` comments claim "pip-audit ... honors [tool.pip-audit] ignore-vuln" (lines ~40-42), which is false; the actual call lives in the org-level `python-ci.yml` (not in this repo) and cannot be verified here.
Recommendation: pass `--ignore-vuln PYSEC-2022-42969 --ignore-vuln PYSEC-2026-89` explicitly in the CI invocation (or migrate to a config format pip-audit reads), and correct the misleading comment in `security-analysis.yml`. Confirm the org `python-ci.yml` step actually passes the flags, otherwise releases will block on the accepted vulns.
CVE: PYSEC-2022-42969 (fix: none; py unmaintained), PYSEC-2026-89.

### SEC-02 detect-secrets not in dependency set; baseline cannot be re-verified
Severity: Medium. Effort: S.
Files: `pyproject.toml` (dev deps), `.secrets.baseline`, `.pre-commit-config.yaml:64-70`.
Evidence: `uv run detect-secrets scan` fails ("Failed to spawn"); `uv run python -m detect_secrets` -> `No module named detect_secrets`. detect-secrets appears nowhere in `pyproject.toml`. It runs only via the pre-commit hook (pinned `01886c8a...` v1.5.0), so the baseline is enforced only when contributors have pre-commit installed; there is no `uv run` path and no CI job in this repo that runs it. Baseline cross-check against a fresh scan was therefore not possible in this environment.
Recommendation: add detect-secrets to the dev dependency group so `uv run detect-secrets scan --baseline .secrets.baseline` works locally and in CI; add a CI step that runs it (do not rely on contributor pre-commit alone).

### SEC-03 detect-secrets baseline content is stale-resistant but unverifiable here (informational)
Severity: Low. Effort: S.
Files: `.secrets.baseline:129-195`, `.pre-commit-config.yaml`.
Evidence: All 9 baseline entries are `Hex High Entropy String` in `.pre-commit-config.yaml` at lines 12,32,40,47,53,72,79,86,94 - these correspond to the action `rev:` SHA pins (e.g. ruff `740a8f85...`, bandit `f3a18ab3...`), i.e. false positives correctly baselined, not live secrets. Line numbers in the current `.pre-commit-config.yaml` still hold SHA pins, so no obvious drift. Could not run a fresh scan to confirm no new live secrets exist outside this file (see SEC-02). `generated_at` 2026-04-27; file has changed since (renovate/trufflehog hooks added) so a regen is due.
Recommendation: once SEC-02 is fixed, regenerate and audit the baseline (`detect-secrets scan --baseline .secrets.baseline` then `audit`); confirm the 9 entries still map to SHA pins and no entry is orphaned.

## Clean areas

- SQL injection: clean. `db.py` and `queries.py` route every user value through `$1/$2` binding; `queries.py:96,133,584` f-strings interpolate only the static `_ENTITY_COLS` constant. `db.py:280,291` interpolate `{table}`, sourced from the internal `loader_map` (three literal names), never user input. S608/B608 suppressions justified.
- Exception handling: clean. No `except Exception`, bare `except`, or `except ... pass` in `src/`. `isin.py:57,99` catch only `httpx.HTTPError`, documented and intentional.
- Zip slip: clean. `download.py:266-269` resolves the member path and rejects anything not under `extract_dir` before `zf.extract`.
- TLS: clean. `httpx` clients in `download.py:180` and `isin.py:52,84` use default verification; no `verify=False`. Timeouts set (600s download, 10s isin).
- Bandit: clean, 0 issues.
- Unsafe deserialization / command exec: none (no pickle/eval/exec/os.system/shell=True).
- Actions posture: strong. Top-level `permissions:` on every workflow (`pr-validation.yml` and `reusable-codeql.yml` use `permissions: {}`); job-level scoping is least-privilege. All third-party actions SHA-pinned (step-security/harden-runner, actions/checkout, setup-uv, codeql-action, cosign, attest-build-provenance, fsfe/reuse). No `pull_request_target`. Untrusted PR title/body reach `run:` only via env-var indirection (`pr-validation.yml`), not inline `${{ }}` interpolation - injection-safe. Org reusable workflows pinned to a branch SHA `6f71aeca...`.
