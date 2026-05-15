# Known Vulnerabilities

| ID | Package | Added | Reason | Next review |
|----|---------|-------|--------|-------------|
| PYSEC-2022-42969 | py 1.11.0 | 2026-05-15 | Transitive via `interrogate` (dev-only). Vulnerability is a regex DoS in `py.path.svnwc` (Subversion working-copy helper); the project does not invoke any `py.path.svnwc` code paths. The `py` package is unmaintained; remove this entry once `interrogate` drops its dependency on `py`. | 2026-07-15 |

Review quarterly. No entry should age past 60 days without reassessment.
By policy, vulnerabilities older than 60 days block releases; review this file
before tagging any release.

Last reviewed: 2026-05-15
