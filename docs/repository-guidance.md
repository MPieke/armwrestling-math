# Repository Guidance

## Branch Naming

Do not commit implementation work directly to `main`. Create one branch per
Linear issue using this format:

```text
<type>/<CODE>-<kebab-case-description>
```

Examples:

```text
feat/MPI-13-document-ingestion-architecture
fix/MPI-14-guard-integration-database
docs/MPI-15-update-data-model-guide
```

Use a Conventional Commit type for `<type>`: `feat`, `fix`, `docs`, `refactor`,
`test`, `chore`, or `build`.

## Commit Naming

Every commit must use this format:

```text
<type>(<CODE>): <imperative description>
```

Examples:

```text
feat(MPI-13): document generic ingestion architecture
fix(MPI-14): guard integration database
docs(MPI-15): update data model guide
```

`CODE` is the Linear issue identifier. The description is concise, imperative,
and lowercase unless it contains a proper name or required identifier.
