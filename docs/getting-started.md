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

```bash
# Download all three datasets and load them into DuckDB in one step
uv run gleif refresh
```

Output:

```
Refreshing GLEIF data...
  Level 1 - LEI Records ━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 823 MB  4.2 MB/s
  Level 2 - Relationships ━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%  12 MB  4.1 MB/s
  Level 2 - Reporting Exceptions ━━━━━━━━━━━━━━━━━━━━ 100%   3 MB  4.0 MB/s

Loading into ~/.local/share/gleif/gleif.duckdb...
  Loading Level 1 - LEI Records from 20240401-gleif-goldencopy-lei2-...csv...
    2,381,240 rows loaded
  Loading Level 2 - Relationships from ...csv...
    4,012,887 rows loaded
  Loading Level 2 - Reporting Exceptions from ...csv...
    521,044 rows loaded
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

```
             GLEIF Database Status
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Dataset                         ┃ Publish Date ┃ Loaded At           ┃   Records ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ Level 1 - LEI Records           │ 2024-04-01   │ 2024-04-02 08:14:05 │ 2,381,240 │
│ Level 2 - Relationships         │ 2024-04-01   │ 2024-04-02 08:14:05 │ 4,012,887 │
│ Level 2 - Reporting Exceptions  │ 2024-04-01   │ 2024-04-02 08:14:05 │   521,044 │
└─────────────────────────────────┴──────────────┴─────────────────────┴───────────┘
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
