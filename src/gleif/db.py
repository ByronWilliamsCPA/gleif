"""DuckDB schema creation, data loading, and connection management."""

from __future__ import annotations

from pathlib import Path

import duckdb
from rich.console import Console

from gleif.constants import (
    LEI_CORE_COLUMNS,
    REPEX_COLUMNS,
    RR_CORE_COLUMNS,
    DatasetType,
)
from gleif.download import DownloadResult

console = Console()

# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------


def get_connection(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Open or create a DuckDB database at the given path.

    Args:
        db_path: Path to the DuckDB file.

    Returns:
        An open DuckDB connection.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db_path))


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------

_LEI_RECORDS_DDL = """
CREATE OR REPLACE TABLE lei_records (
    lei                          VARCHAR PRIMARY KEY,
    legal_name                   VARCHAR,
    legal_address_line1          VARCHAR,
    legal_address_line2          VARCHAR,
    legal_address_city           VARCHAR,
    legal_address_region         VARCHAR,
    legal_address_country        VARCHAR,
    legal_address_postal_code    VARCHAR,
    hq_address_line1             VARCHAR,
    hq_address_line2             VARCHAR,
    hq_address_city              VARCHAR,
    hq_address_region            VARCHAR,
    hq_address_country           VARCHAR,
    hq_address_postal_code       VARCHAR,
    registration_authority_id    VARCHAR,
    registration_authority_entity_id VARCHAR,
    legal_jurisdiction           VARCHAR,
    entity_category              VARCHAR,
    entity_sub_category          VARCHAR,
    legal_form_code              VARCHAR,
    legal_form_other             VARCHAR,
    entity_status                VARCHAR,
    entity_creation_date         VARCHAR,
    associated_lei               VARCHAR,
    associated_entity_type       VARCHAR,
    initial_registration_date    VARCHAR,
    last_update_date             VARCHAR,
    registration_status          VARCHAR,
    next_renewal_date            VARCHAR,
    managing_lou                 VARCHAR,
    validation_sources           VARCHAR,
    conformity_flag              VARCHAR
)
"""

_RELATIONSHIPS_DDL = """
CREATE OR REPLACE TABLE relationships (
    start_node_id          VARCHAR NOT NULL,
    end_node_id            VARCHAR NOT NULL,
    relationship_type      VARCHAR NOT NULL,
    relationship_status    VARCHAR,
    start_node_id_type     VARCHAR,
    end_node_id_type       VARCHAR,
    period_1_start_date    VARCHAR,
    period_1_end_date      VARCHAR,
    period_1_type          VARCHAR,
    qualifier_1_dimension  VARCHAR,
    qualifier_1_category   VARCHAR,
    quantifier_1_method    VARCHAR,
    quantifier_1_amount    VARCHAR,
    quantifier_1_units     VARCHAR,
    registration_initial_date VARCHAR,
    registration_last_update  VARCHAR,
    registration_status       VARCHAR,
    registration_next_renewal VARCHAR,
    managing_lou              VARCHAR,
    validation_sources        VARCHAR,
    validation_documents      VARCHAR,
    validation_reference      VARCHAR,
    PRIMARY KEY (start_node_id, end_node_id, relationship_type)
)
"""

_REPORTING_EXCEPTIONS_DDL = """
CREATE OR REPLACE TABLE reporting_exceptions (
    lei                    VARCHAR NOT NULL,
    exception_category     VARCHAR NOT NULL,
    exception_reason_1     VARCHAR,
    exception_reference_1  VARCHAR,
    PRIMARY KEY (lei, exception_category)
)
"""

_LOAD_METADATA_DDL = """
CREATE TABLE IF NOT EXISTS load_metadata (
    dataset_type   VARCHAR PRIMARY KEY,
    publish_date   VARCHAR,
    loaded_at      TIMESTAMP DEFAULT current_timestamp,
    record_count   INTEGER
)
"""

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_rel_start ON relationships(start_node_id)",
    "CREATE INDEX IF NOT EXISTS idx_rel_end ON relationships(end_node_id)",
    "CREATE INDEX IF NOT EXISTS idx_rel_type ON relationships(relationship_type)",
    "CREATE INDEX IF NOT EXISTS idx_rel_status ON relationships(relationship_status)",
    "CREATE INDEX IF NOT EXISTS idx_repex_lei ON reporting_exceptions(lei)",
]


def create_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Create all tables (without indexes — those come after loading).

    Args:
        con: Open DuckDB connection.
    """
    con.execute(_LOAD_METADATA_DDL)


def _create_indexes(con: duckdb.DuckDBPyConnection) -> None:
    """Create indexes after bulk loading."""
    for stmt in _INDEXES:
        con.execute(stmt)


# ---------------------------------------------------------------------------
# Column-select helpers
# ---------------------------------------------------------------------------


def _build_select_clause(column_map: dict[str, str]) -> str:
    """Build a SQL SELECT clause that renames CSV columns.

    Args:
        column_map: Mapping from CSV header name to desired DB column name.

    Returns:
        SQL fragment like: "col1" AS alias1, "col2" AS alias2, ...
    """
    parts = [f'"{csv_col}" AS {db_col}' for csv_col, db_col in column_map.items()]
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_lei_records(con: duckdb.DuckDBPyConnection, csv_path: Path) -> int:
    """Load Level 1 LEI records from an extracted CSV.

    Args:
        con: Open DuckDB connection.
        csv_path: Path to the extracted Level 1 CSV file.

    Returns:
        Number of rows loaded.
    """
    select_clause = _build_select_clause(LEI_CORE_COLUMNS)
    sql = f"""
        CREATE OR REPLACE TABLE lei_records AS
        SELECT {select_clause}
        FROM read_csv(
            '{csv_path!s}',
            all_varchar=true,
            header=true,
            parallel=true,
            sample_size=100000,
            ignore_errors=true
        )
    """
    con.execute(sql)
    result = con.execute("SELECT count(*) FROM lei_records").fetchone()
    return result[0] if result else 0


def load_relationships(con: duckdb.DuckDBPyConnection, csv_path: Path) -> int:
    """Load Level 2 relationship records from an extracted CSV.

    Args:
        con: Open DuckDB connection.
        csv_path: Path to the extracted Level 2 RR CSV file.

    Returns:
        Number of rows loaded.
    """
    select_clause = _build_select_clause(RR_CORE_COLUMNS)
    sql = f"""
        CREATE OR REPLACE TABLE relationships AS
        SELECT {select_clause}
        FROM read_csv(
            '{csv_path!s}',
            all_varchar=true,
            header=true,
            parallel=true,
            ignore_errors=true
        )
    """
    con.execute(sql)
    result = con.execute("SELECT count(*) FROM relationships").fetchone()
    return result[0] if result else 0


def load_reporting_exceptions(con: duckdb.DuckDBPyConnection, csv_path: Path) -> int:
    """Load Level 2 reporting exceptions from an extracted CSV.

    Args:
        con: Open DuckDB connection.
        csv_path: Path to the extracted Level 2 exceptions CSV file.

    Returns:
        Number of rows loaded.
    """
    select_clause = _build_select_clause(REPEX_COLUMNS)
    sql = f"""
        CREATE OR REPLACE TABLE reporting_exceptions AS
        SELECT {select_clause}
        FROM read_csv(
            '{csv_path!s}',
            all_varchar=true,
            header=true,
            parallel=true,
            ignore_errors=true
        )
    """
    con.execute(sql)
    result = con.execute("SELECT count(*) FROM reporting_exceptions").fetchone()
    return result[0] if result else 0


def _update_metadata(
    con: duckdb.DuckDBPyConnection,
    dataset_type: DatasetType,
    publish_date: str,
    record_count: int,
) -> None:
    """Insert or update the load metadata for a dataset."""
    con.execute(
        """
        INSERT OR REPLACE INTO load_metadata
            (dataset_type, publish_date, loaded_at, record_count)
        VALUES ($1, $2, current_timestamp, $3)
        """,
        [dataset_type.value, publish_date, record_count],
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def load_all(
    con: duckdb.DuckDBPyConnection,
    download_results: list[DownloadResult],
) -> dict[DatasetType, int]:
    """Load all downloaded datasets into DuckDB.

    Args:
        con: Open DuckDB connection.
        download_results: List of DownloadResult from the download phase.

    Returns:
        Mapping of dataset type to number of rows loaded.
    """
    create_schema(con)

    loader_map = {
        DatasetType.LEI: load_lei_records,
        DatasetType.RELATIONSHIPS: load_relationships,
        DatasetType.REPORTING_EXCEPTIONS: load_reporting_exceptions,
    }

    counts: dict[DatasetType, int] = {}
    for result in download_results:
        loader = loader_map[result.dataset_type]
        console.print(
            f"  Loading [cyan]{result.record_label}[/] from {result.csv_path.name}..."
        )
        count = loader(con, result.csv_path)
        _update_metadata(con, result.dataset_type, result.publish_date, count)
        counts[result.dataset_type] = count
        console.print(f"    [green]{count:,} rows loaded[/]")

    console.print("  Creating indexes...")
    _create_indexes(con)
    console.print("  [green]Done.[/]")

    return counts


def get_status(
    con: duckdb.DuckDBPyConnection,
) -> list[tuple[str, str, str, int]]:
    """Get load metadata for all datasets.

    Args:
        con: Open DuckDB connection.

    Returns:
        List of (dataset_type, publish_date, loaded_at, record_count) tuples.
    """
    try:
        rows = con.execute(
            "SELECT dataset_type, publish_date, loaded_at, record_count "
            "FROM load_metadata ORDER BY dataset_type"
        ).fetchall()
    except duckdb.CatalogException:
        return []
    return rows
