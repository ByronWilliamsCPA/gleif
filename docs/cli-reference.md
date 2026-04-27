# CLI Reference

All commands are run via `uv run gleif <command>` (or `gleif <command>` if installed globally).

```text
Usage: gleif [OPTIONS] COMMAND [ARGS]...

  GLEIF Golden Copy data loader and LEI relationship query CLI.

Options:
  --help  Show this message and exit.

Commands:
  download  Download and extract all GLEIF golden copy datasets.
  load      Load extracted CSVs into DuckDB.
  lei       Look up an LEI and display all related entities.
  name      Search for entities by legal name.
  refresh   Download and load GLEIF data in one step.
  status    Show database status: record counts and data freshness.
```

## Global options

| Option | Default | Description |
| ------ | ------- | ----------- |
| `--db PATH` | `~/.local/share/gleif/gleif.duckdb` | Path to the DuckDB database file |
| `--data-dir PATH` | `~/.local/share/gleif/data` | Directory for downloaded data files |

---

## `gleif download`

Download and extract all three GLEIF golden copy datasets from the golden copy API.

```text
Usage: gleif download [OPTIONS]

Options:
  --data-dir PATH  Directory for downloaded data files.
  --force          Re-download even if local data is current.
  --help           Show this message and exit.
```

### Freshness check

Before downloading, the command sends a HEAD request to check the `x-gleif-publish-date` header. If the local publish-date marker matches the remote, the download is skipped. Pass `--force` to bypass this check.

### Output files

Each dataset is downloaded as a ZIP, extracted to a CSV, and the ZIP is deleted. Extracted CSV names follow the GLEIF convention:

```text
<date>-gleif-goldencopy-lei2-full-publish.csv
<date>-gleif-goldencopy-rr-full-publish.csv
<date>-gleif-goldencopy-repex-full-publish.csv
```

### Exit codes

| Code | Meaning |
| ---- | ------- |
| 0 | All datasets downloaded successfully (or already current, skipped) |
| Non-zero | Network or HTTP error (unhandled exception) |

---

## `gleif load`

Load already-extracted CSVs into DuckDB. Useful when CSVs are intact but you need to reload (e.g., after a schema change).

```text
Usage: gleif load [OPTIONS]

Options:
  --db PATH        Path to the DuckDB database file.
  --data-dir PATH  Directory for downloaded data files.
  --help           Show this message and exit.
```

!!! note
    If no extracted CSV is found for a dataset, the command exits with code 1 and instructs you to run `gleif download` first.

### Exit codes

| Code | Meaning |
| ---- | ------- |
| 0 | All CSVs loaded successfully |
| 1 | A required CSV is missing; run `gleif download` first |

---

## `gleif refresh`

Combines `download` and `load` in a single step. This is the recommended way to update your local database.

```text
Usage: gleif refresh [OPTIONS]

Options:
  --db PATH        Path to the DuckDB database file.
  --data-dir PATH  Directory for downloaded data files.
  --force          Re-download even if local data is current.
  --help           Show this message and exit.
```

### Exit codes

| Code | Meaning |
| ---- | ------- |
| 0 | Download and load completed successfully |
| Non-zero | Network or HTTP error (unhandled exception) |

---

## `gleif lei`

Look up a single LEI and display its relationship report or corporate hierarchy tree.

```text
Usage: gleif lei [OPTIONS] LEI_CODE

Arguments:
  LEI_CODE  The LEI to look up. Must be exactly 20 characters.  [required]

Options:
  --db PATH          Path to the DuckDB database file.
  --isin             Fetch ISINs from the GLEIF REST API.
  --tree             Show full corporate hierarchy tree.
  --max-depth INT    Maximum depth for hierarchy traversal.  [default: 50]
  --help             Show this message and exit.
```

### Default output (flat report)

Without `--tree`, the command displays a structured report with:

- **Entity panel**: LEI, legal name, status, category, jurisdiction, addresses, registration status
- **Direct Parent**: The entity that directly consolidates this one (`IS_DIRECTLY_CONSOLIDATED_BY`)
- **Ultimate Parent**: The top-level consolidating entity (`IS_ULTIMATELY_CONSOLIDATED_BY`)
- **Children**: All entities that report this LEI as their direct or ultimate parent
- **Siblings**: Entities sharing the same direct parent
- **Other Relationships**: Non-consolidation relationships (branches, fund links, etc.)
- **Reporting Exceptions**: Reason codes if the entity cannot report ownership data

### Tree output (`--tree`)

Walks the full corporate hierarchy from the ultimate parent down to all descendants, rendered as a Rich tree. Diamond structures (entities with multiple parents) are deduplicated: the first occurrence is shown in full; later references show `(see above)`.

### ISIN lookup (`--isin`)

Fetches ISINs from the GLEIF REST API (`/lei-records/{lei}/isins`) for all LEIs in the report or tree. Makes additional HTTP requests; expect a few seconds of latency.

### Exit codes

| Code | Meaning |
| ---- | ------- |
| 0 | Success |
| 1 | LEI not found in database, or invalid LEI format |

---

## `gleif name`

Search for entities by legal name using a case-insensitive substring match.

```text
Usage: gleif name [OPTIONS] QUERY

Arguments:
  QUERY  Name or substring to search for.  [required]

Options:
  --db PATH        Path to the DuckDB database file.
  -n, --limit INT  Maximum number of results.  [default: 100]
  --isin           Fetch ISINs from the GLEIF API.
  --help           Show this message and exit.
```

Results are displayed in a table with columns: LEI, Legal Name, Jurisdiction, Status. Passing `--isin` adds an ISINs column.

```bash
gleif name "volkswagen" --limit 20
```

### Match behavior

Queries use a parameterized case-insensitive substring match (`ILIKE $1` with bind value `%query%`) against the `legal_name` column, using DuckDB's default collation. Results are ordered alphabetically by legal name. Passing `--limit` caps the result count; the default is 100.

### Exit codes

| Code | Meaning |
| ---- | ------- |
| 0 | Success (results found, or no results) |

---

## `gleif status`

Display the current state of the local DuckDB database.

```text
Usage: gleif status [OPTIONS]

Options:
  --db PATH  Path to the DuckDB database file.
  --help     Show this message and exit.
```

Shows a table with dataset name, publish date, load timestamp, and row count.

### Exit codes

| Code | Meaning |
| ---- | ------- |
| 0 | Database exists and data is loaded |
| 1 | Database file not found, or no data loaded yet |
