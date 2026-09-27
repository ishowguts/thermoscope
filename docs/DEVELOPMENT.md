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
| `GET /api/v1/observations/{id}/context` | P03: approximate pixel area, mapped OSM candidates with distances, snapshot timing, dated land cover, event and site |
| `GET /api/v1/map/facilities.geojson` | P03: mapped OSM features in a bbox (≤ 5° per axis, capped at 2000, truncation declared) with snapshot attribution |
| `GET /api/v1/events`, `GET /api/v1/events/{id}` | P03: events from the latest `event-site-v1` run, with members, site recurrence and lineage |
| `GET /api/v1/observations/{id}/assessment` | P04: rule-based source, behaviour and review priority with reasons; `basis=RETROSPECTIVE` (default) or `OPERATIONAL`; optional timezone-aware `as_of` not before the observation and not in the future |
| `GET /api/v1/observations/{id}/timeline` | P04: per-overpass FRP maxima and per-day retrieval status within 750 m for 7–180 days before the observation |

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

## Context, land cover and events (P03)

After observations exist, from the repository root:

```sh
make migrate
make context ARGS="fetch-osm --region jamnagar"
make context ARGS="extract-landcover --region jamnagar --data-mode HISTORICAL_REPLAY"
make context ARGS="build-events --region jamnagar --data-mode HISTORICAL_REPLAY"
```

`fetch-osm` sends the fixed regional query to the main Overpass server and falls back to the allowed mirror when it is busy. To import a saved response instead, pass its hash and original retrieval time from the `.meta.json` sidecar:

```sh
make context ARGS="import-osm --region jamnagar --file local/context-fetch/jamnagar-osm-20260926T224053Z.json --sha256 f2a94cfd47f3f2e3068afde6bf1faa1cfb632cfc1bb2d9b748d5a8303fe9c2a7 --retrieved-at 2026-09-26T22:41:00+00:00"
```

Repeat for `singrauli` and `punjab` (hashes in `COVERAGE_INVENTORY.md`). Re-importing the same bytes reuses the snapshot. `extract-landcover` reads only small windows from the public WorldCover tiles and skips observations already summarized unless `--force` is given. `build-events` returns `UNCHANGED` when the input set is unchanged; `--force` rebuilds and records lineage. None of these commands classify anything.

## History and rules (P04)

Assessments need history at the same location. The 51 saved history files live in ignored `local/history-fetch/` with `.meta.json` sidecars. Import them all as historical replay, then refresh land cover and events:

```sh
for m in local/history-fetch/*-VIIRS_NOAA20_NRT-*.csv.meta.json; do
  f=${m%.meta.json}
  read -r region start days sha < <(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d['region'], d['start_date'], d['days'], d['content_sha256'])" "$m")
  make ingest ARGS="import-file --region $region --file $f --sha256 $sha --start-date $start --days $days"
done
for r in jamnagar singrauli punjab; do
  make context ARGS="extract-landcover --region $r --data-mode HISTORICAL_REPLAY"
  make context ARGS="build-events --region $r --data-mode HISTORICAL_REPLAY"
done
```

A new machine without those files must fetch its own bounded history with `make ingest ARGS="fetch --region <r> --start-date YYYY-MM-DD --days 5"` (1–5 days per request) and record the hashes. The assessment is computed on request; nothing needs rebuilding when history grows, except events.

## Labels and model (P05)

Needs the optional model libraries: `make install-ml` (macOS may also need `brew install libomp`). Run after the P03/P04 context steps; each command prints a JSON report.

The P05 data are 464 saved FIRMS files (NOAA-20 SP 30 March–30 June for all 14 regions, NRT 1 July–25 September for the 11 new regions) in ignored `local/p05-fetch/raw/`, and 14 Overpass responses in `local/context-fetch/`, all with `.meta.json` sidecars (hashes in `COVERAGE_INVENTORY.md` and `docs/inventory/p05-firms-files.csv`). Import them first; re-running is safe:

```bash
make migrate                                            # 0006_labels_models
PYTHONPATH=backend bash scripts/run.sh uv run --frozen python scripts/import_saved.py \
    --firms-dir local/p05-fetch/raw --osm-dir local/context-fetch
# Registry evidence: WRI Global Power Plant Database v1.3.0 CSV (see DATA_SOURCES)
make ml ARGS="import-gppd --file local/registry/gppd.csv --sha256 4b1f93e0fd93664f18684d9b05d0a52ed9658c6a8cf0d21ff2520791379ba7fc --retrieved-at 2026-09-27T09:40:00+00:00"
make ml ARGS="build-cases --name p05-pilot-v1"          # freezes cases, splits and review order
make ml ARGS="landcover --case-set p05-pilot-v1"        # WorldCover for each case's representative detection
make ml ARGS="features --case-set p05-pilot-v1"         # about 10 minutes for 10,318 cases
make ml ARGS="summary --case-set p05-pilot-v1"          # label tiers, reviewed test labels, agreement
make ml ARGS="train --case-set p05-pilot-v1"            # INSUFFICIENT_LABELS until reviews exist
make ml ARGS="train --case-set p05-pilot-v1 --dry-run-weak"   # pipeline check only, never evidence
```

Blind review: set `ANNOTATION_TOKEN` in `.env` to a long random value (share it with reviewers privately; never commit it), restart `make dev-api`, open `http://127.0.0.1:5173/#/review`, enter a name and work down the queue. Each review needs at least one evidence link unless the answer is "cannot decide". Test cases get two independent reviews; disagreements go to a third person. Endpoints: `GET /api/v1/annotation/case-sets`, `GET /api/v1/annotation/{set}/queue?reviewer=`, `GET /api/v1/annotation/{set}/cases/{case_id}`, `POST /api/v1/annotation/{set}/reviews` (header `X-Annotation-Token`), `GET /api/v1/annotation/{set}/summary`, `GET /api/v1/models`.

## Database checks and lifecycle

`make integration` creates a uniquely named `thermoscope_test_<uuid>` database on the configured loopback PostgreSQL server, applies the migration, checks geography and constraints, rolls it back/reapplies it, then drops only that test database. The configured development database is never rolled back or dropped. Test credentials therefore need local database-creation and PostGIS-extension permission; these are development privileges, not the planned production API role.

The initial migration creates the provenance ledger. Schema changes use Alembic. Production rollback policy is forward correction or a reviewed restore; do not run destructive downgrade commands against retained data.

`make db-stop` stops the project's database and retains its named volume. Use Ctrl+C to stop the two development servers. Do not run `docker compose down -v` casually: that deletes the development data volume.

The pinned PostGIS image provides amd64 only. Docker Desktop runs it under emulation on this arm64 Mac; local timings are not deployment benchmarks. PostGIS raster support is not enabled; P03 reads WorldCover with rasterio in the application instead (ADR-016), with nodata tests. MapLibre/WebGL is checked in P02 and P03.

## Reproducibility and CI

`make install` uses `uv sync --frozen` and `npm ci`; it does not choose new versions. `make check` runs lint, format validation, contract/API tests, TypeScript checks and a production frontend build. `make integration` additionally requires PostgreSQL. The GitHub Actions workflow uses the same commands on Ubuntu with an isolated database and no project credentials.

Dependency updates need an explicit lockfile diff and affected checks. Use `bash scripts/run.sh uv ...` or the Make targets so the project-local runtime and caches are selected consistently. MapLibre is installed in P02; rasterio and numpy in P03. Training libraries remain uninstalled until needed.
