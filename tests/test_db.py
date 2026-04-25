"""Tests for the database module."""

from __future__ import annotations

from pathlib import Path

import duckdb

from gleif.db import (
    create_schema,
    get_status,
    load_lei_records,
    load_relationships,
    load_reporting_exceptions,
)


class TestLoadLeiRecords:
    """Tests for Level 1 LEI record loading."""

    def test_loads_correct_row_count(self, lei_csv: Path) -> None:
        con = duckdb.connect(":memory:")
        count = load_lei_records(con, lei_csv)
        assert count == 4

    def test_primary_key_is_lei(self, lei_csv: Path) -> None:
        con = duckdb.connect(":memory:")
        load_lei_records(con, lei_csv)
        row = con.execute(
            "SELECT lei, legal_name FROM lei_records WHERE lei = 'PARENT00000000000001'"
        ).fetchone()
        assert row is not None
        assert row[0] == "PARENT00000000000001"
        assert row[1] == "Parent Corp"

    def test_column_mapping(self, lei_csv: Path) -> None:
        con = duckdb.connect(":memory:")
        load_lei_records(con, lei_csv)
        row = con.execute(
            "SELECT legal_address_city, legal_address_country, entity_status "
            "FROM lei_records WHERE lei = 'CHILD000000000000001'"
        ).fetchone()
        assert row is not None
        assert row[0] == "Chicago"
        assert row[1] == "US"
        assert row[2] == "ACTIVE"


class TestLoadRelationships:
    """Tests for Level 2 relationship record loading."""

    def test_loads_correct_row_count(self, rr_csv: Path) -> None:
        con = duckdb.connect(":memory:")
        count = load_relationships(con, rr_csv)
        assert count == 4

    def test_relationship_fields(self, rr_csv: Path) -> None:
        con = duckdb.connect(":memory:")
        load_relationships(con, rr_csv)
        row = con.execute(
            "SELECT start_node_id, end_node_id, relationship_type, "
            "relationship_status FROM relationships "
            "WHERE start_node_id = 'CHILD000000000000001' "
            "AND relationship_type = 'IS_DIRECTLY_CONSOLIDATED_BY'"
        ).fetchone()
        assert row is not None
        assert row[0] == "CHILD000000000000001"
        assert row[1] == "PARENT00000000000001"
        assert row[2] == "IS_DIRECTLY_CONSOLIDATED_BY"
        assert row[3] == "ACTIVE"


class TestLoadReportingExceptions:
    """Tests for Level 2 reporting exceptions loading."""

    def test_loads_correct_row_count(self, repex_csv: Path) -> None:
        con = duckdb.connect(":memory:")
        count = load_reporting_exceptions(con, repex_csv)
        assert count == 1

    def test_exception_fields(self, repex_csv: Path) -> None:
        con = duckdb.connect(":memory:")
        load_reporting_exceptions(con, repex_csv)
        row = con.execute(
            "SELECT lei, exception_category, exception_reason_1 "
            "FROM reporting_exceptions "
            "WHERE lei = 'ULTIMATE000000000001'"
        ).fetchone()
        assert row is not None
        assert row[1] == "ULTIMATE_ACCOUNTING_CONSOLIDATION_PARENT"
        assert row[2] == "NO_KNOWN_PERSON"


class TestMetadata:
    """Tests for schema and metadata."""

    def test_create_schema_creates_metadata_table(self) -> None:
        con = duckdb.connect(":memory:")
        create_schema(con)
        result = con.execute("SELECT count(*) FROM load_metadata").fetchone()
        assert result is not None
        assert result[0] == 0

    def test_get_status_empty(self) -> None:
        con = duckdb.connect(":memory:")
        create_schema(con)
        rows = get_status(con)
        assert rows == []

    def test_get_status_no_table(self) -> None:
        con = duckdb.connect(":memory:")
        rows = get_status(con)
        assert rows == []
