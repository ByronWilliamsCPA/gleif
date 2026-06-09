# 02 - Legacy Code Patterns

Scope: deprecated APIs, superseded idioms, dead/commented code, feature flags, vendored copies across `src/gleif/*.py` (9 modules, 2578 LOC) and `tests/`. HEAD 7fd3cb5. Read-only.

## Assessment

Near-clean. The codebase passes CI Ruff (`uv run ruff check .` -> "All checks passed!") and the full legacy rule sweep (`UP,FA,SIM,PERF,RUF,ERA,PTH,FLY,C4,PIE`) reports a single nit. Modern idioms throughout: every module carries `from __future__ import annotations` except `__init__.py` (docstring-only, no code), no `typing.List/Dict/Optional/Union`, no `%`/`.format` string formatting, pathlib everywhere (the one `os`-adjacent reference is `zip_path.open`, a Path method, not `os.path`). HTTP is httpx (sync + async), not requests/urllib. No deprecated stdlib (`utcnow`, `pkg_resources`, `distutils`, `imp`, `get_event_loop`, `cgi`/`telnetlib`/`imghdr`). No commented-out code, TODO/FIXME/HACK markers, feature flags, env toggles, or vendored copies. No dead private helpers. Constants live once in `constants.py`; no cross-file duplication.

One latent staleness: a `# noqa` directive guarding a Ruff preview rule the project does not enable.

## Findings

### LEG-01: Stale `noqa` for non-enabled preview rule PLC0415

- Severity: Low
- Effort: S (<1day)
- Files: `src/gleif/cli.py:105`
- Evidence: line 105 reads
  `from gleif.download import (  # noqa: PLC0415 -- load-command-only symbols`.
  PLC0415 (import-outside-top-level) is a Pylint-derived **preview** rule. Project config (`pyproject.toml` lint.select has `PL` but no `preview = true`), so PLC0415 never fires: `uv run ruff check --select PLC0415 src/gleif/cli.py` -> "All checks passed!". Under a narrowed `--select RUF` run, RUF100 flags it: `Unused noqa directive (non-enabled: PLC0415) --> src/gleif/cli.py:105:35`. The full CI run does not flag it (ruff treats it as a recognized-but-disabled code), so this is latent, not a CI failure.
- Recommendation: Keep the guard if the team plans to enable PL preview later (the local import is intentional: load-command-only symbols, avoids import cost on other CLI paths), or drop the inline directive since the rule is inactive. No change to the import itself needed.

## Clean areas (command evidence)

- Deprecated stdlib/library APIs: none. `grep -rnE "utcnow|pkg_resources|import imp|distutils|get_event_loop|cgi\.|telnetlib|imghdr|smtpd" src/gleif/` -> no matches.
- Legacy typing: none. grep for `typing.List/Dict/Optional/Union/Tuple/Set` and `List[`/`Optional[` -> no matches; only `Annotated` and `TYPE_CHECKING` imported.
- `from __future__ import annotations`: present in all 8 code modules; absent only in `__init__.py` (no executable code, not a finding).
- String formatting: no `%` or `.format()`. `grep -rn "\.format(\|%[sd]" src/gleif/` -> no matches; f-strings used.
- pathlib vs os.path: pathlib throughout; `os.path` never used. PTH rule sweep clean.
- Commented-out / dead code: `uv run ruff check --select ERA .` -> "All checks passed!"; manual grep for commented code lines -> no matches.
- Markers: `grep -rniE "TODO|FIXME|XXX|HACK|DEPRECATED|legacy|vendored|temporary|workaround"` -> only domain hits (GLEIF "ConformityFlag" column), no code markers.
- Feature flags / toggles / env switches: none. `grep -rniE "getenv|environ|if False|FLAG|TOGGLE"` -> only domain data ("conformity_flag").
- Vendored copies: none; httpx/duckdb/typer are declared deps.
- Idiom rules (SIM/PERF/C4/PIE/FLY/FURB) on `src/gleif/`: "All checks passed!".
- Tests: `uv run ruff check --select UP,FA,SIM,PERF,RUF,ERA,PTH,FLY,C4,PIE tests/` -> "All checks passed!". `unittest.mock.patch` used in `test_isin.py` (standard mocking, not legacy).
