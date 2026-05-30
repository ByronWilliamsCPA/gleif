# gleif

[![CI](https://github.com/ByronWilliamsCPA/gleif/actions/workflows/ci.yml/badge.svg)](https://github.com/ByronWilliamsCPA/gleif/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/ByronWilliamsCPA/gleif/badge)](https://securityscorecards.dev/viewer/?uri=github.com/ByronWilliamsCPA/gleif)

A CLI that downloads [GLEIF](https://www.gleif.org) golden copy datasets, loads them into a
local [DuckDB](https://duckdb.org) database, and lets you query LEI relationship hierarchies
from the command line.

```shell
gleif lei 2138005YL12BKW2FQA89
```

```text
Entity          APPLE INC.
LEI             2138005YL12BKW2FQA89
Status          ACTIVE
Jurisdiction    US

Direct parent   549300BPKFKRT74GKU44  (APPLE INC.)
Ultimate parent 549300BPKFKRT74GKU44  (APPLE INC.)

Children (2)
  LEI                          Name
  XKZZ2JZF41MRHTR1V493        Apple Operations International Limited
  ...
```

## Features

- Downloads all three GLEIF golden copy datasets (Level 1 LEI, Level 2 Relationships,
  Level 2 Reporting Exceptions) with freshness checking
- Bulk-loads CSVs into a local DuckDB database (~5 GB uncompressed, loads in under a minute)
- Traverses full parent/child/sibling hierarchies for any LEI
- Resolves reporting exceptions (why a parent relationship was not reported)
- Optional ISIN lookups via the GLEIF REST API (`--isin`)
- Substring name search across all registered legal entities

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Installation

The package is not yet published to PyPI; install from source:

```bash
git clone https://github.com/ByronWilliamsCPA/gleif.git
cd gleif
uv sync
```

## Usage

```bash
# Download all three GLEIF golden copy datasets
gleif download

# Load downloaded CSVs into the local DuckDB database
gleif load

# Download + load in one step
gleif refresh

# Look up an LEI and display its full relationship hierarchy
gleif lei 2138005YL12BKW2FQA89

# Include ISIN mappings in the report
gleif lei 2138005YL12BKW2FQA89 --isin

# Search for entities by legal name (substring)
gleif name "Apple"

# Show record counts for all database tables
gleif status
```

Data is stored at `~/.local/share/gleif/` by default.

## Data Freshness & Update Schedule

GLEIF publishes the golden copy datasets **three times per day** at
`00:00`, `08:00`, and `16:00` UTC. Each publish is identified by an
`x-gleif-publish-date` HTTP header on the download URL.

This CLI uses that header to short-circuit redundant downloads:

- On every `gleif download` / `gleif refresh`, the tool sends an HTTP `HEAD`
  request to each of the three dataset endpoints and reads the
  `x-gleif-publish-date` header.
- If the remote publish date matches the locally stored marker
  (`<dataset>_publish_date.txt` inside the data directory) and the previously
  extracted CSV is still on disk, the download is skipped.
- Pass `--force` to bypass the freshness check and always re-download.

Recommended cadence: run `gleif refresh` daily or every 8 hours via cron /
systemd timer / Task Scheduler if you want to track each publish window.
Use `gleif status` to see the publish date and load timestamp for each
dataset currently in the local database.

The three datasets and their endpoints (all served over HTTPS from
`goldencopy.gleif.org`):

| Dataset | Endpoint |
| ------- | -------- |
| Level 1 LEI | `/api/v2/golden-copies/publishes/lei2/latest.csv` |
| Level 2 Relationships | `/api/v2/golden-copies/publishes/rr/latest.csv` |
| Level 2 Reporting Exceptions | `/api/v2/golden-copies/publishes/repex/latest.csv` |

## Architecture

Three GLEIF datasets are downloaded as ZIPs, extracted to CSV, and bulk-loaded
into a local DuckDB database:

| Dataset | Table | Key |
| ------- | ----- | --- |
| Level 1 LEI (`lei2`) | `lei_records` | `lei` |
| Level 2 Relationships (`rr`) | `relationships` | `(start_node_id, end_node_id, relationship_type)` |
| Level 2 Reporting Exceptions (`repex`) | `reporting_exceptions` | `(lei, exception_category)` |

Relationship direction: `start_node_id` is the child, `end_node_id` is the parent.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and contribution instructions.

## License

MIT. See [LICENSE](LICENSE).
