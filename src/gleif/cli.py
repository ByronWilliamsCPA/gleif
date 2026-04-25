"""Typer CLI for GLEIF golden copy data management and LEI queries."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from gleif.constants import (
    DATASET_LABELS,
    DEFAULT_DATA_DIR,
    DEFAULT_DB_PATH,
    MAX_HIERARCHY_DEPTH,
    DatasetType,
)
from gleif.db import get_connection, get_status, load_all
from gleif.download import download_all
from gleif.isin import fetch_isins_batch
from gleif.models import CorporateGroup, LEIRelationshipReport, RelatedEntity
from gleif.queries import get_corporate_group, get_full_report, search_by_name

app = typer.Typer(
    name="gleif",
    help="GLEIF Golden Copy data loader and LEI relationship query CLI.",
    no_args_is_help=True,
)
console = Console()

DataDirOption = Annotated[
    Path,
    typer.Option(
        "--data-dir",
        help="Directory for downloaded data files.",
    ),
]

DbPathOption = Annotated[
    Path,
    typer.Option(
        "--db",
        help="Path to the DuckDB database file.",
    ),
]

ForceOption = Annotated[
    bool,
    typer.Option(
        "--force",
        help="Re-download even if local data is current.",
    ),
]


@app.command()
def download(
    data_dir: DataDirOption = DEFAULT_DATA_DIR,
    force: ForceOption = False,
) -> None:
    """Download and extract all GLEIF golden copy datasets."""
    console.print("[bold]Downloading GLEIF golden copy datasets...[/]")
    results = asyncio.run(download_all(data_dir, force=force))
    for result in results:
        console.print(
            f"  [green]{result.record_label}[/]: {result.csv_path.name} "
            f"(published {result.publish_date})"
        )
    console.print("[bold green]Download complete.[/]")


@app.command()
def load(
    db: DbPathOption = DEFAULT_DB_PATH,
    data_dir: DataDirOption = DEFAULT_DATA_DIR,
) -> None:
    """Load extracted CSVs into DuckDB."""
    from gleif.download import (  # noqa: PLC0415
        DownloadResult,
        _find_extracted_csv,
        _read_local_publish_date,
    )

    results: list[DownloadResult] = []
    for dt in DatasetType:
        csv_path = _find_extracted_csv(data_dir, dt)
        if csv_path is None:
            console.print(
                f"[red]No extracted CSV found for {DATASET_LABELS[dt]}. "
                f"Run 'gleif download' first.[/]"
            )
            raise typer.Exit(code=1)
        publish_date = _read_local_publish_date(data_dir, dt) or "unknown"
        results.append(
            DownloadResult(
                csv_path=csv_path,
                publish_date=publish_date,
                dataset_type=dt,
                record_label=DATASET_LABELS[dt],
            )
        )

    console.print(f"[bold]Loading data into {db}...[/]")
    con = get_connection(db)
    try:
        load_all(con, results)
    finally:
        con.close()
    console.print("[bold green]Load complete.[/]")


@app.command()
def refresh(
    db: DbPathOption = DEFAULT_DB_PATH,
    data_dir: DataDirOption = DEFAULT_DATA_DIR,
    force: ForceOption = False,
) -> None:
    """Download and load GLEIF data in one step."""
    console.print("[bold]Refreshing GLEIF data...[/]")
    results = asyncio.run(download_all(data_dir, force=force))

    console.print(f"\n[bold]Loading into {db}...[/]")
    con = get_connection(db)
    try:
        load_all(con, results)
    finally:
        con.close()
    console.print("[bold green]Refresh complete.[/]")


@app.command()
def lei(
    lei_code: Annotated[str, typer.Argument(help="The LEI to look up.")],
    db: DbPathOption = DEFAULT_DB_PATH,
    isin: Annotated[
        bool,
        typer.Option(
            "--isin",
            help="Fetch ISINs from the GLEIF API.",
        ),
    ] = False,
    tree: Annotated[
        bool,
        typer.Option(
            "--tree",
            help="Show full corporate hierarchy tree.",
        ),
    ] = False,
    max_depth: Annotated[
        int,
        typer.Option(
            "--max-depth",
            help="Maximum depth for hierarchy traversal.",
        ),
    ] = MAX_HIERARCHY_DEPTH,
) -> None:
    """Look up an LEI and display all related entities."""
    lei_code = lei_code.strip().upper()
    lei_length = 20
    if len(lei_code) != lei_length:
        console.print(
            f"[red]Invalid LEI '{lei_code}': must be exactly 20 characters.[/]"
        )
        raise typer.Exit(code=1)

    con = get_connection(db)
    try:
        if tree:
            group = get_corporate_group(con, lei_code, max_depth=max_depth)
        else:
            group = None
        report = None if tree else get_full_report(con, lei_code)
    finally:
        con.close()

    if tree:
        if group is None:
            console.print(f"[red]LEI '{lei_code}' not found in the database.[/]")
            raise typer.Exit(code=1)

        isin_map: dict[str, list[str]] = {}
        if isin:
            all_leis = list({n.lei for n in group.descendants})
            console.print("[dim]Fetching ISINs from GLEIF API...[/]")
            isin_map = fetch_isins_batch(all_leis)

        _render_tree(group, isin_map=isin_map)
        return

    if report is None:
        console.print(f"[red]LEI '{lei_code}' not found in the database.[/]")
        raise typer.Exit(code=1)

    isin_map_flat: dict[str, list[str]] = {}
    if isin:
        all_leis = _collect_report_leis(report)
        console.print("[dim]Fetching ISINs from GLEIF API...[/]")
        isin_map_flat = fetch_isins_batch(all_leis)

    _render_report(report, isin_map=isin_map_flat)


@app.command()
def name(
    query: Annotated[str, typer.Argument(help="Name or substring to search for.")],
    db: DbPathOption = DEFAULT_DB_PATH,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum number of results."),
    ] = 100,
    isin: Annotated[
        bool,
        typer.Option(
            "--isin",
            help="Fetch ISINs from the GLEIF API.",
        ),
    ] = False,
) -> None:
    """Search for entities by legal name (case-insensitive substring match)."""
    con = get_connection(db)
    try:
        results = search_by_name(con, query, limit=limit)
    finally:
        con.close()

    if not results:
        console.print(f"[yellow]No entities found matching '{query}'.[/]")
        raise typer.Exit(code=0)

    isin_map: dict[str, list[str]] = {}
    if isin:
        console.print("[dim]Fetching ISINs from GLEIF API...[/]")
        isin_map = fetch_isins_batch([e.lei for e in results])

    table = Table(
        title=(
            f"Name Search: '{query}' "
            f"({len(results)} result{'s' if len(results) != 1 else ''})"
        ),
        border_style="cyan",
    )
    table.add_column("LEI", style="cyan", no_wrap=True)
    table.add_column("Legal Name")
    table.add_column("Jurisdiction")
    table.add_column("Status")
    if isin:
        table.add_column("ISINs", style="green")
    for entity in results:
        row = [
            entity.lei,
            entity.legal_name,
            entity.legal_jurisdiction or "",
            entity.entity_status,
        ]
        if isin:
            row.append(", ".join(isin_map.get(entity.lei, [])))
        table.add_row(*row)
    console.print(table)


@app.command()
def status(
    db: DbPathOption = DEFAULT_DB_PATH,
) -> None:
    """Show database status: record counts and data freshness."""
    if not db.exists():
        console.print(f"[red]Database not found at {db}. Run 'gleif refresh' first.[/]")
        raise typer.Exit(code=1)

    con = get_connection(db)
    try:
        rows = get_status(con)
    finally:
        con.close()

    if not rows:
        console.print("[yellow]No data loaded yet. Run 'gleif refresh' first.[/]")
        raise typer.Exit(code=1)

    table = Table(title="GLEIF Database Status")
    table.add_column("Dataset", style="cyan")
    table.add_column("Publish Date", style="green")
    table.add_column("Loaded At", style="blue")
    table.add_column("Records", justify="right", style="bold")

    for dataset_type, publish_date, loaded_at, record_count in rows:
        try:
            dt = DatasetType(dataset_type)
            label = DATASET_LABELS.get(dt, dataset_type)
        except ValueError:
            label = str(dataset_type)
        table.add_row(
            label,
            str(publish_date),
            str(loaded_at)[:19],
            f"{record_count:,}",
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Output rendering
# ---------------------------------------------------------------------------


def _collect_report_leis(report: LEIRelationshipReport) -> list[str]:
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


def _format_isins(isin_map: dict[str, list[str]], lei_code: str) -> str:
    """Format ISINs for a given LEI, or empty string if none."""
    isins = isin_map.get(lei_code, [])
    return ", ".join(isins) if isins else ""


def _render_report(
    report: LEIRelationshipReport,
    *,
    isin_map: dict[str, list[str]] | None = None,
) -> None:
    """Render a full LEI relationship report to the console."""
    entity = report.entity
    isin_map = isin_map or {}

    # Entity info panel
    info_lines = [
        f"[bold]Name:[/]          {entity.legal_name}",
        f"[bold]Status:[/]        {entity.entity_status}",
        f"[bold]Category:[/]      {entity.entity_category or 'N/A'}",
        f"[bold]Jurisdiction:[/]  {entity.legal_jurisdiction or 'N/A'}",
        f"[bold]Legal Addr:[/]    "
        f"{entity.legal_address_city or ''}, "
        f"{entity.legal_address_country or ''}",
        f"[bold]HQ Addr:[/]       "
        f"{entity.hq_address_city or ''}, "
        f"{entity.hq_address_country or ''}",
        f"[bold]Reg. Status:[/]   {entity.registration_status}",
    ]
    entity_isins = _format_isins(isin_map, entity.lei)
    if entity_isins:
        info_lines.append(f"[bold]ISINs:[/]         {entity_isins}")
    console.print(
        Panel(
            "\n".join(info_lines),
            title=f"[bold cyan]{entity.lei}[/]",
            border_style="cyan",
        )
    )

    # Direct parent
    if report.direct_parent:
        _render_parent_section("Direct Parent", report.direct_parent, isin_map)
    else:
        console.print("[dim]Direct Parent: None[/]")

    # Ultimate parent
    if report.ultimate_parent:
        _render_parent_section("Ultimate Parent", report.ultimate_parent, isin_map)
    else:
        console.print("[dim]Ultimate Parent: None[/]")

    # Children
    if report.children:
        _render_related_table("Children", report.children, isin_map)
    else:
        console.print("[dim]Children: None[/]")

    # Siblings
    if report.siblings:
        _render_related_table("Siblings", report.siblings, isin_map)
    else:
        console.print("[dim]Siblings: None[/]")

    # Other relationships
    if report.other_relationships:
        _render_related_table(
            "Other Relationships", report.other_relationships, isin_map
        )

    # Reporting exceptions
    if report.reporting_exceptions:
        table = Table(title="Reporting Exceptions", border_style="yellow")
        table.add_column("Category", style="yellow")
        table.add_column("Reason")
        table.add_column("Reference")
        for exc in report.reporting_exceptions:
            table.add_row(
                exc.exception_category,
                exc.exception_reason or "",
                exc.exception_reference or "",
            )
        console.print(table)


def _render_parent_section(
    title: str,
    parent: object,
    isin_map: dict[str, list[str]] | None = None,
) -> None:
    """Render a parent entity as a compact line."""
    from gleif.models import EntityInfo  # noqa: PLC0415

    if not isinstance(parent, EntityInfo):
        return
    line = (
        f"[bold]{title}:[/] [cyan]{parent.lei}[/] | "
        f"{parent.legal_name} | {parent.entity_status} | "
        f"{parent.legal_jurisdiction or 'N/A'}"
    )
    parent_isins = _format_isins(isin_map or {}, parent.lei)
    if parent_isins:
        line += f" | ISINs: {parent_isins}"
    console.print(line)


def _render_related_table(
    title: str,
    entities: list[RelatedEntity],
    isin_map: dict[str, list[str]] | None = None,
) -> None:
    """Render a list of related entities as a Rich table."""
    isin_map = isin_map or {}
    show_isins = bool(isin_map)

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
            row.append(_format_isins(isin_map, ent.lei))
        table.add_row(*row)
    console.print(table)


def _format_node_label(
    node: object,
    isin_map: dict[str, list[str]],
) -> str:
    """Format a single hierarchy node label for tree display."""
    from gleif.models import HierarchyNode  # noqa: PLC0415

    if not isinstance(node, HierarchyNode):
        return str(node)
    parts = [f"[cyan]{node.lei}[/]"]
    if node.legal_name:
        parts.append(f"[bold]{node.legal_name}[/]")
    details = []
    if node.legal_jurisdiction:
        details.append(node.legal_jurisdiction)
    if node.entity_status:
        details.append(node.entity_status)
    if details:
        parts.append(f"({', '.join(details)})")
    isins = _format_isins(isin_map, node.lei)
    if isins:
        parts.append(f"[green]ISINs: {isins}[/]")
    return " ".join(parts)


def _render_tree(
    group: CorporateGroup,
    *,
    isin_map: dict[str, list[str]] | None = None,
) -> None:
    """Render a corporate group as a Rich tree with DAG-aware dedup."""
    from gleif.models import HierarchyNode  # noqa: PLC0415

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
            branch = parent_tree.add(_format_node_label(child, isin_map))
            _add_children(branch, child.lei, seen)

    # The root node is at depth 0.
    root_nodes = children_map.get(None, [])
    if not root_nodes:
        console.print("[yellow]No hierarchy data found.[/]")
        return

    root = root_nodes[0]
    seen: set[str] = {root.lei}
    rich_tree = Tree(_format_node_label(root, isin_map))
    _add_children(rich_tree, root.lei, seen)
    console.print(rich_tree)
