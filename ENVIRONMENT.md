# Environment and version baseline

Checked 25 September 2026. **These are release candidates for our environment, not prerelease software and not an installed/tested combination.** P01 resolves peer/native compatibility, records exact versions and hashes, and creates lockfiles. Recheck security notices and maintenance status then; do not silently substitute prereleases or `latest` container tags.

## Runtime choices

| Component | Candidate | Rationale/source |
|---|---|---|
| Python | 3.13.15 | Maintained 3.13 line; [release](https://www.python.org/downloads/release/python-31315/). Prefer native geospatial compatibility over newest feature line. |
| Node.js | 24.21.0 LTS | [Official release index](https://nodejs.org/dist/index.json); audited 24.x LTS release |
| PostgreSQL | 18.6 | [Version policy](https://www.postgresql.org/support/versioning/); 19 prereleases excluded |
| PostGIS | 3.6.4 | [Release news](https://postgis.net/news/); exclude 3.7 release candidates |
| uv | 0.12.19 | Python dependency management; freeze tool version |

Verify a supported PostgreSQL/PostGIS image pair and immutable digest instead of guessing an image tag. If the host/image does not support this pair, PostgreSQL 17.11 is a documented candidate fallback; record why and run the same migration/geography checks. Do not install a beta to preserve a table entry.

## Library candidates

Version metadata came from the official package registries. Python sources use `https://pypi.org/pypi/<package>/json`; JavaScript sources use `https://registry.npmjs.org/<package>`. The audit selected releases published by the audit date. A compatibility resolution can select a different supported patch/line with a recorded reason.

| Scope | Package | Candidate version |
|---|---|---|
| API | fastapi | 0.141.1 |
| API/schema | pydantic | 2.13.5 |
| Database | sqlalchemy | 2.0.54 |
| Database | geoalchemy2 | 0.20.0 |
| Database | alembic | 1.20.0 |
| Database | psycopg | 3.3.6 |
| Providers | httpx | 0.28.1 |
| Geography | shapely | 2.1.2 |
| Raster processing | rasterio | 1.5.1 |
| Optional batch analysis | geopandas | 1.1.4 |
| Projections | pyproj | 3.8.0 |
| STAC | pystac-client | 0.9.0 |
| Structured ML | xgboost | 3.4.1 |
| Evaluation | scikit-learn | 1.9.1 |
| Optional image experiment | torch | 2.14.0 |
| Optional image experiment | terratorch | 1.2.13 |
| Tests | pytest | 9.1.1 |
| Lint/format | ruff | 0.16.9 |
| UI | react / react-dom | 19.3.0 |
| UI build | vite | 8.3.1 |
| Types | typescript | 7.0.2 |
| Maps | maplibre-gl | 6.11.2 |
| API cache | @tanstack/react-query | 5.103.2 |
| Browser tests | @playwright/test | 1.63.0 |

SQLAlchemy 2.1.1 appeared in the registry on the audit day; use the maintained 2.0.54 candidate initially to reduce ORM migration risk. NumPy, pandas, GDAL/PROJ/GEOS, ASGI server and testing/type packages are resolved with their consumers during P01, not guessed here. Do not add the entire table to the API image. The optional torch/TerraTorch combination needs its own resolver and one genuine preprocessing/forward-pass check before adoption.

## Required compatibility evidence

1. Record OS/architecture and choose Linux deployment architecture. The user's Mac hardware was not verified; cloud is the primary plan.
2. Resolve backend dependencies into `uv.lock`; exact frontend dependencies into `package-lock.json`. Commit both when they exist. Use frozen installs in CI.
3. Pin runtime files and container digests. Record GDAL/PROJ/GEOS versions; test CRS transforms, raster nodata and a real PostGIS query.
4. Run migration against disposable PostGIS, parser tests, API contract checks and UI typecheck/build. Exercise MapLibre in a browser; a build alone does not test WebGL.
5. Inspect dependency advisories and licenses; record relevant unresolved issues and remediation. Run one fresh-clone installation.
6. Before P06, freeze the model revision, preprocessing, HLS collection, optional ML environment and hardware. Check missing imagery and CPU fallback separately.

The acceptance record must distinguish version lookup, successful installation, tested functionality and operational readiness. None are interchangeable.
