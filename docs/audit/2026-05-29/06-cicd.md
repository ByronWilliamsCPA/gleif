# 06 - CI/CD & Tooling Audit

Scope: 15 workflows (~930 lines YAML), pre-commit, and 9 static-analysis config files against a ~2200 LOC single-package Python CLI. HEAD 7fd3cb5.

## Assessment

The CI surface is not proportionate to the code. A 2200-line CLI carries 15 workflows and a 9-tool static-analysis stack (Ruff, basedpyright, bandit, semgrep, CodeQL, Scorecard, Trivy, OSV, Qlty/radarlint/SonarQube rules, plus dependency-review, REUSE, SLSA, cosign signing). Supply-chain hygiene is strong: every `uses:` is 40-char SHA-pinned with a version comment, no deprecated `set-output`/`save-state`, no node12/node16 runtimes, minimal per-job permissions, harden-runner on every direct job. The cost shows up elsewhere: tool overlap with no clear ownership of which gate blocks, two static-analysis tools (basedpyright, semgrep) that run only locally and never in CI, version/threshold drift across config files, and one release-chain workflow (SLSA provenance) wired to a trigger that never fires. The action-pinning discipline is real and worth keeping; the breadth of overlapping scanners and the config drift are the tax.

Effort: S < 1 day, M few days, L week+.

## Findings

### CICD-01 - SLSA provenance never auto-fires (broken release chain)

Severity: High. Effort: S.
File: `.github/workflows/slsa-provenance.yml:12-15`, `.github/workflows/release.yml:30`.
Evidence: slsa-provenance triggers on `workflow_run: workflows: ["Semantic Release"]`. No workflow declares `name: Semantic Release` (the 15 names are CI, CodeQL Advanced, Release, etc.). release.yml also sets `semantic-release: false`. So the `workflow_run` branch can never match; provenance only generates via manual `workflow_dispatch`. Released artifacts get cosign signatures (release-sign.yml on `release: published`) but no SLSA L3 provenance unless someone remembers to dispatch it.
Recommendation: Point `workflow_run` at the actual release workflow name ("Release") or trigger slsa on `release: published` like release-sign.yml. Then verify the build/version logic still resolves.

### CICD-02 - basedpyright (strict) and semgrep never run in CI

Severity: High. Effort: M.
Files: `.pre-commit-config.yaml:60-68` (basedpyright local hook), `.semgrep.yaml` (5 rules incl. ERROR-severity SQL-injection and command-injection), `.github/workflows/*` (no reference).
Evidence: `grep` for basedpyright/semgrep across all workflows returns nothing. basedpyright runs only as a `language: system` pre-commit hook; semgrep runs only via Qlty (`.qlty/qlty.toml:96`) which is `mode = "comment"` (advisory). pyproject sets `typeCheckingMode = "strict"`. A contributor who skips local hooks (or whose hooks silently no-op) lands untyped code and unscanned SQL strings; CI will not catch it. The org `python-ci.yml` is a black box here, but the thin caller passes no type-check flag and the comment on ci.yml only claims "type checking" generically.
Recommendation: Add an explicit blocking basedpyright job (or confirm the org python-ci.yml runs it on `source-directory: src` in strict mode). Run semgrep `.semgrep.yaml` in a blocking job, or accept it as advisory-only and drop the ERROR severities to avoid implying a gate that does not exist.

### CICD-03 - Coverage threshold drift across three sources; .codecov.yml orphaned

Severity: Medium. Effort: S.
Files: `pyproject.toml:115` (`fail_under = 65`), `.github/workflows/ci.yml:39` (`coverage-threshold: 65`), `.codecov.yml:5,9` (`target: 80%` project and patch).
Evidence: pyproject and ci.yml agree at 65. `.codecov.yml` demands 80% project and patch coverage but no workflow uploads to Codecov (`grep codecov .github/workflows` is empty); coverage flows to Qlty via coverage.yml. So `.codecov.yml` is dead config asserting a stricter target than the real gate, and a reader cannot tell 65 vs 80 is authoritative.
Recommendation: Delete `.codecov.yml` (Codecov is not in the pipeline) or wire it up and reconcile to one number. Track the pyproject TODO to raise 65 to 80.

### CICD-04 - Scanner overlap with no documented blocking matrix

Severity: Medium. Effort: M.
Files: `.qlty/qlty.toml:64-104`, `codeql.yml`, `security-analysis.yml`, `scorecard.yml`, `sbom.yml`, `dependency-review.yml`.
Evidence: Bandit runs in pre-commit, in Qlty, and (per its comment) inside org python-security-analysis.yml. SAST overlaps four ways: CodeQL security-extended (codeql.yml), semgrep (Qlty only), bandit (3 places), radarlint-python SonarQube rules (qlty.toml:76, `mode = "comment"`). Dependency scanning overlaps: Trivy (sbom.yml), OSV (disabled in security-analysis.yml:46 as redundant with pip-audit), pip-audit (org python-ci.yml), dependency-review-action (dependency-review.yml), Renovate OSV alerts (renovate.json:103). The team already disabled run-codeql and run-osv in security-analysis.yml to cut duplication, which shows the overlap is recognized but only partly pruned. Several Qlty plugins are `mode = "comment"` (advisory) while the same checks block elsewhere, so it is unclear which signal a contributor must satisfy.
Recommendation: Write a one-page "which scanner is authoritative for which finding class" matrix; drop bandit from one of its three homes; decide whether radarlint/SonarQube rules earn their keep on 2200 LOC.

### CICD-05 - Python 3.10 tested but unsupported; matrix vs metadata drift

Severity: Medium. Effort: S.
Files: `.github/workflows/python-compatibility.yml:41` (`["3.10", "3.11", "3.12", "3.13"]`), `pyproject.toml:10` (`requires-python = ">=3.11,<4"`), `pyproject.toml:19-21` (classifiers 3.11/3.12/3.13), `.python-version` (3.11).
Evidence: The compat matrix spends macOS + Windows + Linux runner-minutes on 3.10, which the package metadata forbids installing. Either the floor is wrong or the matrix wastes a third of its cells (3.10 x 3 OS).
Recommendation: Drop 3.10 from the matrix, or lower `requires-python` to `>=3.10` and add the classifier. Pick one.

### CICD-06 - Build-time Python version split (3.11 vs 3.12) undocumented

Severity: Low. Effort: S.
Files: ci.yml:36 / release.yml:27 / security-analysis.yml:38 / codeql.yml:34 (3.11) vs sbom.yml:46 / slsa-provenance.yml:61 / docs.yml:56 (3.12).
Evidence: `.python-version` and ruff/basedpyright target 3.11, but SBOM, SLSA build, and docs build on 3.12. SBOM comment at sbom.yml:51-54 explains the no-build flag, not the version choice. Inconsistent build interpreters can mask version-specific packaging or vuln-scan differences.
Recommendation: Standardize build/scan jobs on 3.11 (the declared floor and dev target), or add a one-line comment justifying 3.12 where used.

### CICD-07 - Two pre-commit hook revs not pinned to a documented version

Severity: Low. Effort: S.
File: `.pre-commit-config.yaml:86` (darglint rev `abc26b768cd7135d848223ba53f68323593c33d5`, no version comment), `:94` (interrogate rev `f35a9d68f609d6ceed10f4286efc8d73b79b17cb`, no version comment).
Evidence: Every other hook rev carries a `# vX.Y.Z` comment (pre-commit-hooks v4.5.0, ruff v0.14.4, bandit 1.7.6, detect-secrets v1.5.0, commitizen v3.29.1, trufflehog v3.95.3, renovate-config-validator v43.150.0). darglint and interrogate are SHA-pinned but the version is opaque, so renovate/humans cannot tell what they pin to. Both upstreams are low-activity; an unlabeled SHA is hard to audit.
Recommendation: Add `# vX.Y.Z` comments matching the pinned SHAs for darglint and interrogate.

### CICD-08 - Conventional-commit enforcement split between PR title and commit-msg

Severity: Low. Effort: S.
Files: `.github/workflows/pr-validation.yml:35` (regex on PR title), `.pre-commit-config.yaml:78-82` (commitizen `stages: [commit-msg]`).
Evidence: pr-validation enforces Conventional Commits on the PR title (blocking via pr-validation-gate). commitizen enforces it on each commit message locally. If the repo squash-merges using the PR title, individual commit messages never face CI enforcement (commitizen is local-only). The `dependency-standards-validation` job (pr-validation.yml:72) is named for dependency/standards checks but only re-reads title/body results; it does no dependency check. Misleading job name.
Recommendation: Confirm squash-merge uses PR title (then commit-msg enforcement is cosmetic), and rename `dependency-standards-validation` to reflect that it only gates title/body.

## Clean areas

- Action pinning: all 38 `uses:` lines are 40-char SHA-pinned with version comments; zero tag-pinned, zero `@main`/`@v1` floating refs in action position.
- Deprecations: no `set-output`, no `save-state`, no node12/node16 runtimes anywhere.
- Permissions: top-level `contents: read` default; jobs add only the scopes they need; pr-validation uses `permissions: {}` at top. harden-runner (egress audit) on every direct-runner job.
- Caching: uv cache enabled (`enable-cache: true`) in every uv-using job; codeql adds `cache-dependency-glob: uv.lock`.
- Concurrency: cancel-in-progress groups on all PR-triggered workflows.
- Org reusable workflows: all 8 callers pin the same SHA `6f71aec`, consistent across the repo; renovate.json:66-77 has a rule to track the org `v1` tag (note: callers comment `# main`, not `v1`, a minor mismatch with that rule's `followTag: v1`).
- bandit B608 / ruff S608 suppression is consistent across pyproject (lines 75-76, 97) and qlty triage (lines 136-147) with matching rationale.

## For master backlog

- CICD-01 SLSA provenance never auto-fires (broken release chain) - High - S - slsa-provenance.yml:12-15 workflow_run ["Semantic Release"] (no such workflow; release.yml:30 semantic-release: false)
- CICD-02 basedpyright (strict) and semgrep never run in CI - High - M - basedpyright local-only pre-commit-config.yaml:60-68; .semgrep.yaml runs only via advisory Qlty
- CICD-03 Coverage threshold drift; .codecov.yml orphaned - Medium - S - pyproject:115 fail_under=65 / ci.yml:39 =65 / .codecov.yml:5,9 target 80%, no codecov upload
- CICD-04 Scanner overlap, no blocking matrix - Medium - M - bandit x3, SAST x4 (CodeQL/semgrep/bandit/radarlint), dep-scan x5; qlty.toml:64-104
- CICD-05 Python 3.10 tested but unsupported - Medium - S - python-compatibility.yml:41 vs pyproject:10 requires-python>=3.11
- CICD-06 Build Python version split 3.11 vs 3.12 undocumented - Low - S - sbom.yml:46/slsa:61/docs:56 use 3.12 vs 3.11 elsewhere
- CICD-07 darglint/interrogate hook revs lack version comments - Low - S - .pre-commit-config.yaml:86,94
- CICD-08 Conventional-commit enforcement split; misnamed gate job - Low - S - pr-validation.yml:35 title vs commitizen commit-msg local; dependency-standards-validation:72 does no dep check
