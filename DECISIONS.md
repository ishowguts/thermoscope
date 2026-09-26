# Design decisions

All entries below are design decisions for the fresh specification on 25 September 2026. Runtime validation remains a separate milestone.

## ADR-001 — Rebuild from the folder's concept
Choose the local ThermalGuard concept over the fixed-response Part 1 implementation. Preserve detection/event/site separation, provenance, PostGIS and an unknown outcome. Start a new repository and implementation. Neither old repository is a source of validated model performance.

## ADR-002 — Separate source, behaviour and priority
Keep industrial/vegetation/agriculture source classification separate from routine/abnormal behaviour, facility type and analyst priority. A nearby refinery or high FRP does not establish an accident. Allow abstention and independently reviewed incident status.

## ADR-003 — Establish the simpler comparison first
Use proximity rules, thermal history and XGBoost as measured baselines. Evaluate AlphaEarth context next; make a compact Prithvi experiment optional. Promote added complexity only after fair held-out comparison. Do not use a generative language model as the live scientific classifier.

## ADR-004 — One small operational system
FastAPI, a scheduled worker, PostgreSQL/PostGIS, object storage and React/MapLibre form the pilot. Database leases and idempotence handle jobs initially. No Kubernetes, Kafka or Redis requirement before measured demand.

## ADR-005 — Historical availability is part of the feature contract
Keep acquisition, publication/availability and ingestion times. Exclude future context from earlier predictions. Unknown historical availability means a retrospective experiment, not a proven real-time replay. Current OSM or annual embeddings applied to older incidents must be disclosed.

## ADR-006 — Evidence governs model promotion
Reviewed labels, site/episode grouping, separate unseen-site and known-site protocols, saved manifests, calibration and error analysis are required. Weak labels may assist training but cannot certify the test set. No predetermined headline accuracy.

## ADR-007 — Stable versions require compatibility checks
Prefer supported stable lines over previews. Candidate versions are verified releases, not a tested lockfile. Start on Python 3.13 and Node 24 LTS; check the geospatial/native stack in the deployment image. Keep optional image-model dependencies separate if needed.

## ADR-008 — One shared work contract
One integrator merges by default; other contributors take bounded tasks. Task contracts, Git state, evidence and handoffs carry context across sessions. Parallel work requires separate worktrees and explicit ownership. Do not depend on account rotation.

## ADR-009 — Submit an accurate proposal promptly
Use the 2026 template and current portal rules. The complete research system will take longer than the submission window. Clearly distinguish implemented evidence and proposed work; preserve final submitted artifacts and receipt. A supporting video is recommended if permitted, with no guarantee of selection.

## ADR-010 — P01 resolved environment (26 September 2026)
Python 3.13.15 / uv 0.12.19 and Node 24.21.0 / bundled npm 11.19.0 are isolated locally. Exact manifests and lockfiles are committed. PostGIS image 18-3.6 is pinned by digest; actual PostgreSQL 18.6 and PostGIS 3.6.4 were queried. The image only provides amd64, so this arm64 Mac uses Docker emulation; select native amd64 for the matching cloud pilot. Local timings are not performance evidence.

Starlette 1.7.0 deprecated its old `httpx` test-client path. Use stable `httpx2` 2.13.1 for test transport, as recommended by the [official TestClient documentation](https://www.starlette.io/testclient/), and verify the same tests. This replaces the P01 test dependency; a production provider client remains a P02 decision. Optional maps/ML/raster packages remain uninstalled until needed.

## ADR-011 — Host processes for the development foundation
P01 Compose runs only PostgreSQL/PostGIS; API and Vite run as loopback host processes with frozen environments. This keeps first-run development small and inspectable. Containerized API/worker deployment remains a later deployment deliverable, not an implied P01 capability. Database test creation/drop is restricted to a uniquely named test-owned database on loopback. No development data-volume rollback is performed.

## ADR-012 — P02 bounded ingestion and source receipts (27 September 2026 IST)

Implement NOAA-20, NOAA-21 and S-NPP VIIRS NRT parsing only; the verified real pilot uses NOAA-20. MODIS, standard-product reconciliation and scheduled polling remain later work. Python's standard HTTPS client is sufficient: fixed NASA host, no redirects, 20-second timeout, at most three attempts, bounded response and row counts, sanitized outcomes.

Observation identity hashes product/sensor/satellite/acquisition time and canonical decimal coordinates without rounding. Replay and provider fetches share the physical identity; synthetic fixtures use a separate namespace. A unique database key and consistent insertion order protect overlapping concurrent imports. A changed payload for the same identity is quarantined for review, never silently substituted. This is revision detection, not complete scientific reconciliation.

Content-addressed raw objects are immutable. Every receipt has its own manifest and database run; identical bytes can reuse a snapshot. The P01 snapshot's `data_mode` describes its first receipt only. Mode filtering, current receipt and availability in P02 come from `ingestion_runs`/`observation_receipts`, never from that legacy snapshot field. For live data, `first_available_at` means the earliest successful receipt observed by this application, not NASA's earliest publication. Saved-file historical availability remains unknown.

Database writes are atomic; a failed provider call cannot remove retained observations. An interrupted process or a database outage that also prevents failure recording can leave a RUNNING attempt; automatic leases/recovery are not implemented. Immutable receipt manifests can precede a failed database transaction and are not commit certificates.

## ADR-013 — P02 map and read API

Read queries require a region no wider/taller than five degrees and a 1–31 day UTC window. Results are paginated with a 500-row maximum page and offset ceiling 10000; a capped response explicitly requests a narrower window. One request uses a repeatable-read database snapshot; separate pages are current views, not a frozen export.

MapLibre renders only observations returned on the current page. SHA identities are carried in a feature property for picking/highlighting because the renderer's vector-tile feature ID conversion changed string hashes in browser testing. Pixel centres are not fire perimeters. The list remains usable without the map, and source confidence is not shown as model probability.

The small online pilot uses attributed OSM standard raster tiles with normal browser caching/referrer behavior, following the [tile policy](https://operations.osmfoundation.org/policies/tiles/). No bulk prefetch or offline map pack is implemented. Production and offline deployment need a permitted provider/assets and their own checks.

## ADR-014 — P03 facility context: dated OSM snapshots and approximate support (27 September 2026 IST)

Facility context comes from one fixed, hashed Overpass query per pilot region (`osm-industrial-v1`): industrial land use, `industrial=*`, works/flares/chimneys/kilns/wells/mineshafts/gasometers, non-renewable power plants/generators and quarries. Wind, solar and hydro are excluded as non-thermal. Individual storage tanks are excluded to keep refinery complexes from producing hundreds of near-identical candidates; tank farms still arrive through `industrial=*`. Only two Overpass hosts are allowed (main server, then a public mirror when busy). An HTTP-200 answer carrying a runtime-error remark is rejected as incomplete, never stored as complete. Non-retryable errors stop immediately.

Each response is an immutable raw object with a manifest. A snapshot records OSM's own `timestamp_osm_base` and our retrieval time; applying a snapshot newer than an observation is labelled `RETROSPECTIVE`. PostGIS builds relation areas from member lines, repairs invalid polygons and rejects anything that is not a valid point or area. Facility type (`facility-type-v1`) is a deterministic tag reading, first match wins; untyped industrial land is `UNKNOWN`. It proposes what a mapped feature is and is not a label.

The pixel support region is a circle: half the scan×track diagonal (covers the pixel in any orientation) plus a 100 m location buffer (an engineering default, not measured accuracy); nominal 375 m pixels are used and labelled when scan/track are missing. Every mapped feature intersecting the circle is kept with geodesic distance, centre containment and area overlap; features within 2 km are listed as nearby. Status distinguishes no snapshot, nothing within 2 km, nearby only, one feature and several features. Nothing is collapsed to "the nearest facility". Association is computed at read time from a fixed snapshot and version, so it is deterministic and cannot go stale; P04 feature snapshots can materialize it. Fixture context (`TEST_FIXTURE` provider) and real context never mix.

## ADR-015 — P03 events and recurring sites (`event-site-v1`)

Observations with a successful receipt in one data mode are processed in (acquisition time, ID) order. An observation joins an open event when it is within 24 h of the event's last observation and within 750 m of any member (architecture defaults, not physical laws), provided the event stays within a 1500 m maximum diameter. If it links to several events and the union stays within the diameter, they merge; otherwise it joins the nearest and the extra link is counted as ambiguous. Sites group events by location regardless of time with the same link/diameter limits; a site's identity is anchored to its first observation so it survives later growth. Distances are PostGIS geodesic metres. Event and site IDs hash membership plus the parameter hash, so identical inputs give identical IDs.

Each build is a versioned run with its parameters and an input hash; an unchanged input set returns the existing run unless forced. A rebuild records late arrivals (new observations older than the previous run's latest input) and lineage to the previous run's events: SAME, GREW, SHRANK, MERGED, SPLIT or CHANGED. Recomputation is currently whole-region; the earliest late arrival is recorded so a later optimization can restart from that checkpoint. FRP is kept as a per-event maximum and overpass count, never summed across overpasses. Events are groupings, not confirmed fires; no maximum event duration is imposed yet, so persistent sources can form long events (an open question for P04 behaviour baselines). Pairwise distances are bounded by the diameter and inputs are capped at 20,000 observations per run.

## ADR-016 — P03 land cover: ESA WorldCover 2021 v200 with rasterio

Land cover comes from the public ESA WorldCover 10 m 2021 v200 COGs (published 28 October 2022, DOI 10.5281/zenodo.7254221, CC BY 4.0), read through one allowed host prefix. For each observation, a window covering 1 km is read; class fractions are computed over pixel centres inside the support circle and a 1 km context circle using WGS84 metre scaling. Nodata (0) and unknown codes stay missing; windows running off a tile are filled as nodata and flagged, never as a class. Fewer than 50% valid support pixels is `INSUFFICIENT`. Each window is hashed and saved as a small GeoTIFF chip with a run manifest. The map year and the observation's age relative to it are shown with the product's published global accuracy (76.7 ± 0.5 %). Land cover is evidence about surroundings, not a label.

`rasterio` 1.5.1 (bundling GDAL 3.12.4) and `numpy` 2.5.3 join the backend environment rather than enabling PostGIS raster: the raster step is a bounded read per observation, and wheels exist for Python 3.13 on macOS 14+ arm64 and Linux x86_64. The macOS wheel requires macOS 14 or newer; an older Mac would need a source build with system GDAL, which is not supported here. Transitive additions were checked for licence and advisories (see EVIDENCE). A pytest filter hides one rasterio-internal PendingDeprecationWarning; ThermoScope code does not use the deprecated operator.
