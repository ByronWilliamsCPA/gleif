"""Fetch ISIN mappings from the GLEIF API."""

from __future__ import annotations

import httpx

GLEIF_API_BASE = "https://api.gleif.org/api/v1/lei-records"
_REQUEST_TIMEOUT = 10.0


def fetch_isins(lei: str) -> list[str]:
    """Fetch ISINs associated with an LEI from the GLEIF API.

    Args:
        lei: The LEI to look up.

    Returns:
        List of ISIN strings, or empty list on error/no data.
    """
    try:
        response = httpx.get(
            f"{GLEIF_API_BASE}/{lei}/isins",
            timeout=_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return []

    data = response.json().get("data", [])
    return [
        item["attributes"]["isin"]
        for item in data
        if item.get("attributes", {}).get("isin")
    ]


def fetch_isins_batch(leis: list[str]) -> dict[str, list[str]]:
    """Fetch ISINs for multiple LEIs concurrently.

    Args:
        leis: List of LEIs to look up.

    Returns:
        Mapping of LEI to list of ISINs.
    """
    results: dict[str, list[str]] = {}
    with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
        for lei_code in leis:
            try:
                response = client.get(
                    f"{GLEIF_API_BASE}/{lei_code}/isins",
                )
                response.raise_for_status()
                data = response.json().get("data", [])
                isins = [
                    item["attributes"]["isin"]
                    for item in data
                    if item.get("attributes", {}).get("isin")
                ]
                if isins:
                    results[lei_code] = isins
            except httpx.HTTPError:
                continue
    return results
