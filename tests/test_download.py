"""Tests for the download module."""

from __future__ import annotations

import asyncio
import io
import zipfile
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from gleif.constants import DatasetType
from gleif.download import (
    DownloadResult,
    download_all,
    download_dataset,
    find_extracted_csv,
    read_local_publish_date,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

_GLEIF_CSV = "20240101-0000-gleif-goldencopy-lei2-full.csv"
_CSV_BODY = b"LEI,Entity.LegalName\nABC,Test\n"


def _zip_bytes(member: str, content: bytes = _CSV_BODY) -> bytes:
    """Return the bytes of a ZIP containing a single ``member`` entry."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(member, content)
    return buf.getvalue()


class _FakeStreamResponse:
    """Minimal async stand-in for an httpx streaming response."""

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    def raise_for_status(self) -> None:
        """No-op; the fake always represents a 2xx response."""
        return

    async def aiter_bytes(self, **_kwargs: object) -> AsyncIterator[bytes]:
        """Yield the preconfigured chunks one at a time."""
        for chunk in self._chunks:
            yield chunk


class _FakeStream:
    """Async context manager yielding a :class:`_FakeStreamResponse`."""

    def __init__(self, chunks: list[bytes]) -> None:
        self._response = _FakeStreamResponse(chunks)

    async def __aenter__(self) -> _FakeStreamResponse:
        return self._response

    async def __aexit__(self, *_args: object) -> None:
        return


def _fake_client(*, publish_date: str, chunks: list[bytes] | None = None) -> MagicMock:
    """Build a MagicMock httpx client with async head and streaming GET."""
    head_resp = MagicMock()
    head_resp.raise_for_status = MagicMock()
    head_resp.headers = {
        "x-gleif-publish-date": publish_date,
        "content-length": "10",
    }
    client = MagicMock()
    client.head = AsyncMock(return_value=head_resp)
    if chunks is not None:
        client.stream = MagicMock(return_value=_FakeStream(chunks))
    return client


def _patch_async_client(mock_client_cls: MagicMock, client: MagicMock) -> None:
    """Wire a patched AsyncClient class to yield ``client`` from ``async with``."""
    mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=client)
    mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)


class TestFindExtractedCsv:
    """Tests for locating the most recent extracted CSV."""

    def test_returns_latest_match(self, tmp_path: Path) -> None:
        (tmp_path / "20240101-0000-gleif-goldencopy-lei2-full.csv").write_text("")
        (tmp_path / "20240202-0000-gleif-goldencopy-lei2-full.csv").write_text("")
        found = find_extracted_csv(tmp_path, DatasetType.LEI)
        assert found is not None
        assert found.name.startswith("20240202")

    def test_returns_none_when_absent(self, tmp_path: Path) -> None:
        assert find_extracted_csv(tmp_path, DatasetType.LEI) is None


class TestPublishDateMarker:
    """Tests for reading the cached publish-date marker."""

    def test_roundtrip(self, tmp_path: Path) -> None:
        (tmp_path / "lei2_publish_date.txt").write_text("2024-06-15")
        assert read_local_publish_date(tmp_path, DatasetType.LEI) == "2024-06-15"

    def test_missing_returns_none(self, tmp_path: Path) -> None:
        assert read_local_publish_date(tmp_path, DatasetType.LEI) is None


class TestDownloadDataset:
    """Tests for download_dataset freshness and streaming logic."""

    @patch("gleif.download.httpx.AsyncClient")
    def test_skips_when_current(
        self, mock_client_cls: MagicMock, tmp_path: Path
    ) -> None:
        existing = tmp_path / _GLEIF_CSV
        existing.write_text("col\n1\n")
        (tmp_path / "lei2_publish_date.txt").write_text("2024-06-15")
        client = _fake_client(publish_date="2024-06-15")
        _patch_async_client(mock_client_cls, client)

        result = asyncio.run(download_dataset(DatasetType.LEI, tmp_path))

        assert result.csv_path == existing
        assert result.publish_date == "2024-06-15"
        client.stream.assert_not_called()

    @patch("gleif.download.httpx.AsyncClient")
    def test_streams_extracts_and_cleans_up(
        self, mock_client_cls: MagicMock, tmp_path: Path
    ) -> None:
        member = "20240301-0000-gleif-goldencopy-lei2-full.csv"
        client = _fake_client(publish_date="2024-09-01", chunks=[_zip_bytes(member)])
        _patch_async_client(mock_client_cls, client)

        result = asyncio.run(download_dataset(DatasetType.LEI, tmp_path, force=True))

        assert result.csv_path.name == member
        assert result.csv_path.exists()
        assert result.publish_date == "2024-09-01"
        assert read_local_publish_date(tmp_path, DatasetType.LEI) == "2024-09-01"
        assert not (tmp_path / "lei2.csv.zip").exists()

    @patch("gleif.download.httpx.AsyncClient")
    def test_rejects_archive_without_csv(
        self, mock_client_cls: MagicMock, tmp_path: Path
    ) -> None:
        client = _fake_client(
            publish_date="2024-09-01", chunks=[_zip_bytes("readme.txt")]
        )
        _patch_async_client(mock_client_cls, client)
        with pytest.raises(ValueError, match="No CSV"):
            asyncio.run(download_dataset(DatasetType.LEI, tmp_path, force=True))

    @patch("gleif.download.httpx.AsyncClient")
    def test_rejects_path_traversal_member(
        self, mock_client_cls: MagicMock, tmp_path: Path
    ) -> None:
        # Extract straight into tmp_path (not a subdir) so the guard is shown
        # to trip on the member name alone: ``../escape.csv`` resolves to
        # tmp_path's parent regardless of how deep tmp_path itself sits.
        client = _fake_client(
            publish_date="2024-09-01", chunks=[_zip_bytes("../escape.csv")]
        )
        _patch_async_client(mock_client_cls, client)
        with pytest.raises(ValueError, match="Path traversal"):
            asyncio.run(download_dataset(DatasetType.LEI, tmp_path, force=True))
        # The escaping member must not be written outside the extract dir.
        assert not (tmp_path.parent / "escape.csv").exists()

    @patch("gleif.download.httpx.AsyncClient")
    def test_propagates_http_status_error(
        self, mock_client_cls: MagicMock, tmp_path: Path
    ) -> None:
        # download_dataset documents that httpx.HTTPStatusError propagates
        # (e.g. a 404 if the dataset URL changes). The HEAD raise_for_status
        # is the first place it can surface; assert it is not swallowed.
        request = httpx.Request("HEAD", "https://example.test/lei2")
        head_resp = MagicMock()
        head_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=request,
            response=httpx.Response(404, request=request),
        )
        client = MagicMock()
        client.head = AsyncMock(return_value=head_resp)
        _patch_async_client(mock_client_cls, client)
        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(download_dataset(DatasetType.LEI, tmp_path, force=True))
        client.stream.assert_not_called()

    @patch("gleif.download.httpx.AsyncClient")
    def test_propagates_bad_zip_file(
        self, mock_client_cls: MagicMock, tmp_path: Path
    ) -> None:
        # download_dataset documents that zipfile.BadZipFile propagates when
        # the streamed archive is not a valid ZIP. Feed non-ZIP bytes and
        # confirm the error is raised rather than caught and hidden.
        client = _fake_client(
            publish_date="2024-09-01", chunks=[b"this is not a zip archive"]
        )
        _patch_async_client(mock_client_cls, client)
        with pytest.raises(zipfile.BadZipFile):
            asyncio.run(download_dataset(DatasetType.LEI, tmp_path, force=True))


class TestDownloadAll:
    """Tests for the concurrent download_all orchestration."""

    @patch("gleif.download.download_dataset")
    def test_gathers_all_datasets(
        self, mock_download: MagicMock, tmp_path: Path
    ) -> None:
        mock_download.side_effect = [
            DownloadResult(
                csv_path=tmp_path / f"{dt.value}.csv",
                publish_date="2024-01-01",
                dataset_type=dt,
                record_label=dt.value,
            )
            for dt in DatasetType
        ]
        results = asyncio.run(download_all(tmp_path))
        assert [r.dataset_type for r in results] == list(DatasetType)
        # download_all must schedule exactly one download_dataset per dataset
        # type, each receiving the shared data_dir; assert the orchestration
        # rather than only the gather ordering.
        assert mock_download.call_count == len(list(DatasetType))
        for call in mock_download.call_args_list:
            assert call.args[0] in DatasetType
            assert call.args[1] == tmp_path
