# 04 - Architecture & Structure Audit

Scope: module boundaries, layering, coupling, config centralization across `src/gleif/*.py` (HEAD 7fd3cb5).

## Assessment

The structure is sound for a CLI this size. The dependency graph is a clean DAG with one
direction: `cli -> {rendering, queries, db, download, isin, constants}`,
`queries -> {models, constants}`, `db -> {constants, download(TYPE_CHECKING only)}`,
`rendering -> models`, `download/isin -> constants`. Verified at runtime: importing
`gleif.db`, `gleif.queries`, `gleif.models` pulls in only `gleif.constants` and each other,
never `cli` or `rendering`. No circular imports. The persistence layer does not import the
presentation layer, and `models` depends on nothing internal. Cohesion is good: each module
owns one concern and the public API in `__init__.py` matches the actual layout.

Real problems are narrow. The two that cost maintainers: `db.py` does its own terminal
output (a layering leak the codebase explicitly tries to avoid elsewhere), and a handful of
config values that belong in `constants.py` are scattered (`'ACTIVE'`, the ISIN base URL,
network magic numbers). The convention docs also contain one drift (`# noqa` ban) and one
stale example (RAD doc) that will mislead.

## Findings

### ARCH-01 - Persistence layer writes terminal output

Severity: Medium. Effort: S.
Files: `db.py:54,68,433-443`.
`db.py` imports `rich.console.Console`, instantiates its own `console = Console()`
(db.py:68), and `load_all` prints progress directly (`console.print(...)` at db.py:433, 435,
439, 441, 443). The codebase otherwise concentrates presentation in `rendering.py`, whose
own docstring states the split exists "so the CLI module can focus on ... command dispatch"
(rendering.py:9-12). The data layer emitting Rich markup couples persistence to a UI library
and means there are now two independent `Console()` instances (db.py:68 and rendering.py:36)
with no shared configuration. Anyone using `load_all` as a library function (the `__init__.py`
and db.py docstrings both advertise programmatic use) gets unsolicited stdout.
Recommendation: have `load_all` take an optional progress/callback or return per-step
counts, and let `cli.py` render. At minimum, route through the single `rendering.console`.

### ARCH-02 - `'ACTIVE'` relationship status hardcoded in 6 SQL bodies

Severity: Low. Effort: S.
Files: `queries.py:138,177,222,226,280,404,467`.
Every traversal query inlines `r.relationship_status = 'ACTIVE'`. `constants.py` already
houses the analogous relationship-type literals (`DIRECT_PARENT`, `ULTIMATE_PARENT`,
`CONSOLIDATION_TYPES`, constants.py:153-160), so the active-status filter is the one
query-semantics constant that leaks. If GLEIF adds a status the tool should also accept, the
change touches seven call sites. Recommendation: add `ACTIVE_STATUS = "ACTIVE"` to
constants.py and reference it (string-build or bind as a parameter).

### ARCH-03 - ISIN endpoint URL lives outside constants.py

Severity: Low. Effort: S.
Files: `isin.py:32`, `constants.py:21`.
`GLEIF_API_BASE = "https://api.gleif.org/api/v1/lei-records"` is defined in `isin.py`, while
the golden-copy base URL and `DATASET_URLS` live in `constants.py:21,50`. constants.py's
module docstring claims it is the home for "the GLEIF API endpoints used for downloads"
(constants.py:3-4). Two GLEIF hosts, two homes. Centralizing both makes the external
dependency surface visible in one file. Recommendation: move `GLEIF_API_BASE` (and the
`_REQUEST_TIMEOUT`, see ARCH-04) into constants.py.

### ARCH-04 - Network magic numbers inline

Severity: Low. Effort: S.
Files: `download.py:180,215`, `cli.py:186`.
`timeout=600.0` (download.py:180) and `chunk_size=65536` (download.py:215) are unnamed
literals; the docstring describes them as "10-minute timeout" and "64 KiB chunks" but the
numbers are not constants. `cli.py:186` defines `lei_length = 20` as a local inside the `lei`
command. By contrast `isin.py:33` does name `_REQUEST_TIMEOUT = 10.0`, so the codebase is
inconsistent about whether these are named. Recommendation: name the download timeout and
chunk size as module constants (or in constants.py); promote LEI length to a shared constant
since the 20-char rule is a domain invariant referenced in several docstrings.

### ARCH-05 - `# noqa` present despite documented ban

Severity: Low. Effort: S.
Files: `cli.py:105`, `AGENTS.md:77`, `.github/copilot-instructions.md:30-31`.
AGENTS.md:77 states "No `# noqa`, `# type: ignore`, or CI bypass flags; fix the actual
issue." cli.py:105 carries `# noqa: PLC0415` on a function-local import of
`DownloadResult`, `find_extracted_csv`, `read_local_publish_date` inside the `load` command.
This is the only suppression in the source (no `type: ignore` anywhere, confirmed), and the
function-local import is itself a minor smell: those three symbols are public `download`
exports used only by one command, imported lazily to avoid... nothing measurable here, since
`download` is already imported at cli.py:41. Recommendation: hoist the import to module top
(it adds no cycle and `download_all` is already imported there) and drop the `noqa`, or
amend AGENTS.md to carve out an explicit exception. Right now the code contradicts the stated
rule.

### ARCH-06 - RAD doc example contradicts actual code conventions

Severity: Low. Effort: S.
Files: `docs/response-aware-development.md:37-48`.
The "real-world" code sample uses `conn.execute("... WHERE lei = ?", [lei])` with `?`
placeholders and recommends a `table_exists(conn, "lei_records")` guard. The actual codebase
uses DuckDB `$1` named parameters everywhere (queries.py passim) and has no `table_exists`
helper; cold-start protection is instead the `except duckdb.CatalogException` pattern
(db.py:470, documented in queries.py:20-22). A maintainer following this doc would write
SQL in a style the project does not use and reach for a helper that does not exist.
Recommendation: update the example to `$1` and to the actual catalog-exception pattern, or
mark it as illustrative pseudocode.

## Clean areas

- Dependency direction: one-way DAG, no cycles, persistence/query layers do not import UI (verified at runtime).
- `models.py`: pure frozen dataclasses, zero internal deps, all `@dataclass(frozen=True)` per house standard; `frozen` caveat on contained lists is documented (models.py:14-18).
- pathlib: used throughout; no `os` / `os.path` / `os.environ` anywhere in src.
- SQL building: one consistent style (`$1` parameter binding); the only interpolated identifier is the source-controlled table name in `_load_csv_into_table`, with an inline justification (db.py:273-278).
- Async discipline: sync `httpx` confined to `isin.py` (interactive enrichment, documented as deliberate); download path is fully async per copilot-instructions.
- Config single-sourcing for the download pipeline: URLs, column maps, labels, depth bound all in constants.py and imported, not duplicated.
