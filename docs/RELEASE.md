# ThermoScope demo release `v0.8.0-demo`

Prepared on 28 September 2026 IST under `P08-REL-001` (internal record P08-RELEASE-CHECKS). **Status: released on 29 September 2026 as the annotated tag `v0.8.0-demo` on `78e73de` (CI green), published from the owner's Mac** (`local/p08-verify/finish_release_mac.sh`, after `verify_release_mac.sh` passed on macOS: 164 + 23 tests, offline demo load) because the cloud workspace cannot push tags. Integrated with the owner's explicit approval. It is not a public release, a GitHub release page or a deployment.

## 1. What the release is

`main` (`c1d48b8`, accepted P01–P05) plus two branches, merged in `1e22d54` after two independent reviews of each and green CI:

| Branch | Adds |
| --- | --- |
| `p07-demo` (tip `1f951f1`, CI green) | P07-SUB-001: offline historical-replay package, bounded CSV/GeoJSON evidence exports, map-free fallback, status strip, accessibility fixes. Runbook: `docs/DEMO_RUNBOOK.md` |
| `p08-release` (stacked on `p07-demo`) | These notes; release tooling (`scripts/release_audit.py`, `scripts/public_release_review.py`) with tests (`test_release_secrets.py`, `test_release_audit.py`); per-stage load timings; a JSON error instead of a traceback when the demo script cannot reach the database |

It is a **research demonstration of saved real observations**: NASA FIRMS VIIRS NOAA-20 detections with dated OpenStreetMap and ESA WorldCover context, 180-day history and transparent, uncalibrated source/behaviour/review-priority rules. It does not monitor live, send alerts, serve a learned model, report accuracy or confirm incidents. Human validation is deferred (ADR-024).

## 2. How it was frozen

On 29 September the branches were merged into `main` in a cloud clone (`1e22d54`), re-ran `make check` (164) and `make integration` (23), updated these records (`78e73de`), pushed and waited for CI ([36472978149](https://github.com/ishowguts/thermoscope/actions/runs/36472978149), success). The tag push from there was refused by the workspace's Git proxy (HTTP 403), so the tag is created on the Mac: in the Mac checkout, `bash local/p08-verify/verify_release_mac.sh` (isolated clone; the checkout and its database are not changed), then `bash local/p08-verify/finish_release_mac.sh`, which refuses unless the report shows every step passed, fast-forwards `main`, creates the annotated `v0.8.0-demo` on `78e73de` and pushes only that tag. `the handoff log` records the commits and CI run. The general procedure, for a later release:

```bash
git fetch origin
git switch main && git pull --ff-only
git merge --no-ff -m "Integrate P07 demo and P08 release checks" origin/p08-release   # contains p07-demo
make install && make install-ml && make check && make integration   # expect 164 + 23 passed
# update README (drop "awaiting acceptance"), PROJECT_STATE, EVIDENCE and HANDOFF, commit
git push origin main                        # then wait for CI to pass on this pushed tip
git tag -a <release-name> -m "ThermoScope demo release: offline replay, evidence exports" <pushed-tip-sha>
git push origin <release-name>
```

The tag name, whether to publish a GitHub release and whether to make anything public are owner decisions. Record the tag, commit, CI run and the package hash actually demonstrated in `docs/EVIDENCE.md`. If the Mac builds its own demo package, its content hash is the one to quote (runbook §2).

## 3. Verified for this candidate (cloud workspace, 28 September)

Evidence files are in the cloud workspace (`fresh2/` and `p08/`, outside Git); numbers below come from them.

| Check | Result |
| --- | --- |
| Fresh clones from GitHub, empty caches | Final tip `05a2431`: `make install` 9.9 s (downloads Python 3.13.15, locked packages, `npm ci`), `make install-ml` 1.1 s, `make check` **164 passed** + lint, format, types, build (21.6 s), `make integration` **23 passed** (46.1 s), audit exit 0. Candidate `c17ba3b` (the full demo run below): 162 + 23, `doctor` ok. `p07-demo` `1f951f1`: 155 + 23. Later commits changed only CLI error reporting, release tooling and tests. CI [36466090643](https://github.com/ishowguts/thermoscope/actions/runs/36466090643) (`05a2431`) and every earlier branch run: success |
| Demo from the `c17ba3b` clone | Package verified with its expected hash (0.36 s); loaded offline into two new, migrated databases (`ok: true`, 5,971 rows each, 65.8 s and 77.7 s) and reloaded (`ok: true`, nothing inserted, events `UNCHANGED`, 55.2 s); API health, readiness, status, observations and CSV export 200; production UI build (`vite preview`, `VITE_BASEMAP=off`) with the network refused: 57 rows in 0.75 s, evidence panel 1.7 s, evidence download, **0 external requests, 0 console errors** |
| Dependency vulnerabilities | `release_audit.py` from that clone: OSV for every locked version (48 Python incl. ML and dev tools, 93 npm incl. dev, 28 of them in the runtime bundle): **0 known**; installed versions equal the lockfile; exit 0. `npm audit`: 0 |
| Licences | Section 6 |
| Secret safety | Tests with an unreachable database and a recognisable fake password, a well-formed fake FIRMS key and a well-formed fake reviewer token: 14 API requests on a normal and on a blind-review server each return the status of the step they test (503 at the database, 403 where withheld, 200 for liveness/status) and no secret appears in bodies, headers or logs; FIRMS provider failures carrying the key never expose it, tracebacks included; six failing commands (ingest — given a matching file hash so only the database can fail — P05 CLI ×2, demo build/load, migrations) fail at the database and print no secret. A test mutation that logs the token makes them fail |
| Tracked files | `docs/inventory/public-release-review.csv` (131 files at `9ccc49c`): the screen for FIRMS keys and API URLs, database URLs and password/secret/token assignments, reviewer and GitHub tokens, JWTs and private keys finds none; the real workspace database password is also absent from the branch; largest file 80 KB; provider payloads are not tracked. Section 6 lists what needs a decision |
| Backup and restore | `pg_dump -Fc` of the fresh-clone demo database 0.96 s (3.1 MB) → restore into a new database 1.96 s: 25 tables, 34,471 rows, identical content fingerprints; migration `0008`, PostGIS 3.6.4 on both; 11 API responses identical apart from their request time. Object folder archived and restored: 3,403 content-addressed objects all match their names. (An earlier run on the workspace demo database: 1.7 s / 1.4 s, same result) |
| Pipeline stages (four saved loads) | verify 0.3–0.4 s, FIRMS 12.7–17.3 s, OSM 0.8–0.9 s, land-cover summaries recomputed from chips 33–42 s, events 10.1–18.8 s (1.6 s when unchanged). Totals on this 2-vCPU workspace: 57–78 s into empty databases, 55 s for a reload; earlier unsaved P07 loads took 49–53 s |
| API | Per P07: list 0.05 s, window export 0.04–0.05 s (57 observations), with rule outputs 3.6–3.8 s, one assessment 0.06–0.08 s, evidence export 0.22–0.28 s |
| Satellite/provider delay | **Not measurable here.** Every file is a historical replay retrieved in bulk weeks or months after acquisition, and historical availability is unknown; the retrieval lag in the manifest reflects when this project fetched, not FIRMS latency |
| P05 model artifacts | 10 recorded runs: every manifest hash and file hash matches. 5 reviewed-label runs `INSUFFICIENT_LABELS`, 5 weak-rule runs `DRY_RUN_NOT_EVIDENCE`. There is no evaluation to reproduce and no score to quote |
| Recovery incidents | The workspace's Docker daemon stopped three times while idle; each time `dockerd` + `docker start ts-pg` restored PostGIS within seconds with all data intact (named volume). On the Mac, `make db-up`; never remove the volume |

## 4. Data card — demo package `thermoscope-demo-v1`

- **Contents:** 5,971 NASA FIRMS VIIRS NOAA-20 detections for Jamnagar (69.5–70.5 E, 22–23 N) and the Punjab comparison region (74.5–75.5 E, 30–31 N): NRT 1 July–26 September 2026, SP 30 December 2025–30 June 2026, in 110 files (106 five-day windows and 4 three-day ones: SP 28–30 June and NRT 19–21 September for each region). Two OpenStreetMap Overpass extracts (retrieved 26 September 2026). 3,307 ESA WorldCover 2021 chips with summaries; 2,664 detections have no land-cover summary and show it as missing.
- **Provenance:** every file's SHA-256, size, window and source, the licence and attribution of each source, and the source database's import time and status; provider retrieval times for 108 of 110 FIRMS files. Content hash `e5117f72…0464` (workspace build). Mode: historical replay; historical availability unknown.
- **Meaning:** a detection is a satellite pixel centre with fire radiative power (MW) and brightness temperatures (K, not flame temperature); the heat can lie anywhere in the approximate pixel area. A non-detection does not prove absence (cloud, overpass gaps). OSM is volunteer-mapped and incomplete; WorldCover describes 2021.
- **Not included:** labels, reviews, reviewer accounts, frozen case sets, features, model outputs, basemap tiles, credentials.
- **Licences:** FIRMS (NASA open data; acknowledgement), OSM ODbL-1.0 (attribution; share-alike for derived databases), WorldCover CC-BY-4.0 (doi:10.5281/zenodo.7254221). Attribution travels in the manifest, README and every export.

## 5. Model status card

- **Built:** XGBoost/baseline training and evaluation pipeline on the frozen `p05-pilot-v2` case set (10,318 cases, 2,437 facility-aware groups; TRAIN 6,488 / VALIDATION 2,060 / TEST 1,770), `case-features-v4` (10,035 history-complete), blind review workflow with personal reviewer accounts.
- **Not built / not available:** reviewed labels (zero human reviews), an evaluated model, calibration, accuracy or any reportable metric. The workbench serves **no** learned predictions; exports say `learned_model = NOT_SERVED` and `human_validation = PENDING`.
- **What runs:** transparent rules with uncalibrated thresholds (`rules_version` in every assessment). Rule outputs are review aids, not probabilities or labels.

## 6. Licences and public-release blockers

- **Dependencies:** permissive (MIT, BSD, Apache-2.0, ISC and similar) except `certifi` (MPL-2.0), `psycopg`/`psycopg-binary` (LGPL-3.0-only) and the build-time CSS tool `lightningcss` (MPL-2.0; not part of the shipped bundle). All are used unmodified as libraries and are listed as reviewed exceptions in `scripts/release_audit.py`, which fails on any new one. The browser bundle's runtime packages are MIT/ISC/BSD (MapLibre GL BSD-3-Clause, React MIT). Binary wheels also bundle native libraries under their own licences — for example libpq and OpenSSL in `psycopg-binary`, GDAL and about 28 libraries (libcurl, OpenSSL, HDF5 …) in `rasterio`, and libgfortran (GPL-3.0+ with the GCC runtime exception) and libquadmath (LGPL-2.1+) in NumPy/SciPy — which matters only if binaries or images are redistributed. The PostGIS server image is GPL-2.0-licensed and runs as a separate service; distributing an image would carry its obligations. Report from the fresh clone: SHA-256 `e2e48a3b…` (outside Git).
- **Map tiles:** online, the basemap uses OpenStreetMap standard tiles under the OSMF tile usage policy (attribution, no bulk or heavy use). A public or high-traffic deployment needs its own tile provider; offline, the basemap is off.
- **Before any public repository or release (owner decision, nothing published):**
  1. Choose a code licence — the repository has none, so no reuse is granted.
  2. Go through `docs/inventory/public-release-review.csv` (regenerate with `scripts/public_release_review.py`, identity terms kept in an ignored local file): 21 committed files carry team or personal identity (team name, ID, leader name, institute or account handle — for example `PROJECT_STATE.md`, `docs/SUBMISSION_*.md`, `docs/REMAINING_WORK.md`, and the sidebar/footer in `frontend/src/Rail.tsx`, `Review.tsx`, `main.tsx`); `docs/SUBMISSION_PACKAGE.md` contains a local user path; 19 files are internal process records (the contributor guide, the work contract, the contributor notes, the contributor rules, `docs/tasks/`, `docs/review/`).
  3. Re-run that review and the secret scan on the exact allowlist; keep provider data out of Git (the ignore rules already exclude `local/`, `.env*` and rasters).

## 7. Judge-facing links (checked signed out, 28 September)

| Link | Result |
| --- | --- |
| NASA FIRMS, OSM copyright, OSMF tile policy, CC BY 4.0, ESA WorldCover data access | Load (HTTP 200) |
| WorldCover Zenodo record (doi:10.5281/zenodo.7254221) | Loads; CC-BY-4.0 and the DOI shown (the workspace's own HTTP client was refused; the web fetcher succeeded) |
| WRI Global Power Plant Database (P05 registry) | Public; data CC BY 4.0, code MIT; unmaintained since 2022 |
| `github.com/ishowguts/thermoscope` | 404 signed out: private, **not** a judge-accessible link |
| SIH portal pages, template and guidelines (`sih.gov.in`) | Refused (HTTP 403) to both automated fetchers from this cloud workspace — **not verified**; check in a signed-out browser |
| The v6 deck's six reference links (slide 6) | Resolve to the named pages (29 September, web fetcher): FIRMS, the Zenodo WorldCover record, Ma et al. (Nature Scientific Data), Caseiro et al. and Soltan and González-Martínez (MDPI), the Earth Engine Satellite Embedding catalog |

## 8. Claims delta for the deck, text and video

Applied on 29 September in submission package v6 and the demo video (`docs/SUBMISSION_PACKAGE.md`). Kept here as the reference for any later wording.

**Now demonstrable:** an offline replay of saved real NASA FIRMS observations for two regions, loaded and served with the network refused; per-observation evidence (measurements, mapped OSM context, 2021 land cover where extracted, 180-day history, transparent rules with reasons and missing data); bounded CSV/GeoJSON evidence exports with units, provenance and licences; a map-free mode; reproducible setup from a clean clone; no known dependency vulnerabilities in the locked versions; a rehearsed database backup and restore.

**Suggested wording:** "A working research prototype replays genuine NASA FIRMS satellite detections with mapped industrial context, land cover where available and detection history, explains each rule-based assessment and its uncertainty, and exports the evidence with its sources, hashes and licences — offline if needed. The labelling and model-training pipeline is built and tested, but no model has been trained on human-reviewed labels; none is served or evaluated."

**Do not claim:** live or real-time monitoring, alerts, deployed or public service, AI/ML detection or accuracy, validated or confirmed industrial incidents, calibrated probabilities, offline basemaps, performance targets, all 14 regions offline (the package holds two; the full local database holds 51,354 observations across 14 regions), or that a persistent heat source is safe.

**Video (recorded 29 September, not uploaded):** runbook §5 order — refinery candidate (High review priority, "review order, not accident likelihood"), persistent container-terminal heat (Low, "never certified safe"), the Unknown solar case, a Punjab cropland contrast and exports — with the status strip visible and the basemap off; recorded with internet access refused.

## 9. Still open for P08 (not done here)

Hosting provider, budget cap, TLS, authentication, private database, monitoring, retention and a deployment smoke test (only if hosting is chosen); the Mac verification and tag (owner's scripts) and a Mac run of the offline demo with Wi-Fi off; the team's review of submission package v6 and the signed-out check of `sih.gov.in`; the code licence and public allowlist decisions; human validation and any model claims (ADR-024).
