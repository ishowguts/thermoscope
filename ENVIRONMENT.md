# Environment and version baseline

Candidate research dated 25 September 2026; P01–P04 verification dated 26–27 September. **The installed API/UI/map and raster subset is tested and frozen on the Mac and in CI. P05's optional ML group is frozen and independently Mac-verified (148 unit/API + 19 PostGIS tests); the recorded dependency advisory audit is point-in-time and must be refreshed for release. Other optional packages remain candidates.** Do not silently substitute prereleases or `latest` tags.

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

1. Record OS/architecture and choose Linux deployment architecture. P01 verified macOS arm64; RAM was not measured. Cloud is the primary deployment plan.
2. Resolve backend dependencies into `uv.lock`; exact frontend dependencies into `package-lock.json`. Commit both when they exist. Use frozen installs in CI.
3. Pin runtime files and container digests. Record GDAL/PROJ/GEOS versions; test CRS transforms, raster nodata and a real PostGIS query.
4. Run migration against disposable PostGIS, parser tests, API contract checks and UI typecheck/build. Exercise MapLibre in a browser; a build alone does not test WebGL.
5. Inspect dependency advisories and licenses; record relevant unresolved issues and remediation. Run one fresh-clone installation.
6. Before P06, freeze the model revision, preprocessing, HLS collection, optional ML environment and hardware. Check missing imagery and CPU fallback separately.

The acceptance record must distinguish version lookup, successful installation, tested functionality and operational readiness. None are interchangeable.

## P01 verified environment — 26 September 2026

- macOS arm64, isolated Python **3.13.15**, uv **0.12.19**, Node **24.21.0**, bundled npm **11.19.0**. System runtimes were preserved.
- Docker server **29.7.2**, Compose **5.5.0**. Digest-pinned `postgis/postgis:18-3.6` runs linux/amd64 under emulation.
- Database query: PostgreSQL **18.6**, PostGIS **3.6.4**, runtime GEOS **3.14.1**, runtime PROJ **9.8.1** with network disabled. PostGIS reports compile-time GEOS 3.13.1 / PROJ 9.6.0. Distance and migration checks passed with the installed pair.
- `postgis_raster` is not enabled; `PostGIS_GDAL_Version()` is consequently unavailable. No raster, nodata or MapLibre/WebGL capability is certified by P01.
- `uv.lock` freezes API/test dependencies. Additional resolved direct packages: uvicorn **0.54.0**, pydantic-settings **2.15.0**, test transport httpx2 **2.13.1** (ADR-010). Starlette **1.7.0** is the resolved FastAPI dependency.
- `frontend/package-lock.json` freezes React/ReactDOM **19.3.0**, matching type packages, TypeScript **7.0.2**, Vite **8.3.1** and transitives. Vite's built-in TSX transform is sufficient here; no extra React transform plugin is required for this foundation.
- Fresh separate Python environment and `npm ci` passed, followed by contract/API tests and frontend typecheck/build. The real disposable PostGIS migration/rollback/reapply test passed.
- npm audit reported zero known vulnerabilities. PyPI version metadata was checked for known advisories; this is a dependency metadata check, not a full security audit. Package metadata is saved locally. Final validation details are in `docs/EVIDENCE.md`.

GitHub Actions revisions are pinned to official v6 commit SHAs verified through the GitHub API. Cloud containerization, production permissions, backup/restore and the optional ML environment remain future gates.

## P02 additions — 27 September 2026 IST

- MapLibre GL JS **6.11.2** (BSD-3-Clause) and Prettier **3.9.9** (MIT) are exact frontend dependencies with a committed npm lock. Registry metadata and [MapLibre documentation](https://maplibre.org/maplibre-gl-js/docs/) checked; the Vite build bundles the v6 ESM worker using `?worker&url`.
- The provider uses Python's standard-library HTTPS client; no extra runtime HTTP library is needed for this bounded adapter. The proposed production httpx dependency remains uninstalled.
- npm audit reported zero known vulnerabilities after these additions. This is a point-in-time advisory check, not a full security certification.
- The map is a separate lazy-loaded chunk. Vite still warns that it exceeds 500 kB (about 1.03 MB minified / 278 kB gzip, plus a 510 kB worker). Do not claim a mobile performance budget has passed.
- Local WebGL rendering and point/list selection are checked separately from the compiler. Raster processing was unverified at P02; see the later P03/P04 Mac verification below. The optional ML environment remains pending Mac verification.

## P03 additions — 27 September 2026 IST (branch `p03-context`)

- Backend: **rasterio 1.5.1** (BSD-3-Clause; bundled **GDAL 3.12.4**) and **numpy 2.5.3** (BSD-3-Clause and bundled permissive licences). New transitive packages: affine 3.0.1 (BSD-3-Clause), attrs 26.1.0 (MIT), certifi 2026.7.22 (MPL-2.0), pyparsing 3.3.3 (MIT). PyPI reported zero known vulnerabilities for all six at lock time.
- rasterio's macOS arm64 wheel is tagged **macOS 14.0 or newer**. Frozen installation and actual raster reads now pass on the owner's macOS 26.3 arm64 machine. Linux x86_64 is verified by CI; older Macs still need a compatible environment.
- Frontend: `@types/geojson` **7946.0.16** is now a declared dev dependency (already present transitively via MapLibre). TypeScript 7 no longer loads global `@types` packages without a declaration.
- WorldCover reads use GDAL's `/vsicurl/` with directory listing disabled, `.tif` only, 30 s timeout and two retries. In a proxied environment, GDAL needs `CURL_CA_BUNDLE` pointing at the proxy CA; the owner's Mac needs nothing extra.
- Verified in a Linux cloud workspace (Python 3.13.15, Node 24.21.0, uv 0.12.19, the same digest-pinned PostGIS) and in GitHub Actions. P03/P04 were subsequently verified on the owner's Mac: 106 unit/API tests, 15 PostGIS integration tests, actual OSM and WorldCover reads, and the built browser flow. See `docs/EVIDENCE.md`. XGBoost/OpenMP is a separate P05 check, not covered by these results.

## P05 additions — 27 September 2026 IST

- Optional `ml` dependency group (`make install-ml`, i.e. `uv sync --frozen --group ml`): scikit-learn **1.9.1** (BSD-3-Clause) and XGBoost **3.4.1** (Apache-2.0) — the `xgboost` wheel on macOS, `xgboost-cpu` on Linux through a platform marker. Resolved transitives: SciPy 1.18.1 (BSD-3-Clause), joblib 1.6.0, threadpoolctl 3.7.0, cloudpickle 3.1.2 (BSD-3-Clause), narwhals 2.26.0 (MIT). The CPU-only Linux build avoids the NVIDIA communication libraries that the default Linux wheel pulls in.
- Advisory audit (27 September 2026, 17:06 UTC, P05 reconciliation): `pip-audit` 2.9.0 against these exact versions with both the PyPI and OSV vulnerability services found no known vulnerabilities. Point-in-time only; re-run before a release.
- Licence obligations: all Python packages above are permissive (BSD-3-Clause, Apache-2.0, MIT) and need their notices kept when redistributed. The Linux wheels bundle native runtimes: `libgomp` (xgboost-cpu, scikit-learn) and `libgfortran` under GPL-3.0 with the GCC Runtime Library Exception, `libquadmath` (LGPL-2.1) and OpenBLAS (BSD-3-Clause) in NumPy/SciPy. Using them locally imposes nothing; a container or binary redistribution must ship their notices. The macOS `xgboost` 3.4.1 wheel does not bundle OpenMP: `libxgboost.dylib` loads `@rpath/libomp.dylib` with the single rpath `/opt/homebrew/opt/libomp/lib` (checked with `otool` on the owner's Mac). Homebrew's `libomp` (Apache-2.0 with LLVM exception; 23.1.2 on the owner's Mac) is therefore a system prerequisite on macOS, installed by the user, not by the project.
- `uv run` keeps the extra group once installed. Tests needing XGBoost or scikit-learn skip when the group is absent, so `make check` still runs without it; CI installs it.
- Verified on Linux x86_64 (cloud workspace, Python 3.13.15) and, on 28 September 2026, on the owner's Mac (macOS 26.3 arm64) in an isolated clone with `scripts/verify_p05_mac.sh`: without `libomp` XGBoost failed to load (146 of 148 unit tests passed, the two model tests failed; 19 of 19 PostGIS tests passed); after `brew install libomp` everything passed (148 unit/API, 19 PostGIS, lint, format, typecheck, build). Neither a dyld fallback path nor scikit-learn's bundled `libomp` satisfies XGBoost's `@rpath` lookup, so no workaround is shipped.
- PostgreSQL batch jobs (event builds, case sets, features) use a 10-minute statement timeout; API requests keep 2 seconds.
- P05 reconciliation adds migration `0007_review_integrity` (PostgreSQL triggers; no extension) and the optional `REVIEW_ONLY` setting. No new dependency.
- 28 September: migration `0008_reviewer_accounts` (reviewer accounts, review-account link, adjudication-view log; triggers only). The former `ANNOTATION_TOKEN` setting is no longer read (an old `.env` entry is ignored); reviewer tokens live in the database as SHA-256 hashes and, until handed over, in ignored owner-only files under `local/reviewer-tokens/`. No new dependency.

## Independent P05 Mac acceptance — 28 September 2026 IST

Final implementation `d9ca117`: frozen API/UI/ML install, a small synthetic XGBoost fit, `make check` (148 unit/API tests plus lint/format/type/build) and `make integration` (19 PostGIS tests) passed in the isolated review worktree. Main subsequently installed the same environment, migrated to 0008 and ran the real P05 pipeline. Details: internal record P05-MAC-ACCEPTANCE. libomp 23.1.2 was already installed by the owner; no new runtime/dependency choice was introduced. A local backup was fully restored into the isolated database. Cloud restore and production deployment remain untested.
