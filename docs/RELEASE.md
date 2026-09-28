# ThermoScope demo release — candidate notes

Prepared on 28 September 2026 IST under `P08-REL-001` (internal record P08-RELEASE-CHECKS). **Status: candidate, not frozen.** The release is whatever the integrator integrates and tags after its own verification; nothing here is a tag, a public release or a deployment.

## 1. What the candidate is

`main` (`c1d48b8`, accepted P01–P05) plus two branches awaiting the acceptance:

| Branch | Adds |
| --- | --- |
| `p07-demo` (tip `1f951f1`, CI green) | P07-SUB-001: offline historical-replay package, bounded CSV/GeoJSON evidence exports, map-free fallback, status strip, accessibility fixes. Runbook: `docs/DEMO_RUNBOOK.md` |
| `p08-release` (stacked on `p07-demo`) | These notes, release checks and their tooling/tests: `scripts/release_audit.py`, `backend/tests/test_release_secrets.py`, per-stage load timings |

It is a **research demonstration of saved real observations**: NASA FIRMS VIIRS NOAA-20 detections with dated OpenStreetMap and ESA WorldCover context, 180-day history and transparent, uncalibrated source/behaviour/review-priority rules. It does not monitor live, send alerts, serve a learned model, report accuracy or confirm incidents. Human validation is deferred (ADR-024).

## 2. Freezing it

After reviewing both branches (in a separate worktree, not the Mac main checkout):

```bash
git fetch origin
git switch main && git pull --ff-only
git merge --no-ff origin/p08-release        # contains p07-demo
make install && make install-ml && make check && make integration   # expect 158 + 23 passed
git push origin main                        # then wait for CI to pass
git tag -a <release-name> -m "ThermoScope demo release: offline replay, evidence exports" <merge-sha>
git push origin <release-name>
```

The tag name, whether to publish a GitHub release and whether to make anything public are owner decisions. Record the tag, commit, CI run and the package hash actually demonstrated in `docs/EVIDENCE.md`. If the Mac builds its own demo package, its content hash is the one to quote (runbook §2).

## 3. Verified for this candidate (cloud workspace, 28 September)

| Check | Result |
| --- | --- |
| Fresh clone of `p07-demo` (`1f951f1`) | Cold frozen install 7.1 s (downloaded Python 3.13.15, 37 packages, `npm ci`); ML group 1.0 s; `make check` 155 passed + lint/format/type/build (14.3 s); `make integration` 23 passed (33.6 s); `doctor`: database, PostGIS, schema ok |
| Demo from the fresh clone | Package verified with its expected hash; loaded offline into a new, migrated database (`ok: true`, 50.9 s); API health, readiness, status and observations 200; production UI build served by `vite preview` with `VITE_BASEMAP=off`, network refused: 57 rows in 0.67 s, evidence panel 0.76 s, evidence download, **0 external requests, 0 console errors** |
| Branch checks (`p08-release`) | `make check` 158 passed; `make integration` 23 passed |
| Dependency vulnerabilities | OSV for every locked version (48 Python incl. ML and dev tools, 93 npm incl. dev): **0 known**; `npm audit`: 0 |
| Licences | Section 6 |
| Secret safety | With an unreachable database and recognisable fake password, FIRMS key and reviewer token: 14 API paths (normal and review-only servers) return handled errors and no secret in bodies, headers or logs; six failing commands (ingest, P05 CLI ×2, demo build/load, migrations) print no secret. 124 tracked files: no credentials, tokens, private keys, key-bearing URLs or files over 300 KB; provider payloads are not tracked |
| Backup and restore | `pg_dump -Fc` of the demo database 1.7 s (3.1 MB) → restore into a new database 1.4 s: 25 tables, 34,471 rows, identical content fingerprints; migration `0008`, PostGIS 3.6.4 on both; 11 API responses identical apart from their request time. Object folder archived (0.7 s, 11 MB) and restored: 3,403 content-addressed objects all match their names |
| Rebuild from the package | Load into an empty database 50–57 s: verify 0.3 s, FIRMS 12.7 s, OSM 0.7–0.8 s, land-cover summaries recomputed from chips 28–33 s, events 8.6–10.1 s |
| API | Per P07: list 0.05 s, window export 0.04–0.05 s (57 observations), with rule outputs 3.6–3.8 s, one assessment 0.06–0.08 s, evidence export 0.22–0.28 s |
| Satellite/provider delay | **Not measurable here.** Every file is a historical replay retrieved in bulk weeks or months after acquisition, and historical availability is unknown; the retrieval lag in the manifest reflects when this project fetched, not FIRMS latency |
| P05 model artifacts | 10 recorded runs: every manifest hash and file hash matches. 5 reviewed-label runs `INSUFFICIENT_LABELS`, 5 weak-rule runs `DRY_RUN_NOT_EVIDENCE`. There is no evaluation to reproduce and no score to quote |
| Recovery incidents | The workspace's Docker daemon stopped three times while idle; each time `dockerd` + `docker start ts-pg` restored PostGIS within seconds with all data intact (named volume). On the Mac, `make db-up`; never remove the volume |

## 4. Data card — demo package `thermoscope-demo-v1`

- **Contents:** 5,971 NASA FIRMS VIIRS NOAA-20 detections for Jamnagar (69.5–70.5 E, 22–23 N) and the Punjab comparison region (74.5–75.5 E, 30–31 N): NRT 1 July–26 September 2026, SP 30 December 2025–30 June 2026, in 110 five-day files (the last SP window three days). Two OpenStreetMap Overpass extracts (retrieved 26 September 2026). 3,307 ESA WorldCover 2021 chips with summaries; 2,664 detections have no land-cover summary and show it as missing.
- **Provenance:** every file's SHA-256, size, window, source, licence and the source database's import time and status; provider retrieval times for 108 of 110 FIRMS files. Content hash `e5117f72…0464` (workspace build). Mode: historical replay; historical availability unknown.
- **Meaning:** a detection is a satellite pixel centre with fire radiative power (MW) and brightness temperatures (K, not flame temperature); the heat can lie anywhere in the approximate pixel area. A non-detection does not prove absence (cloud, overpass gaps). OSM is volunteer-mapped and incomplete; WorldCover describes 2021.
- **Not included:** labels, reviews, reviewer accounts, frozen case sets, features, model outputs, basemap tiles, credentials.
- **Licences:** FIRMS (NASA open data; acknowledgement), OSM ODbL-1.0 (attribution; share-alike for derived databases), WorldCover CC-BY-4.0 (doi:10.5281/zenodo.7254221). Attribution travels in the manifest, README and every export.

## 5. Model status card

- **Built:** XGBoost/baseline training and evaluation pipeline on the frozen `p05-pilot-v2` case set (10,318 cases, 2,437 facility-aware groups; TRAIN 6,488 / VALIDATION 2,060 / TEST 1,770), `case-features-v4` (10,035 history-complete), blind review workflow with personal reviewer accounts.
- **Not built / not available:** reviewed labels (zero human reviews), an evaluated model, calibration, accuracy or any reportable metric. The workbench serves **no** learned predictions; exports say `learned_model = NOT_SERVED` and `human_validation = PENDING`.
- **What runs:** transparent rules with uncalibrated thresholds (`rules_version` in every assessment). Rule outputs are review aids, not probabilities or labels.

## 6. Licences and public-release blockers

- **Dependencies:** permissive (MIT, BSD, Apache-2.0, ISC and similar) except `certifi` (MPL-2.0), `psycopg`/`psycopg-binary` (LGPL-3.0-only; the binary wheel bundles libpq and OpenSSL with their own notices) and the build-time CSS tool `lightningcss` (MPL-2.0; not part of the shipped bundle). All are used unmodified as libraries. The browser bundle's runtime packages are MIT/ISC/BSD (MapLibre GL BSD-3-Clause, React MIT). The PostGIS server image is GPL-2.0-licensed and runs as a separate service; distributing an image would carry its obligations. Full inventory: run `scripts/release_audit.py` (workspace report SHA-256 `472e188c…`, outside Git).
- **Map tiles:** online, the basemap uses OpenStreetMap standard tiles under the OSMF tile usage policy (attribution, no bulk or heavy use). A public or high-traffic deployment needs its own tile provider; offline, the basemap is off.
- **Before any public repository or release (owner decision, nothing published):**
  1. Choose a code licence — the repository has none, so no reuse is granted.
  2. Decide what personal and team information stays: team name, ID, leader name and institute appear in 15 tracked files (for example `PROJECT_STATE.md`, `docs/SUBMISSION_*.md`, `docs/REMAINING_WORK.md`) and the UI footer; `docs/SUBMISSION_PACKAGE.md` contains a local user path.
  3. Decide whether internal process records (the contributor guide, the work contract, `docs/tasks/`) belong in a public copy.
  4. Re-run the secret scan on the exact allowlist; keep provider data out of Git (the ignore rules already exclude `local/`, `.env*` and rasters).

## 7. Judge-facing links (checked signed out, 28 September)

| Link | Result |
| --- | --- |
| NASA FIRMS, OSM copyright, OSMF tile policy, CC BY 4.0, ESA WorldCover data access | Load (HTTP 200) |
| WorldCover Zenodo record (doi:10.5281/zenodo.7254221) | Loads; CC-BY-4.0 and the DOI shown (the workspace's own HTTP client was refused; the web fetcher succeeded) |
| WRI Global Power Plant Database (P05 registry) | Public; data CC BY 4.0, code MIT; unmaintained since 2022 |
| `github.com/ishowguts/thermoscope` | 404 signed out: private, **not** a judge-accessible link |
| SIH portal pages, template and guidelines (`sih.gov.in`) | Refused (HTTP 403) to both automated fetchers from this cloud workspace — **not verified**; check in a signed-out browser |
| The deck's five reference hyperlinks | Not checked here: the PDF is a separately owned submission file on the Mac |

## 8. Claims delta for the deck, text and video (; submission files untouched)

**Now demonstrable** (after the integrator accepts `p07-demo`): an offline replay of saved real NASA FIRMS observations for two regions, loaded and served with the network refused; per-observation evidence (measurements, mapped OSM context, 2021 land cover, 180-day history, transparent rules with reasons and missing data); bounded CSV/GeoJSON evidence exports with units, provenance and licences; a map-free mode; reproducible setup from a clean clone; no known dependency vulnerabilities in the locked versions; a rehearsed database backup and restore.

**Suggested wording:** "A working research prototype replays genuine NASA FIRMS satellite detections with mapped industrial context, land cover and history, explains each rule-based assessment and its uncertainty, and exports the evidence with full provenance — offline if needed. The labelling and model-training pipeline is built; the model has not yet been independently evaluated."

**Do not claim:** live or real-time monitoring, alerts, deployed or public service, AI/ML detection or accuracy, validated or confirmed industrial incidents, calibrated probabilities, offline basemaps, performance targets, all 14 regions offline (the package holds two; the full local database holds 51,354 observations across 14 regions), or that a persistent heat source is safe.

**Video (optional, not recorded here):** follow runbook §5 — refinery candidate (High review priority, "review order, not accident likelihood"), persistent container-terminal heat (Low, "not certified safe"), the Unknown solar case, a Punjab cropland contrast and an export — with the status strip visible and the basemap off or clearly online.

## 9. Still open for P08 (not done here)

Hosting provider, budget cap, TLS, authentication, private database, monitoring, retention and a deployment smoke test (only if hosting is chosen); a Mac run of the offline demo with Wi-Fi off; the deck/text/video refresh and signed-out check of the deck's links; the code licence and public allowlist decisions; human validation and any model claims (ADR-024).
