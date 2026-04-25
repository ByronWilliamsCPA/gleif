# gleif

CLI tool for downloading GLEIF (Global Legal Entity Identifier Foundation) golden copy
datasets, loading them into a local DuckDB database, and querying LEI relationship
hierarchies.

## Features

- Download all three GLEIF Level 1 and Level 2 datasets
- Bulk-load CSVs into a local DuckDB database for fast querying
- Look up any LEI and display its parents, children, siblings, and reporting exceptions
- Search entities by legal name
- Optional ISIN mapping via GLEIF REST API

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager

## Installation

```bash
uv sync --all-extras
```

## Quick Start

```bash
# Download GLEIF datasets and load into DuckDB (one step)
uv run gleif refresh

# Look up an LEI
uv run gleif lei 5493001KJTIIGC8Y1R12

# Include ISIN mappings
uv run gleif lei 5493001KJTIIGC8Y1R12 --isin

# Search by name
uv run gleif name "Goldman Sachs"

# Show database record counts
uv run gleif status
```

## Commands

| Command | Description |
| ------- | ----------- |
| `gleif download` | Download GLEIF datasets (ZIP files) |
| `gleif load` | Load downloaded CSVs into DuckDB |
| `gleif refresh` | Download and load in one step |
| `gleif lei <LEI>` | Look up an LEI and display related entities |
| `gleif name <QUERY>` | Search entities by legal name (substring) |
| `gleif status` | Show database record counts and data freshness |

## Data Storage

By default, data is stored in:

- Data files: `~/.local/share/gleif/data`
- Database: `~/.local/share/gleif/gleif.duckdb`

## Documentation

Full documentation including CLI reference, architecture overview, and data model:
see the `docs/` directory or run `uv run mkdocs serve` to browse locally.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
