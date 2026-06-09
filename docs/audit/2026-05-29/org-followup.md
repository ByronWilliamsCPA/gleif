# Org Follow-up: ByronWilliamsCPA/.github

Changes to apply in the org reusable-workflow repo so the centralized workflows
agree with the gleif local gates instead of duplicating and drifting. These are
out of scope for the gleif repo audit (different repository) and are recorded
here for the maintainer to apply.

Context: gleif's CI consists of thin callers into org workflows pinned at
`6f71aec`. Two High findings (SEC-01, CICD-02) have their real lever in those
org workflows. The gleif branch `claude/repo-audit-LKTO1` adds a self-contained
`static-analysis.yml` so the gates exist regardless of the org state. The items
below remove the resulting duplication once applied.

## 1. python-ci.yml: run basedpyright strict (covers CICD-02)

The gleif caller (`.github/workflows/ci.yml`) passes `source-directory: src` and
relies on python-ci.yml for "type checking". Confirm python-ci.yml actually runs
basedpyright in strict mode on `source-directory`, blocking on failure. If it
does not, add a step:

```yaml
- name: Type check (basedpyright strict)
  run: uv run basedpyright "${{ inputs.source-directory }}"
```

basedpyright must be in the caller's dev dependency group (it is, in gleif's
`pyproject.toml`). If python-ci.yml is confirmed to run this, drop the
`basedpyright` step from gleif's `static-analysis.yml` to remove the overlap.

## 2. python-ci.yml: pass pip-audit --ignore-vuln flags (covers SEC-01)

pip-audit's CLI does not read `[tool.pip-audit] ignore-vuln` from pyproject.toml.
If python-ci.yml runs pip-audit, the accepted vulns
(PYSEC-2022-42969, PYSEC-2026-89, see `docs/known-vulnerabilities.md`) re-surface
and fail the gate. Either:

- Read the suppression IDs from the caller's `[tool.pip-audit]` table and expand
  them into `--ignore-vuln <ID>` flags, or
- Accept an input list and pass it through:

```yaml
- name: Dependency audit
  run: |
    uv run pip-audit ${IGNORE_FLAGS}
  env:
    IGNORE_FLAGS: ${{ inputs.pip-audit-ignore-vulns }}
```

Until python-ci.yml does this, the authoritative pip-audit suppression lives in
gleif's `static-analysis.yml`. Once it does, drop the `pip-audit` step from
`static-analysis.yml`.

## 3. python-security-analysis.yml: semgrep (optional, CICD-02)

gleif runs `.semgrep.yaml` as a blocking step in `static-analysis.yml`. If you
prefer to centralize, add a semgrep step to python-security-analysis.yml that
reads the caller's `.semgrep.yaml`, then drop it from `static-analysis.yml`.

## Verification after org changes

1. Bump the pinned org SHA in each gleif caller from `6f71aec` to the new commit.
2. Open a gleif PR and confirm the org workflow now reports the type-check and
   pip-audit results as blocking checks.
3. Remove the now-duplicated steps from gleif `static-analysis.yml` in the same
   PR so each check has one authoritative home.
