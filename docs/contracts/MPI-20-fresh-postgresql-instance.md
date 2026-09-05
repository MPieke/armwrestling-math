---
linear_issue: MPI-20
status: proposed
---

# Contract MPI-20: Fresh PostgreSQL Instance, Deprecate Legacy

## Scope

Stand up a new local Postgres instance so MPI-19 onward can add `NOT NULL`
columns with no backfill logic, without touching the existing dev-stage rows
(a handful, from the MPI-16 YouTube evidence work). The existing instance is
preserved, not deleted, and excluded from the default `docker-compose up`.

Out of scope: any schema change, migrating old rows into the new instance.

## 1. Current-State Architecture

```text
docker-compose.yaml
  service: postgres        volume: db  -->  armwrestling-math_db (has data)
  port:    127.0.0.1:5432
```

`.env.example`'s `DATABASE_URL` points at this instance by host/port/db-name.

## 2. Target-State Architecture

```text
docker-compose.yaml
  service: postgres           volume: db_fresh --> armwrestling-math_db_fresh (new, empty)
  port:    127.0.0.1:5432                            started by default

  service: postgres-legacy    volume: db       --> armwrestling-math_db (untouched, existing data)
  port:    127.0.0.1:5433                            profile "legacy", NOT started by default
```

The existing top-level volume key `db` is kept exactly as-is and reassigned
to the renamed `postgres-legacy` service — Compose volume identity follows
the volume key, not the service name, so this preserves the physical volume
`armwrestling-math_db` with zero data movement. The new `postgres` service
gets a new volume key (`db_fresh`), guaranteeing an empty instance.
`.env.example`'s `DATABASE_URL` is unchanged (same host, port, db name) since
the new default service reuses them — no other file needs to change.

## 3. Verification (no code behavior to unit test; this is infra)

- `docker compose up -d postgres` brings up a container against the new
  empty volume; `docker compose ps` shows no `postgres-legacy` container
  running.
- `docker compose --profile legacy up -d postgres-legacy` brings up the old
  data on port 5433, proving it still exists and is reachable.
- Applying `db/migrations/*.sql` against the new instance succeeds from
  `0001` with zero pre-existing rows.

## 4. Commit-by-Commit Breakdown

1. `docs(MPI-20): add fresh PostgreSQL instance contract`

2. `build(MPI-20): provision fresh PostgreSQL instance, deprecate legacy`
   - Edit `docker-compose.yaml` per the target state above.
   - No `.env.example` change required (see above).
   - Update `docs/architecture/ingestion.md`'s Operations section to note the
     legacy instance's existence and how to start it if ever needed.

## 5. Verification Plan

```sh
docker compose down                       # stop the currently running old container
docker compose up -d postgres
docker compose ps                         # only `postgres` running
docker exec -i $(docker compose ps -q postgres) psql -U admin -d armwrestling-math -c '\dt'
# expect: no relations (fresh)

docker compose --profile legacy up -d postgres-legacy
docker exec -i $(docker compose ps -q postgres-legacy) psql -U admin -d armwrestling-math -c '\dt'
# expect: existing tables from before this change, proving the volume survived

docker compose --profile legacy stop postgres-legacy
```
