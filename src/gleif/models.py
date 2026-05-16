"""Typed result models for GLEIF query functions.

This module defines frozen dataclasses returned by the query helpers
in :mod:`gleif.queries`. Each dataclass mirrors a subset of the GLEIF
golden copy schema fields that are loaded into the local DuckDB
database. The conversion rules used by the query layer are:

* Fields typed ``str | None`` (most address / metadata fields) are
  set to ``None`` when the underlying CSV cell is empty.
* Fields typed plain ``str`` (e.g. ``EntityInfo.legal_name``,
  ``EntityInfo.entity_status``, ``RelatedEntity.relationship_status``)
  default to an empty string when the underlying cell is empty.

All models are declared with ``frozen=True``, which prevents
attribute rebinding. Note that ``frozen=True`` does **not** make
contained lists (e.g. ``CorporateGroup.descendants``,
``LEIRelationshipReport.children``) immutable, so callers must not
rely on these models being deeply immutable or hashable.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EntityInfo:
    """Core entity information from a Level 1 LEI record.

    Populated from the ``lei_records`` table. Address-related fields
    are kept compact (city + country only); see ``LEI_CORE_COLUMNS``
    in :mod:`gleif.constants` for the full list of columns that are
    actually loaded into the database.

    Data quality note: GLEIF Level 1 data is self-reported and not
    every field is mandatory. The ``str | None`` fields below are
    exposed as ``None`` when the source CSV cell is empty; the
    plain ``str`` fields (``legal_name``, ``entity_status``,
    ``registration_status``) default to an empty string instead.

    Attributes:
        lei: 20-character Legal Entity Identifier (uppercase
            alphanumeric).
        legal_name: Registered legal name. Empty string if blank in
            the source CSV.
        entity_status: Lifecycle status of the entity, e.g. ``ACTIVE``
            or ``INACTIVE``. Empty string if blank.
        registration_status: Status of the LEI registration itself,
            e.g. ``ISSUED``, ``LAPSED``, ``RETIRED``. Empty string
            if blank.
        entity_category: GLEIF entity category, e.g. ``GENERAL``,
            ``BRANCH``, ``FUND``.
        legal_jurisdiction: ISO 3166-2 jurisdiction code of the entity.
        legal_address_city: City of the registered legal address.
        legal_address_country: ISO 3166-1 country code of the legal
            address.
        hq_address_city: City of the headquarters address.
        hq_address_country: ISO 3166-1 country code of the
            headquarters address.
    """

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
    """An entity related to the queried LEI via a relationship record.

    Returned by :func:`gleif.queries.get_children`,
    :func:`gleif.queries.get_siblings`, and
    :func:`gleif.queries.get_other_relationships`.

    Attributes:
        lei: 20-character LEI of the related entity.
        legal_name: Legal name of the related entity, or ``None`` if
            the entity is referenced by an active relationship but
            does not have a corresponding row in ``lei_records``.
            This can happen when the Level 1 and Level 2 datasets
            are published at slightly different times.
        relationship_type: GLEIF relationship type, e.g.
            ``IS_DIRECTLY_CONSOLIDATED_BY`` or
            ``IS_INTERNATIONAL_BRANCH_OF``.
        relationship_status: Status of the relationship record, e.g.
            ``ACTIVE`` (query helpers only return ``ACTIVE`` rows).
            Empty string if blank in the source CSV.
        direction: Direction relative to the queried LEI - one of
            ``"parent"``, ``"child"``, ``"sibling"``, or ``"other"``.
    """

    lei: str
    legal_name: str | None
    relationship_type: str
    relationship_status: str
    direction: str  # "parent", "child", "sibling", "other"


@dataclass(frozen=True)
class ReportingException:
    """A documented reason an entity did not report a parent.

    GLEIF allows entities to register an "exception" instead of
    reporting a parent relationship (for example, when the parent
    consents have not been obtained or the entity has no consolidating
    parent). Returned by :func:`gleif.queries.get_reporting_exceptions`.

    Attributes:
        exception_category: Category of exception, e.g.
            ``ULTIMATE_ACCOUNTING_CONSOLIDATION_PARENT`` or
            ``DIRECT_ACCOUNTING_CONSOLIDATION_PARENT``.
        exception_reason: Standardized reason code, e.g.
            ``NO_KNOWN_PERSON``, ``NON_CONSOLIDATING``,
            ``LEGAL_OBSTACLES``.
        exception_reference: Free-text reference supplied by the
            reporter, when present.
    """

    exception_category: str
    exception_reason: str | None = None
    exception_reference: str | None = None


@dataclass(frozen=True)
class HierarchyNode:
    """A single entity in a hierarchy traversal, with depth context.

    Returned in lists by :func:`gleif.queries.get_ancestor_chain` and
    :func:`gleif.queries.get_descendant_tree`.

    Attributes:
        lei: 20-character LEI of the node.
        legal_name: Legal name, or ``None`` if the LEI is referenced
            by relationship rows but is missing from ``lei_records``.
        depth: 0 for the starting entity, 1 for its direct parent or
            child, and so on. Always non-negative.
        entity_status: Entity status from the Level 1 record, when
            available.
        entity_category: Entity category from the Level 1 record.
        legal_jurisdiction: Jurisdiction code from the Level 1 record.
        relationship_type: Relationship type that connects this node
            to its parent in the traversal (``None`` for the root
            node at depth 0).
        parent_lei: LEI of this node's parent in the traversal
            (``None`` for the root node at depth 0).
    """

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
    """A complete corporate group: root entity plus descendant tree.

    Returned by :func:`gleif.queries.get_corporate_group`. The
    descendants list is a flat, breadth-first ordering of every
    entity in the subtree rooted at ``root``, including ``root``
    itself at depth 0. To rebuild the tree shape, group by
    ``HierarchyNode.parent_lei``.

    Attributes:
        root: The ultimate parent of the corporate group.
        descendants: Flat list of every entity in the group,
            including the root at depth 0. Diamond structures are
            deduplicated by keeping the shallowest occurrence.
        total_entities: Total number of unique entities in the
            group, equal to ``len(descendants)``.
    """

    root: EntityInfo
    descendants: list[HierarchyNode] = field(default_factory=list)
    total_entities: int = 0


@dataclass(frozen=True)
class LEIRelationshipReport:
    """Complete relationship report for a single LEI.

    Returned by :func:`gleif.queries.get_full_report`. Aggregates the
    queried entity's direct and ultimate parents, its immediate
    children and siblings, any non-consolidation relationships, and
    any reporting exceptions filed against it.

    Edge cases:
        - ``direct_parent`` or ``ultimate_parent`` may be ``None``
          if the entity has no active consolidation relationship.
        - ``children``, ``siblings``, and ``other_relationships`` may
          be empty lists.
        - When a parent is filed as a reporting exception rather than
          a relationship, ``direct_parent`` / ``ultimate_parent`` will
          be ``None`` and ``reporting_exceptions`` will be populated.

    Attributes:
        entity: The queried entity.
        direct_parent: Entity that directly consolidates the queried
            entity, or ``None``.
        ultimate_parent: Top-of-tree consolidating entity, or ``None``.
        children: Entities that report the queried entity as a parent.
        siblings: Entities sharing the same direct parent (excludes
            the queried entity itself).
        other_relationships: Non-consolidation relationships such as
            international branch or fund relationships.
        reporting_exceptions: Documented reasons the entity did not
            report a parent relationship.
    """

    entity: EntityInfo
    direct_parent: EntityInfo | None = None
    ultimate_parent: EntityInfo | None = None
    children: list[RelatedEntity] = field(default_factory=list)
    siblings: list[RelatedEntity] = field(default_factory=list)
    other_relationships: list[RelatedEntity] = field(default_factory=list)
    reporting_exceptions: list[ReportingException] = field(default_factory=list)
