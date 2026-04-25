"""Tests for recursive hierarchy traversal functions."""

from __future__ import annotations

import duckdb

from gleif.queries import (
    get_ancestor_chain,
    get_corporate_group,
    get_descendant_tree,
)


class TestGetAncestorChain:
    """Tests for recursive ancestor chain traversal."""

    def test_walks_full_chain_from_leaf(
        self, deep_hierarchy_db: duckdb.DuckDBPyConnection
    ) -> None:
        """Grandchild -> Child A -> Parent -> Ultimate."""
        chain = get_ancestor_chain(deep_hierarchy_db, "GRANDCHILD0000000001")
        assert len(chain) == 4
        assert chain[0].lei == "GRANDCHILD0000000001"
        assert chain[0].depth == 0
        assert chain[1].lei == "CHILD000000000000001"
        assert chain[1].depth == 1
        assert chain[2].lei == "PARENT00000000000001"
        assert chain[2].depth == 2
        assert chain[3].lei == "ULTIMATE000000000001"
        assert chain[3].depth == 3

    def test_root_entity_returns_single_node(
        self, loaded_db: duckdb.DuckDBPyConnection
    ) -> None:
        """Ultimate parent has no direct parents; chain is just itself."""
        chain = get_ancestor_chain(loaded_db, "ULTIMATE000000000001")
        assert len(chain) == 1
        assert chain[0].lei == "ULTIMATE000000000001"
        assert chain[0].depth == 0

    def test_nonexistent_lei_returns_empty(
        self, loaded_db: duckdb.DuckDBPyConnection
    ) -> None:
        chain = get_ancestor_chain(loaded_db, "NONEXISTENT0000000001")
        assert chain == []

    def test_depth_limit_respected(
        self, deep_hierarchy_db: duckdb.DuckDBPyConnection
    ) -> None:
        chain = get_ancestor_chain(
            deep_hierarchy_db,
            "GRANDCHILD0000000001",
            max_depth=2,
        )
        assert all(n.depth <= 2 for n in chain)
        leis = {n.lei for n in chain}
        assert "ULTIMATE000000000001" not in leis

    def test_parent_lei_populated(
        self, deep_hierarchy_db: duckdb.DuckDBPyConnection
    ) -> None:
        chain = get_ancestor_chain(deep_hierarchy_db, "GRANDCHILD0000000001")
        assert chain[0].parent_lei is None
        assert chain[1].parent_lei == "GRANDCHILD0000000001"
        assert chain[2].parent_lei == "CHILD000000000000001"

    def test_entity_fields_populated(
        self, loaded_db: duckdb.DuckDBPyConnection
    ) -> None:
        chain = get_ancestor_chain(loaded_db, "CHILD000000000000001")
        child = chain[0]
        assert child.legal_name == "Child A Inc."
        assert child.entity_status == "ACTIVE"
        assert child.legal_jurisdiction == "US"


class TestGetDescendantTree:
    """Tests for recursive descendant tree traversal."""

    def test_walks_full_tree_from_root(
        self, deep_hierarchy_db: duckdb.DuckDBPyConnection
    ) -> None:
        """Ultimate -> Parent -> [Child A -> Grandchild, Child B]."""
        tree = get_descendant_tree(deep_hierarchy_db, "ULTIMATE000000000001")
        assert len(tree) == 5
        assert tree[0].lei == "ULTIMATE000000000001"
        assert tree[0].depth == 0
        leis = {n.lei for n in tree}
        assert "GRANDCHILD0000000001" in leis
        assert "CHILD000000000000002" in leis

    def test_leaf_entity_returns_single_node(
        self, loaded_db: duckdb.DuckDBPyConnection
    ) -> None:
        tree = get_descendant_tree(loaded_db, "CHILD000000000000001")
        assert len(tree) == 1
        assert tree[0].depth == 0

    def test_mid_level_entity_subtree(
        self, deep_hierarchy_db: duckdb.DuckDBPyConnection
    ) -> None:
        """Parent -> [Child A -> Grandchild, Child B]."""
        tree = get_descendant_tree(deep_hierarchy_db, "PARENT00000000000001")
        assert len(tree) == 4
        depths = [n.depth for n in tree]
        assert depths == sorted(depths)

    def test_nonexistent_lei_returns_empty(
        self, loaded_db: duckdb.DuckDBPyConnection
    ) -> None:
        tree = get_descendant_tree(loaded_db, "NONEXISTENT0000000001")
        assert tree == []

    def test_depth_limit_respected(
        self, deep_hierarchy_db: duckdb.DuckDBPyConnection
    ) -> None:
        tree = get_descendant_tree(
            deep_hierarchy_db,
            "ULTIMATE000000000001",
            max_depth=1,
        )
        assert all(n.depth <= 1 for n in tree)
        leis = {n.lei for n in tree}
        assert "GRANDCHILD0000000001" not in leis

    def test_parent_lei_populated(
        self, deep_hierarchy_db: duckdb.DuckDBPyConnection
    ) -> None:
        tree = get_descendant_tree(deep_hierarchy_db, "ULTIMATE000000000001")
        root = next(n for n in tree if n.depth == 0)
        assert root.parent_lei is None
        parent_node = next(n for n in tree if n.lei == "PARENT00000000000001")
        assert parent_node.parent_lei == "ULTIMATE000000000001"

    def test_diamond_does_not_duplicate(
        self, diamond_db: duckdb.DuckDBPyConnection
    ) -> None:
        """Shared entity (child of both Child A and Child B) appears once."""
        tree = get_descendant_tree(diamond_db, "ULTIMATE000000000001")
        shared_nodes = [n for n in tree if n.lei == "SHARED00000000000001"]
        # Path tracking prevents revisiting — Shared appears once
        assert len(shared_nodes) == 1


class TestGetCorporateGroup:
    """Tests for full corporate group discovery."""

    def test_from_leaf_finds_entire_group(
        self, deep_hierarchy_db: duckdb.DuckDBPyConnection
    ) -> None:
        group = get_corporate_group(deep_hierarchy_db, "GRANDCHILD0000000001")
        assert group is not None
        assert group.root.lei == "ULTIMATE000000000001"
        assert group.total_entities == 5

    def test_from_root_finds_entire_group(
        self, deep_hierarchy_db: duckdb.DuckDBPyConnection
    ) -> None:
        group = get_corporate_group(deep_hierarchy_db, "ULTIMATE000000000001")
        assert group is not None
        assert group.root.lei == "ULTIMATE000000000001"
        assert group.total_entities == 5

    def test_from_mid_level(self, deep_hierarchy_db: duckdb.DuckDBPyConnection) -> None:
        group = get_corporate_group(deep_hierarchy_db, "PARENT00000000000001")
        assert group is not None
        assert group.root.lei == "ULTIMATE000000000001"

    def test_nonexistent_lei(self, loaded_db: duckdb.DuckDBPyConnection) -> None:
        group = get_corporate_group(loaded_db, "NONEXISTENT0000000001")
        assert group is None

    def test_standalone_entity_is_own_group(
        self, loaded_db: duckdb.DuckDBPyConnection
    ) -> None:
        """Ultimate parent with no parents is its own root."""
        group = get_corporate_group(loaded_db, "ULTIMATE000000000001")
        assert group is not None
        assert group.root.lei == "ULTIMATE000000000001"
        assert group.total_entities >= 1

    def test_root_has_full_entity_info(
        self, loaded_db: duckdb.DuckDBPyConnection
    ) -> None:
        group = get_corporate_group(loaded_db, "CHILD000000000000001")
        assert group is not None
        assert group.root.legal_name == "Ultimate Holdings PLC"
        assert group.root.entity_status == "ACTIVE"
