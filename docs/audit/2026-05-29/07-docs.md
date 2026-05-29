# 07 Documentation & Developer Experience Audit

Scope: README, mkdocs site, docs/**, AI-assistant config files, CONTRIBUTING, CHANGELOG cross-checked against src/gleif/cli.py and pyproject.toml. HEAD 7fd3cb5.

## Assessment

CLI commands and options in the published docs (README, cli-reference.md, getting-started.md, AGENTS.md, GEMINI.md) match the six Typer commands in `src/gleif/cli.py` accurately, including exit codes, `--tree`, `--max-depth`, `--limit/-n`, and `--isin`. The data-model and architecture docs match the documented schema and design. The main problems are not command drift but: (1) `docs/development.md` still states coverage and type-checker values the CHANGELOG claims were already corrected, (2) five published doc files are absent from the mkdocs nav and render as orphan pages, (3) four empty `.gitkeep` placeholder dirs collide with same-named `.md` files, (4) install instructions assume a PyPI package that the compliance retrospective indicates is a private, unpublished repo, and (5) no ADR directory exists for documented design decisions. No `# Architecture Decision Records` dir is tracked (`git ls-files` for adr/decision returns none).

---

## DOC-01 development.md coverage and type-checker values contradict pyproject and CHANGELOG

Severity: High. Effort: S. Files: `docs/development.md`, `pyproject.toml`, `CHANGELOG.md`.

`docs/development.md:56` table states "Line coverage | 80%" and line 57-59 add "Branch 70% / Critical 90% / New patches 90%". `docs/development.md:107` states the CI step is an "80% coverage gate". Actual gate: `pyproject.toml:115` `fail_under = 65`, `pyproject.toml:93` runs `--cov=gleif`. `.github/copilot-instructions.md:25` documents "65% line (interim) ... 70% branch". The CHANGELOG "Fixed" section (`CHANGELOG.md:67-69`) explicitly claims `docs/development.md` was already "corrected ... coverage threshold (65%, not 80%)". The file still says 80%, so either the fix was reverted or never applied. Onboarding contributors will believe the gate is 80% and be surprised when CI passes at 65%.

Same file, `docs/development.md:69`: "BasedPyright runs in `standard` mode with strict inference". Actual: `pyproject.toml:84` `typeCheckingMode = "strict"`; AGENTS.md:34, GEMINI.md, copilot-instructions.md:18 all say strict. CHANGELOG.md:67 again claims this exact line was "corrected (`strict`, not `standard`)". Still wrong.

Recommendation: set line coverage to 65% and basedpyright to `strict` in `docs/development.md`; drop or footnote the 90% critical/new-patch rows (no enforcement of those exists in pyproject). Investigate why the CHANGELOG-documented fix is not present in HEAD.

## DOC-02 Five published doc files are missing from mkdocs nav (orphan pages)

Severity: Medium. Effort: S. Files: `mkdocs.yml`, `docs/known-vulnerabilities.md`, `docs/known-vulnerabilities-template.md`, `docs/response-aware-development.md`, `docs/compliance-reports/lessons-learned/2026-04-25.md`, `docs/reusable-workflow-jobs.yaml`.

`mkdocs.yml:71-79` nav lists only index, getting-started, cli-reference, troubleshooting, architecture/{index,data-model}, development. All seven nav targets resolve to existing files (good). But the following tracked files under `docs_dir: docs` have no nav entry: `known-vulnerabilities.md`, `known-vulnerabilities-template.md`, `response-aware-development.md`, `compliance-reports/lessons-learned/2026-04-25.md`. MkDocs builds these into the site but they are unreachable from navigation and emit "not in nav" warnings (fatal under `mkdocs build --strict`). `reusable-workflow-jobs.yaml` is a non-markdown file inside `docs/` that mkdocs copies verbatim into the site as a downloadable asset.

Recommendation: decide per file. `known-vulnerabilities.md` + template are legitimate published reference docs; add a "Security" nav section. `response-aware-development.md`, the compliance retrospective, and `reusable-workflow-jobs.yaml` are internal/process artifacts that do not belong in a published user site; move them out of `docs/` (e.g. to a top-level `internal/` or `.github/`) or add an mkdocs `exclude` so the public site stays user-facing.

## DOC-03 Internal process files published in the user docs tree

Severity: Medium. Effort: S. Files: `docs/response-aware-development.md`, `docs/compliance-reports/lessons-learned/2026-04-25.md`, `docs/reusable-workflow-jobs.yaml`, `docs/known-vulnerabilities-template.md`.

`docs/response-aware-development.md` is an AI-development-process essay (RAD tiers, model selection, cost metrics) with no relevance to a CLI end user; it also contains banned filler the project's own writing standard prohibits ("Conclusion" heading at line 205, "optimizations" line 64). `docs/compliance-reports/lessons-learned/2026-04-25.md` is an internal audit retrospective listing unremediated findings (e.g. line 169-175: untested `download.py`, private-function imports in `load`, `gleif name` empty-string matches all records). `docs/reusable-workflow-jobs.yaml` is a CI registry with a `last_verified` staleness contract (CI-024). Shipping these on the public GitHub Pages site exposes internal process detail and outstanding-defect lists to end users.

Recommendation: relocate these out of `docs/` (see DOC-02). If they must stay tracked, place under a non-published path. The `known-vulnerabilities*` pair can stay if intentionally public; confirm that is desired.

## DOC-04 Empty .gitkeep placeholder dirs collide with same-named .md pages

Severity: Low. Effort: S. Files: `docs/architecture/.gitkeep`, `docs/development/.gitkeep`, `docs/getting-started/.gitkeep`, `docs/reference/.gitkeep`.

Four tracked empty directories duplicate the names of existing pages: `docs/development/` vs `docs/development.md`, `docs/getting-started/` vs `docs/getting-started.md`, `docs/architecture/` (this one legitimately holds index.md + data-model.md), and `docs/reference/` (no `reference.md`, but nav uses `cli-reference.md`). The `development/` and `getting-started/` dir-vs-file pairs can confuse mkdocs URL resolution and editors. `docs/reference/` is dead (nothing references it). The dirs contain only `.gitkeep` and serve no purpose now that the sibling `.md` files exist.

Recommendation: delete the four `.gitkeep` placeholder dirs. `docs/architecture/.gitkeep` is also redundant since the dir already holds two tracked `.md` files.

## DOC-05 Install instructions assume a published PyPI package; repo is private and unpublished

Severity: Medium. Effort: S. Files: `README.md`.

`README.md:49` instructs `uv tool install gleif` and `README.md:4` renders a `pypi/pyversions/gleif` badge linking `pypi.org/project/gleif/`. The compliance retrospective states the repo is private (`docs/compliance-reports/lessons-learned/2026-04-25.md:155` "the repository is private"), and `pyproject.toml` shows version 0.1.0 with no evidence of a PyPI release. If the package is not on PyPI, `uv tool install gleif` fails for every new user and the PyPI/pyversions badge is broken. The from-source path (`README.md:54-58` git clone + `uv sync`) is correct.

Recommendation: either publish to PyPI, or remove the `uv tool install gleif` block and the PyPI badge until published, leaving the from-source instructions as primary.

## DOC-06 CHANGELOG [Unreleased] internally contradicts itself on SBOM format; version still 0.1.0

Severity: Low. Effort: S. Files: `CHANGELOG.md`, `pyproject.toml`.

`CHANGELOG.md:18-22` (Unreleased / Changed) says the release SBOM "changes from SPDX-JSON ... to CycloneDX-JSON". Twelve lines later `CHANGELOG.md:26-27` (Unreleased / Added) still lists "SPDX SBOM generation via `anchore/sbom-action` on tagged releases" as a current addition, and `CHANGELOG.md:108` (under released 0.1.0) repeats "SPDX SBOM generation". The Unreleased section therefore both adds SPDX and replaces it with CycloneDX. The [Unreleased] block is large (workflow migration, action bumps, security fixes) yet `pyproject.toml:3` is still `version = "0.1.0"`, so none of it is released. The CHANGELOG also has two separate "### Changed" subsections within [Unreleased] (lines 10 and 33), which Keep a Changelog does not use.

Recommendation: reconcile the SBOM entries (CycloneDX is the current state per line 18-22; drop the stale SPDX "Added" line). Merge the duplicate Changed subsections. Cut a 0.2.0 release or relabel the Unreleased content so docs match the shipped version.

## DOC-07 No ADR directory for the design decisions documented inline

Severity: Low. Effort: M. Files: `docs/architecture/index.md` (decisions live here), no `docs/adr/` or `docs/decisions/`.

`docs/architecture/index.md:42-85` documents five real decisions (DuckDB as local store, relationship-direction convention, recursive-CTE cycle prevention, async download with sequential load, frozen dataclasses as return types) as prose under "Key design decisions". `git ls-files` finds no ADR/decision directory. These are exactly the decisions a contributor needs the rationale and alternatives for (why DuckDB over SQLite, why async download but sync load). The inline prose captures the "what" but not rejected alternatives or status, and is not discoverable as decision history.

Recommendation: optional but low-cost value: add `docs/adr/` with one short ADR per existing decision (DuckDB choice, async-download/sync-load, frozen dataclasses), using the MADR template. Link from architecture/index.md. Add to nav if pursued.

---

## Clean areas

- CLI command surface: all six commands (`download`, `load`, `refresh`, `lei`, `name`, `status`) and every option/argument/exit-code in README, cli-reference.md, getting-started.md match `src/gleif/cli.py` exactly, including `--tree`, `--max-depth` default 50, and `-n/--limit` default 100.
- AI-assistant config consistency: AGENTS.md, GEMINI.md, and copilot-instructions.md agree with each other and with CONTRIBUTING.md on toolchain (ruff 88-char, basedpyright strict, conventional + GPG-signed commits, async httpx, parameterized DuckDB). GEMINI.md correctly defers to AGENTS.md for detail. No conflicting instructions found. Note copilot-instructions.md:25 and pyproject agree on 65% coverage, so development.md (DOC-01) is the lone outlier.
- Data model: `docs/architecture/data-model.md` schema, keys, indexes, relationship direction, and the frozen-dataclass definitions match the architecture overview and AGENTS.md.
- mkdocs theme/extensions config is well-formed; all seven nav targets resolve to existing files.
- known-vulnerabilities.md and its template are consistent with each other and with the `[tool.pip-audit] ignore-vuln` IDs in pyproject.toml:99-109 (PYSEC-2022-42969, PYSEC-2026-89).

---

## Findings summary

| ID | Title | Severity | Effort |
|----|-------|----------|--------|
| DOC-01 | development.md coverage 80% / basedpyright "standard" contradict pyproject (65/strict) and CHANGELOG | High | S |
| DOC-02 | Five published doc files missing from mkdocs nav (orphan pages, fatal under --strict) | Medium | S |
| DOC-03 | Internal process/retrospective files published in user docs tree | Medium | S |
| DOC-04 | Empty .gitkeep dirs collide with same-named .md pages | Low | S |
| DOC-05 | README `uv tool install gleif` + PyPI badge assume an unpublished package (repo private) | Medium | S |
| DOC-06 | CHANGELOG [Unreleased] contradicts itself on SBOM format; still version 0.1.0; duplicate Changed sections | Low | S |
| DOC-07 | No ADR directory for documented design decisions | Low | M |
