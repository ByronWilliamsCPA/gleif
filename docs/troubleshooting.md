# Troubleshooting

## DuckDB file locked

**Symptom:** The command fails immediately with an error similar to:

```text
duckdb.duckdb.IOException: Could not set lock on file
"~/.local/share/gleif/gleif.duckdb": Conflicting lock is held
```

**Cause:** DuckDB allows only one writer connection at a time. If a previous
`gleif` command was interrupted without closing cleanly, or if another process
(such as a DuckDB shell session or a Jupyter notebook) still has the file open,
subsequent write operations will be blocked.

**Fix:**

1. Identify and close the process holding the lock:

    ```bash
    lsof ~/.local/share/gleif/gleif.duckdb
    ```

2. Close or kill the process, then retry the command.

!!! note
    Read-only tools such as DB browsers can sometimes hold a shared lock that
    blocks writes. Close them before running `gleif load` or `gleif refresh`.

---

## Download timeout or partial failure

**Symptom:** The download progress bar stalls, the terminal shows a network
error, or the command exits before all three datasets are downloaded:

```text
httpx.ReadTimeout: timed out while receiving response
```

**Cause:** The Level 1 LEI file is approximately 800 MB compressed. A slow or
unstable connection may time out mid-stream, leaving a partial ZIP on disk.

**Fix:**

Re-run the download. The freshness check compares the `x-gleif-publish-date`
header against a local marker file; because the partial download did not write
a valid marker, the command will restart the download cleanly:

```bash
uv run gleif download
```

To force a full re-download regardless of any existing marker:

```bash
uv run gleif download --force
```

!!! tip
    Run the download on a wired connection or a machine with a stable network
    connection. On typical broadband (4-5 MB/s), all three datasets take
    5-10 minutes.

---

## CSV not found (load before download)

**Symptom:** Running `gleif load` without having downloaded the data first
produces an error and exits with code 1:

```text
No extracted CSV found for Level 1 - LEI Records. Run 'gleif download' first.
```

**Cause:** `gleif load` expects the extracted CSVs to already exist in the
data directory. It does not download them.

**Fix:**

Run `gleif download` (or `gleif refresh`, which combines both steps) before
`gleif load`:

```bash
# Download only
uv run gleif download

# Or download + load in one step (recommended)
uv run gleif refresh
```

---

## Disk space

**Symptom:** The load command fails partway through, or the database file is
unexpectedly small after loading. The error may mention disk space:

```text
IOException: No space left on device
```

**Cause:** The fully loaded DuckDB file is approximately 1-2 GB. Combined with
the extracted CSVs (roughly 900 MB in total), you need at least 3 GB of free
space in the target partition during a refresh.

**Check available space:**

```bash
df -h ~/.local/share/gleif/
```

**Fix:**

Free up disk space, then re-run the load:

```bash
uv run gleif load
```

To store the database on a different partition, use `--db` and `--data-dir`:

```bash
uv run gleif refresh --data-dir /mnt/large-disk/gleif --db /mnt/large-disk/gleif.duckdb
```

!!! warning
    If a `gleif.duckdb` file exists but the load was interrupted, the file may
    be in a partially written state. Delete it and reload to ensure a clean
    database:

    ```bash
    rm ~/.local/share/gleif/gleif.duckdb
    uv run gleif load
    ```

---

## Proxy and TLS issues

**Symptom:** Downloads fail with a TLS or SSL certificate error:

```text
httpx.ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed
```

**Cause:** Corporate networks that perform TLS inspection (MITM proxies) can
present a self-signed or corporate root certificate that Python's default trust
store does not recognize.

**Fix:**

Set the `SSL_CERT_FILE` environment variable to point to your corporate CA
bundle:

```bash
export SSL_CERT_FILE=/path/to/corporate-ca-bundle.pem
uv run gleif refresh
```

If your proxy requires explicit configuration, set the standard proxy
environment variables before running any command:

```bash
export HTTPS_PROXY=http://proxy.example.com:8080
uv run gleif refresh
```

!!! warning
    Do not disable SSL verification entirely. Passing `verify=False` to httpx
    removes all certificate validation, which exposes the connection to
    man-in-the-middle attacks. Contact your network team for the correct CA
    bundle instead.

---

## Stale or missing data

**Symptom:** LEI lookups return no results, or results appear out of date
relative to the GLEIF registry. There is no visible error.

**Cause:** GLEIF publishes updated golden copy files daily. If `gleif refresh`
has not been run recently, the local database may be days or weeks behind the
current registry.

**Check data freshness:**

```bash
uv run gleif status
```

Sample output:

```text
 Dataset                      Publish Date   Loaded At              Rows
 Level 1 - LEI Records        2026-04-25     2026-04-26 07:31:02    2,381,240
 Level 2 - Relationships      2026-04-25     2026-04-26 07:33:15    4,012,887
 Level 2 - Reporting Exc.     2026-04-25     2026-04-26 07:34:02      521,044
```

**Fix:**

Update to the latest published data:

```bash
uv run gleif refresh
```

`refresh` checks the `x-gleif-publish-date` header before downloading. If your
local copy is already current, it exits quickly without re-downloading.

!!! note
    GLEIF typically publishes at approximately 08:00 UTC. Data from the current
    calendar day may not yet be available if you run `gleif refresh` shortly
    after midnight UTC.

---

## Database does not exist yet

The behavior differs depending on which command you run:

**`gleif status` on a missing database:** The command checks whether the
database file exists and exits immediately with:

```text
Database not found at <path>. Run 'gleif refresh' first.
```

**`gleif lei` / `gleif name` on a missing or empty database:** These commands
do not check for the database file before connecting. `duckdb.connect()`
silently creates an empty file if none exists, so queries return empty results
rather than an error. `gleif lei` reports the LEI as not found, and `gleif name`
returns an empty results list.

**Fix:**

Run the initial load before querying:

```bash
uv run gleif refresh
```

See [Getting Started](getting-started.md) for full first-run instructions.
