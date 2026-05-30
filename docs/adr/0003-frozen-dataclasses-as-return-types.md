# 0003. Frozen dataclasses as query return types

Status: accepted

## Context

The query layer (`queries.py`) returns structured results to the CLI and to
library callers. Raw DuckDB tuples are positional and untyped, which is error
prone at the call site and opaque to the type checker.

## Decision

Return frozen dataclasses defined in `models.py` (`EntityInfo`,
`RelatedEntity`, `HierarchyNode`, `CorporateGroup`, `LEIRelationshipReport`,
`ReportingException`). Each query maps rows to these types at the boundary.

## Alternatives considered

- Raw tuples: compact but positional; a column reorder silently breaks callers.
- Plain dicts: flexible but untyped, so basedpyright cannot check field access.
- Pydantic models: richer validation, but the data is already validated at load
  and the runtime dependency is not warranted for read-only result shaping.

## Consequences

- Callers get named, type-checked fields; basedpyright (strict) verifies access.
- `frozen=True` prevents attribute rebinding but does not deep-freeze contained
  lists, so the models are not hashable or deeply immutable; this is documented
  in `models.py`.
