# Known Vulnerabilities

| ID | Package | Added | Reason | Next review |
|----|---------|-------|--------|-------------|
| PYSEC-2022-42969 | py 1.11.0 | 2026-05-15 | Transitive via `interrogate` (dev-only). Vulnerability is a regex DoS in `py.path.svnwc` (Subversion working-copy helper); the project does not invoke any `py.path.svnwc` code paths. The `py` package is unmaintained; remove this entry once `interrogate` drops its dependency on `py`. | 2026-07-14 |
| PYSEC-2026-89 | markdown 3.10.2 | 2026-05-21 | Transitive via mkdocs / mkdocs-material / pymdown-extensions (docs-only). No fix is available upstream as of this entry. The runtime CLI never imports markdown; the package is invoked only during `mkdocs build` and `mkdocs serve` against repo-controlled `.md` files. Remove once the upstream advisory is resolved or markdown is no longer reachable. | 2026-07-20 |

Review quarterly. No entry should age past 60 days without reassessment.
By policy, vulnerabilities older than 60 days block releases; review this file
before tagging any release.

Last reviewed: 2026-05-21
