# Demo runbook — offline historical replay and evidence exports

Release `v0.8.0-demo`. Measured results are in `docs/EVIDENCE.md` and `docs/RELEASE.md`.

This is a research demonstration of **saved real observations replayed from local files**. It is not live monitoring, not incident confirmation and not an evaluated model. Rule outputs are transparent, uncalibrated heuristics; the learned model is not served; human validation is pending (ADR-024).

## 1. What the demo shows, and what it does not

| Shown in this demo (checked in the browser) | Intended product capability, **not shown** |
| --- | --- |
| Genuine NASA FIRMS VIIRS NOAA-20 detections for Jamnagar and the Punjab comparison region, replayed from a hashed local package by a loader and API that refuse non-local connections | Live or near-real-time ingestion, scheduled fetching, alerts or notifications |
| Per observation: likely source, behaviour, review priority, reasons and missing/limited data, from transparent rules | A learned classifier's output (built, **not served**; no reviewed labels to evaluate it) |
| Mapped OpenStreetMap context and ESA WorldCover 2021 land cover inside the approximate pixel area | Confirmation of a source or of an incident; satellite imagery checks (P06, deferred) |
| 180-day detection history for the same place, with days not retrieved shown as unknown | Human-validated labels, accuracy or calibration (deferred, ADR-024) |
| Bounded CSV/GeoJSON exports with units, receipts, source dates, licences and attribution | Bulk data service, production authentication, hosted deployment |
| Map-free operation: no internet basemap, WebGL failure fallback, empty region, keyboard use | Offline internet basemap tiles (never downloaded; the basemap is simply off offline) |

## 2. The package

`demo-package-v1`, name `thermoscope-demo-v1`, regions `jamnagar,punjab`, mode `HISTORICAL_REPLAY`. Built from the files this project already retained — never refetched. It is **not** the frozen P05 evaluation set and contains no labels, reviews, reviewer accounts, cases, features or model outputs.

| Content | Files | Source and licence |
| --- | --- | --- |
| FIRMS area CSVs for both regions: NRT 1 July–26 September 2026, SP 30 December 2025–30 June 2026, five-day windows (the last SP window three days); 5,971 detections | 110 | NASA FIRMS (open data; acknowledgement in every export) |
| Overpass JSON extracts with their retrieval sidecars, retrieved 26 September 2026 22:41 UTC | 2 (+2 sidecars) | © OpenStreetMap contributors, ODbL-1.0 |
| WorldCover 2021 v200 raster chips and every recorded `landcover-summary-v2` row for these detections: 3,307 of 5,971 (73 of 131 NRT, 3,234 of 5,840 SP). The rest were never extracted in the source database and show "Land cover not available", as there | 3,307 chips + `summaries.json` | ESA WorldCover, CC-BY-4.0, doi:10.5281/zenodo.7254221 |

Workspace build: 3,420 listed files, 12,642,434 bytes, content SHA-256 **`e5117f7266cb4ceea3f065b8c048a60bddeb8776b99410f4d8400be008220464`** (identical on a rebuild). `docs/inventory/demo-v1-files.csv` lists every FIRMS, OSM and summary file with its hash; chips are named by their own SHA-256 and referenced by `worldcover/summaries.json`. `manifest.json` records for each file its SHA-256, size, source, region, product, window, the provider retrieval time where a sidecar was retained (108 of 110 FIRMS files; the two 22–26 September NRT windows were imported from files whose sidecars were not kept), when the source database first imported it and that import's status. `README.txt` repeats the sources, licences and the load command with the expected hash.

**Builder:** refuses a file containing a FIRMS API URL or the configured key (`POSSIBLE_CREDENTIAL_IN_FILE`), a stored object whose hash does not match, a target that already exists, or more than 50 MB. Unusable retrieval-time sidecars are skipped and counted.

**Verify and load:** every listed file must be present **inside** the package with its hash (no `..`, absolute paths or symbolic links; nothing unlisted), and every entry and region well formed, and `README.txt` exactly what the manifest generates. The content hash covers the whole manifest except its build time: regions, sources and licences, and every file entry with the region, product and window the loader uses. `verify` alone catches damage; because whoever can edit a copy can also rewrite its manifest, pass `--expect-sha256` with the hash received separately (above, or from whoever built it) before trusting a copied package. The loader then imports FIRMS and OSM through the normal importers in historical replay mode, restores a land-cover summary only if the packaged chip reproduces its window hash, support basis, both summaries, status and tile (the source URL, tile-edge flag, run and extraction time are carried as recorded), and rebuilds events. It reports `ok: false` and exits 1 if any import ends differently from the source database. Reloading is harmless: stored rows are reused and events report `UNCHANGED` (`ok: true`).

## 3. Export contract (`evidence-export-v1`)

| Route | Returns |
| --- | --- |
| `GET /api/v1/exports/observations.csv` | One row per satellite observation in the window |
| `GET /api/v1/exports/observations.geojson` | The same as RFC 7946 points, with a `meta` block |
| `GET /api/v1/exports/observations/{id}/evidence.geojson` | One observation: pixel centre, approximate pixel area, mapped facilities, rule assessment, 180-day history, context and sources |

- **Filtering:** the window routes take exactly the observation list's parameters and filter (`bbox` ≤ 5° per axis, `start_date`/`end_date` UTC, 1–31 days, `data_mode`, `product`); invalid input → 422. Only observations with a stored receipt in that data mode are included; modes never mix. `basis` (`RETROSPECTIVE` default, or `OPERATIONAL`) selects the rule basis, as in the workbench.
- **Bounds:** at most **2,000 observations** per window export and **100 with `rule_outputs=true`** (rules are computed per observation). Larger requests get **413 `EXPORT_TOO_LARGE`** with the matching count and the limit. Nothing is truncated. The UI disables the buttons above these limits and says why.
- **Columns (CSV/GeoJSON properties):** observation ID; acquisition time (UTC); latitude/longitude; `location_meaning = PIXEL_CENTRE`; approximate pixel radius (m) and its basis; FRP (MW); I4/I5 brightness temperature (K, not flame temperature); scan/track (km); day/night; NASA confidence; satellite, sensor, product, collection; data mode; historical availability; raw file SHA-256, row number, ingestion run, import time; FIRMS attribution. With `rule_outputs`: source, subtype, behaviour, review priority, missing/limited, rules version, rule basis, feature snapshot SHA-256, the OSM data date the rules used, the WorldCover map year, and OSM/WorldCover attribution (GeoJSON `meta.context_sources` adds their licences and DOI). CSV adds `learned_model = NOT_SERVED` and `human_validation = PENDING`.
- **Semantics:** a point is a pixel centre, never a fire boundary; the pixel area polygon is approximate; mapped OSM features are context, *not a confirmed source*. Missing values are empty (CSV) or null (GeoJSON), never zero. UNKNOWN stays UNKNOWN.
- **CSV safety:** text cells that start with `=`, `+`, `-`, `@`, tab, CR or LF — also after leading spaces, and their full-width forms — are prefixed with `'`; numbers stay numeric. UTF-8, header row always (an empty window exports only the header).
- **Excluded:** credentials and key-bearing URLs, reviewer identities, tokens, labels, case sets, model scores or run metrics.
- **Blind-review servers (`REVIEW_ONLY=true`):** rule outputs and evidence exports → 403 `WITHHELD_ON_REVIEW_SERVER`; plain measurement exports stay available, like the observation list.
- Every download is an attachment with `Cache-Control: no-store`, `X-ThermoScope-Export` and `X-ThermoScope-Observations` headers (exposed to cross-origin pages too). `/api/v1/status` additionally reports `human_validation: PENDING_DEFERRED` and `exports: evidence-export-v1`; existing fields are unchanged.

## 4. Commands (from the repository root; bash or zsh)

Prerequisites: `make install` done, PostGIS running (`make db-up`), `.env` configured with a **loopback** `DATABASE_URL`. `build` only reads the database and object store configured in `.env`. `load` and `serve` require `--database thermoscope_<name>`, refuse the database configured in `.env`, and write objects to `--objects` (default `local/demo-objects`, never the configured store). Nothing below prints a secret. Each command prints one JSON report.

The demo API uses port 8000 and Vite 5173 (the Vite proxy is fixed to 8000). If the main API/Vite are running there, stop them first and restart them afterwards with `make dev-api` / `make dev-web`.

```bash
R() { env PYTHONPATH=backend bash scripts/run.sh uv run --frozen python scripts/demo_package.py "$@"; }

# 1. Build from the retained files (no network needed; never overwrites an existing package)
R build --name thermoscope-demo-v1 --regions jamnagar,punjab
#    -> local/demo-package/thermoscope-demo-v1 and its content_sha256; compare with §2 and the inventory

# --- Disconnect the network now (e.g. turn Wi-Fi off) ---

# 2. Verify every file. H = the content_sha256 your build printed, or the one received with a
#    copied package (the workspace build's is in §2).
H=paste-the-content_sha256-here
R verify --package local/demo-package/thermoscope-demo-v1 --expect-sha256 "$H" --offline

# 3. Load into a separate demo database (created and migrated if missing)
R load --package local/demo-package/thermoscope-demo-v1 --expect-sha256 "$H" \
  --database thermoscope_demo --create --offline

# 4. Serve the API from the demo database (terminal 1; historical replay mode is set for you)
R serve --database thermoscope_demo --offline

# 5. Serve the UI (terminal 2). VITE_BASEMAP=off makes the page request no internet tiles at all.
VITE_BASEMAP=off bash scripts/run.sh npm --prefix frontend run dev -- --host 127.0.0.1
#    open http://127.0.0.1:5173/
```

**From a separate worktree** (recommended for review, so the main checkout stays untouched): ignored files are per checkout, so give the worktree the settings and point the build at the main checkout's retained files, which it only reads. `M` below is the main checkout's absolute path.

```bash
cp "$M/.env" .env   # or a symlink; never print it
R build --source-objects "$M/local/objects" --osm-dir "$M/local/context-fetch" \
  --firms-dir "$M/local/history-fetch" --firms-dir "$M/local/p05-fetch/raw" --firms-dir "$M/local/p05-backfill/raw"
# then steps 2–5 unchanged (they use this worktree's local/demo-package and local/demo-objects)
```

Missing `--firms-dir` folders are skipped; they only add provider retrieval times. If `.env` keeps its object store elsewhere, pass that folder to `--source-objects`. The build writes only under this worktree's `local/demo-package/`.

**What `--offline` does:** it is a guard for that Python process, not a firewall. Python-level connections, datagrams and name lookups (forward and reverse) for anything but the local machine are refused; HTTP clients inside C libraries (curl, GDAL) are pointed at a dead local proxy; and the command refuses to run unless the database — including any `host`/`hostaddr` override in `DATABASE_URL` — is on this machine. The database driver's own C-level connection and raw sockets are outside the guard, which is why the loopback check exists. A successful offline load or API run therefore fetched nothing through those paths. Turning the network off is still the acceptance check.

Without `VITE_BASEMAP=off`, a page opened with no network first tries the OpenStreetMap tiles; after several fail with none arriving it switches to "Basemap unavailable · retry", shows "No basemap: points, pixel area and mapped facilities are drawn from stored data only", and remembers that choice so later loads make no internet request. "Basemap off" / "Basemap on" in the map header switches it by hand. A stray tile failure while online only shows a notice. If the browser still has tiles cached from earlier online use it may show them; that is cached internet content, not an offline basemap, so switch the basemap off for a clean map-free recording.

## 5. Demonstration path (about three minutes)

Default window: Jamnagar, 26 August–25 September 2026 (57 observations). Rows are labelled by FRP and UTC time.

1. **Status strip** — "Assessments: transparent rules, uncalibrated thresholds · not a probability"; "Learned model: built, not served"; "Human validation: pending · deferred". Browsing is not blocked.
2. **Industrial-context candidate** — select **1.91 MW, 09 Sept 2026, 21:31 UTC** (22.3315, 69.7481). Likely source *Industrial (heuristic)*: one mapped refinery feature in the pixel area (OSM "Vadinar Refinery"), built-up land cover 75%. Behaviour *New or transient*: no earlier detection within 750 m in 90 retrieved days (the page adds that non-detection can also mean cloud or no overpass). Review priority **High** ("New detection at a mapped industrial feature; check recent imagery and operator or official records") — a review order, not an accident probability. The history chart shows the older record honestly: three detections between April and June, none in the 90 days the rule looks at, and the context panel lists 12 earlier events at this site since January. Click **Download evidence (GeoJSON)** (pixel centre, pixel area and the 33 mapped features nearby, each marked "not a confirmed source").
3. **Contrasting persistent heat** — select **9.89 MW, 09 Sept 2026, 09:05 UTC** (22.9289, 70.1085). *Industrial (heuristic) · persistent heat*, mapped "Tuna-Tekra Container Terminal" in the pixel area, "Detected on 21 earlier days within 750 m"; behaviour *within its observed record* (9.89 MW against 17 earlier comparable daytime overpasses, median 7.05 MW); the 180-day history shows detections on 84 of its 181 days; priority Low with "Kept in the list: a persistent site is not suppressed or certified safe."
4. **Uncertain case** — set dates 2026-07-20 → 2026-08-15, *Apply dates*, select **1.57 MW, 03 Aug 2026, 21:23 UTC**. Source stays **Unknown**: the nearest mapped power feature is solar/wind/water, so the heat is not attributed to it. Priority Medium.
5. **Different land use** — region *Punjab comparison*, 2026-07-01 → 2026-07-31, select **9.68 MW, 10 July 2026, 08:07 UTC**: *Agricultural burning (heuristic)*, cropland 98% of the pixel area, no mapped industry, *not enough comparable history*.
6. **Window export** — tick *with rule outputs* and click **CSV** (about 4 s for 57 observations in the workspace), or **GeoJSON**. Open the CSV: pixel centres in WGS84, units, receipts, FIRMS and context attribution, `NOT_SERVED`/`PENDING` status columns.
7. **Empty region** — select *Simlipal* (not in the package): "No observations in this window. A non-detection does not prove absence of fire." Its export is a header-only CSV.
8. Optional: **Hide map** (list-only view), keyboard only (first Tab reaches "Skip to the observation list", Enter focuses the first row, Enter opens it).

## 6. Measured timings and limits (cloud workspace: 2 vCPU, 7 GB, Linux; not the Mac)

| Step | Measured |
| --- | --- |
| Package build / verify | 1.1–2.8 s / 0.25 s |
| Offline load into an empty database (110 FIRMS files, 5,971 rows, 2 OSM extracts, 3,307 land-cover summaries recomputed from chips, events for both regions) | 49.1–52.8 s; reload into the same database 47.2 s (`ok: true`, nothing inserted) |
| Loaded vs full workspace database | All 5,971 detections present, land-cover rows identical for all 5,971; rule labels, rule inputs (except the database-local OSM snapshot ID) and missing data identical for all 131 NRT and a seeded sample of 300 SP detections; association, land cover, event size and 180-day timeline identical for the 131 NRT |
| API, three runs each | observation list 0.05 s; window CSV/GeoJSON (57 obs) 0.04–0.05 s; CSV with rule outputs (57 obs) 3.6–3.8 s; one assessment 0.06–0.08 s; evidence export 0.22–0.28 s |
| Browser (headless Chromium, 1920×1080, network refused) | first rows 0.8–1.8 s (1.8 s on a cold Vite start); evidence panel 0.9–1.5 s; evidence download 0.3–1.2 s; window CSV with rules 4.0–4.6 s |

No performance target was set or claimed. Limits: window exports ≤ 2,000 observations (≤ 100 with rule outputs); query windows ≤ 5° and ≤ 31 days; package ≤ 50 MB.

## 7. Known limitations

- Only two regions are packaged. Any region can be added to a new package name (`--regions`), up to 50 MB, if its FIRMS receipts, an OSM extract and land-cover summaries exist in the source database.
- The demo database records when the package was loaded as each FIRMS file's import time ("Latest import attempt" on the page). Provider retrieval times are in the manifest (108 of 110 files). Historical availability at acquisition time is unknown, so every assessment is retrospective and says so.
- 2,664 of the 5,971 detections (58 of the 131 NRT listed in the workbench) have no land-cover summary in the source database; the page and exports show that as missing.
- OSM context is as of 26 September 2026 and WorldCover describes 2021; both are retrospective context, not evidence of the source.
- Rules and priorities are uncalibrated heuristics. No human review, validated accuracy or learned inference exists.
- Offline behaviour was demonstrated in the cloud workspace with the Python guard above and a dead proxy plus DNS blackhole in Chromium; the machine itself was not physically disconnected. Repeat steps 2–5 on the Mac with Wi-Fi off for acceptance.
- A package built elsewhere has its own content hash if its database holds different receipts or land-cover summaries, or if different `--firms-dir` folders supply the retrieval times (the hash covers all manifest metadata); compare the FIRMS/OSM/summary file hashes with the inventory.
- Timings come from the cloud workspace; the Mac will differ.

## 8. Troubleshooting

| Report / symptom | Meaning and action |
| --- | --- |
| `PACKAGE_VERIFICATION_FAILED` (load) or `ok: false` (verify) | See `problems`: `MISSING`, `HASH_MISMATCH`, `NOT_IN_MANIFEST`, `UNSAFE_PATH`, `SYMLINK_NOT_ALLOWED`, `INVALID_ENTRY`, `CONTENT_DIGEST_MISMATCH`, `README_NOT_FROM_MANIFEST` or `NOT_THE_EXPECTED_PACKAGE`. Rebuild under a new name or obtain the package again; do not edit package files. |
| Load prints `ok: false` / exits 1 | `unexpected` lists imports whose status differs from the source database; investigate before demonstrating. |
| `FileExistsError` (build) | The target folder exists. Use another `--name` or `--out`; old packages are never overwritten. |
| `OSM_SNAPSHOT_MISSING` (build) | No `<region>-osm-*.json` with sidecar in `--osm-dir` (default `local/context-fetch`). |
| `OBJECT_HASH_MISMATCH` (build) | A stored raw object does not match its database hash, or `--source-objects` points at the wrong store. |
| `LANDCOVER_OBSERVATION_MISSING` / `LANDCOVER_CHIP_MISSING` / `LANDCOVER_SUMMARY_NOT_REPRODUCED` (load) | The package's land cover does not match its observations or chips; rebuild from the source database. |
| `… needs --database`, `must not be the database configured in .env`, `must look like thermoscope_<name>`, `only … on a loopback server`, `--objects must not be, contain or lie inside the object store in .env` | Refusals that keep the main database and object store untouched; use a demo name and folder on a local PostGIS. |
| Port 8000 or 5173 in use | Stop the main API/Vite first (see §4), or stop a stale demo process. |
| Map area shows "Map rendering is unavailable" | WebGL is unavailable; the observation list, evidence panel and exports still work. |
