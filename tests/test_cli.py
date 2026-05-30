"""Tests for the CLI module."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import duckdb
import pytest
from typer.testing import CliRunner

from gleif.cli import app
from gleif.constants import DATASET_LABELS, DatasetType
from gleif.db import (
    create_indexes,
    create_schema,
    load_lei_records,
    load_relationships,
    load_reporting_exceptions,
    update_metadata,
)
from gleif.download import DownloadResult
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


_DATASET_SUFFIXES = {
    DatasetType.LEI: "lei2",
    DatasetType.RELATIONSHIPS: "rr",
    DatasetType.REPORTING_EXCEPTIONS: "repex",
}


@pytest.fixture
def gleif_data_dir(
    tmp_path: Path,
    lei_csv: Path,
    rr_csv: Path,
    repex_csv: Path,
) -> Path:
    """Stage extracted CSVs and publish-date markers under GLEIF names.

    Reproduces what ``gleif download`` leaves on disk, so the ``load``
    command's ``find_extracted_csv`` glob resolves each dataset.
    """
    data_dir = tmp_path / "gleif_data"
    data_dir.mkdir()
    sources = {
        DatasetType.LEI: lei_csv,
        DatasetType.RELATIONSHIPS: rr_csv,
        DatasetType.REPORTING_EXCEPTIONS: repex_csv,
    }
    for dataset_type, source in sources.items():
        suffix = _DATASET_SUFFIXES[dataset_type]
        dest = data_dir / f"20240101-0000-gleif-goldencopy-{suffix}-full.csv"
        dest.write_text(source.read_text())
        (data_dir / f"{suffix}_publish_date.txt").write_text("2024-01-01")
    return data_dir


class TestLoadCommand:
    """Tests for the 'load' CLI command."""

    def test_load_succeeds(self, gleif_data_dir: Path, tmp_path: Path) -> None:
        db_path = tmp_path / "loaded.duckdb"
        result = runner.invoke(
            app,
            ["load", "--data-dir", str(gleif_data_dir), "--db", str(db_path)],
        )
        assert result.exit_code == 0
        assert "Load complete" in result.output
        status_result = runner.invoke(app, ["status", "--db", str(db_path)])
        assert "Level 1" in status_result.output

    def test_load_missing_csv_errors(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        db_path = tmp_path / "x.duckdb"
        result = runner.invoke(
            app, ["load", "--data-dir", str(empty), "--db", str(db_path)]
        )
        assert result.exit_code == 1
        assert "No extracted CSV" in result.output


class TestDownloadRefreshCommands:
    """Tests for the 'download' and 'refresh' CLI commands."""

    @patch("gleif.cli.download_all")
    def test_download_reports_results(
        self, mock_download_all: MagicMock, tmp_path: Path
    ) -> None:
        mock_download_all.return_value = [
            DownloadResult(
                csv_path=tmp_path / "lei2.csv",
                publish_date="2024-01-01",
                dataset_type=DatasetType.LEI,
                record_label=DATASET_LABELS[DatasetType.LEI],
            )
        ]
        result = runner.invoke(app, ["download", "--data-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "Download complete" in result.output

    @patch("gleif.cli.download_all")
    def test_refresh_downloads_and_loads(
        self, mock_download_all: MagicMock, gleif_data_dir: Path, tmp_path: Path
    ) -> None:
        results: list[DownloadResult] = []
        for dataset_type, suffix in _DATASET_SUFFIXES.items():
            csv = next(gleif_data_dir.glob(f"*-{suffix}-full.csv"))
            results.append(
                DownloadResult(
                    csv_path=csv,
                    publish_date="2024-01-01",
                    dataset_type=dataset_type,
                    record_label=DATASET_LABELS[dataset_type],
                )
            )
        mock_download_all.return_value = results
        db_path = tmp_path / "refreshed.duckdb"
        result = runner.invoke(
            app,
            ["refresh", "--data-dir", str(gleif_data_dir), "--db", str(db_path)],
        )
        assert result.exit_code == 0
        assert "Refresh complete" in result.output


class TestIsinFlag:
    """Tests for the --isin enrichment branches across commands."""

    @patch("gleif.cli.fetch_isins_batch")
    def test_lei_isin(self, mock_batch: MagicMock, cli_db_path: Path) -> None:
        mock_batch.return_value = {"CHILD000000000000001": ["US0000000001"]}
        result = runner.invoke(
            app,
            ["lei", "CHILD000000000000001", "--isin", "--db", str(cli_db_path)],
        )
        assert result.exit_code == 0
        assert "US0000000001" in result.output
        mock_batch.assert_called_once()

    @patch("gleif.cli.fetch_isins_batch")
    def test_name_isin(self, mock_batch: MagicMock, cli_db_path: Path) -> None:
        mock_batch.return_value = {"CHILD000000000000001": ["US0000000001"]}
        result = runner.invoke(
            app, ["name", "Child", "--isin", "--db", str(cli_db_path)]
        )
        assert result.exit_code == 0
        assert "US0000000001" in result.output

    @patch("gleif.cli.fetch_isins_batch")
    def test_tree_isin(
        self, mock_batch: MagicMock, cli_deep_hierarchy_db_path: Path
    ) -> None:
        mock_batch.return_value = {"GRANDCHILD0000000001": ["US0000000002"]}
        result = runner.invoke(
            app,
            [
                "lei",
                "ULTIMATE000000000001",
                "--tree",
                "--isin",
                "--db",
                str(cli_deep_hierarchy_db_path),
            ],
        )
        assert result.exit_code == 0
        assert "US0000000002" in result.output
