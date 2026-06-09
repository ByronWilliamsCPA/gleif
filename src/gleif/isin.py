"""Fetch ISIN mappings from the GLEIF REST API.

ISINs (International Securities Identification Numbers) are not part
of the golden copy CSV files. Instead, GLEIF exposes them through a
JSON:API endpoint:

    GET https://api.gleif.org/api/v1/lei-records/<LEI>/isins

The response follows the JSON:API envelope: a top-level ``"data"``
array of objects with an ``"attributes"`` dict containing an
``"isin"`` field.

The helpers below are intended for *interactive* enrichment of
already-known LEIs (the CLI surfaces them behind the ``--isin``
flag). They are not designed for bulk ETL: each LEI requires a
separate HTTP request, and GLEIF rate-limits the public API.

Error handling: every ``httpx.HTTPError`` (network, 4xx, 5xx) is
swallowed and yields an empty result for the affected LEI. This is
deliberate - one LEI without ISINs should not abort an entire
enrichment pass. Note that JSON decoding errors are not caught:
GLEIF's REST API has always returned valid JSON on 2xx responses,
so a ``json.JSONDecodeError`` here would indicate an API contract
change rather than expected operating conditions.
"""

from __future__ import annotations

from typing import Any

import httpx

from gleif.constants import GLEIF_API_BASE, ISIN_REQUEST_TIMEOUT


def _extract_isins(payload: Any) -> list[str]:
    """Pull the ISIN strings out of a GLEIF JSON:API response body.

    Args:
        payload (Any): Decoded JSON from an ``/isins`` response. Expected
            to carry a top-level ``"data"`` array of objects with an
            ``"attributes"`` dict containing an ``"isin"`` field.

    Returns:
        list[str]: List of ISIN strings; empty if ``data`` is absent or no
        entry carries an ``isin``.
    """
    data = payload.get("data", [])
    return [
        item["attributes"]["isin"]
        for item in data
        if item.get("attributes", {}).get("isin")
    ]


def fetch_isins(lei: str) -> list[str]:
    """Fetch ISINs associated with an LEI from the GLEIF REST API.

    Hits ``GET {GLEIF_API_BASE}/{lei}/isins`` with a 10-second
    timeout. Any HTTP error (network failure, 4xx, 5xx) is caught
    and treated as "no ISINs".

    Args:
        lei (str): The 20-character LEI to look up.

    Returns:
        list[str]: List of ISIN strings. Empty list if the LEI has no
        associated ISINs, the LEI is unknown to GLEIF, or any HTTP
        error occurs.
    """
    try:
        response = httpx.get(
            f"{GLEIF_API_BASE}/{lei}/isins",
            timeout=ISIN_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return []

    return _extract_isins(response.json())


def fetch_isins_batch(leis: list[str]) -> dict[str, list[str]]:
    """Fetch ISINs for multiple LEIs sequentially over one HTTP client.

    Reuses a single ``httpx.Client`` (HTTP keep-alive) and issues
    one request per LEI. LEIs with HTTP errors or no ISINs are
    omitted from the result.

    Args:
        leis (list[str]): List of 20-character LEIs to look up.

    Returns:
        dict[str, list[str]]: Mapping of LEI to list of ISINs. LEIs without
        any ISINs (or for which the lookup failed) are not present as keys,
        so ``result.get(lei, [])`` is the safe access pattern.
    """
    results: dict[str, list[str]] = {}
    with httpx.Client(timeout=ISIN_REQUEST_TIMEOUT) as client:
        for lei_code in leis:
            try:
                response = client.get(
                    f"{GLEIF_API_BASE}/{lei_code}/isins",
                )
                response.raise_for_status()
                isins = _extract_isins(response.json())
                if isins:
                    results[lei_code] = isins
            except httpx.HTTPError:
                continue
    return results
