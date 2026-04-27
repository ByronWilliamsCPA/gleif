# GLEIF CLI

A command-line tool for working with [GLEIF](https://www.gleif.org/) (Global Legal Entity Identifier Foundation) golden copy datasets. It downloads the three public LEI datasets, loads them into a local [DuckDB](https://duckdb.org/) database, and lets you query ownership hierarchies, search entities by name, and resolve ISINs.

## What it does

| Step | Command | What happens |
| ---- | ------- | ------------ |
| Download | `gleif download` | Fetches three GLEIF ZIP files from the golden copy API, extracts CSVs |
| Load | `gleif load` | Bulk-loads the CSVs into DuckDB with column renaming |
| Query | `gleif lei <LEI>` | Looks up parents, children, siblings, and reporting exceptions |
| Search | `gleif name <QUERY>` | Case-insensitive substring search across 2M+ legal names |
| Status | `gleif status` | Shows row counts and publish dates for loaded datasets |

## Datasets

GLEIF publishes three "golden copy" datasets daily:

| Level | Dataset | Contents |
| ----- | ------- | -------- |
| Level 1 | LEI Records (`lei2`) | ~2.3M legal entities: names, addresses, jurisdictions, statuses |
| Level 2 | Relationships (`rr`) | Parent-child consolidation links between entities |
| Level 2 | Reporting Exceptions (`repex`) | Entities that cannot or do not report ownership relationships |

## Quick example

```bash
# First-time setup: download and load all datasets (~5 min)
gleif refresh

# Look up Apple Inc.'s global ultimate parent and subsidiaries
gleif lei HWUPKR0MPOU8FGXBT394

# Show the full corporate tree from any node
gleif lei HWUPKR0MPOU8FGXBT394 --tree

# Search for entities with "Deutsche Bank" in their legal name
gleif name "Deutsche Bank"

# Check how fresh your local data is
gleif status
```

## Navigation

- [Getting Started](getting-started.md) — installation, first run, freshness checks
- [CLI Reference](cli-reference.md) — all commands, options, and exit codes
- [Architecture](architecture/index.md) — data pipeline, module map, design decisions
- [Data Model & Schema](architecture/data-model.md) — DuckDB tables, column mappings, relationship conventions
- [Development](development.md) — local setup, testing, linting, CI/CD
