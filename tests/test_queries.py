"""Tests for the query module."""

from __future__ import annotations

import duckdb

from gleif.queries import (
    get_children,
    get_entity,
    get_full_report,
    get_other_relationships,
    get_parent,
    get_reporting_exceptions,
    get_siblings,
    search_by_name,
)


class TestGetEntity:
    """Tests for entity lookup."""

    def test_finds_existing_entity(self, loaded_db: duckdb.DuckDBPyConnection) -> None:
        entity = get_entity(loaded_db, "PARENT00000000000001")
        assert entity is not None
        assert entity.lei == "PARENT00000000000001"
        assert entity.legal_name == "Parent Corp"
        assert entity.entity_status == "ACTIVE"
        assert entity.legal_address_city == "New York"

    def test_returns_none_for_missing(
        self, loaded_db: duckdb.DuckDBPyConnection
    ) -> None:
        entity = get_entity(loaded_db, "NONEXISTENT0000000001")
        assert entity is None


class TestGetParent:
    """Tests for parent lookup."""

    def test_finds_direct_parent(self, loaded_db: duckdb.DuckDBPyConnection) -> None:
        parent = get_parent(
            loaded_db,
            "CHILD000000000000001",
            "IS_DIRECTLY_CONSOLIDATED_BY",
        )
        assert parent is not None
        assert parent.lei == "PARENT00000000000001"
        assert parent.legal_name == "Parent Corp"

    def test_finds_ultimate_parent(self, loaded_db: duckdb.DuckDBPyConnection) -> None:
        parent = get_parent(
            loaded_db,
            "CHILD000000000000001",
            "IS_ULTIMATELY_CONSOLIDATED_BY",
        )
        assert parent is not None
        assert parent.lei == "ULTIMATE000000000001"

    def test_returns_none_when_no_parent(
        self, loaded_db: duckdb.DuckDBPyConnection
    ) -> None:
        parent = get_parent(
            loaded_db,
            "ULTIMATE000000000001",
            "IS_DIRECTLY_CONSOLIDATED_BY",
        )
        assert parent is None


class TestGetChildren:
    """Tests for finding child entities."""

    def test_finds_children_of_parent(
        self, loaded_db: duckdb.DuckDBPyConnection
    ) -> None:
        children = get_children(loaded_db, "PARENT00000000000001")
        child_leis = {c.lei for c in children}
        assert "CHILD000000000000001" in child_leis
        assert "CHILD000000000000002" in child_leis
        assert all(c.direction == "child" for c in children)

    def test_no_children_for_leaf(self, loaded_db: duckdb.DuckDBPyConnection) -> None:
        children = get_children(loaded_db, "CHILD000000000000001")
        assert children == []


class TestGetSiblings:
    """Tests for finding sibling entities."""

    def test_finds_sibling(self, loaded_db: duckdb.DuckDBPyConnection) -> None:
        siblings = get_siblings(loaded_db, "CHILD000000000000001")
        sibling_leis = {s.lei for s in siblings}
        assert "CHILD000000000000002" in sibling_leis
        # Should not include self
        assert "CHILD000000000000001" not in sibling_leis

    def test_no_siblings_for_top_entity(
        self, loaded_db: duckdb.DuckDBPyConnection
    ) -> None:
        siblings = get_siblings(loaded_db, "ULTIMATE000000000001")
        assert siblings == []


class TestGetOtherRelationships:
    """Tests for non-consolidation relationships."""

    def test_no_other_relationships(self, loaded_db: duckdb.DuckDBPyConnection) -> None:
        others = get_other_relationships(loaded_db, "CHILD000000000000001")
        assert others == []


class TestGetReportingExceptions:
    """Tests for reporting exception lookup."""

    def test_finds_exceptions(self, loaded_db: duckdb.DuckDBPyConnection) -> None:
        exceptions = get_reporting_exceptions(loaded_db, "ULTIMATE000000000001")
        assert len(exceptions) == 1
        assert (
            exceptions[0].exception_category
            == "ULTIMATE_ACCOUNTING_CONSOLIDATION_PARENT"
        )
        assert exceptions[0].exception_reason == "NO_KNOWN_PERSON"

    def test_no_exceptions(self, loaded_db: duckdb.DuckDBPyConnection) -> None:
        exceptions = get_reporting_exceptions(loaded_db, "CHILD000000000000001")
        assert exceptions == []


class TestSearchByName:
    """Tests for name-based entity search."""

    def test_finds_matching_entities(
        self, loaded_db: duckdb.DuckDBPyConnection
    ) -> None:
        results = search_by_name(loaded_db, "Child")
        assert len(results) == 2
        names = {r.legal_name for r in results}
        assert "Child A Inc." in names
        assert "Child B Ltd." in names

    def test_case_insensitive(self, loaded_db: duckdb.DuckDBPyConnection) -> None:
        results = search_by_name(loaded_db, "parent")
        assert len(results) == 1
        assert results[0].legal_name == "Parent Corp"

    def test_no_matches(self, loaded_db: duckdb.DuckDBPyConnection) -> None:
        results = search_by_name(loaded_db, "ZZZZNOTFOUND")
        assert results == []

    def test_limit(self, loaded_db: duckdb.DuckDBPyConnection) -> None:
        results = search_by_name(loaded_db, "Child", limit=1)
        assert len(results) == 1

    def test_returns_entity_info(self, loaded_db: duckdb.DuckDBPyConnection) -> None:
        results = search_by_name(loaded_db, "Ultimate")
        assert len(results) == 1
        entity = results[0]
        assert entity.lei == "ULTIMATE000000000001"
        assert entity.entity_status == "ACTIVE"
        assert entity.legal_jurisdiction == "GB"


class TestGetFullReport:
    """Tests for the full relationship report."""

    def test_full_report_for_child(self, loaded_db: duckdb.DuckDBPyConnection) -> None:
        report = get_full_report(loaded_db, "CHILD000000000000001")
        assert report is not None
        assert report.entity.lei == "CHILD000000000000001"
        assert report.direct_parent is not None
        assert report.direct_parent.lei == "PARENT00000000000001"
        assert report.ultimate_parent is not None
        assert report.ultimate_parent.lei == "ULTIMATE000000000001"
        # Sibling should be Child B
        assert len(report.siblings) == 1
        assert report.siblings[0].lei == "CHILD000000000000002"
        # No children
        assert report.children == []

    def test_full_report_for_parent(self, loaded_db: duckdb.DuckDBPyConnection) -> None:
        report = get_full_report(loaded_db, "PARENT00000000000001")
        assert report is not None
        assert len(report.children) >= 2
        assert report.direct_parent is not None
        assert report.direct_parent.lei == "ULTIMATE000000000001"

    def test_full_report_missing_lei(
        self, loaded_db: duckdb.DuckDBPyConnection
    ) -> None:
        report = get_full_report(loaded_db, "NONEXISTENT0000000001")
        assert report is None
