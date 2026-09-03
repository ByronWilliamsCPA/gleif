"""Rich rendering helpers for the GLEIF CLI.

This module owns the formatting and console-output side of the
``gleif`` command line tool. Each ``render_*`` function takes already
materialised dataclasses from :mod:`gleif.models` and writes a Rich
artefact (Panel, Table, or Tree) to the shared ``console``.

The helpers are split out from :mod:`gleif.cli` so the CLI module can
focus on argument parsing, database wiring, and command dispatch; this
also keeps the per-module cyclomatic complexity below the qlty smell
threshold. The split is import-only: callers do not pass a Console in,
and behaviour is unchanged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from gleif.models import EntityInfo, HierarchyNode

if TYPE_CHECKING:
    from collections.abc import Sequence

    from gleif.models import (
        CorporateGroup,
        LEIRelationshipReport,
        RelatedEntity,
        ReportingException,
    )

console = Console()


def collect_report_leis(report: LEIRelationshipReport) -> list[str]:
    """Collect all unique LEIs referenced in a report."""
    leis = [report.entity.lei]
    if report.direct_parent:
        leis.append(report.direct_parent.lei)
    if report.ultimate_parent:
        leis.append(report.ultimate_parent.lei)
    leis.extend(child.lei for child in report.children)
    leis.extend(sibling.lei for sibling in report.siblings)
    leis.extend(other.lei for other in report.other_relationships)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for lei_code in leis:
        if lei_code not in seen:
            seen.add(lei_code)
            unique.append(lei_code)
    return unique


def format_isins(isin_map: dict[str, list[str]], lei_code: str) -> str:
    """Format ISINs for a given LEI, or empty string if none."""
    isins = isin_map.get(lei_code, [])
    return ", ".join(isins) if isins else ""


def render_entity_panel(
    entity: EntityInfo,
    isin_map: dict[str, list[str]],
) -> None:
    """Render the top-level entity info panel."""
    info_lines = [
        f"[bold]Name:[/]          {entity.legal_name}",
        f"[bold]Status:[/]        {entity.entity_status}",
        f"[bold]Category:[/]      {entity.entity_category or 'N/A'}",
        f"[bold]Jurisdiction:[/]  {entity.legal_jurisdiction or 'N/A'}",
        (
            f"[bold]Legal Addr:[/]    "
            f"{entity.legal_address_city or ''}, "
            f"{entity.legal_address_country or ''}"
        ),
        (
            f"[bold]HQ Addr:[/]       "
            f"{entity.hq_address_city or ''}, "
            f"{entity.hq_address_country or ''}"
        ),
        f"[bold]Reg. Status:[/]   {entity.registration_status}",
    ]
    entity_isins = format_isins(isin_map, entity.lei)
    if entity_isins:
        info_lines.append(f"[bold]ISINs:[/]         {entity_isins}")
    console.print(
        Panel(
            "\n".join(info_lines),
            title=f"[bold cyan]{entity.lei}[/]",
            border_style="cyan",
        )
    )


def render_exceptions_table(exceptions: Sequence[ReportingException]) -> None:
    """Render reporting exceptions as a Rich table."""
    table = Table(title="Reporting Exceptions", border_style="yellow")
    table.add_column("Category", style="yellow")
    table.add_column("Reason")
    table.add_column("Reference")
    for exc in exceptions:
        table.add_row(
            exc.exception_category,
            exc.exception_reason or "",
            exc.exception_reference or "",
        )
    console.print(table)


def render_report(
    report: LEIRelationshipReport,
    *,
    isin_map: dict[str, list[str]] | None = None,
) -> None:
    """Render a full LEI relationship report to the console."""
    isin_map = isin_map or {}

    render_entity_panel(report.entity, isin_map)

    if report.direct_parent:
        render_parent_section("Direct Parent", report.direct_parent, isin_map)
    else:
        console.print("[dim]Direct Parent: None[/]")

    if report.ultimate_parent:
        render_parent_section("Ultimate Parent", report.ultimate_parent, isin_map)
    else:
        console.print("[dim]Ultimate Parent: None[/]")

    if report.children:
        render_related_table("Children", report.children, isin_map)
    else:
        console.print("[dim]Children: None[/]")

    if report.siblings:
        render_related_table("Siblings", report.siblings, isin_map)
    else:
        console.print("[dim]Siblings: None[/]")

    if report.other_relationships:
        render_related_table(
            "Other Relationships", report.other_relationships, isin_map
        )

    if report.reporting_exceptions:
        render_exceptions_table(report.reporting_exceptions)


def render_parent_section(
    title: str,
    parent: EntityInfo | None,
    isin_map: dict[str, list[str]] | None = None,
) -> None:
    """Render a parent entity as a compact line."""
    if parent is None:
        return
    line = (
        f"[bold]{title}:[/] [cyan]{parent.lei}[/] | "
        f"{parent.legal_name} | {parent.entity_status} | "
        f"{parent.legal_jurisdiction or 'N/A'}"
    )
    parent_isins = format_isins(isin_map or {}, parent.lei)
    if parent_isins:
        line += f" | ISINs: {parent_isins}"
    console.print(line)


def render_related_table(
    title: str,
    entities: list[RelatedEntity],
    isin_map: dict[str, list[str]] | None = None,
) -> None:
    """Render a list of related entities as a Rich table."""
    isin_map = isin_map or {}
    # Only add the ISINs column when at least one rendered entity actually has
    # ISINs; a non-empty isin_map covering unrelated LEIs would otherwise
    # produce a column of empty strings.
    show_isins = any(isin_map.get(ent.lei) for ent in entities)

    table = Table(title=title, border_style="blue")
    table.add_column("LEI", style="cyan", no_wrap=True)
    table.add_column("Name")
    table.add_column("Relationship Type")
    if show_isins:
        table.add_column("ISINs", style="green")
    for ent in entities:
        row = [
            ent.lei,
            ent.legal_name or "[dim]N/A[/]",
            ent.relationship_type,
        ]
        if show_isins:
            row.append(format_isins(isin_map, ent.lei))
        table.add_row(*row)
    console.print(table)


def format_node_label(
    node: object,
    isin_map: dict[str, list[str]],
) -> str:
    """Format a single hierarchy node label for tree display."""
    if not isinstance(node, HierarchyNode):
        return str(node)
    parts = [f"[cyan]{node.lei}[/]"]
    if node.legal_name:
        parts.append(f"[bold]{node.legal_name}[/]")
    details: list[str] = []
    if node.legal_jurisdiction:
        details.append(node.legal_jurisdiction)
    if node.entity_status:
        details.append(node.entity_status)
    if details:
        parts.append(f"({', '.join(details)})")
    isins = format_isins(isin_map, node.lei)
    if isins:
        parts.append(f"[green]ISINs: {isins}[/]")
    return " ".join(parts)


def render_tree(
    group: CorporateGroup,
    *,
    isin_map: dict[str, list[str]] | None = None,
) -> None:
    """Render a corporate group as a Rich tree with DAG-aware dedup."""
    isin_map = isin_map or {}

    console.print(f"\n[bold]Corporate Group[/] ({group.total_entities} entities)\n")

    # Build a mapping from parent_lei -> children for tree construction.
    children_map: dict[str | None, list[HierarchyNode]] = {}
    for node in group.descendants:
        children_map.setdefault(node.parent_lei, []).append(node)

    def _add_children(
        parent_tree: Tree,
        parent_lei: str,
        seen: set[str],
    ) -> None:
        """Recursively add child nodes to the tree."""
        for child in children_map.get(parent_lei, []):
            if child.lei in seen:
                parent_tree.add(
                    f"[dim]{child.lei} {child.legal_name or ''} (see above)[/]"
                )
                continue
            seen.add(child.lei)
            branch = parent_tree.add(format_node_label(child, isin_map))
            _add_children(branch, child.lei, seen)

    # Root nodes are at depth 0. A corporate group may have more than one
    # top-level entity (e.g., distinct ultimate parents whose subsidiaries
    # all appear in `group.descendants`). Iterate all roots so none are
    # silently dropped.
    root_nodes = children_map.get(None, [])
    if not root_nodes:
        console.print("[yellow]No hierarchy data found.[/]")
        return

    seen: set[str] = set()
    for root in root_nodes:
        if root.lei in seen:
            continue
        seen.add(root.lei)
        rich_tree = Tree(format_node_label(root, isin_map))
        _add_children(rich_tree, root.lei, seen)
        console.print(rich_tree)
