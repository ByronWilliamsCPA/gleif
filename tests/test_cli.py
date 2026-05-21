"""Tests for the CLI module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import duckdb
import pytest
from typer.testing import CliRunner

from gleif.cli import app
from gleif.constants import DatasetType
from gleif.db import (
    create_indexes,
    create_schema,
    load_lei_records,
    load_relationships,
    load_reporting_exceptions,
    update_metadata,
)
from tests.conftest import insert_lei, insert_relationship

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


@pytest.fixture
def cli_db_path(
    tmp_path: Path,
    lei_csv: Path,
    rr_csv: Path,
    repex_csv: Path,
) -> Path:
    """Return the path to an on-disk DuckDB loaded with the fixture CSVs.

    Indexes and load_metadata are populated, matching what ``gleif refresh``
    would produce on a real run.
    """
    db_path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db_path))
    create_schema(con)
    count_lei = load_lei_records(con, lei_csv)
    count_rr = load_relationships(con, rr_csv)
    count_repex = load_reporting_exceptions(con, repex_csv)
    create_indexes(con)
    update_metadata(con, DatasetType.LEI, "2024-01-01", count_lei)
    update_metadata(con, DatasetType.RELATIONSHIPS, "2024-01-01", count_rr)
    update_metadata(con, DatasetType.REPORTING_EXCEPTIONS, "2024-01-01", count_repex)
    con.close()
    return db_path


@pytest.fixture
def cli_deep_hierarchy_db_path(cli_db_path: Path) -> Path:
    """Extend cli_db_path with a 4-level hierarchy for tree-render tests."""
    con = duckdb.connect(str(cli_db_path))
    try:
        insert_lei(
            con,
            lei="GRANDCHILD0000000001",
            legal_name="Grandchild GmbH",
            jurisdiction="DE",
        )
        insert_relationship(
            con,
            child_lei="GRANDCHILD0000000001",
            parent_lei="CHILD000000000000001",
            relationship_type="IS_DIRECTLY_CONSOLIDATED_BY",
        )
        insert_relationship(
            con,
            child_lei="GRANDCHILD0000000001",
            parent_lei="ULTIMATE000000000001",
            relationship_type="IS_ULTIMATELY_CONSOLIDATED_BY",
        )
    finally:
        con.close()
    return cli_db_path


class TestLeiCommand:
    """Tests for the 'lei' CLI command."""

    def test_lei_found(self, cli_db_path: Path) -> None:
        result = runner.invoke(
            app, ["lei", "CHILD000000000000001", "--db", str(cli_db_path)]
        )
        assert result.exit_code == 0
        assert "Child A Inc." in result.output
        assert "PARENT00000000000001" in result.output

    def test_lei_not_found(self, cli_db_path: Path) -> None:
        result = runner.invoke(
            app, ["lei", "NONEXISTENT000000001", "--db", str(cli_db_path)]
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

    def test_name_finds_matches(self, cli_db_path: Path) -> None:
        result = runner.invoke(app, ["name", "Child", "--db", str(cli_db_path)])
        assert result.exit_code == 0
        assert "Child A Inc." in result.output
        assert "Child B Ltd." in result.output

    def test_name_case_insensitive(self, cli_db_path: Path) -> None:
        result = runner.invoke(app, ["name", "parent", "--db", str(cli_db_path)])
        assert result.exit_code == 0
        assert "Parent Corp" in result.output

    def test_name_no_matches(self, cli_db_path: Path) -> None:
        result = runner.invoke(app, ["name", "ZZZZNOTFOUND", "--db", str(cli_db_path)])
        assert result.exit_code == 0
        assert "No entities found" in result.output

    def test_name_limit(self, cli_db_path: Path) -> None:
        result = runner.invoke(
            app, ["name", "Child", "--limit", "1", "--db", str(cli_db_path)]
        )
        assert result.exit_code == 0
        assert "1 result" in result.output


class TestStatusCommand:
    """Tests for the 'status' CLI command."""

    def test_status_with_data(self, cli_db_path: Path) -> None:
        result = runner.invoke(app, ["status", "--db", str(cli_db_path)])
        assert result.exit_code == 0
        assert "GLEIF Database Status" in result.output

    def test_status_no_db(self, tmp_path: Path) -> None:
        db_path = tmp_path / "nonexistent.duckdb"
        result = runner.invoke(app, ["status", "--db", str(db_path)])
        assert result.exit_code == 1
        assert "not found" in result.output


class TestLeiTreeCommand:
    """Tests for the 'lei --tree' CLI command."""

    def test_tree_shows_hierarchy(self, cli_deep_hierarchy_db_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "lei",
                "GRANDCHILD0000000001",
                "--tree",
                "--db",
                str(cli_deep_hierarchy_db_path),
            ],
        )
        assert result.exit_code == 0
        assert "Corporate Group" in result.output
        assert "Ultimate Holdings PLC" in result.output
        assert "Grandchild GmbH" in result.output
        assert "5 entities" in result.output

    def test_tree_max_depth(self, cli_deep_hierarchy_db_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "lei",
                "ULTIMATE000000000001",
                "--tree",
                "--max-depth",
                "1",
                "--db",
                str(cli_deep_hierarchy_db_path),
            ],
        )
        assert result.exit_code == 0
        assert "Corporate Group" in result.output
        # Grandchild is at depth 3, so should not appear with max-depth 1
        assert "Grandchild GmbH" not in result.output

    def test_tree_not_found(self, cli_db_path: Path) -> None:
        result = runner.invoke(
            app,
            ["lei", "NONEXISTENT000000001", "--tree", "--db", str(cli_db_path)],
        )
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_tree_from_root(self, cli_deep_hierarchy_db_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "lei",
                "ULTIMATE000000000001",
                "--tree",
                "--db",
                str(cli_deep_hierarchy_db_path),
            ],
        )
        assert result.exit_code == 0
        assert "Ultimate Holdings PLC" in result.output
        assert "Parent Corp" in result.output
        assert "Child A Inc." in result.output
        assert "Child B Ltd." in result.output
