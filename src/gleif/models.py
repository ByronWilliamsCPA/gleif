"""Frozen dataclasses for typed query results."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EntityInfo:
    """Core entity information from Level 1 LEI records."""

    lei: str
    legal_name: str
    entity_status: str
    registration_status: str
    entity_category: str | None = None
    legal_jurisdiction: str | None = None
    legal_address_city: str | None = None
    legal_address_country: str | None = None
    hq_address_city: str | None = None
    hq_address_country: str | None = None


@dataclass(frozen=True)
class RelatedEntity:
    """An entity related to the queried LEI via a relationship record."""

    lei: str
    legal_name: str | None
    relationship_type: str
    relationship_status: str
    direction: str  # "parent", "child", "sibling", "other"


@dataclass(frozen=True)
class ReportingException:
    """A reporting exception for a given LEI."""

    exception_category: str
    exception_reason: str | None = None
    exception_reference: str | None = None


@dataclass(frozen=True)
class HierarchyNode:
    """A single entity in a hierarchy traversal, with depth context."""

    lei: str
    legal_name: str | None
    depth: int
    entity_status: str | None = None
    entity_category: str | None = None
    legal_jurisdiction: str | None = None
    relationship_type: str | None = None
    parent_lei: str | None = None


@dataclass(frozen=True)
class CorporateGroup:
    """Complete corporate group: root entity and full descendant tree."""

    root: EntityInfo
    descendants: list[HierarchyNode] = field(default_factory=list)
    total_entities: int = 0


@dataclass(frozen=True)
class LEIRelationshipReport:
    """Complete relationship report for a single LEI."""

    entity: EntityInfo
    direct_parent: EntityInfo | None = None
    ultimate_parent: EntityInfo | None = None
    children: list[RelatedEntity] = field(default_factory=list)
    siblings: list[RelatedEntity] = field(default_factory=list)
    other_relationships: list[RelatedEntity] = field(default_factory=list)
    reporting_exceptions: list[ReportingException] = field(default_factory=list)
