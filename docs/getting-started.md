# Getting Started

## Requirements

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Installation

```bash
# Clone the repository
git clone https://github.com/ByronWilliamsCPA/gleif.git
cd gleif

# Install with uv (installs all runtime and dev dependencies)
uv sync --all-extras
```

The `gleif` command is then available via:

```bash
uv run gleif --help
```

## First run

The datasets are large (the Level 1 LEI file is ~800 MB compressed). Allow 5-10 minutes for the initial download on a typical broadband connection.

!!! warning "Disk space"
    The initial refresh requires approximately 2 GB of free disk space: ~835 MB for the three ZIP archives during download, plus ~1 GB for the loaded DuckDB database. The ZIPs are deleted after extraction, leaving ~1 GB in use at steady state.

```bash
# Download all three datasets and load them into DuckDB in one step
uv run gleif refresh
```

Output:

```text
Refreshing GLEIF data...
  Level 1 - LEI Records ━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 823 MB  4.2 MB/s
  Level 2 - Relationships ━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%  12 MB  4.1 MB/s
  Level 2 - Reporting Exceptions ━━━━━━━━━━━━━━━━━━━━ 100%   3 MB  4.0 MB/s

Loading into ~/.local/share/gleif/gleif.duckdb...
  Loading Level 1 - LEI Records...    2,381,240 rows loaded
  Loading Level 2 - Relationships...  4,012,887 rows loaded
  Loading Level 2 - Reporting Exceptions...  521,044 rows loaded
  Creating indexes...
  Done.
Refresh complete.
```

## File locations

By default, data and the database are stored under your home directory:

| Path | Contents |
| ---- | -------- |
| `~/.local/share/gleif/data/` | Extracted CSVs and publish-date markers |
| `~/.local/share/gleif/gleif.duckdb` | DuckDB database file |

Override these with `--data-dir` and `--db` on any command:

```bash
uv run gleif refresh --data-dir /mnt/data/gleif --db /mnt/data/gleif.duckdb
```

## Keeping data fresh

GLEIF publishes updated golden copy files daily. Re-running `gleif refresh` is safe: it checks the `x-gleif-publish-date` response header and skips downloading if your local copy is already current.

```bash
# No-op if already up to date
uv run gleif refresh

# Force re-download regardless of freshness
uv run gleif refresh --force
```

Check when your data was last loaded:

```bash
uv run gleif status
```

## Your first LEI lookup

```bash
uv run gleif lei HWUPKR0MPOU8FGXBT394
```

This returns a structured report with:

- Entity details (name, status, jurisdiction, addresses)
- Direct parent (immediate consolidating entity)
- Ultimate parent (top of the ownership chain)
- Children (entities that report this LEI as their parent)
- Siblings (entities sharing the same direct parent)
- Reporting exceptions (if the entity cannot disclose ownership)

To see the full corporate hierarchy as a tree:

```bash
uv run gleif lei HWUPKR0MPOU8FGXBT394 --tree
```

To include ISIN mappings from the GLEIF REST API:

```bash
uv run gleif lei HWUPKR0MPOU8FGXBT394 --isin
```

An ISIN (International Securities Identification Number) is a 12-character alphanumeric code that uniquely identifies a security such as a stock or bond. GLEIF maps LEIs to ISINs where the legal entity is also an issuer of securities.
