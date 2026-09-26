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
