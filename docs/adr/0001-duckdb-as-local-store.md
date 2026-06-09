# 0001. DuckDB as the local analytical store

Status: accepted

## Context

The three GLEIF golden copy datasets total several GB uncompressed. The CLI
needs to bulk-load CSVs, run recursive hierarchy queries (parent/child
traversal), and substring name search, all on a single user machine with no
server component.

## Decision

Use DuckDB as the embedded store. It loads CSVs directly via `read_csv`, runs
recursive CTEs for hierarchy traversal, supports parameterized queries (`$1`),
and ships as a single file dependency with no separate process.

## Alternatives considered

- SQLite: ubiquitous and embedded, but columnar analytical scans and recursive
  CTE performance over millions of relationship rows are weaker, and `read_csv`
  bulk import is less direct.
- PostgreSQL: strong analytical features, but requires a running server, which
  contradicts the single-user, zero-setup CLI goal.

## Consequences

- One file dependency, no server, fast bulk CSV load and analytical queries.
- Queries against a database that has not been loaded raise
  `duckdb.CatalogException`; the query layer treats that as "no data".
- DuckDB does not bind SQL identifiers, so table and column names are
  interpolated from internal constants (never user input); user values use
  `$1`/`$2` binding.
