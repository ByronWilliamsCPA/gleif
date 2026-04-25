"""Tests for the CLI module."""

from __future__ import annotations

from pathlib import Path

import duckdb
from typer.testing import CliRunner

from gleif.cli import app
from gleif.constants import DatasetType
from gleif.db import (
    _create_indexes,
    _update_metadata,
    create_schema,
    load_lei_records,
    load_relationships,
    load_reporting_exceptions,
)

runner = CliRunner()


def _create_test_db(
    db_path: Path,
    lei_csv: Path,
    rr_csv: Path,
    repex_csv: Path,
) -> None:
    """Create a test database from fixture CSVs."""
    con = duckdb.connect(str(db_path))
    create_schema(con)
    count_lei = load_lei_records(con, lei_csv)
    count_rr = load_relationships(con, rr_csv)
    count_repex = load_reporting_exceptions(con, repex_csv)
    _create_indexes(con)
    _update_metadata(con, DatasetType.LEI, "2024-01-01", count_lei)
    _update_metadata(con, DatasetType.RELATIONSHIPS, "2024-01-01", count_rr)
    _update_metadata(con, DatasetType.REPORTING_EXCEPTIONS, "2024-01-01", count_repex)
    con.close()


class TestLeiCommand:
    """Tests for the 'lei' CLI command."""

    def test_lei_found(
        self,
        tmp_path: Path,
        lei_csv: Path,
        rr_csv: Path,
        repex_csv: Path,
    ) -> None:
        db_path = tmp_path / "test.duckdb"
        _create_test_db(db_path, lei_csv, rr_csv, repex_csv)

        result = runner.invoke(
            app, ["lei", "CHILD000000000000001", "--db", str(db_path)]
        )
        assert result.exit_code == 0
        assert "Child A Inc." in result.output
        assert "PARENT00000000000001" in result.output

    def test_lei_not_found(
        self,
        tmp_path: Path,
        lei_csv: Path,
        rr_csv: Path,
        repex_csv: Path,
    ) -> None:
        db_path = tmp_path / "test.duckdb"
        _create_test_db(db_path, lei_csv, rr_csv, repex_csv)

        result = runner.invoke(
            app, ["lei", "NONEXISTENT000000001", "--db", str(db_path)]
        )
        assert result.exit_code == 1

    def test_lei_invalid_length(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.duckdb"
        duckdb.connect(str(db_path)).close()

        result = runner.invoke(app, ["lei", "SHORT", "--db", str(db_path)])
        assert result.exit_code == 1
        assert "20 characters" in result.output


class TestNameCommand:
    """Tests for the 'name' CLI command."""

    def test_name_finds_matches(
        self,
        tmp_path: Path,
        lei_csv: Path,
        rr_csv: Path,
        repex_csv: Path,
    ) -> None:
        db_path = tmp_path / "test.duckdb"
        _create_test_db(db_path, lei_csv, rr_csv, repex_csv)

        result = runner.invoke(app, ["name", "Child", "--db", str(db_path)])
        assert result.exit_code == 0
        assert "Child A Inc." in result.output
        assert "Child B Ltd." in result.output

    def test_name_case_insensitive(
        self,
        tmp_path: Path,
        lei_csv: Path,
        rr_csv: Path,
        repex_csv: Path,
    ) -> None:
        db_path = tmp_path / "test.duckdb"
        _create_test_db(db_path, lei_csv, rr_csv, repex_csv)

        result = runner.invoke(app, ["name", "parent", "--db", str(db_path)])
        assert result.exit_code == 0
        assert "Parent Corp" in result.output

    def test_name_no_matches(
        self,
        tmp_path: Path,
        lei_csv: Path,
        rr_csv: Path,
        repex_csv: Path,
    ) -> None:
        db_path = tmp_path / "test.duckdb"
        _create_test_db(db_path, lei_csv, rr_csv, repex_csv)

        result = runner.invoke(app, ["name", "ZZZZNOTFOUND", "--db", str(db_path)])
        assert result.exit_code == 0
        assert "No entities found" in result.output

    def test_name_limit(
        self,
        tmp_path: Path,
        lei_csv: Path,
        rr_csv: Path,
        repex_csv: Path,
    ) -> None:
        db_path = tmp_path / "test.duckdb"
        _create_test_db(db_path, lei_csv, rr_csv, repex_csv)

        result = runner.invoke(
            app, ["name", "Child", "--limit", "1", "--db", str(db_path)]
        )
        assert result.exit_code == 0
        assert "1 result" in result.output


class TestStatusCommand:
    """Tests for the 'status' CLI command."""

    def test_status_with_data(
        self,
        tmp_path: Path,
        lei_csv: Path,
        rr_csv: Path,
        repex_csv: Path,
    ) -> None:
        db_path = tmp_path / "test.duckdb"
        _create_test_db(db_path, lei_csv, rr_csv, repex_csv)

        result = runner.invoke(app, ["status", "--db", str(db_path)])
        assert result.exit_code == 0
        assert "GLEIF Database Status" in result.output

    def test_status_no_db(self, tmp_path: Path) -> None:
        db_path = tmp_path / "nonexistent.duckdb"
        result = runner.invoke(app, ["status", "--db", str(db_path)])
        assert result.exit_code == 1
        assert "not found" in result.output


def _create_deep_hierarchy_db(
    db_path: Path, lei_csv: Path, rr_csv: Path, repex_csv: Path
) -> None:
    """Create a test database with a 4-level hierarchy for tree tests."""
    con = duckdb.connect(str(db_path))
    create_schema(con)
    count_lei = load_lei_records(con, lei_csv)
    count_rr = load_relationships(con, rr_csv)
    count_repex = load_reporting_exceptions(con, repex_csv)
    _create_indexes(con)
    _update_metadata(con, DatasetType.LEI, "2024-01-01", count_lei)
    _update_metadata(con, DatasetType.RELATIONSHIPS, "2024-01-01", count_rr)
    _update_metadata(con, DatasetType.REPORTING_EXCEPTIONS, "2024-01-01", count_repex)
    con.execute(
        "INSERT INTO lei_records "
        "(lei, legal_name, entity_status, registration_status, "
        "entity_category, legal_jurisdiction) VALUES "
        "('GRANDCHILD0000000001', 'Grandchild GmbH', "
        "'ACTIVE', 'ISSUED', 'GENERAL', 'DE')"
    )
    con.execute(
        "INSERT INTO relationships "
        "(start_node_id, start_node_id_type, end_node_id, "
        "end_node_id_type, relationship_type, relationship_status) "
        "VALUES "
        "('GRANDCHILD0000000001', 'LEI', 'CHILD000000000000001', "
        "'LEI', 'IS_DIRECTLY_CONSOLIDATED_BY', 'ACTIVE')"
    )
    con.execute(
        "INSERT INTO relationships "
        "(start_node_id, start_node_id_type, end_node_id, "
        "end_node_id_type, relationship_type, relationship_status) "
        "VALUES "
        "('GRANDCHILD0000000001', 'LEI', 'ULTIMATE000000000001', "
        "'LEI', 'IS_ULTIMATELY_CONSOLIDATED_BY', 'ACTIVE')"
    )
    con.close()


class TestLeiTreeCommand:
    """Tests for the 'lei --tree' CLI command."""

    def test_tree_shows_hierarchy(
        self,
        tmp_path: Path,
        lei_csv: Path,
        rr_csv: Path,
        repex_csv: Path,
    ) -> None:
        db_path = tmp_path / "test.duckdb"
        _create_deep_hierarchy_db(db_path, lei_csv, rr_csv, repex_csv)

        result = runner.invoke(
            app,
            ["lei", "GRANDCHILD0000000001", "--tree", "--db", str(db_path)],
        )
        assert result.exit_code == 0
        assert "Corporate Group" in result.output
        assert "Ultimate Holdings PLC" in result.output
        assert "Grandchild GmbH" in result.output
        assert "5 entities" in result.output

    def test_tree_max_depth(
        self,
        tmp_path: Path,
        lei_csv: Path,
        rr_csv: Path,
        repex_csv: Path,
    ) -> None:
        db_path = tmp_path / "test.duckdb"
        _create_deep_hierarchy_db(db_path, lei_csv, rr_csv, repex_csv)

        result = runner.invoke(
            app,
            [
                "lei",
                "ULTIMATE000000000001",
                "--tree",
                "--max-depth",
                "1",
                "--db",
                str(db_path),
            ],
        )
        assert result.exit_code == 0
        assert "Corporate Group" in result.output
        # Grandchild is at depth 3, so should not appear with max-depth 1
        assert "Grandchild GmbH" not in result.output

    def test_tree_not_found(
        self,
        tmp_path: Path,
        lei_csv: Path,
        rr_csv: Path,
        repex_csv: Path,
    ) -> None:
        db_path = tmp_path / "test.duckdb"
        _create_test_db(db_path, lei_csv, rr_csv, repex_csv)

        result = runner.invoke(
            app,
            ["lei", "NONEXISTENT000000001", "--tree", "--db", str(db_path)],
        )
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_tree_from_root(
        self,
        tmp_path: Path,
        lei_csv: Path,
        rr_csv: Path,
        repex_csv: Path,
    ) -> None:
        db_path = tmp_path / "test.duckdb"
        _create_deep_hierarchy_db(db_path, lei_csv, rr_csv, repex_csv)

        result = runner.invoke(
            app,
            ["lei", "ULTIMATE000000000001", "--tree", "--db", str(db_path)],
        )
        assert result.exit_code == 0
        assert "Ultimate Holdings PLC" in result.output
        assert "Parent Corp" in result.output
        assert "Child A Inc." in result.output
        assert "Child B Ltd." in result.output
