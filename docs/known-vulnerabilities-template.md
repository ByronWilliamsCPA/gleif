# Known Vulnerabilities Template

Use this template when adding a new entry to
[known-vulnerabilities.md](known-vulnerabilities.md). One row per accepted
vulnerability. Keep the file's table headers exactly as shown so the
documented and committed tables stay aligned.

## Required columns

| Column | What to write | Example |
|--------|---------------|---------|
| ID | Authoritative advisory ID (PYSEC, GHSA, CVE) | `PYSEC-2022-42969` |
| Package | Vulnerable package and pinned version | `py 1.11.0` |
| Added | UTC date the entry was added, `YYYY-MM-DD` | `2026-05-15` |
| Reason | Why this is accepted: transitive scope, affected code path, runtime vs dev-only, removal condition | Transitive via `interrogate` (dev-only); affected `py.path.svnwc` not invoked; remove when `interrogate` drops `py`. |
| Next review | UTC date for the next reassessment, `YYYY-MM-DD`, no more than 60 days after `Added` | `2026-07-14` |

## Row template

```markdown
| <ADVISORY-ID> | <package> <version> | YYYY-MM-DD | <one-sentence rationale that covers: transitive vs direct, runtime vs dev-only, why the affected code path is unreachable, and the condition under which this entry should be removed> | YYYY-MM-DD |
```

## Policy reminders

- The OpenSSF release gate blocks releases for any vulnerability older than
  60 days regardless of reassessment status. Set `Next review` strictly less
  than 60 days after `Added`.
- Every entry must be paired with a `[tool.pip-audit] ignore-vuln` line in
  `pyproject.toml` carrying the same ID. Never suppress `pip-audit` output
  without a documented entry here.
- Update the file's "Last reviewed" footer date whenever you edit any row.
- If a vulnerability becomes fixable (e.g., upstream releases a patched
  version), remove the row instead of updating the review date.
