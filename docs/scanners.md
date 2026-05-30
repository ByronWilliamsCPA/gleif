# Security and Quality Scanners

The repository runs several scanners. This page records which one is the
authoritative (blocking) gate for each finding class, so contributors know which
signal they must satisfy and maintainers avoid duplicate ownership.

## Authoritative gate per finding class

| Finding class | Authoritative gate | Where it runs | Advisory copies |
| --- | --- | --- | --- |
| Python type errors | basedpyright (strict) | `static-analysis.yml` (blocking) | pre-commit (local) |
| Lint / format | ruff | org `python-ci.yml` (blocking) | pre-commit, Qlty |
| SAST (code patterns) | CodeQL security-extended | `codeql.yml` (blocking) | semgrep (Qlty, advisory) |
| Custom SQL / injection rules | semgrep `.semgrep.yaml` | `static-analysis.yml` (blocking) | Qlty (advisory) |
| Python security smells | bandit | pre-commit + org `python-security-analysis.yml` | (removed from Qlty) |
| Dependency vulnerabilities | pip-audit | `static-analysis.yml` (blocking) | Trivy (SBOM), dependency-review, Renovate alerts |
| Secrets | detect-secrets (baseline) | `static-analysis.yml` + pre-commit | trufflehog (pre-commit, Qlty) |
| Test coverage | coverage `fail_under` | org `python-ci.yml` (blocking, 80%) | Qlty |

## Notes

- bandit was removed from Qlty (`qlty.toml`) so it has one advisory home
  (pre-commit) and one blocking home (the org security workflow), not three.
- OSV scanning is disabled in `security-analysis.yml` because pip-audit covers
  the same advisory database; Trivy in `sbom.yml` is the dependency-scan that
  runs on a schedule.
- Qlty plugins set to `mode = "comment"` are advisory only; they post review
  comments but never block a merge. The blocking gates are the GitHub Actions
  jobs listed above.
- Accepted dependency vulnerabilities are suppressed only via explicit
  `--ignore-vuln` flags in `static-analysis.yml` (the `[tool.pip-audit]` table
  in `pyproject.toml` is not read by the pip-audit CLI).
