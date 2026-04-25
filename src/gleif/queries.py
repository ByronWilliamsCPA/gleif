"""Relationship query functions for LEI lookups."""

from __future__ import annotations

import duckdb

from gleif.constants import DIRECT_PARENT, MAX_HIERARCHY_DEPTH, ULTIMATE_PARENT
from gleif.models import (
    CorporateGroup,
    EntityInfo,
    HierarchyNode,
    LEIRelationshipReport,
    RelatedEntity,
    ReportingException,
)


def _row_to_entity(row: tuple[object, ...]) -> EntityInfo:
    """Convert a database row to an EntityInfo dataclass.

    Expected column order: lei, legal_name, entity_status, registration_status,
    entity_category, legal_jurisdiction, legal_address_city,
    legal_address_country, hq_address_city, hq_address_country.
    """
    return EntityInfo(
        lei=str(row[0]),
        legal_name=str(row[1]) if row[1] else "",
        entity_status=str(row[2]) if row[2] else "",
        registration_status=str(row[3]) if row[3] else "",
        entity_category=str(row[4]) if row[4] else None,
        legal_jurisdiction=str(row[5]) if row[5] else None,
        legal_address_city=str(row[6]) if row[6] else None,
        legal_address_country=str(row[7]) if row[7] else None,
        hq_address_city=str(row[8]) if row[8] else None,
        hq_address_country=str(row[9]) if row[9] else None,
    )


_ENTITY_COLS = """
    l.lei, l.legal_name, l.entity_status, l.registration_status,
    l.entity_category, l.legal_jurisdiction, l.legal_address_city,
    l.legal_address_country, l.hq_address_city, l.hq_address_country
"""


def get_entity(con: duckdb.DuckDBPyConnection, lei: str) -> EntityInfo | None:
    """Look up a single entity by LEI.

    Args:
        con: Open DuckDB connection.
        lei: The LEI to look up.

    Returns:
        EntityInfo or None if not found.
    """
    row = con.execute(
        f"SELECT {_ENTITY_COLS} FROM lei_records l WHERE l.lei = $1",
        [lei],
    ).fetchone()
    if row is None:
        return None
    return _row_to_entity(row)


def get_parent(
    con: duckdb.DuckDBPyConnection,
    lei: str,
    relationship_type: str,
) -> EntityInfo | None:
    """Find a parent entity via the relationships table.

    Args:
        con: Open DuckDB connection.
        lei: The child LEI.
        relationship_type: IS_DIRECTLY_CONSOLIDATED_BY or
            IS_ULTIMATELY_CONSOLIDATED_BY.

    Returns:
        EntityInfo of the parent, or None.
    """
    row = con.execute(
        f"""
        SELECT {_ENTITY_COLS}
        FROM relationships r
        LEFT JOIN lei_records l ON l.lei = r.end_node_id
        WHERE r.start_node_id = $1
          AND r.relationship_type = $2
          AND r.relationship_status = 'ACTIVE'
        LIMIT 1
        """,
        [lei, relationship_type],
    ).fetchone()
    if row is None:
        return None
    # If parent LEI exists in relationships but not in lei_records,
    # we still return what we can.
    if row[0] is None:
        return None
    return _row_to_entity(row)


def get_children(con: duckdb.DuckDBPyConnection, lei: str) -> list[RelatedEntity]:
    """Find all entities that report this LEI as a parent.

    Args:
        con: Open DuckDB connection.
        lei: The parent LEI.

    Returns:
        List of child RelatedEntity records.
    """
    rows = con.execute(
        """
        SELECT r.start_node_id, l.legal_name,
               r.relationship_type, r.relationship_status
        FROM relationships r
        LEFT JOIN lei_records l ON l.lei = r.start_node_id
        WHERE r.end_node_id = $1
          AND r.relationship_status = 'ACTIVE'
        ORDER BY l.legal_name
        """,
        [lei],
    ).fetchall()
    return [
        RelatedEntity(
            lei=str(row[0]),
            legal_name=str(row[1]) if row[1] else None,
            relationship_type=str(row[2]),
            relationship_status=str(row[3]) if row[3] else "",
            direction="child",
        )
        for row in rows
    ]


def get_siblings(con: duckdb.DuckDBPyConnection, lei: str) -> list[RelatedEntity]:
    """Find entities sharing the same direct parent.

    Args:
        con: Open DuckDB connection.
        lei: The LEI to find siblings for.

    Returns:
        List of sibling RelatedEntity records (excludes the queried LEI).
    """
    rows = con.execute(
        """
        SELECT r2.start_node_id, l.legal_name,
               r2.relationship_type, r2.relationship_status
        FROM relationships r2
        LEFT JOIN lei_records l ON l.lei = r2.start_node_id
        WHERE r2.end_node_id = (
            SELECT r1.end_node_id
            FROM relationships r1
            WHERE r1.start_node_id = $1
              AND r1.relationship_type = $2
              AND r1.relationship_status = 'ACTIVE'
            LIMIT 1
        )
        AND r2.relationship_type = $2
        AND r2.relationship_status = 'ACTIVE'
        AND r2.start_node_id != $1
        ORDER BY l.legal_name
        """,
        [lei, DIRECT_PARENT],
    ).fetchall()
    return [
        RelatedEntity(
            lei=str(row[0]),
            legal_name=str(row[1]) if row[1] else None,
            relationship_type=str(row[2]),
            relationship_status=str(row[3]) if row[3] else "",
            direction="sibling",
        )
        for row in rows
    ]


def get_other_relationships(
    con: duckdb.DuckDBPyConnection, lei: str
) -> list[RelatedEntity]:
    """Find non-consolidation relationships (branches, funds, etc.).

    Args:
        con: Open DuckDB connection.
        lei: The LEI to query.

    Returns:
        List of RelatedEntity with direction="other".
    """
    rows = con.execute(
        """
        SELECT
            CASE WHEN r.start_node_id = $1 THEN r.end_node_id
                 ELSE r.start_node_id END AS related_lei,
            l.legal_name,
            r.relationship_type,
            r.relationship_status
        FROM relationships r
        LEFT JOIN lei_records l ON l.lei = (
            CASE WHEN r.start_node_id = $1 THEN r.end_node_id
                 ELSE r.start_node_id END
        )
        WHERE (r.start_node_id = $1 OR r.end_node_id = $1)
          AND r.relationship_type NOT IN ($2, $3)
          AND r.relationship_status = 'ACTIVE'
        ORDER BY l.legal_name
        """,
        [lei, DIRECT_PARENT, ULTIMATE_PARENT],
    ).fetchall()
    return [
        RelatedEntity(
            lei=str(row[0]),
            legal_name=str(row[1]) if row[1] else None,
            relationship_type=str(row[2]),
            relationship_status=str(row[3]) if row[3] else "",
            direction="other",
        )
        for row in rows
    ]


def get_reporting_exceptions(
    con: duckdb.DuckDBPyConnection, lei: str
) -> list[ReportingException]:
    """Get all reporting exceptions for an LEI.

    Args:
        con: Open DuckDB connection.
        lei: The LEI to query.

    Returns:
        List of ReportingException records.
    """
    rows = con.execute(
        """
        SELECT exception_category, exception_reason_1, exception_reference_1
        FROM reporting_exceptions
        WHERE lei = $1
        ORDER BY exception_category
        """,
        [lei],
    ).fetchall()
    return [
        ReportingException(
            exception_category=str(row[0]),
            exception_reason=str(row[1]) if row[1] else None,
            exception_reference=str(row[2]) if row[2] else None,
        )
        for row in rows
    ]


def _row_to_hierarchy_node(row: tuple[object, ...]) -> HierarchyNode:
    """Convert a CTE result row to a HierarchyNode.

    Expected column order: node_lei, legal_name, entity_status,
    entity_category, legal_jurisdiction, via_type, depth, parent_lei.
    """
    return HierarchyNode(
        lei=str(row[0]),
        legal_name=str(row[1]) if row[1] else None,
        entity_status=str(row[2]) if row[2] else None,
        entity_category=str(row[3]) if row[3] else None,
        legal_jurisdiction=str(row[4]) if row[4] else None,
        relationship_type=str(row[5]) if row[5] else None,
        depth=int(str(row[6])),
        parent_lei=str(row[7]) if row[7] else None,
    )


def get_ancestor_chain(
    con: duckdb.DuckDBPyConnection,
    lei: str,
    *,
    max_depth: int = MAX_HIERARCHY_DEPTH,
) -> list[HierarchyNode]:
    """Walk UP from an entity to its ultimate parent via direct-parent links.

    Returns a list of HierarchyNode ordered by depth (0 = starting entity,
    1 = direct parent, 2 = grandparent, etc.).  Uses path tracking to
    prevent cycles.

    Args:
        con: Open DuckDB connection.
        lei: The starting LEI.
        max_depth: Maximum recursion depth.

    Returns:
        List of HierarchyNode from entity to root, or empty if LEI
        not found.
    """
    rows = con.execute(
        """
        WITH RECURSIVE ancestors AS (
            SELECT lei AS node_lei,
                   CAST(NULL AS VARCHAR) AS via_type,
                   0 AS depth,
                   CAST(NULL AS VARCHAR) AS parent_lei,
                   [lei] AS path
            FROM lei_records
            WHERE lei = $1
            UNION ALL
            SELECT r.end_node_id,
                   r.relationship_type,
                   a.depth + 1,
                   a.node_lei,
                   list_append(a.path, r.end_node_id)
            FROM ancestors a
            JOIN relationships r
                ON r.start_node_id = a.node_lei
                AND r.relationship_type = $2
                AND r.relationship_status = 'ACTIVE'
            WHERE a.depth < $3
              AND NOT list_contains(a.path, r.end_node_id)
        )
        SELECT a.node_lei, l.legal_name, l.entity_status,
               l.entity_category, l.legal_jurisdiction,
               a.via_type, a.depth, a.parent_lei
        FROM ancestors a
        LEFT JOIN lei_records l ON l.lei = a.node_lei
        ORDER BY a.depth
        """,
        [lei, DIRECT_PARENT, max_depth],
    ).fetchall()
    return [_row_to_hierarchy_node(row) for row in rows]


def get_descendant_tree(
    con: duckdb.DuckDBPyConnection,
    lei: str,
    *,
    max_depth: int = MAX_HIERARCHY_DEPTH,
) -> list[HierarchyNode]:
    """Walk DOWN from an entity to all descendants via direct-parent links.

    Returns a flat list of HierarchyNode ordered by (depth, legal_name).
    The starting entity is at depth 0.  Uses path tracking to prevent
    cycles; diamond structures are deduplicated via first-parent-wins
    (shallowest depth kept).

    Args:
        con: Open DuckDB connection.
        lei: The root LEI to walk down from.
        max_depth: Maximum recursion depth.

    Returns:
        List of HierarchyNode for the entire subtree, or empty if LEI
        not found.
    """
    rows = con.execute(
        """
        WITH RECURSIVE descendants AS (
            SELECT lei AS node_lei,
                   CAST(NULL AS VARCHAR) AS via_type,
                   0 AS depth,
                   CAST(NULL AS VARCHAR) AS parent_lei,
                   [lei] AS path
            FROM lei_records
            WHERE lei = $1
            UNION ALL
            SELECT r.start_node_id,
                   r.relationship_type,
                   d.depth + 1,
                   d.node_lei,
                   list_append(d.path, r.start_node_id)
            FROM descendants d
            JOIN relationships r
                ON r.end_node_id = d.node_lei
                AND r.relationship_type = $2
                AND r.relationship_status = 'ACTIVE'
            WHERE d.depth < $3
              AND NOT list_contains(d.path, r.start_node_id)
        )
        SELECT sub.node_lei, sub.legal_name, sub.entity_status,
               sub.entity_category, sub.legal_jurisdiction,
               sub.via_type, sub.depth, sub.parent_lei
        FROM (
            SELECT d.node_lei, l.legal_name, l.entity_status,
                   l.entity_category, l.legal_jurisdiction,
                   d.via_type, d.depth, d.parent_lei,
                   ROW_NUMBER() OVER (
                       PARTITION BY d.node_lei ORDER BY d.depth
                   ) AS rn
            FROM descendants d
            LEFT JOIN lei_records l ON l.lei = d.node_lei
        ) sub
        WHERE sub.rn = 1
        ORDER BY sub.depth, sub.legal_name
        """,
        [lei, DIRECT_PARENT, max_depth],
    ).fetchall()
    return [_row_to_hierarchy_node(row) for row in rows]


def get_corporate_group(
    con: duckdb.DuckDBPyConnection,
    lei: str,
    *,
    max_depth: int = MAX_HIERARCHY_DEPTH,
) -> CorporateGroup | None:
    """Build a complete corporate group for any entity in the hierarchy.

    Walks UP to find the ultimate parent, then DOWN to retrieve the full
    descendant tree.

    Args:
        con: Open DuckDB connection.
        lei: Any LEI in the corporate group.
        max_depth: Maximum recursion depth for traversal.

    Returns:
        CorporateGroup or None if the LEI is not found.
    """
    entity = get_entity(con, lei)
    if entity is None:
        return None

    # Walk up to find the root of the hierarchy.
    chain = get_ancestor_chain(con, lei, max_depth=max_depth)
    root_lei = chain[-1].lei if chain else lei

    root = get_entity(con, root_lei)
    if root is None:
        root = entity

    # Walk down from the root to get the full tree.
    tree = get_descendant_tree(con, root.lei, max_depth=max_depth)

    return CorporateGroup(
        root=root,
        descendants=tree,
        total_entities=len(tree),
    )


def search_by_name(
    con: duckdb.DuckDBPyConnection,
    name: str,
    *,
    limit: int = 100,
) -> list[EntityInfo]:
    """Search for entities whose legal name contains the given string.

    Args:
        con: Open DuckDB connection.
        name: Case-insensitive substring to match against legal_name.
        limit: Maximum number of results to return.

    Returns:
        List of matching EntityInfo records, ordered by legal_name.
    """
    rows = con.execute(
        f"""
        SELECT {_ENTITY_COLS}
        FROM lei_records l
        WHERE l.legal_name ILIKE $1
        ORDER BY l.legal_name
        LIMIT $2
        """,
        [f"%{name}%", limit],
    ).fetchall()
    return [_row_to_entity(row) for row in rows]


def get_full_report(
    con: duckdb.DuckDBPyConnection, lei: str
) -> LEIRelationshipReport | None:
    """Build a complete relationship report for an LEI.

    Args:
        con: Open DuckDB connection.
        lei: The LEI to query.

    Returns:
        LEIRelationshipReport or None if the LEI is not found.
    """
    entity = get_entity(con, lei)
    if entity is None:
        return None

    return LEIRelationshipReport(
        entity=entity,
        direct_parent=get_parent(con, lei, DIRECT_PARENT),
        ultimate_parent=get_parent(con, lei, ULTIMATE_PARENT),
        children=get_children(con, lei),
        siblings=get_siblings(con, lei),
        other_relationships=get_other_relationships(con, lei),
        reporting_exceptions=get_reporting_exceptions(con, lei),
    )
