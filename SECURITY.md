# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |

## Reporting a Vulnerability

Please do not open a public GitHub issue for security vulnerabilities.

Use [GitHub private vulnerability reporting](https://github.com/ByronWilliamsCPA/gleif/security/advisories/new)
to submit a report. You will receive a response within 72 hours acknowledging receipt.

If the vulnerability is confirmed, a fix will be prioritized based on severity:

- **Critical / High**: patch released within 7 days
- **Medium**: patch released within 30 days
- **Low**: addressed in the next scheduled release

You will be credited in the release notes unless you request otherwise.

## Scope

This tool downloads and processes publicly available GLEIF data files. It does not
handle authentication credentials, payment data, or personal information beyond
what is present in the GLEIF golden copy datasets (which are public records).

The primary security surface areas are:

- **Dependency vulnerabilities**: tracked with `uv run pip-audit` and OSV Scanner
- **ZIP path traversal**: mitigated in `download.py` via `resolve().is_relative_to()` check before extraction
- **SQL injection**: mitigated by parameterized DuckDB queries in `queries.py`
