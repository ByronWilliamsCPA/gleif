# CLI Reference

All commands are run via `uv run gleif <command>` (or `gleif <command>` if installed globally).

```
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

```
Usage: gleif download [OPTIONS]

  Download and extract all GLEIF golden copy datasets.

Options:
  --data-dir PATH  Directory for downloaded data files.
  --force          Re-download even if local data is current.
  --help           Show this message and exit.
```

### Freshness check

Before downloading, the command sends a HEAD request to check the `x-gleif-publish-date` header. If the local publish-date marker matches the remote, the download is skipped. Pass `--force` to bypass this check.

### Output files

Each dataset is downloaded as a ZIP, extracted to a CSV, and the ZIP is deleted. The extracted CSV names follow the GLEIF convention:

```
<date>-gleif-goldencopy-lei2-full-publish.csv
<date>-gleif-goldencopy-rr-full-publish.csv
<date>-gleif-goldencopy-repex-full-publish.csv
```

---

## `gleif load`

Load already-extracted CSVs into DuckDB. Use this when you have CSVs but do not need to re-download (e.g., after a network interruption that left CSVs intact).

```
Usage: gleif load [OPTIONS]

  Load extracted CSVs into DuckDB.

Options:
  --db PATH        Path to the DuckDB database file.
  --data-dir PATH  Directory for downloaded data files.
  --help           Show this message and exit.
```

!!! note
    If no extracted CSV is found for a dataset, the command exits with code 1 and instructs you to run `gleif download` first.

---

## `gleif refresh`

Combines `download` and `load` in a single step. This is the recommended way to update your local database.

```
Usage: gleif refresh [OPTIONS]

  Download and load GLEIF data in one step.

Options:
  --db PATH        Path to the DuckDB database file.
  --data-dir PATH  Directory for downloaded data files.
  --force          Re-download even if local data is current.
  --help           Show this message and exit.
```

---

## `gleif lei`

Look up a single LEI and display its relationship report or corporate hierarchy tree.

```
Usage: gleif lei [OPTIONS] LEI_CODE

  Look up an LEI and display all related entities.

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

Without `--tree`, the command displays a structured report with sections for:

- **Entity panel**: LEI, legal name, status, category, jurisdiction, addresses, registration status, and optionally ISINs
- **Direct Parent**: The entity that directly consolidates this one (`IS_DIRECTLY_CONSOLIDATED_BY`)
- **Ultimate Parent**: The top-level consolidating entity (`IS_ULTIMATELY_CONSOLIDATED_BY`)
- **Children**: All entities that report this LEI as their direct or ultimate parent
- **Siblings**: Entities sharing the same direct parent
- **Other Relationships**: Non-consolidation relationships (branches, fund links, etc.)
- **Reporting Exceptions**: Reason codes if the entity cannot report ownership data

### Tree output (`--tree`)

With `--tree`, the command walks the full corporate hierarchy from the ultimate parent down to all descendants, rendered as a Rich tree. DAG structures (entities with multiple parents) are deduplicated: the first occurrence is shown in full; later references show `(see above)`.

### ISIN lookup (`--isin`)

When `--isin` is passed, the CLI fetches ISINs from the GLEIF REST API (`/lei-records/{lei}/isins`) for all LEIs in the report or tree. This makes additional HTTP requests and may add a few seconds to the response time.

### Exit codes

| Code | Meaning |
| ---- | ------- |
| 0 | Success |
| 1 | LEI not found in database, or invalid LEI format |

---

## `gleif name`

Search for entities by legal name using a case-insensitive substring match.

```
Usage: gleif name [OPTIONS] QUERY

  Search for entities by legal name (case-insensitive substring match).

Arguments:
  QUERY  Name or substring to search for.  [required]

Options:
  --db PATH        Path to the DuckDB database file.
  -n, --limit INT  Maximum number of results.  [default: 100]
  --isin           Fetch ISINs from the GLEIF API.
  --help           Show this message and exit.
```

### Example

```bash
gleif name "volkswagen" --limit 20
```

Results are displayed in a table with columns: LEI, Legal Name, Jurisdiction, Status. Passing `--isin` adds an ISINs column.

---

## `gleif status`

Display the current state of the local DuckDB database.

```
Usage: gleif status [OPTIONS]

  Show database status: record counts and data freshness.

Options:
  --db PATH  Path to the DuckDB database file.
  --help     Show this message and exit.
```

Shows a table with dataset name, publish date, load timestamp, and row count. Exits with code 1 if the database file does not exist or no data has been loaded.
