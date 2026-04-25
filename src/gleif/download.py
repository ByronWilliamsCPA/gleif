"""Download and extract GLEIF golden copy datasets."""

from __future__ import annotations

import asyncio
import zipfile
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TransferSpeedColumn,
)

from gleif.constants import DATASET_LABELS, DATASET_URLS, DatasetType

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class DownloadResult:
    """Result of downloading and extracting a single dataset."""

    csv_path: Path
    publish_date: str
    dataset_type: DatasetType
    record_label: str


def _publish_date_marker(data_dir: Path, dataset_type: DatasetType) -> Path:
    return data_dir / f"{dataset_type.value}_publish_date.txt"


def read_local_publish_date(data_dir: Path, dataset_type: DatasetType) -> str | None:
    marker = _publish_date_marker(data_dir, dataset_type)
    if marker.exists():
        return marker.read_text().strip()
    return None


def _write_local_publish_date(
    data_dir: Path, dataset_type: DatasetType, publish_date: str
) -> None:
    marker = _publish_date_marker(data_dir, dataset_type)
    marker.write_text(publish_date)


def find_extracted_csv(data_dir: Path, dataset_type: DatasetType) -> Path | None:
    """Find an already-extracted CSV for this dataset type."""
    pattern = f"*-gleif-goldencopy-{dataset_type.value}-*"
    csvs = sorted(data_dir.glob(pattern))
    if csvs:
        return csvs[-1]
    return None


async def download_dataset(
    dataset_type: DatasetType,
    data_dir: Path,
    *,
    force: bool = False,
    progress: Progress | None = None,
) -> DownloadResult:
    """Download and extract a single GLEIF golden copy dataset.

    Args:
        dataset_type: Which dataset to download.
        data_dir: Directory to store downloaded and extracted files.
        force: Re-download even if local copy is current.
        progress: Optional Rich progress bar instance.

    Returns:
        DownloadResult with path to the extracted CSV.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    url = DATASET_URLS[dataset_type]
    label = DATASET_LABELS[dataset_type]

    async with httpx.AsyncClient(follow_redirects=True, timeout=600.0) as client:
        # HEAD request to check publish date and content length
        head_resp = await client.head(url)
        head_resp.raise_for_status()
        remote_publish_date = head_resp.headers.get("x-gleif-publish-date", "unknown")
        content_length = int(head_resp.headers.get("content-length", 0))

        # Check freshness
        if not force:
            local_date = read_local_publish_date(data_dir, dataset_type)
            existing_csv = find_extracted_csv(data_dir, dataset_type)
            if (
                local_date == remote_publish_date
                and existing_csv is not None
                and existing_csv.exists()
            ):
                return DownloadResult(
                    csv_path=existing_csv,
                    publish_date=remote_publish_date,
                    dataset_type=dataset_type,
                    record_label=label,
                )

        # Stream download
        zip_path = data_dir / f"{dataset_type.value}.csv.zip"
        task_id = None
        if progress is not None:
            task_id = progress.add_task(
                f"[cyan]{label}",
                total=content_length or None,
            )

        async with client.stream("GET", url) as response:
            response.raise_for_status()
            with zip_path.open("wb") as fh:
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    fh.write(chunk)
                    if progress is not None and task_id is not None:
                        progress.update(task_id, advance=len(chunk))

        if progress is not None and task_id is not None:
            progress.update(task_id, description=f"[green]{label} (extracting)")

        # Extract CSV from ZIP
        csv_path = _extract_zip(zip_path, data_dir)

        # Update freshness marker
        _write_local_publish_date(data_dir, dataset_type, remote_publish_date)

        # Clean up ZIP to save disk space
        zip_path.unlink(missing_ok=True)

        return DownloadResult(
            csv_path=csv_path,
            publish_date=remote_publish_date,
            dataset_type=dataset_type,
            record_label=label,
        )


def _extract_zip(zip_path: Path, extract_dir: Path) -> Path:
    """Extract the single CSV from a GLEIF ZIP archive.

    Args:
        zip_path: Path to the ZIP file.
        extract_dir: Directory to extract into.

    Returns:
        Path to the extracted CSV file.

    Raises:
        ValueError: If the ZIP doesn't contain exactly one CSV.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
        if not csv_names:
            msg = f"No CSV file found in {zip_path}"
            raise ValueError(msg)
        csv_name = csv_names[0]
        zf.extract(csv_name, extract_dir)
        return extract_dir / csv_name


async def download_all(
    data_dir: Path,
    *,
    force: bool = False,
) -> list[DownloadResult]:
    """Download all three GLEIF golden copy datasets.

    Args:
        data_dir: Directory to store downloaded files.
        force: Re-download even if local copies are current.

    Returns:
        List of DownloadResult for each dataset.
    """
    progress = Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
    )

    with progress:
        tasks = [
            download_dataset(dt, data_dir, force=force, progress=progress)
            for dt in DatasetType
        ]
        return await asyncio.gather(*tasks)
