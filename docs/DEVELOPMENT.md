# Local development

The local pilot runs the API and frontend on the host and PostGIS in Docker. This is a development setup, not a cloud deployment recipe. The current machine has project-local tools; a new machine needs Python 3.13.15, Node 24.21.0, uv 0.12.19 and a running Docker engine with Compose. The runtime files and committed lockfiles are authoritative.

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

`make configure` preserves existing values and generates a random local database password if the database URL is empty. `.env` is ignored and saved with owner-only permissions. It does not change a password in an existing database volume. Keep any FIRMS key in `.env`; do not paste it into a command or browser address bar. No NASA key is needed by automated tests or CI; provider behavior there uses explicit fixtures.

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
| `GET /api/v1/status` | Observation stage, manual CLI ingestion, classifier unimplemented; use the bounded query for actual counts |
| `GET /api/v1/catalog` | Available pilot regions and actual stored coverage for mode/product |
| `GET /api/v1/observations` | Bounded GeoJSON page with source receipts, latest acquisition and matching ingestion attempt |

There is no prediction endpoint. The UI offers saved historical replay and manually fetched NASA data. Reload refreshes the database view; it does not call NASA. `LIVE` configuration does not create scheduled polling.

Example: `/api/v1/observations?bbox=69.5,22,70.5,23&start_date=2026-09-22&end_date=2026-09-26&data_mode=HISTORICAL_REPLAY&limit=100&offset=0`. Dates are inclusive UTC, up to 31 days; each bbox axis is at most five degrees. Limit is 1–500 and offset 0–10000. `pagination_capped` requires a narrower window. A failed latest ingestion can coexist with usable retained data.

## Ingest real observations

After configuration/migration, make one bounded request:

```sh
make ingest ARGS="fetch --region jamnagar --days 5"
```

Regions are `jamnagar`, `singrauli` and `punjab`. Default product is `VIIRS_NOAA20_NRT`; supported alternatives are `VIIRS_NOAA21_NRT` and `VIIRS_SNPP_NRT`. Without a start date, the window ends on today's UTC date. An explicit `--start-date YYYY-MM-DD` starts a forward window of 1–5 days, following [NASA Area API semantics](https://firms.modaps.eosdis.nasa.gov/api/area/). Access to older data is not guaranteed by the NRT endpoint.

To replay the existing local Jamnagar sample:

```sh
make ingest ARGS="import-file --region jamnagar --start-date 2026-09-22 --days 5 --file local/access-checks/jamnagar-noaa20-20260926T113602Z.csv --sha256 d2185a5fc74871782f4dc9feca73932f6d288d925b5f285514c425fadd73870d"
```

That file is deliberately absent from Git. Another machine must fetch a real sample and use its actual checksum/date window, or show an empty view. Never create invented replacement observations. File imports are historical replay; API-fetched receipts are LIVE. Original CSV rows, hashes and receipt manifests remain in ignored `local/objects`; the key never enters them. A manifest proves receipt, not successful database commit. PostgreSQL is the run-status authority.

Bad rows are quarantined individually; a completely wrong feed schema fails. Identical observations do not grow the table when imported repeatedly. Changed measurements with the same identity are quarantined as `SOURCE_REVISION_CONFLICT`, awaiting an explicit future revision-review workflow. Scheduled polling, background retry jobs and automatic recovery of interrupted RUNNING attempts are not part of P02.

## Database checks and lifecycle

`make integration` creates a uniquely named `thermoscope_test_<uuid>` database on the configured loopback PostgreSQL server, applies the migration, checks geography and constraints, rolls it back/reapplies it, then drops only that test database. The configured development database is never rolled back or dropped. Test credentials therefore need local database-creation and PostGIS-extension permission; these are development privileges, not the planned production API role.

The initial migration creates the provenance ledger. Schema changes use Alembic. Production rollback policy is forward correction or a reviewed restore; do not run destructive downgrade commands against retained data.

`make db-stop` stops the project's database and retains its named volume. Use Ctrl+C to stop the two development servers. Do not run `docker compose down -v` casually: that deletes the development data volume.

The pinned PostGIS image provides amd64 only. Docker Desktop runs it under emulation on this arm64 Mac; local timings are not deployment benchmarks. Raster support is not enabled in P01. MapLibre/WebGL is checked in P02; GDAL/raster nodata checks remain for the raster milestone.

## Reproducibility and CI

`make install` uses `uv sync --frozen` and `npm ci`; it does not choose new versions. `make check` runs lint, format validation, contract/API tests, TypeScript checks and a production frontend build. `make integration` additionally requires PostgreSQL. The GitHub Actions workflow uses the same commands on Ubuntu with an isolated database and no project credentials.

Dependency updates need an explicit lockfile diff and affected checks. Use `bash scripts/run.sh uv ...` or the Make targets so the project-local runtime and caches are selected consistently. MapLibre is installed in P02. Training libraries and the raster stack remain uninstalled until needed.
