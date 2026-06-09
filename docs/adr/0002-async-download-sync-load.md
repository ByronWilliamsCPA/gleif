# 0002. Async download, synchronous load

Status: accepted

## Context

The download phase fetches three independent ZIP archives over HTTP; the load
phase bulk-inserts the extracted CSVs into a single DuckDB connection. The two
phases have different concurrency characteristics.

## Decision

Download concurrently with `asyncio.gather` over `httpx.AsyncClient`
(`download.py`), then load synchronously, one dataset at a time, over a single
DuckDB connection (`db.py`).

## Alternatives considered

- Async load as well: DuckDB writes through one connection and the bottleneck is
  local disk and the CSV parser, not I/O concurrency, so async adds complexity
  without throughput.
- Fully synchronous download: the three archives are independent network fetches
  that overlap well; serial download leaves bandwidth idle.

## Consequences

- The network-bound phase overlaps the three fetches; the CPU/disk-bound phase
  stays simple and sequential.
- ISIN enrichment (`isin.py`) uses synchronous `httpx` by design: it is
  interactive, per-LEI, and rate-limited by GLEIF, so concurrency buys little.
