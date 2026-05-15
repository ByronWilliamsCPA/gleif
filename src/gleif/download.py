"""Asynchronous downloader for GLEIF golden copy datasets.

GLEIF publishes the three Level 1 and Level 2 golden copy datasets as
ZIP archives at:

    https://goldencopy.gleif.org/api/v2/golden-copies/publishes/<type>/latest.csv

where ``<type>`` is one of ``lei2``, ``rr``, or ``repex`` (see
:class:`gleif.constants.DatasetType`). Each ZIP contains a single
CSV file whose filename encodes the publish date.

This module performs an HTTP HEAD request to read the
``x-gleif-publish-date`` header, compares it against a marker file
in the local data directory, and skips the download when the local
copy is current. When the local copy is stale (or ``force=True``)
the archive is streamed to disk, the embedded CSV is extracted, and
the freshness marker is updated.

Public surface:
    * :class:`DownloadResult` - returned for each downloaded dataset.
    * :func:`download_dataset` - download a single dataset.
    * :func:`download_all` - download all three datasets concurrently.
    * :func:`find_extracted_csv` - look up the latest extracted CSV
      for a dataset type.
    * :func:`read_local_publish_date` - read the cached publish-date
      marker.
"""

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
    """Result of downloading and extracting a single dataset.

    Returned by :func:`download_dataset` and (in a list) by
    :func:`download_all`. Also accepted as input by
    :func:`gleif.db.load_all`.

    Attributes:
        csv_path: Filesystem path to the extracted CSV.
        publish_date: Value of the GLEIF ``x-gleif-publish-date``
            header for the downloaded archive (e.g. ``"2024-06-15"``)
            or ``"unknown"`` if the header was missing.
        dataset_type: Which dataset this result corresponds to.
        record_label: Human-readable label, e.g.
            ``"Level 1 - LEI Records"``.
    """

    csv_path: Path
    publish_date: str
    dataset_type: DatasetType
    record_label: str


def _publish_date_marker(data_dir: Path, dataset_type: DatasetType) -> Path:
    """Return the path of the freshness marker file for a dataset."""
    return data_dir / f"{dataset_type.value}_publish_date.txt"


def read_local_publish_date(data_dir: Path, dataset_type: DatasetType) -> str | None:
    """Read the cached publish date for a previously downloaded dataset.

    The marker is written by :func:`download_dataset` after each
    successful download and is used both for freshness checking
    on subsequent runs and by the ``gleif load`` command (which
    needs the publish date but does not re-contact GLEIF).

    Args:
        data_dir: Directory where downloaded data is stored.
        dataset_type: Which dataset's marker to read.

    Returns:
        The publish date string, or ``None`` if no marker exists
        for this dataset (i.e. the dataset has never been
        downloaded into ``data_dir``).
    """
    marker = _publish_date_marker(data_dir, dataset_type)
    if marker.exists():
        return marker.read_text().strip()
    return None


def _write_local_publish_date(
    data_dir: Path, dataset_type: DatasetType, publish_date: str
) -> None:
    """Persist the publish date for a freshly downloaded dataset."""
    marker = _publish_date_marker(data_dir, dataset_type)
    marker.write_text(publish_date)


def find_extracted_csv(data_dir: Path, dataset_type: DatasetType) -> Path | None:
    """Find the most recent extracted CSV for a dataset type.

    GLEIF CSV filenames follow the pattern
    ``<YYYYMMDD-HHMM>-gleif-goldencopy-<type>-<full|delta>.csv``;
    this function returns the lexicographically last match, which
    corresponds to the most recent publish.

    Args:
        data_dir: Directory containing extracted CSVs.
        dataset_type: Which dataset to look up.

    Returns:
        Path to the most recent CSV, or ``None`` if none is present
        in ``data_dir``.
    """
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

    Issues a HEAD request to the dataset URL (see
    :data:`gleif.constants.DATASET_URLS`) to read the
    ``x-gleif-publish-date`` header and ``content-length``. If the
    local data directory already contains a CSV from the same
    publish date and ``force`` is ``False``, the existing file is
    returned unchanged. Otherwise the ZIP is streamed in 64 KiB
    chunks via an ``httpx.AsyncClient`` (10-minute timeout),
    extracted into ``data_dir``, and the freshness marker is
    updated. The ZIP file is removed after extraction to save disk
    space.

    Propagates ``httpx.HTTPStatusError`` for non-2xx HTTP responses
    (e.g. 404 if the dataset URL changes, 503 if GLEIF is
    rate-limiting), ``httpx.RequestError`` for network-level
    failures (DNS, connection timeout, read timeout), and
    ``ValueError`` from :func:`_extract_zip` if the downloaded
    archive is malformed.

    Args:
        dataset_type: Which dataset to download.
        data_dir: Directory to store the downloaded ZIP and the
            extracted CSV. Created if it does not exist.
        force: If ``True``, re-download even when the local CSV is
            already current.
        progress: Optional Rich ``Progress`` instance for visual
            progress reporting. When supplied, a task is added per
            dataset and updated as bytes arrive.

    Returns:
        DownloadResult with the path to the extracted CSV and the
        remote publish date.
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

    GLEIF archives always contain exactly one CSV. This helper also
    guards against zip-slip path traversal by checking that the
    resolved destination stays inside ``extract_dir``.

    Args:
        zip_path: Path to the ZIP file.
        extract_dir: Directory to extract into.

    Returns:
        Path to the extracted CSV file.

    Raises:
        ValueError: If no CSV is present in the archive, or if the
            archive contains a path-traversal attempt.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
        if not csv_names:
            msg = f"No CSV file found in {zip_path}"
            raise ValueError(msg)
        csv_name = csv_names[0]
        dest = (extract_dir / csv_name).resolve()
        if not dest.is_relative_to(extract_dir.resolve()):
            msg = f"Path traversal attempt detected: {csv_name}"
            raise ValueError(msg)
        zf.extract(csv_name, extract_dir)
        return extract_dir / csv_name


async def download_all(
    data_dir: Path,
    *,
    force: bool = False,
) -> list[DownloadResult]:
    """Download all three GLEIF golden copy datasets concurrently.

    Schedules one :func:`download_dataset` coroutine per entry in
    :class:`gleif.constants.DatasetType` and awaits them with
    ``asyncio.gather``. Progress is reported via a shared Rich
    ``Progress`` instance.

    Any error raised by :func:`download_dataset` propagates from
    ``asyncio.gather``: ``httpx.HTTPStatusError`` for non-2xx HTTP
    responses, ``httpx.RequestError`` for network failures, or
    ``ValueError`` for a malformed archive. ``asyncio.gather``
    re-raises the first error and cancels the remaining tasks.

    Args:
        data_dir: Directory to store downloaded ZIPs and extracted
            CSVs. Created if it does not exist.
        force: If ``True``, re-download every dataset even when the
            local copy is already current.

    Returns:
        A list of :class:`DownloadResult`, one per dataset, in the
        order defined by :class:`gleif.constants.DatasetType`.
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
