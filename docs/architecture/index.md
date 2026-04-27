# Architecture Overview

## Data pipeline

```text
GLEIF REST API
    │
    │  HEAD  x-gleif-publish-date (freshness check)
    │  GET   /golden-copies/publishes/{dataset}/latest.csv  (streamed ZIP)
    ▼
download.py ──► extract CSV from ZIP ──► delete ZIP
    │
    │  DownloadResult (csv_path, publish_date, dataset_type)
    ▼
db.py ──► DuckDB read_csv() with column select/rename
    │
    │  CREATE OR REPLACE TABLE ... AS SELECT <column_map> FROM read_csv(...)
    ▼
DuckDB file at ~/.local/share/gleif/gleif.duckdb
    │
    │  parameterized SQL queries
    ▼
queries.py ──► frozen dataclasses (models.py)
    │
    ▼
cli.py ──► Rich terminal output (panels, tables, trees)
```

## Module map

| Module | Responsibility |
| ------ | -------------- |
| `constants.py` | Dataset URLs, CSV-to-DB column mappings, `DatasetType` enum, relationship type constants |
| `download.py` | Async download of three GLEIF ZIP files with freshness checking via publish-date markers; `DownloadResult` dataclass |
| `db.py` | DuckDB connection management, `CREATE OR REPLACE TABLE` via `read_csv()`, index creation, load metadata tracking |
| `queries.py` | LEI lookup functions: entity info, parent traversal, children, siblings, reporting exceptions, corporate group tree |
| `models.py` | Frozen dataclasses: `EntityInfo`, `RelatedEntity`, `ReportingException`, `HierarchyNode`, `CorporateGroup`, `LEIRelationshipReport` |
| `isin.py` | ISIN lookup via GLEIF REST API (`/lei-records/{lei}/isins`); single and batch with httpx |
| `cli.py` | Typer app with all commands; Rich rendering of reports, tables, and hierarchy trees |

## Key design decisions

### DuckDB as the local store

The GLEIF golden copy datasets are large (Level 1 is ~2.3M rows with 338 columns). DuckDB's `read_csv()` function can bulk-load these files in seconds using parallel I/O. Queries run against the local file without any server process, which keeps the tool self-contained.

The full Level 1 CSV has 338 columns. Loading only the ~30 relevant columns via a `SELECT` inside `read_csv()` avoids storing data that is never queried and keeps the database file small.

### Relationship direction convention

In the GLEIF relationship dataset, `start_node_id` is the **child** and `end_node_id` is the **parent**. This follows the GLEIF spec: the relationship type is `IS_DIRECTLY_CONSOLIDATED_BY`, read left-to-right as "child IS_DIRECTLY_CONSOLIDATED_BY parent".

```sql
-- Find the direct parent of an entity
SELECT end_node_id AS parent_lei
FROM relationships
WHERE start_node_id = '<child_lei>'
  AND relationship_type = 'IS_DIRECTLY_CONSOLIDATED_BY'
  AND relationship_status = 'ACTIVE'

-- Find all children of an entity
SELECT start_node_id AS child_lei
FROM relationships
WHERE end_node_id = '<parent_lei>'
  AND relationship_type = 'IS_DIRECTLY_CONSOLIDATED_BY'
  AND relationship_status = 'ACTIVE'
```

### Cycle prevention in recursive queries

Corporate ownership structures can contain cycles (e.g., cross-holdings). Both `get_ancestor_chain` and `get_descendant_tree` use DuckDB's recursive CTE with a `path` array to track visited nodes and halt if a cycle is detected:

```sql
WHERE NOT list_contains(a.path, r.end_node_id)
```

The `MAX_HIERARCHY_DEPTH` constant (default: 50) provides a secondary depth limit.

### Async download with sequential loading

All three datasets are downloaded concurrently using `asyncio.gather()` with a shared Rich progress bar. Loading is done sequentially: DuckDB connections are not thread-safe, and `CREATE OR REPLACE TABLE` DDL statements cannot be parallelized over a single connection.

### Frozen dataclasses as query return types

All query results are returned as frozen dataclasses (`@dataclass(frozen=True)`). This prevents accidental mutation of results between query and render, and makes the types hashable for use in sets and dict keys (e.g., deduplicating LEI lists for batch ISIN lookups).
