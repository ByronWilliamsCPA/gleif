"""Typed query helpers for LEI lookups and hierarchy traversal.

Every helper in this module takes an open ``duckdb.DuckDBPyConnection``
as its first argument and returns one of the frozen dataclasses
defined in :mod:`gleif.models`. Queries only consider relationship
rows with ``relationship_status = 'ACTIVE'``; relationships that
have lapsed or been retired are ignored.

LEI format
----------
A Legal Entity Identifier is a 20-character ISO 17442 code consisting
of uppercase ASCII alphanumerics and a 2-character checksum. The
query helpers do not validate the format - the caller is responsible
for normalisation (``lei.strip().upper()`` is what the CLI does). An
unrecognised or malformed LEI is treated as "not found" and the
relevant helper returns ``None`` or an empty list.

Edge cases
----------
* Lookups against a database that has not yet been populated raise
  ``duckdb.CatalogException`` from DuckDB (the tables do not exist).
* When a parent relationship has been replaced with a reporting
  exception, ``get_parent`` returns ``None`` and
  ``get_reporting_exceptions`` returns the rationale.
* When the Level 1 and Level 2 datasets are published at slightly
  different times an LEI may appear in ``relationships`` but be
  missing from ``lei_records``; ``RelatedEntity.legal_name`` will be
  ``None`` in that case.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gleif.constants import DIRECT_PARENT, MAX_HIERARCHY_DEPTH, ULTIMATE_PARENT
from gleif.models import (
    CorporateGroup,
    EntityInfo,
    HierarchyNode,
    LEIRelationshipReport,
    RelatedEntity,
    ReportingException,
)

if TYPE_CHECKING:
    import duckdb


def _row_to_entity(row: tuple[object, ...]) -> EntityInfo:
    """Convert a database row to an EntityInfo dataclass.

    Args:
        row (tuple[object, ...]): Tuple with columns in order: lei,
            legal_name, entity_status, registration_status,
            entity_category, legal_jurisdiction, legal_address_city,
            legal_address_country, hq_address_city, hq_address_country.

    Returns:
        EntityInfo: EntityInfo populated from the row values.
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
        con (duckdb.DuckDBPyConnection): Open DuckDB connection.
        lei (str): The 20-character LEI to look up. Case sensitive - GLEIF
            stores LEIs in uppercase, so callers should normalise
            with ``lei.strip().upper()`` before passing.

    Returns:
        EntityInfo | None: :class:`gleif.models.EntityInfo` for the matching
        row, or ``None`` if the LEI is not present in ``lei_records``.
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

    Joins the active relationship row for ``lei`` against
    ``lei_records`` so the returned ``EntityInfo`` carries the full
    Level 1 metadata. If the parent LEI is referenced by an active
    relationship but is itself missing from ``lei_records`` (Level 1
    / Level 2 publish lag), this returns ``None``.

    Args:
        con (duckdb.DuckDBPyConnection): Open DuckDB connection.
        lei (str): The child LEI to look up the parent for.
        relationship_type (str): Either
            :data:`gleif.constants.DIRECT_PARENT`
            (``"IS_DIRECTLY_CONSOLIDATED_BY"``) or
            :data:`gleif.constants.ULTIMATE_PARENT`
            (``"IS_ULTIMATELY_CONSOLIDATED_BY"``).

    Returns:
        EntityInfo | None: :class:`gleif.models.EntityInfo` for the parent,
        or ``None`` if there is no active parent relationship of that type,
        or the parent LEI is missing from ``lei_records``.
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

    Returns every entity whose active relationship row points at
    ``lei`` as the ``end_node_id``, regardless of relationship type
    (direct, ultimate, branch, fund, etc.). To restrict to direct
    consolidation children, filter the result by
    ``relationship_type == DIRECT_PARENT``.

    Args:
        con (duckdb.DuckDBPyConnection): Open DuckDB connection.
        lei (str): The parent LEI.

    Returns:
        list[RelatedEntity]: List of :class:`gleif.models.RelatedEntity`
        (one per relationship row), ordered by ``legal_name``. Empty list
        if no children are recorded.
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
    """Find entities sharing the same direct parent as ``lei``.

    Two entities are siblings here iff they share an active
    ``IS_DIRECTLY_CONSOLIDATED_BY`` relationship pointing at the
    same parent LEI. Entities that share only an ultimate parent
    (i.e. cousins) are not returned.

    Args:
        con (duckdb.DuckDBPyConnection): Open DuckDB connection.
        lei (str): The LEI whose siblings to find.

    Returns:
        list[RelatedEntity]: List of :class:`gleif.models.RelatedEntity`
        (excludes the queried LEI itself), ordered by ``legal_name``. Empty
        list if ``lei`` has no direct parent or is an only child.
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
    """Find non-consolidation relationships for an LEI.

    Returns active relationships in either direction whose type is
    *not* :data:`gleif.constants.DIRECT_PARENT` or
    :data:`gleif.constants.ULTIMATE_PARENT`. In practice this
    surfaces international branch, fund-management, and umbrella
    relationships.

    Args:
        con (duckdb.DuckDBPyConnection): Open DuckDB connection.
        lei (str): The LEI to query.

    Returns:
        list[RelatedEntity]: List of :class:`gleif.models.RelatedEntity`
        with ``direction="other"``, ordered by ``legal_name``. The ``lei``
        field is the *other* end of the relationship (i.e. not the queried
        LEI).
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
    """Get all reporting exceptions filed against an LEI.

    Reporting exceptions are filed when an entity is unable or
    unwilling to report a parent relationship (for example, because
    no consolidating parent exists, or consent could not be
    obtained). An LEI can have at most one exception per category.

    Args:
        con (duckdb.DuckDBPyConnection): Open DuckDB connection.
        lei (str): The LEI to query.

    Returns:
        list[ReportingException]: List of
        :class:`gleif.models.ReportingException`, ordered by
        ``exception_category``. Empty list if no exceptions are on file.
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

    Args:
        row (tuple[object, ...]): Tuple with columns in order: node_lei,
            legal_name, entity_status, entity_category, legal_jurisdiction,
            via_type, depth, parent_lei.

    Returns:
        HierarchyNode: HierarchyNode populated from the row values.
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
    """Walk UP from an entity to its ultimate parent.

    Uses a recursive CTE that follows
    :data:`gleif.constants.DIRECT_PARENT` relationships from child
    to parent. Tracks the visited path to break cycles defensively
    (the data is meant to be acyclic but malformed entries do
    occur).

    Args:
        con (duckdb.DuckDBPyConnection): Open DuckDB connection.
        lei (str): The starting LEI.
        max_depth (int): Upper bound on recursion depth. Defaults to
            :data:`gleif.constants.MAX_HIERARCHY_DEPTH`.

    Returns:
        list[HierarchyNode]: List of :class:`gleif.models.HierarchyNode`
        ordered by depth (0 = starting entity, 1 = direct parent,
        2 = grandparent, ...). Empty list if ``lei`` is not present in
        ``lei_records``. The last element is the ultimate parent of
        ``lei`` within the depth bound.
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
    """Walk DOWN from an entity to all descendants.

    Uses a recursive CTE that follows
    :data:`gleif.constants.DIRECT_PARENT` relationships from parent
    to child. Uses path tracking to prevent cycles, and applies a
    ``ROW_NUMBER() PARTITION BY node_lei ORDER BY depth`` filter so
    diamond structures (an entity reachable from the root via two
    different paths) appear exactly once, at the shallowest depth.

    Args:
        con (duckdb.DuckDBPyConnection): Open DuckDB connection.
        lei (str): The LEI to root the traversal at.
        max_depth (int): Upper bound on recursion depth. Defaults to
            :data:`gleif.constants.MAX_HIERARCHY_DEPTH`.

    Returns:
        list[HierarchyNode]: Flat list of :class:`gleif.models.HierarchyNode`
        for the entire subtree, ordered by ``(depth, legal_name)``. The
        starting entity is at depth 0. Empty list if ``lei`` is not present
        in ``lei_records``.
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

    Internally walks UP from ``lei`` via
    :func:`get_ancestor_chain` to find the ultimate parent, then
    DOWN via :func:`get_descendant_tree` to retrieve the entire
    subtree. The caller may pass any LEI in the group; the result
    is rooted at the ultimate parent regardless.

    Args:
        con (duckdb.DuckDBPyConnection): Open DuckDB connection.
        lei (str): Any LEI in the corporate group of interest.
        max_depth (int): Upper bound on recursion depth for both the
            up-walk and the down-walk. Defaults to
            :data:`gleif.constants.MAX_HIERARCHY_DEPTH`.

    Returns:
        CorporateGroup | None: :class:`gleif.models.CorporateGroup` with the
        root entity and the flat descendant list, or ``None`` if ``lei`` is
        not present in ``lei_records``.

    Example:
        >>> from gleif.constants import DEFAULT_DB_PATH
        >>> from gleif.db import get_connection
        >>> from gleif.queries import get_corporate_group
        >>> con = get_connection(DEFAULT_DB_PATH)  # doctest: +SKIP
        >>> group = get_corporate_group(con, "2138005YL12BKW2FQA89")  # doctest: +SKIP
        >>> group.root.legal_name  # doctest: +SKIP
        'Apple Inc.'
        >>> len(group.descendants)  # doctest: +SKIP
        42
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

    Uses DuckDB ``ILIKE`` for case-insensitive substring matching;
    the query string is wrapped in ``%`` wildcards. The match is
    against ``Entity.LegalName`` only - aliases and previous names
    are not searched (they are not loaded into the local schema).

    Args:
        con (duckdb.DuckDBPyConnection): Open DuckDB connection.
        name (str): Substring to match. Matched case-insensitively.
        limit (int): Maximum number of results to return. Defaults to 100.

    Returns:
        list[EntityInfo]: List of :class:`gleif.models.EntityInfo` ordered by
        ``legal_name``. Empty list if nothing matches.

    Example:
        >>> from gleif.constants import DEFAULT_DB_PATH
        >>> from gleif.db import get_connection
        >>> from gleif.queries import search_by_name
        >>> con = get_connection(DEFAULT_DB_PATH)  # doctest: +SKIP
        >>> results = search_by_name(con, "Apple", limit=5)  # doctest: +SKIP
        >>> [e.legal_name for e in results]  # doctest: +SKIP
        ['Apple Inc.', 'Apple Operations International Limited', ...]
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

    Aggregates one call to each of :func:`get_entity`,
    :func:`get_parent` (for both DIRECT and ULTIMATE),
    :func:`get_children`, :func:`get_siblings`,
    :func:`get_other_relationships`, and
    :func:`get_reporting_exceptions` into a single
    :class:`gleif.models.LEIRelationshipReport`.

    Args:
        con (duckdb.DuckDBPyConnection): Open DuckDB connection.
        lei (str): The 20-character LEI to query. Case sensitive; callers
            should normalise to uppercase.

    Returns:
        LEIRelationshipReport | None: :class:`gleif.models.LEIRelationshipReport`
        with all relationship slices populated, or ``None`` if ``lei`` is not
        present in ``lei_records``.

    Example:
        >>> from gleif.constants import DEFAULT_DB_PATH
        >>> from gleif.db import get_connection
        >>> from gleif.queries import get_full_report
        >>> con = get_connection(DEFAULT_DB_PATH)  # doctest: +SKIP
        >>> report = get_full_report(con, "2138005YL12BKW2FQA89")  # doctest: +SKIP
        >>> report.entity.legal_name  # doctest: +SKIP
        'Apple Inc.'
        >>> report.direct_parent is None  # doctest: +SKIP
        False
        >>> [c.legal_name for c in report.children][:2]  # doctest: +SKIP
        ['Apple Operations International Limited', ...]
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
