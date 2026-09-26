# Local development

P01 runs the API and frontend on the host and PostGIS in Docker. It is a development foundation, not a deployment recipe. The current machine has project-local tools; a new machine needs Python 3.13.15, Node 24.21.0, uv 0.12.19 and a running Docker engine with Compose. The runtime files and committed lockfiles are authoritative.

From the repository root:

```sh
make install
make configure
make db-up
make migrate
make doctor
make check
make integration
```

`make configure` preserves existing values and generates a random local database password if the database URL is empty. `.env` is ignored and saved with owner-only permissions. It does not change a password in an existing database volume. Keep any FIRMS key in `.env`; do not paste it into a command or browser address bar. No NASA key is needed by P01 tests or CI.

The shell wrapper selects this Mac's isolated tools when present, otherwise tools on PATH. It supports paths containing spaces and does not alter shell startup files or system installations. `make doctor` prints the actual runtime versions and sanitized dependency state. On a different architecture, install the pinned versions with the team's approved package manager; do not copy a macOS binary to Linux.

Start two terminals:

```sh
make dev-api
make dev-web
```

Open http://127.0.0.1:5173. The Vite development proxy forwards `/api` and `/health` to port 8000. The API and frontend bind to loopback; the database exposes only `127.0.0.1:55432`. No public service is created. An occupied port is an error, not permission to terminate another service.

## Available endpoints

| Endpoint | Meaning |
|---|---|
| `GET /health/live` | API process responds; independent of database health |
| `GET /health/ready` | Database, PostGIS and expected migration revision are ready; otherwise sanitized 503 |
| `GET /api/v1/status` | Explicit foundation stage and configured data mode; ingestion/classifier unimplemented, observation count unknown |

There is no observations or prediction endpoint yet. `LIVE` in configuration does not create a live feed; the UI explicitly states ingestion is pending. FIRMS coverage CSVs in `local/access-checks/` are real saved samples, not API results or labelled incidents.

## Database checks and lifecycle

`make integration` creates a uniquely named `thermoscope_test_<uuid>` database on the configured loopback PostgreSQL server, applies the migration, checks geography and constraints, rolls it back/reapplies it, then drops only that test database. The configured development database is never rolled back or dropped. Test credentials therefore need local database-creation and PostGIS-extension permission; these are development privileges, not the planned production API role.

The initial migration creates the provenance ledger. Schema changes use Alembic. Production rollback policy is forward correction or a reviewed restore; do not run destructive downgrade commands against retained data.

`make db-stop` stops the project's database and retains its named volume. Use Ctrl+C to stop the two development servers. Do not run `docker compose down -v` casually: that deletes the development data volume.

The pinned PostGIS image provides amd64 only. Docker Desktop runs it under emulation on this arm64 Mac; local timings are not deployment benchmarks. Raster support is not enabled in P01. GDAL/raster nodata and MapLibre/WebGL checks belong to the milestones that introduce those components.

## Reproducibility and CI

`make install` uses `uv sync --frozen` and `npm ci`; it does not choose new versions. `make check` runs lint, format validation, contract/API tests, TypeScript checks and a production frontend build. `make integration` additionally requires PostgreSQL. The GitHub Actions workflow uses the same commands on Ubuntu with an isolated database and no project credentials.

Dependency updates need an explicit lockfile diff and affected checks. Use `bash scripts/run.sh uv ...` or the Make targets so the project-local runtime and caches are selected consistently. No training libraries, map engine or raster stack are installed until their task needs them.
