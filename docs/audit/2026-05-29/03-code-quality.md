# 03 - Code Quality & Maintainability

Scope: read-only audit of `src/gleif/` (9 files, ~1530 LOC) and `tests/` (6 files, ~1330 LOC) at HEAD 7fd3cb5.

## Assessment

This is a clean, well-factored codebase. Tooling already enforces most of what a quality audit would otherwise flag: zero `# type: ignore`, zero `cast(`, zero `Any` annotations, zero TODO/FIXME/HACK/XXX markers, zero ruff complexity violations, and basedpyright strict passes with 0 errors / 0 warnings / 0 notes. Functions are small and single-purpose (queries.py is 642 lines across 13 functions, db.py 472 lines across 11). The real maintainability tax sits in test coverage: 67.30% overall, dragged down by download.py at 21% (the entire HTTP/extract path is unexercised) and the CLI download/load/refresh and `--isin` paths having no tests. A handful of small structural duplications exist in the query and ISIN layers. No Critical or High findings.

## Findings

### CQ-01 download.py is 21% covered; the core download/extract path is untested
Severity: Medium. Effort: M. Files: src/gleif/download.py, tests/.
Evidence: `uv run pytest` coverage report: `download.py 79 stmts, 58 miss, 21%`, missing lines 77, 97-100, 107-108, 127-131, 176-232, 260-271, 303-315. Lines 176-232 are the whole `download_dataset` HEAD/stream/extract body; 260-271 are `_extract_zip` including the zip-slip guard (download.py:267-269) and the empty-archive `ValueError` (download.py:263-264); 303-315 are `download_all`. No test file references `respx`, `monkeypatch`, or mocks any httpx call for downloads. test_isin.py already shows the working pattern (`@patch("gleif.isin.httpx.get")` with `MagicMock`), so the same approach applies to `download_dataset`.
Recommendation: mock the httpx AsyncClient and add tests for: fresh-vs-stale skip logic (download.py:188-201), the zip-slip guard, the no-CSV `ValueError`, and ZIP cleanup. This single file is the main blocker to raising fail_under.

### CQ-02 CLI download/load/refresh and --isin branches have no tests
Severity: Medium. Effort: M. Files: src/gleif/cli.py, tests/test_cli.py.
Evidence: `cli.py 136 stmts, 42 miss, 69%`, missing 89-96 (download), 105-136 (load), 146-155 (refresh), 210-212/223-225 (the `--isin` enrichment branches in `lei`), 259-260 (name `--isin`). `grep "isin" tests/test_cli.py` returns nothing; `grep '"download"\|"load"\|"refresh"' tests/` returns nothing. Existing CLI tests cover lei/name/status/tree well with content assertions, so the gap is specifically the three data-management commands and the ISIN flag.
Recommendation: add CliRunner tests for `load` (point at a fixture data dir; the load path is pure-local and needs no network) and for `lei --isin` / `name --isin` (patch `fetch_isins_batch`). download/refresh need the same httpx mock as CQ-01.

### CQ-03 fail_under is 65 with a stale "raise to 80" comment
Severity: Low. Effort: S. Files: pyproject.toml:115.
Evidence: `fail_under = 65  # interim: raise to 80 once download.py and CLI command tests are added`. The interim comment was introduced 2026-04-25 (commit d39fa7e, `git log -L`), 34 days before this audit, and is the oldest unresolved deferred-work note in the repo (there are no TODO/FIXME markers anywhere). Current coverage 67.30% leaves only ~2 points of headroom; the named prerequisites (CQ-01, CQ-02) are still outstanding.
Recommendation: treat CQ-01/CQ-02 as the work that unblocks raising fail_under to 80, then bump the value and delete the comment.

### CQ-04 rendering.py 62% covered; conditional output branches untested
Severity: Low. Effort: S. Files: src/gleif/rendering.py.
Evidence: `rendering.py 126 stmts, 40 miss, 62%`, missing 41-56 (`collect_report_leis`), 97-107 (`render_exceptions_table`), and the ISIN-column branches in `render_related_table` (192-194) and `render_parent_section` (162-164). Branch-partial hits at 204-215 (`format_node_label` detail assembly). These are pure formatting functions with no I/O, so they are cheap to test directly without the CLI.
Recommendation: unit-test the render helpers against constructed dataclasses, asserting on the returned/printed strings (use a Rich Console with `record=True` or capture stdout).

### CQ-05 Duplicated RelatedEntity row-mapping comprehension across four queries
Severity: Low. Effort: S. Files: src/gleif/queries.py:182-191, 232-241, 285-294 (and the get_siblings block).
Evidence: `grep -c 'direction="'` = 4. The list comprehension building `RelatedEntity(lei=str(row[0]), legal_name=str(row[1]) if row[1] else None, relationship_type=str(row[2]), relationship_status=str(row[3]) if row[3] else "", direction=...)` is repeated verbatim in get_children, get_siblings, get_other_relationships (and the four-arg shape matches), differing only in the `direction` literal. The module already uses this pattern for the single-row case (`_row_to_entity`, `_row_to_hierarchy_node`).
Recommendation: add a `_rows_to_related(rows, direction)` helper mirroring the existing `_row_to_*` helpers.

### CQ-06 Duplicated ISIN-extraction comprehension between fetch_isins and fetch_isins_batch
Severity: Low. Effort: S. Files: src/gleif/isin.py:61-65, 92-96.
Evidence: the identical comprehension `[item["attributes"]["isin"] for item in data if item.get("attributes", {}).get("isin")]` appears in both `fetch_isins` (single, module-level httpx.get) and `fetch_isins_batch` (loop over a shared client). Only the request issuance differs.
Recommendation: extract a `_extract_isins(response_json) -> list[str]` helper used by both.

### CQ-07 get_status return type is declared but not enforced on the duckdb rows
Severity: Low. Effort: S. Files: src/gleif/db.py:448-472.
Evidence: signature declares `-> list[tuple[str, str, str, int]]` but returns `con.execute(...).fetchall()` directly (db.py:466-472); duckdb's `fetchall()` is typed loosely enough that basedpyright accepts this without a cast, so the declared element types are unchecked promises. The `status` CLI consumer (cli.py:313) unpacks four columns positionally, so a schema drift in `load_metadata` would surface only at runtime. Minor; lines 422-445 of `load_all` are also untested (db.py 74% coverage, missing 422-445), which is the same gap as CQ-02's `load` command.
Recommendation: low priority; either narrow at the boundary with an explicit row-mapping helper (consistent with the `_row_to_*` style elsewhere) or accept the loose typing and rely on the `load_all`/`status` tests added under CQ-02.

## Clean areas

- Type discipline: 0 `# type: ignore`, 0 `cast(`, 0 `Any` annotations (the three `Any` grep hits are docstring prose); basedpyright strict = 0 errors / 0 warnings / 0 notes; AGENTS.md ban on `# type: ignore` is honored.
- Complexity: `uv run ruff check --select C901,PLR0912,PLR0913,PLR0915` = "All checks passed!"; no function exceeds the C901 default threshold of 10.
- Tech-debt markers: 0 TODO/FIXME/HACK/XXX in src or tests.
- Test hygiene: 67 passed, 0 skipped, 0 xfail; assertions check output content and values, not just exit codes; no empty/no-op assertions found.
- Module structure: rendering split out of cli to keep per-module complexity down; docstrings are thorough and document edge cases and raised exceptions.
