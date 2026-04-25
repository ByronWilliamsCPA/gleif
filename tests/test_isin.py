"""Tests for the ISIN lookup module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from gleif.isin import fetch_isins, fetch_isins_batch


class TestFetchIsins:
    """Tests for single-LEI ISIN lookup."""

    @patch("gleif.isin.httpx.get")
    def test_returns_isins(self, mock_get: MagicMock) -> None:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "type": "isins",
                        "attributes": {
                            "lei": "549300UVN46B3BBDHO85",
                            "isin": "US69608A1088",
                        },
                    }
                ]
            },
        )
        result = fetch_isins("549300UVN46B3BBDHO85")
        assert result == ["US69608A1088"]

    @patch("gleif.isin.httpx.get")
    def test_returns_multiple_isins(self, mock_get: MagicMock) -> None:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "type": "isins",
                        "attributes": {"lei": "ABC", "isin": "US111"},
                    },
                    {
                        "type": "isins",
                        "attributes": {"lei": "ABC", "isin": "US222"},
                    },
                ]
            },
        )
        result = fetch_isins("ABC")
        assert result == ["US111", "US222"]

    @patch("gleif.isin.httpx.get")
    def test_returns_empty_on_no_data(self, mock_get: MagicMock) -> None:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": []},
        )
        result = fetch_isins("NOISINS00000000000001")
        assert result == []

    @patch("gleif.isin.httpx.get")
    def test_returns_empty_on_http_error(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = httpx.HTTPError("timeout")
        result = fetch_isins("TIMEOUT00000000000001")
        assert result == []


class TestFetchIsinsBatch:
    """Tests for batch ISIN lookup."""

    @patch("gleif.isin.httpx.Client")
    def test_batch_returns_map(self, mock_client_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = lambda _: mock_client
        mock_client_cls.return_value.__exit__ = lambda *_args: None

        def mock_get(url: str) -> MagicMock:
            if "LEI_A" in url:
                resp = MagicMock(status_code=200)
                resp.json.return_value = {
                    "data": [
                        {
                            "type": "isins",
                            "attributes": {
                                "lei": "LEI_A",
                                "isin": "US111",
                            },
                        }
                    ]
                }
                resp.raise_for_status = MagicMock()
                return resp
            resp = MagicMock(status_code=200)
            resp.json.return_value = {"data": []}
            resp.raise_for_status = MagicMock()
            return resp

        mock_client.get.side_effect = mock_get

        result = fetch_isins_batch(["LEI_A", "LEI_B"])
        assert result == {"LEI_A": ["US111"]}
        assert "LEI_B" not in result
