"""Tests for the Rich rendering helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gleif.models import (
    CorporateGroup,
    EntityInfo,
    HierarchyNode,
    LEIRelationshipReport,
    RelatedEntity,
    ReportingException,
)
from gleif.rendering import (
    collect_report_leis,
    format_isins,
    format_node_label,
    render_report,
    render_tree,
)

if TYPE_CHECKING:
    import pytest


def _entity(lei: str, name: str) -> EntityInfo:
    """Build a minimal EntityInfo for rendering tests."""
    return EntityInfo(
        lei=lei,
        legal_name=name,
        entity_status="ACTIVE",
        registration_status="ISSUED",
        entity_category="GENERAL",
        legal_jurisdiction="US",
    )


def _related(lei: str, name: str, direction: str) -> RelatedEntity:
    """Build a RelatedEntity for rendering tests."""
    return RelatedEntity(
        lei=lei,
        legal_name=name,
        relationship_type="IS_DIRECTLY_CONSOLIDATED_BY",
        relationship_status="ACTIVE",
        direction=direction,
    )


class TestFormatHelpers:
    """Tests for the small format helpers."""

    def test_format_isins_joins(self) -> None:
        assert format_isins({"AAA": ["US1", "US2"]}, "AAA") == "US1, US2"

    def test_format_isins_absent(self) -> None:
        assert format_isins({}, "AAA") == ""

    def test_format_node_label_non_node(self) -> None:
        assert format_node_label("plain", {}) == "plain"

    def test_format_node_label_with_isins(self) -> None:
        node = HierarchyNode(
            lei="NODE0000000000000001",
            legal_name="Node Co",
            depth=0,
            entity_status="ACTIVE",
            legal_jurisdiction="US",
        )
        label = format_node_label(node, {"NODE0000000000000001": ["US9"]})
        assert "Node Co" in label
        assert "US9" in label


class TestCollectReportLeis:
    """Tests for collecting and deduplicating report LEIs."""

    def test_dedupes_preserving_order(self) -> None:
        entity = _entity("AAA0000000000000001", "Root")
        parent = _entity("BBB0000000000000001", "Parent")
        report = LEIRelationshipReport(
            entity=entity,
            direct_parent=parent,
            ultimate_parent=parent,
            children=[_related("CCC0000000000000001", "Child", "child")],
        )
        leis = collect_report_leis(report)
        assert leis == [
            "AAA0000000000000001",
            "BBB0000000000000001",
            "CCC0000000000000001",
        ]


class TestRenderReport:
    """Tests for the full report renderer."""

    def test_renders_none_branches(self, capsys: pytest.CaptureFixture[str]) -> None:
        report = LEIRelationshipReport(entity=_entity("AAA0000000000000001", "Solo"))
        render_report(report)
        out = capsys.readouterr().out
        assert "Solo" in out
        assert "Direct Parent: None" in out
        assert "Children: None" in out

    def test_renders_populated_sections(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        report = LEIRelationshipReport(
            entity=_entity("AAA0000000000000001", "Root Co"),
            direct_parent=_entity("BBB0000000000000001", "Parent Co"),
            ultimate_parent=_entity("CCC0000000000000001", "Ultimate Co"),
            children=[_related("DDD0000000000000001", "Child Co", "child")],
            other_relationships=[_related("EEE0000000000000001", "Branch Co", "other")],
            reporting_exceptions=[
                ReportingException(
                    exception_category="ULTIMATE_PARENT",
                    exception_reason="NO_KNOWN_PERSON",
                )
            ],
        )
        isin_map = {"BBB0000000000000001": ["US5"], "DDD0000000000000001": ["US6"]}
        render_report(report, isin_map=isin_map)
        out = capsys.readouterr().out
        assert "Parent Co" in out
        assert "Reporting Exceptions" in out
        assert "NO_KNOWN_PERSON" in out
        assert "US5" in out


class TestRenderTree:
    """Tests for the corporate-group tree renderer."""

    def test_no_hierarchy_message(self, capsys: pytest.CaptureFixture[str]) -> None:
        group = CorporateGroup(root=_entity("AAA0000000000000001", "Root"))
        render_tree(group)
        out = capsys.readouterr().out
        assert "No hierarchy data found" in out

    def test_diamond_marks_repeat(self, capsys: pytest.CaptureFixture[str]) -> None:
        root = HierarchyNode(lei="ROOT", legal_name="Root", depth=0, parent_lei=None)
        branch_a = HierarchyNode(
            lei="A", legal_name="A Co", depth=1, parent_lei="ROOT"
        )
        branch_b = HierarchyNode(
            lei="B", legal_name="B Co", depth=1, parent_lei="ROOT"
        )
        shared_via_a = HierarchyNode(
            lei="SHARED", legal_name="Shared", depth=2, parent_lei="A"
        )
        shared_via_b = HierarchyNode(
            lei="SHARED", legal_name="Shared", depth=2, parent_lei="B"
        )
        group = CorporateGroup(
            root=_entity("ROOT", "Root"),
            descendants=[root, branch_a, branch_b, shared_via_a, shared_via_b],
            total_entities=4,
        )
        render_tree(group)
        out = capsys.readouterr().out
        assert "see above" in out
