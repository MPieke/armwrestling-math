# Repository Guidance

## Architecture Documentation

Read the relevant document under [`docs/architecture/`](architecture/) before
changing a documented subsystem. The current ingestion architecture is defined
in [`docs/architecture/ingestion.md`](architecture/ingestion.md); the
prediction track (experiment ledger, evaluation protocols, rating/model
computation) is defined separately in
[`docs/architecture/prediction.md`](architecture/prediction.md), since it is
a distinct concern from ingestion that happens to share the same database.

Update the relevant architecture document in the same change when an approved
implementation changes a system boundary, ownership model, data flow,
transaction boundary, or extension workflow. Keep its ASCII diagrams aligned
with the implementation.

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

## Contract Naming

Every software-change contract must make its Linear ticket identifier visible
in both its filename and title:

```text
docs/contracts/<CODE>-<kebab-case-description>.md
# Contract <CODE>: <Title>
```

For example:

```text
docs/contracts/MPI-14-generic-ingestion-test-expansion.md
# Contract MPI-14: Generic Ingestion Test Expansion
```

Keep the `linear_issue: <CODE>` frontmatter field. The filename, heading, and
frontmatter must all use the same ticket identifier.

A meta-contract — one that sequences several already-written contracts
(dependency order, gate conditions, parallelism) rather than implementing a
ticket itself — lives in `docs/meta-contracts/` instead, named after every
ticket code it spans, with a `linear_issues: [<CODE>, ...]` frontmatter list
rather than a single `linear_issue`. It does not replace or duplicate the
verification detail already in the contracts it sequences.

## Contract Precision

A contract is read by someone without full context of the discussion that
produced it. Every claim about scope or a boundary — "read-only," "owns X,"
"cannot modify Y" — must name exactly what it covers: the specific tables,
files, or paths, not left to be inferred from prior discussion or another
document.

## Testing Standards

Tests must prove meaningful behavior, invariants, or failure handling. A
passing test suite is not sufficient if tests only execute code without
asserting the observable contract.

### Test Design

- Prefer tests that verify outcomes at the relevant boundary: returned values,
  persisted records, emitted output, HTTP responses, or CLI exit status.
- Each test must make a specific claim about behavior. Avoid smoke tests that
  only assert that code does not error unless absence of error is itself the
  contract under test.
- Test valid behavior, important failure behavior, and the invariants that
  protect data integrity or user-visible correctness.
- Group equivalent invalid inputs into representative cases. Do not duplicate
  integration tests for every spelling of the same validation rule.
- Use table-driven unit tests when many inputs share one validation mechanism.
  Name each case by the behavior it proves.
- Avoid asserting implementation details unless they are the contract. Prefer
  observable behavior over private helper calls, call ordering, or incidental
  internal structure.

### Test-First Workflow

For non-trivial behavior changes governed by a software-change contract, write
and commit the behavior-defining tests before the implementation that makes
them pass.

- The contract's commit breakdown must place each test commit immediately
  before its corresponding implementation commit.
- Run the new tests before implementation and record the expected failure. A
  red test commit is intentionally allowed when its failure demonstrates the
  missing behavior named by the contract.
- The following implementation commit must make those tests pass without
  weakening, deleting, skipping, or replacing their assertions.
- Add CI discovery and execution for a new test layer before considering the
  feature complete. A local-only test suite is incomplete.
- Test-first does not mean testing private implementation structure. Tests
  still define observable behavior at the smallest appropriate boundary.
- Generated code is exempt from hand-written unit tests, but the schema,
  generator inputs, and generated boundary must be covered by integration or
  reproducibility checks.

### Test Layers

- Unit tests cover deterministic, in-memory business rules: parsing, mapping,
  validation, calculations, and error classification.
- Integration tests cover real boundaries: PostgreSQL, migrations, generated
  queries, filesystem, subprocesses, HTTP clients, or other external services.
- End-to-end tests cover a complete user or operator flow only when the
  repository exposes such a boundary, such as a CLI command, API, or UI.
- Do not use a database integration test where a unit test can prove a pure
  rule. Add integration coverage where correctness depends on transactions,
  constraints, serialization, migrations, or generated queries.

### Data Integrity And Failure Tests

For persistence workflows, tests must establish the intended atomicity:

- invalid input rejected by a Go validation gate must not reach database work;
- failures during persistence must not leave partial canonical data;
- where failure auditing is intentional, assert both the preserved canonical
  state and the expected audit record;
- replay or idempotency tests must assert all relevant canonical relationships,
  not only a convenient subset of tables;
- use dedicated, explicitly named test resources. Destructive tests must reject
  production or developer targets before cleanup begins.

For ingestion work, identify whether each new behavior belongs to the pure Go
validation gate, the transactional PostgreSQL write path, or an adapter
boundary. Test it at that layer unless a broader test is required to prove a
cross-boundary contract.

### CI Transparency

CI must make executed checks and their purpose visible in logs:

- print discovered test names before running a package or tagged suite;
- run tests verbosely and disable Go test-result caching where fresh execution
  matters (`go test -v -count=1`);
- name workflow steps after the behavior being checked, not only the tool;
- print relevant integration setup evidence, such as target database and
  applied migrations;
- on failure, print actionable diagnostics where practical: generated-code
  diffs, failed assertions, schema state, or command output;
- explicitly state when a generated package has no direct tests and identify
  the integration coverage that exercises it.

### Review Bar

A test change is incomplete when it:

- adds a test with no meaningful assertion;
- only tests the happy path for a change with material failure or integrity
  risks;
- claims integration coverage without exercising the real boundary;
- hides skipped, tagged, or undiscovered tests behind opaque CI output;
- uses broad mocks where a narrow real-boundary test is necessary to prove the
  contract.

## Readability

Use descriptive names for hand-written code when a short name would hide a
value's domain role, ownership, lifetime, or side effect. For example, prefer
`transactionQueries` to `qtx` when distinguishing transaction-bound database
operations from ordinary pool-backed operations.

Keep established language idioms where they improve recognition: in Go, retain
`ctx` for `context.Context`, `err` for errors, and conventional short loop
indices such as `i` and `j`.

Add concise comments for non-obvious decisions or boundaries, including
resource ownership, transaction or lifecycle behavior, ordered workflows, and
unusual control flow. Do not comment code whose purpose is already clear from
its names and structure.

## Function And Module Design

Each function does one thing. When a function does several, extract named
helpers so each piece is independently readable and testable on its own —
prefer three small functions a reader can verify at a glance over one that
requires holding the whole sequence in their head.

Prefer pure functions with explicit inputs and outputs for domain logic
(validation rules, rating math, scoring, mapping) over hidden state or side
effects. Push I/O (database, network, filesystem, subprocess) to the edges of
a component and keep the logic between those edges plain and directly unit
testable without a real database or provider. `services/importer`'s
`internal/youtube` (no PostgreSQL dependency) and `services/prediction`'s
`elo.py` (pure `fit`/`predict`, no database dependency) are the existing
examples of this shape.

Do not duplicate logic across call sites. Extract a shared, named helper in
the layer that already owns the concept rather than repeating it inline or
introducing a near-duplicate elsewhere.

This is the writing-time version of the bar the
`thermo-nuclear-code-quality-review` skill enforces on review — treat that
skill's criteria as the detailed standard this section summarizes, not a
separate one.

## Multi-Contract Execution

When the user explicitly approves a sequence of software-change contracts and
authorizes implementation, treat the sequence as one active work turn.

- Do not send a `final` response after an intermediate ticket, commit, test
  pass, review, branch, or pull request.
- Use `commentary` for concise progress and real verification results while
  continuing directly to the next dependency-ready ticket.
- Send a `final` response only after the final approved ticket has completed
  its implementation, required thermo-nuclear review, and verification plan;
  or when a genuine gate needs the user's decision, credentials, external
  state change, or explicit paid-operation approval.
- A `final` response ends active work. Never say that work will continue
  autonomously after sending one.
