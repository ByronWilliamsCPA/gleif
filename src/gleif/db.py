"""DuckDB schema creation, bulk CSV loading, and connection management.

This module owns the local persistence layer for GLEIF data. It
opens connections to a DuckDB file, declares the three data tables
plus a small ``load_metadata`` tracking table, and bulk-loads the
extracted golden copy CSVs via DuckDB's ``read_csv`` reader. CSV
columns are projected and renamed on the fly using the
``LEI_CORE_COLUMNS``, ``RR_CORE_COLUMNS``, and ``REPEX_COLUMNS``
mappings from :mod:`gleif.constants`.

Schema overview
---------------
The data tables are created via ``CREATE OR REPLACE TABLE ... AS
SELECT ... FROM read_csv(...)`` and so do **not** carry SQL primary
key constraints. The columns below are the logical keys used by
the query layer; ``load_metadata`` is created with a real
``PRIMARY KEY`` constraint via ``CREATE TABLE IF NOT EXISTS``.

======================  =================================================
Table                   Logical key
======================  =================================================
``lei_records``         ``lei``
``relationships``       ``(start_node_id, end_node_id, relationship_type)``
``reporting_exceptions``  ``(lei, exception_category)``
``load_metadata``       ``dataset_type`` (enforced)
======================  =================================================

For relationships, ``start_node_id`` is the child LEI and
``end_node_id`` is the parent LEI - matching the GLEIF Level 2 RR
file convention.

Usage
-----
.. code-block:: python

    from gleif.constants import DEFAULT_DB_PATH
    from gleif.db import get_connection, load_all
    from gleif.download import download_all
    import asyncio

    results = asyncio.run(download_all(DEFAULT_DB_PATH.parent / "data"))
    con = get_connection(DEFAULT_DB_PATH)
    try:
        counts = load_all(con, results)
    finally:
        con.close()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import duckdb
from rich.console import Console

from gleif.constants import (
    LEI_CORE_COLUMNS,
    REPEX_COLUMNS,
    RR_CORE_COLUMNS,
    DatasetType,
)

if TYPE_CHECKING:
    from pathlib import Path

    from gleif.download import DownloadResult

console = Console()

# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------


def get_connection(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Open or create a DuckDB database at the given path.

    The parent directory is created if it does not exist. Callers are
    responsible for closing the returned connection (typically via a
    ``try/finally`` block). DuckDB raises ``duckdb.IOException`` if
    the path cannot be opened for writing (permissions, full disk,
    etc.).

    Args:
        db_path: Filesystem path to the DuckDB database file. If the
            file does not yet exist, DuckDB will create an empty one.

    Returns:
        An open ``duckdb.DuckDBPyConnection``.
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
    """Create the ``load_metadata`` tracking table.

    Data tables (``lei_records``, ``relationships``,
    ``reporting_exceptions``) are created during loading via
    ``CREATE OR REPLACE TABLE ... AS SELECT ... FROM read_csv()``
    in the corresponding ``load_*`` helpers, so this function only
    needs to create the auxiliary tracking table.

    Args:
        con: Open DuckDB connection.
    """
    con.execute(_LOAD_METADATA_DDL)


def create_indexes(con: duckdb.DuckDBPyConnection) -> None:
    """Create secondary indexes after bulk loading.

    Indexes cover the ``relationships`` join columns
    (``start_node_id``, ``end_node_id``, ``relationship_type``,
    ``relationship_status``) and the ``reporting_exceptions.lei``
    lookup column. Building indexes after the bulk insert is faster
    than maintaining them during the insert.

    Args:
        con: Open DuckDB connection.
    """
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
        Comma-separated SELECT fragments quoting each source column and aliasing it.
    """
    parts = [f'"{csv_col}" AS {db_col}' for csv_col, db_col in column_map.items()]
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def _load_csv_into_table(
    con: duckdb.DuckDBPyConnection,
    *,
    table: str,
    csv_path: Path,
    column_map: dict[str, str],
) -> int:
    """Bulk-load a projection of a GLEIF CSV into a DuckDB table.

    Issues ``CREATE OR REPLACE TABLE <table> AS SELECT ... FROM
    read_csv(...)`` and returns the resulting row count. All columns
    are read as ``VARCHAR`` (``all_varchar=true``) so optional fields
    do not break type inference; downstream queries cast as needed.

    Args:
        con: Open DuckDB connection.
        table: Target table name. Source-controlled via the internal
            ``load_*`` wrappers; everything user-supplied flows through
            ``column_map`` and ``csv_path``.
        csv_path: Path to the extracted CSV file.
        column_map: Mapping from CSV header name to DB column name; passed
            through :func:`_build_select_clause`.

    Returns:
        Number of rows loaded into ``table``.
    """
    select_clause = _build_select_clause(column_map)
    sql = f"""
        CREATE OR REPLACE TABLE {table} AS
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
    result = con.execute(f"SELECT count(*) FROM {table}").fetchone()
    return result[0] if result else 0


def load_lei_records(con: duckdb.DuckDBPyConnection, csv_path: Path) -> int:
    """Load Level 1 LEI records from an extracted CSV.

    Issues ``CREATE OR REPLACE TABLE lei_records AS SELECT ...``,
    projecting only the ~30 core columns listed in
    :data:`gleif.constants.LEI_CORE_COLUMNS` out of the ~338 columns
    in the source CSV. All columns are read as ``VARCHAR`` to avoid
    type inference issues on optional fields; downstream queries
    cast as needed. DuckDB raises ``duckdb.IOException`` if the CSV
    file cannot be read, or ``duckdb.InvalidInputException`` if the
    CSV is missing one of the column headers in
    :data:`gleif.constants.LEI_CORE_COLUMNS`.

    Args:
        con: Open DuckDB connection.
        csv_path: Path to the extracted Level 1 CSV file.

    Returns:
        Number of rows loaded into ``lei_records``.
    """
    return _load_csv_into_table(
        con,
        table="lei_records",
        csv_path=csv_path,
        column_map=LEI_CORE_COLUMNS,
    )


def load_relationships(con: duckdb.DuckDBPyConnection, csv_path: Path) -> int:
    """Load Level 2 relationship records from an extracted CSV.

    Projects the columns in :data:`gleif.constants.RR_CORE_COLUMNS`.
    ``start_node_id`` is the child LEI and ``end_node_id`` is the
    parent LEI in the GLEIF Level 2 schema. DuckDB raises
    ``duckdb.IOException`` if the CSV file cannot be read, or
    ``duckdb.InvalidInputException`` if required columns are missing.

    Args:
        con: Open DuckDB connection.
        csv_path: Path to the extracted Level 2 RR CSV file.

    Returns:
        Number of rows loaded into ``relationships``.
    """
    return _load_csv_into_table(
        con,
        table="relationships",
        csv_path=csv_path,
        column_map=RR_CORE_COLUMNS,
    )


def load_reporting_exceptions(con: duckdb.DuckDBPyConnection, csv_path: Path) -> int:
    """Load Level 2 reporting exceptions from an extracted CSV.

    Projects the columns in :data:`gleif.constants.REPEX_COLUMNS`.
    DuckDB raises ``duckdb.IOException`` if the CSV file cannot be
    read, or ``duckdb.InvalidInputException`` if required columns
    are missing.

    Args:
        con: Open DuckDB connection.
        csv_path: Path to the extracted Level 2 exceptions CSV file.

    Returns:
        Number of rows loaded into ``reporting_exceptions``.
    """
    return _load_csv_into_table(
        con,
        table="reporting_exceptions",
        csv_path=csv_path,
        column_map=REPEX_COLUMNS,
    )


def update_metadata(
    con: duckdb.DuckDBPyConnection,
    dataset_type: DatasetType,
    publish_date: str,
    record_count: int,
) -> None:
    """Insert or update the ``load_metadata`` row for a dataset.

    Args:
        con: Open DuckDB connection.
        dataset_type: Which dataset was loaded.
        publish_date: GLEIF publish date for the loaded CSV.
        record_count: Number of rows loaded.
    """
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

    Creates the ``load_metadata`` tracking table, dispatches to the
    appropriate ``load_*`` helper for each result, records the
    publish date and row count in ``load_metadata``, and finally
    builds the secondary indexes. Progress is printed via Rich.
    Propagates ``KeyError`` if a :class:`DownloadResult` references
    an unknown dataset type, and ``duckdb.IOException`` if a CSV
    file cannot be read.

    Args:
        con: Open DuckDB connection.
        download_results: List of :class:`DownloadResult` from the
            download phase. Order does not matter; the function
            dispatches by ``dataset_type``.

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
        update_metadata(con, result.dataset_type, result.publish_date, count)
        counts[result.dataset_type] = count
        console.print(f"    [green]{count:,} rows loaded[/]")

    console.print("  Creating indexes...")
    create_indexes(con)
    console.print("  [green]Done.[/]")

    return counts


def get_status(
    con: duckdb.DuckDBPyConnection,
) -> list[tuple[str, str, str, int]]:
    """Get load metadata for all datasets.

    Useful for surfacing data freshness; the ``gleif status`` CLI
    command renders this as a Rich table.

    Args:
        con: Open DuckDB connection.

    Returns:
        List of ``(dataset_type, publish_date, loaded_at,
        record_count)`` tuples, ordered by dataset type. Returns an
        empty list if the ``load_metadata`` table does not exist
        (i.e. no data has ever been loaded into this database).
    """
    try:
        rows = con.execute(
            "SELECT dataset_type, publish_date, loaded_at, record_count "
            "FROM load_metadata ORDER BY dataset_type"
        ).fetchall()
    except duckdb.CatalogException:
        return []
    return rows
