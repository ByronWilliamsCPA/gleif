"""Typer CLI for GLEIF golden copy data management and LEI queries.

This module defines the ``gleif`` console script entry point exposed
in ``pyproject.toml`` (``[project.scripts]``). The CLI wraps the
library functions in :mod:`gleif.download`, :mod:`gleif.db`, and
:mod:`gleif.queries` with Rich-rendered output. The render helpers
themselves live in :mod:`gleif.rendering`.

Subcommands
-----------
* ``download`` - fetch the three golden copy archives.
* ``load`` - load already-downloaded CSVs into DuckDB.
* ``refresh`` - download + load in one step.
* ``lei`` - look up an LEI and print its relationship report or
  full hierarchy tree.
* ``name`` - substring search over legal names.
* ``status`` - print row counts and publish dates per dataset.

The ``app`` object is the importable ``typer.Typer`` instance, used
both by the installed script and by the test suite (via
``typer.testing.CliRunner``).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from gleif.constants import (
    DATASET_LABELS,
    DEFAULT_DATA_DIR,
    DEFAULT_DB_PATH,
    LEI_LENGTH,
    MAX_HIERARCHY_DEPTH,
    DatasetType,
)
from gleif.db import get_connection, get_status, load_all
from gleif.download import (
    DownloadResult,
    download_all,
    find_extracted_csv,
    read_local_publish_date,
)
from gleif.isin import fetch_isins_batch
from gleif.queries import get_corporate_group, get_full_report, search_by_name
from gleif.rendering import (
    collect_report_leis,
    console,
    render_report,
    render_tree,
)

app = typer.Typer(
    name="gleif",
    help="GLEIF Golden Copy data loader and LEI relationship query CLI.",
    no_args_is_help=True,
)
_FETCHING_ISINS_MSG = "[dim]Fetching ISINs from GLEIF API...[/]"

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
    results: list[DownloadResult] = []
    for dt in DatasetType:
        csv_path = find_extracted_csv(data_dir, dt)
        if csv_path is None:
            console.print(
                f"[red]No extracted CSV found for {DATASET_LABELS[dt]}. "
                f"Run 'gleif download' first.[/]"
            )
            raise typer.Exit(code=1)
        publish_date = read_local_publish_date(data_dir, dt) or "unknown"
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
        load_all(con, results, on_progress=console.print)
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
        load_all(con, results, on_progress=console.print)
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
    if len(lei_code) != LEI_LENGTH:
        console.print(
            f"[red]Invalid LEI '{lei_code}': must be exactly {LEI_LENGTH} "
            f"characters.[/]"
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
            console.print(_FETCHING_ISINS_MSG)
            isin_map = fetch_isins_batch(all_leis)

        render_tree(group, isin_map=isin_map)
        return

    if report is None:
        console.print(f"[red]LEI '{lei_code}' not found in the database.[/]")
        raise typer.Exit(code=1)

    isin_map_flat: dict[str, list[str]] = {}
    if isin:
        all_leis = collect_report_leis(report)
        console.print(_FETCHING_ISINS_MSG)
        isin_map_flat = fetch_isins_batch(all_leis)

    render_report(report, isin_map=isin_map_flat)


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
        console.print(_FETCHING_ISINS_MSG)
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
