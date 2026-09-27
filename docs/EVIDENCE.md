# Evidence ledger

This ledger records completed verification, not planned checks. Large audit downloads and page renders remain in the local review workspace; provider data and secrets are not copied into Git.

## Planning audit — 25-26 September 2026

| Check | Observed result | Scope / limitation |
|---|---|---|
| Public GitHub source inspection | Main commit `e110fd19398d69631d8bf3c77f78bf413f3a3aa5`; fixed backend events/facilities/classification | Source read through GitHub connector; not a fresh runtime test |
| Local Git/source inspection | `thermalguard-ai` at `c36e47a`, clean tracked tree and no remote | Original source preserved; ignored environment values not read |
| Submitted deck inspection | Six slides; XML text, embedded figures and Canva design reviewed | Claims/branding issues listed in AUDIT.md; deck not modified |
| Official SIH sources | Current guidelines and blank template inspected; table showed 93/500 at ~23:31 IST, 25 September | Snapshot only; no slot reservation, portal submission or recurring monitor |
| Provider/model research | NASA, AlphaEarth, Prithvi, OSM and other primary documentation inspected | No model training or genuine-data experiment performed |
| Version lookup | Candidate release metadata checked against official registries | No dependency installation/compatibility certification |
| Briefing render | `render_docx.py ... --emit_pdf` completed; eight page PNGs visually inspected | Document-layout verification, not application evidence |
| GitHub identity | Connector and creation UI identify `ishowguts` | Does not imply access to another owner's private data |
| Fresh remote repository | Creation UI and connector confirm `ishowguts/thermoscope`, private, push/admin permission | No application deployment or public release |
| Specification package check | 21 text files; 12 relative Markdown links resolve; DOCX ZIP/XML valid; no credential-pattern findings after checking empty-setting false positives | Local structural/content scan, not a full application security audit |
| Ignore rules | `git check-ignore` confirms `.env`, `.env.local`, local objects and raw data excluded | `.env.example` contains empty/example settings only |
| Final briefing revisions | Eight rendered pages; all pages visually inspected, with every changed page rechecked after revision | Confirms the user's available team-leader login and clean title/heading layout |
| Remote content verification | Initial commit `c534b7478aa1a6b3640a4a74e6a35124f142133c` pushed; connector confirmed matching remote `main` and 21 file blobs | Local working tree clean after push; originals preserved |

## Not yet performed

Programmatic Earthdata download, model training/evaluation, cloud deployment, offline basemap replay, cloud restore and SIH submission remain unperformed. Completed P01/P02 local ingestion, storage, API and browser evidence is recorded below.

## FIRMS access check — 26 September 2026

- Time: 10:36:45 UTC (16:06:45 IST); source commit at check: `4b73904059707832f66d96aa5eab8448a14eea10`.
- Credential stored only in ignored `.env`, file mode `0600`. Git ignore checks passed; an exact-value scan found no credential in tracked files. No key or key-bearing URL is recorded here.
- Command: bundled Python running `local/access-checks/check_firms.py`, exit 0. This is a local prerequisite check, not application implementation.
- Request: NASA FIRMS Area CSV, `VIIRS_NOAA20_NRT`, bounds west 69.5 / south 22 / east 70.5 / north 23, latest UTC day, day range 1. Redirects disabled; response and timeout bounded; errors sanitized.
- Result: HTTP 200, expected VIIRS fields present, 122 response bytes, zero observation rows. Empty data does not prove the region had no fires or establish scientific coverage.
- Local evidence: `local/access-checks/firms-access-result.json` and `local/access-checks/firms-noaa20-access-sample-20260926T103645Z.csv`, both ignored. CSV SHA-256: `2b11a44667d05367ecf77651b95fd3d34c545c7ec154856094b91245e41ae697`.
- Conclusion: FIRMS endpoint access is ready. A populated sample, historical availability, application parsing/storage and inference still require their own checks. Earthdata programmatic download has not been tested; the user subsequently confirmed web login.

## Record format for future checks

Include timestamp/timezone, task, source commit, environment/lock versions, exact command or interaction, exit/result, important output counts and artifact URI/hash. Record failures and blocked checks alongside passes. Remove secret-bearing request URLs before storing evidence. A model score additionally needs data/split/model manifests and per-class support.

## P01 local verification — 26 September 2026

Base commit `84fb66f7622a5a2c6479c6f6b26c404f6f71d752`; implementation changes initially uncommitted during these checks. The final implementation is the commit containing this ledger update. Host macOS arm64; exact versions in `ENVIRONMENT.md`.

| Check / command | Result | Boundary |
|---|---|---|
| Isolated Python/Node/uv install | Python 3.13.15, Node 24.21.0, uv 0.12.19; Node tarball SHA-256 matched official release checksum | Project-local tools; system tools preserved |
| `make configure` | Local random DB credential generated; existing FIRMS setting preserved; `.env` mode 0600 | No credential values logged |
| `make db-up`, `make migrate`, `make doctor` | Loopback DB healthy, expected migration; API readiness can connect to PostGIS | Local Compose only; no cloud provisioning |
| `make check` | Lint/format, 21 contract/API tests, TypeScript check and Vite build passed | No map, model or provider parser tested yet |
| `make integration` | One real PostGIS scenario passed: pre-migration 503, upgrade 200, duplicate/hash/mode constraints, downgrade 503, reapply 200; equatorial one-degree geography distance within 1 m of 111319.49 m | Random test-owned DB created and removed; development volume retained |
| Fresh frozen install | `UV_PROJECT_ENVIRONMENT=local/verification-venv make install` and `... make check` passed | Separate new Python environment and npm clean install; not a production image |
| Browser at `127.0.0.1:5173` | Rendered page inspected; connected/ready, replay/no-data and classifier-not-built states visible; stop DB -> needs attention; restart -> ready | Local browser check, not production deployment or MapLibre validation |
| Three bounded NASA requests at 11:36 UTC | HTTP 200, 10/1/2 rows in Jamnagar/Singrauli/Punjab; expected schema and bounds checked | Saved real samples, not application ingestion; inventory and hashes in COVERAGE_INVENTORY.md |
| npm dependency check | Zero known vulnerabilities reported during frozen install | Advisory snapshot; no claim of complete security |

Corrections made during verification: initial Make command lookup selected system tools; the explicit shell wrapper now selects the pinned local tools. TypeScript 7 required Vite's CSS module declarations. Alembic's path separator is explicit. Starlette's deprecated test HTTP client was replaced with its documented stable httpx2 client, and the suite passed without those deprecation warnings. The GDAL query failed because raster support is not enabled; raster validation remains pending. npm reported an unapproved optional fsevents install script on macOS; it was not approved, and installation/build succeeded with that restriction.

GitHub Actions is configured to use the same frozen install and check commands on Ubuntu with the digest-pinned PostGIS service. Remote run evidence is recorded separately after push; a workflow file alone is not a passed CI run.

## P01 remote verification and checkpoint — 26 September 2026

- Implementation commit: `217e4a7a26dc71a7467f538bf9740d0ab78c2b84`, pushed to private `ishowguts/thermoscope`; local branch matched origin after push.
- [GitHub Actions run 36239752092](https://github.com/ishowguts/thermoscope/actions/runs/36239752092), job 108397919111: **completed / success**. Official actions setup, fresh frozen install, `make check`, `make integration` and container cleanup all succeeded on Ubuntu 24.04. This supplies independent clean-checkout Linux evidence in addition to local macOS checks.
- PyPI advisory metadata checked for all 33 third-party locked package versions: no reported vulnerabilities in that snapshot. License metadata saved to ignored `local/python-package-review.json`; Colorama's license is given in its BSD classifier rather than SPDX field. This is not legal clearance or a complete security audit.
- 46 changed files were scanned before implementation push: zero exact matches for the local FIRMS key/database secret/connection string. Ignore checks for `.env`, real NASA samples, Python environment and npm dependencies passed; `.env` is mode 0600.
- Fifteen relative Markdown links resolved. All three saved NASA sample SHA-256 values matched their coverage manifests.
- P01 marked complete. Final checkpoint changes are documentation only and skip repeat CI; no code changed after the successful run. Local preview/database remain running as listed in `PROJECT_STATE.md`.

## P02 local implementation and verification — 27 September 2026 IST

Base commit `6358bd94394cc81bfd45963dc7302841c3fd1fda`; code was uncommitted during local checks. All tests used the frozen environment above plus MapLibre 6.11.2 and Prettier 3.9.9. The implementation commit is the commit containing this record; remote verification is recorded separately after push.

| Check | Observed result | Scope / limitation |
|---|---|---|
| `make migrate` | `0002_observations` applied; real DB ready | Retained development volume; no destructive rollback |
| `make check` | 41 unit/API cases, Python lint/format, frontend Prettier, TypeScript and Vite build passed | Includes 20 provider/parser cases; fixtures are explicit |
| `make integration` | Six real PostGIS scenarios passed | Duplicate/concurrent reversed import, quarantine, mode separation, revision conflict, provider failure with retained data, hash rejection, bounds/pagination and migration round trip |
| Real Jamnagar import | Run `0f8d43cb-7b62-4be7-8dd7-dd30ea333bb3`: 10 accepted, 10 inserted, zero rejected | Real historical replay; acquisition 22–25 September |
| Repeat Jamnagar import | Run `8f94db03-1e7c-4aa3-b07c-6f4bad4f3a7c`: 10 accepted, zero inserted, 10 duplicates | Same source snapshot and unchanged observation count |
| Singrauli / Punjab imports | Runs `4216da8c-eead-466d-9f65-ceef334df818` / `6ba22e85-f0df-446b-a01a-a3f239849865`: 1 / 2 inserted | Overall 13 real physical observations; no reviewed labels |
| Fresh NASA provider fetch | Run `cca32298-fc86-4367-85f1-f4c410e2f5fa`, received 26 September **21:53:28.757683 UTC**: 10 accepted, zero inserted, 10 duplicates | Same Jamnagar bytes/hash, distinct LIVE receipts; last acquisition 25 September 21:31 UTC, not fetch time |
| Running HTTP API smoke | Jamnagar returned ten unique IDs in each replay/live view, correct modes, source hashes and last run metadata | Local `local/p02-api-smoke.json`; no cloud API |
| Development browser | Real tiles/points; point and row selection; source measurements/hash/time; live/replay differences; regional counts 10/1/2; Punjab 24 September filter gives 1; reversed dates give error; 25 September gives zero; hidden-map list remains selectable | Native date keyboard interaction used after automation fill did not change controlled input state |
| Built browser at port 5174 | Production bundle's ESM worker rendered the map; clicking a Jamnagar point selected the matching 1.61 MW observation/evidence; no warning/error console entries | Local Vite preview, not cloud deployment; mobile and forced GPU loss not tested |
| Dependency metadata | MapLibre/Prettier stable releases and licenses inspected; npm audit reports zero known vulnerabilities | Backend dependencies unchanged; fresh complete CI install follows push |

Original real CSV hashes are in `COVERAGE_INVENTORY.md`. Application raw objects live under ignored `local/objects/raw/<sha>.csv`; receipt manifests under `local/objects/manifests/<run-id>.json`. Local import summaries: `local/p02-real-import-check.json`. No provider key, key-bearing URL or real raw data is committed.

Corrections from verification: sorted observation insertion order prevents opposite-order overlap deadlocks; earliest observed availability remains stable over repeated live receipts; impossible maximum-date queries return 422; a malformed optional CSV column is quarantined; the MapLibre renderer's string-ID conversion is avoided with an explicit property for picking/highlighting. Historical file imports do not acquire invented publication dates.

Limitations: P02 is manually invoked, VIIRS NRT only. The UI currently selects NOAA-20; other parser products are not real-data-certified here. Source-revision conflicts are preserved for review, not automatically reconciled. Interrupted attempts can remain RUNNING. List-only operation was tested; automatic WebGL-loss handling exists but was not forced. Vite's lazy map chunk remains over its 500 kB warning threshold. The online OSM basemap is not an offline tile pack. No accuracy, incident labels, classifier or operational alert readiness is claimed.

## P02 remote verification and checkpoint — 27 September 2026 IST

Session: the implementer, taking over after the integrator reached its usage limit. Takeover and exit points are in the internal handoff log.

| Check | Observed result | Scope / limitation |
|---|---|---|
| Local Git state before push (lock-free `git --no-optional-locks status`) | `main` clean, one commit ahead of `origin/main`; `origin/main` (`6358bd9`) is an ancestor of `43cf2b0` | Read on the owner's Mac checkout through the desktop bridge |
| Pre-push secret scan | Exact local FIRMS key (32 chars) and database password: zero matches in the tracked tree at `43cf2b0` or in the `6358bd9..43cf2b0` diff; generic key/secret/token pattern scan of the diff: zero findings; only `.env.example` tracked among env files; nothing under `local/` tracked | Values compared in-shell, never printed |
| Push path | Local bridge shell had no GitHub credentials. `git bundle create local/p02-handoff.bundle origin/main..main` (SHA-256 `8022814b96ef5f26c1a780fa2755d902695ab605bb250a88a0694e3b2fda7728`), verified, fetched into a cloud clone with the same hash, pushed `43cf2b0` unchanged | Same commit SHA, author and tree as the local commit; bundle deleted after sync |
| `git push origin 43cf2b0:refs/heads/main` | `6358bd9..43cf2b0` fast-forward; `git ls-remote` returned `43cf2b0453a559a4841a05de73413211d9200e3e` for `refs/heads/main` | No force push, no history rewrite |
| [GitHub Actions run 36275992464](https://github.com/ishowguts/thermoscope/actions/runs/36275992464), job 108498732565 | **completed / success**, 22:21:14–22:21:56 UTC on Ubuntu 24.04 with the digest-pinned PostGIS service. All steps ran, none skipped: `make install`; `make check` (Ruff "All checks passed", Ruff format, **41 passed, 6 deselected**, Prettier, `tsc --noEmit`, Vite build); `make integration` (**6 passed, 41 deselected**) | Job log SHA-256 `0ca5ef70397f019a60dd28cdfb0309da7e57b3b0d5d10e40633fe10c9a2b620c`, kept outside Git. Vite still warns that the map chunk exceeds 500 kB |

P02 marked done. The checkpoint commit that contains this record changes documentation only and uses `[skip ci]`; no code changed after the successful run.

Incident during takeover: an ordinary `git status` from the bridge shell at about 03:43 IST created `.git/index.lock` and could not remove it (deletion was not yet permitted). It was an empty file created by that command, and it was deleted at about 03:45 IST once permission was granted. Any Git error from another tool in that window came from this, not from repository corruption. Bridged sessions now use lock-free reads.

## P03 implementation and verification — 27 September 2026 IST (branch `p03-context`)

Base: branch point `0aa9725` (P02 complete). Commits `99c2d6f` (OSM context), `43ce845` (events/sites), `430acd6` (workbench UI), `e3c0117` (land cover), plus the documentation checkpoint containing this record. Environment: Linux x86_64 cloud workspace, Python 3.13.15, uv 0.12.19, Node 24.21.0, digest-pinned PostGIS 18-3.6 in Docker, rasterio 1.5.1 / GDAL 3.12.4. **Not yet run on the owner's Mac.**

| Check | Observed result | Scope / limitation |
|---|---|---|
| Baseline before changes | `make check` 41 passed; `make integration` 6 passed | Same numbers as P02 CI, confirming the workspace matches |
| `make check` after P03 | Ruff lint/format clean; **77 passed** (36 new: 24 OSM/support, 6 events, 6 land cover); Prettier; `tsc --noEmit`; Vite build | Vite still warns the lazy map chunk is over 500 kB |
| `make integration` after P03 | **10 passed** (4 new): context association, timing/hash/outage, events/lineage, land cover | Disposable databases created and dropped by the tests |
| GitHub Actions on `p03-context` | Runs 36277388287 (`99c2d6f`), 36277616785 (`43ce845`), 36277883106 (`430acd6`), 36278247417 (`e3c0117`): all **completed / success** | Clean Ubuntu install including rasterio wheels |
| Metre distances | Point 0.001° of longitude from a facility at 22.3° N: PostGIS 103.0 m vs WGS84 formula 103.04 m; 0.012° gives 1236.5 m vs 1236.5 m | Asserted to ±0.5 m / ±1 m in tests |
| Geometry handling | Relation with a hole: observation inside the hole is not "inside" and is 103 m from the edge; self-intersecting polygon repaired to a valid area; zero-area polygon quarantined as `INVALID_GEOMETRY` | Fixture geometry, labelled as such |
| Provider behaviour (unit) | Busy primary (504) falls back to the allowed mirror; HTTP-200 answer with a runtime-error remark rejected as `OVERPASS_INCOMPLETE` and retried; a 400 stops immediately; an unlisted host is refused; failure codes carry no request details | The 400 case was a real bug found by the test and fixed before commit |
| Real OSM retrieval | Adapter query text sent from the owner's bridge shell at 22:40–22:41 UTC: main server returned 504 once during sizing, then 200 for all three regions; responses and hashes in `COVERAGE_INVENTORY.md` | Retrieved with curl using the adapter's exact query, not by the adapter's own HTTP client; `fetch-osm` itself still needs one run on the Mac |
| Real OSM import | 313 / 208 / 126 elements accepted, zero rejected, all geometries valid; re-import of identical bytes reuses the snapshot | Current OSM applied to 22–25 September observations is flagged retrospective |
| Real association (13 observations) | 3 inside the mapped Reliance refinery; 7 around one mapped power plant (3 with it inside the pixel area); Singrauli 122 m from Jhingurdah Mine; Punjab: nothing within 2 km | Context only; no reviewed source label |
| Real events | Jamnagar 10 → 5 events at 3 sites; Singrauli 1 → 1; Punjab 2 → 2 events at 2 sites; unchanged rebuild returns `UNCHANGED` | Event grouping, not incidents |
| Real land cover | All 13 windows 100% valid; refinery 96% built-up; Punjab 99% and 71% cropland; Singrauli tree/grass/bare | WorldCover 2021, five years older than the observations; product global accuracy 76.7 ± 0.5 % |
| Land-cover ordering bug | JSONB reordered class keys, so "largest first" was lost after storage; fixed by returning a ranked list, with a test | Found by inspecting real output, not by the first tests |
| Browser (headless Chromium 1194, SwiftShader WebGL, Vite dev server + API) | Region map with facility layer; selecting refinery, power-plant, Singrauli and Punjab observations shows the dashed pixel area, candidate list, retrospective warning, land cover, event and site; map-hidden mode keeps the evidence panel; **zero console errors or warnings** after adding an inline favicon (the earlier 404 was `/favicon.ico`) | Screenshots outside Git: `ui-jamnagar-region.png` `00c170f0…`, `ui-refinery-landcover.png` `ba3f846e…`, `ui-power-selected.png` `5a30ecd3…`, `ui-punjab-landcover.png` `a6dcfbd9…`, `ui-singrauli-selected.png` `63c66bf9…`. Not the owner's browser; built preview not re-checked |
| Dependencies | rasterio, numpy and four transitive packages: permissive licences, zero PyPI advisories; `@types/geojson` declared without changing the resolved version | Advisory snapshot, not a security audit |
| Secret scan | Before each commit, the workspace database password was checked against the diff: zero matches. No FIRMS key exists in this workspace | The Mac's `.env` was never read |

Evidence gaps that keep P03 in **review**, not done: (1) no person has reviewed an adjacent industrial/agricultural hard case; the Jamnagar power-plant group is the only candidate; (2) `make install`, migrations 0003–0005, `fetch-osm`, `extract-landcover` and the browser flow have not run on the owner's Mac (rasterio needs macOS 14+ there); (3) the built production preview was not re-checked after P03.

## P04 implementation and verification — 27 September 2026 IST (branch `p04-history`)

Base `31f0498` (P03 handoff). Commits `9c1f788` (history and rules), `8357770` (assessment panel and timeline), plus the documentation checkpoint containing this record. Same Linux workspace and toolchain as P03. **Not yet run on the owner's Mac.**

| Check | Observed result | Scope / limitation |
|---|---|---|
| FIRMS data availability | NOAA-20 NRT 2026-07-01 → 2026-09-26; NOAA-20 SP → 2026-06-30 (file hash in `COVERAGE_INVENTORY.md`) | Checked at 23:11 UTC, 26 September |
| History retrieval | 51 of 51 bounded requests HTTP 200 with the VIIRS schema; key read from `.env` inside the bridge shell, piped to curl, never printed; each response checked for the key | curl with the adapter's URL form, not the application's own fetch |
| History import | 51 runs `SUCCEEDED`, 232 inserted, zero rejected; per-file SHA-256 matched sidecars | Historical replay mode; availability unknown by design |
| `make check` | Ruff clean; **104 passed** (27 new assessment tests); Prettier; `tsc`; Vite build | Map chunk still over 500 kB |
| `make integration` | **11 passed** (new: 95-day fixture history through the API — recurrent, spike → REVIEW, quiet location → new, operational exclusion, `as_of` validation, future exclusion, timeline retrieval flags) | Disposable databases |
| GitHub Actions | Runs 36279214564 (`9c1f788`) and 36279461793 (`8357770`): **completed / success** | Clean Ubuntu install |
| Rule behaviour on the pilot (retrospective) | Jamnagar power plant: industrial / persistent heat, within record (27 earlier N20 night overpasses, median 1.85 MW, z 0.89), LOW. North refinery: industrial, within record, LOW. South refinery: industrial / unresolved, new (no earlier detection in 83 retrieved days), HIGH. Four hotspots near the plant: UNKNOWN (mixed), MEDIUM. Singrauli: industrial / mining heat, within record (z −0.41), LOW. Punjab ×2: agricultural burn, new, LOW | Heuristic outcomes, uncalibrated thresholds, no reviewed labels |
| Operational replay on the pilot | Every case: behaviour insufficient ("availability not on record"), source unknown ("no OSM snapshot had been retrieved by this time"), MEDIUM | Correct: this history and OSM data were retrieved after the observations |
| Browser (headless Chromium, SwiftShader WebGL) | Three assessment cards with reasons, basis toggle, 180-day timeline (not-retrieved hatching, as-of line, tooltips on hover/focus kept inside the chart, table view) for Jamnagar, Singrauli and Punjab cases; **zero console errors or warnings** | Screenshots outside Git: `p04-power-tooltip.png` `d7325eb1…`, `p04-refinery-new-evidence.png` `64c049e8…`, `p04-singrauli-evidence.png` `23f28b30…`, `p04-punjab.png` `1498f8e9…`, `p04-power-operational.png` `cbe32e3a…`, `p04-timeline.png` `d9d7997c…` |
| Chart palette | Night `#2a78d6` / day `#eb6834` validated with the dataviz validator: CVD ΔE 24.7, normal-vision ΔE 33.6, contrast ≥ 3:1 on the chart surface | Light theme only, matching the app |
| Fixes found during verification | Unit-test tolerance vs 3-decimal rounding; "current max" wording clarified as the 24 h episode maximum within 750 m; groups not compared are listed; operational reason when the observation itself is unavailable; tooltip overflow at the right edge; y-axis headroom; empty priority notes | All re-checked |
| Secret scan | Workspace database password: zero matches in each diff; no FIRMS key in the cloud workspace | The Mac `.env` was read only inside the bridge shell |

Open items: thresholds need calibration on reviewed cases (P05); 180-day windows are ~50% covered until the SP archive is added; the Mac run; the P03 hard-case review.

## 27 September 2026 — independent P03/P04 review and Mac integration

The `p04-history` head `f7e99dc` was reviewed in an isolated worktree/database. Baseline 104 unit/API + 11 PostGIS checks passed on Mac. Five independently reproduced failing regression cases exposed missing-history, product/partial coverage, OSM boundary and raster-window defects; these were fixed. A sixth regression and actual source inspection exposed a solar photovoltaic feature treated as industrial heat evidence. Review commit `329b716` contains the corrections; details in internal record P03-P04-REVIEW.

**Correction to the older P03/P04 records above:** OSM way 1002375165 is tagged solar photovoltaic. It is not evidence of a combustion heat source. Three old industrial rule outputs are now UNKNOWN; all seven recent observations around that feature are UNKNOWN. No incident or actual source has been independently established. The earlier recorded outputs remain historical implementation behavior, not accepted truth.

| Check | Result | Limits |
| --- | --- | --- |
| Frozen Mac install | Python/npm install, rasterio/NumPy and direct WorldCover reads succeeded on macOS 26.3 arm64 | PostGIS runs in the pinned amd64 Docker image under emulation |
| Automated review checks | 106 unit/API + 15 PostGIS tests passed; lint/format/typecheck/build passed | Six review regressions; fixtures remain separate from real inputs |
| Real provider/context | Adapter OSM Jamnagar run `a1ddd2ea-a052-4269-874a-c028700112f2`: 313 accepted, 0 rejected; WorldCover 13/13 success | Three-region pilot, dated 2021 land cover, no truth labels |
| Data loading | 232 saved history rows + 13 recent observations = 245; 133 events / 45 sites; raw hashes matched inventory | History retrieval is not continuous cloud-free coverage |
| Built browser | Solar UNKNOWN and source tags; operational replay excludes unavailable history/context; timeline/table; Punjab and list-only flow; zero warnings/errors | Desktop Mac; forced WebGL context loss and mobile not exercised in this review |
| Main migration/data preservation | 0002 → 0005; preexisting 13-observation fingerprint `54a75ac875ca21352d81dc5dd80e2469` unchanged; original 33 receipts retained | Backup directory inspected; full restore not performed |
| Main runtime | API ready HTTP 200; all 13 recent assessments return rules-v2; 3 solar abstentions asserted; historical reimport 0 inserted / 7 duplicates; 245 total unchanged | Main is a local research preview, not a public deployment |
| Review branch CI | [Run 36313891363](https://github.com/ishowguts/thermoscope/actions/runs/36313891363) succeeded on `329b716` | Clean GitHub checkout |
| Integrated main CI | [Run 36314032712](https://github.com/ishowguts/thermoscope/actions/runs/36314032712), job `108605230663`, succeeded on `b87fa869cbf7a1e1c804d9673ac5ec0c3f8a1d7e`; frozen install, make check and make integration all success | Final checkpoint is documentation only; no application changes after this run |
| Human domain review | Three-case sheet prepared with hashes, dates, limitations and blank reviewer fields | Pending; no generated human sign-off or gold labels |

Main preserves original branch authorship, both merge histories, and the newer P05 handoff. P05 branch `4b76b57` is not merged or independently accepted here. Additional P05 files were left untouched; the import allowlist was narrowed after newly collected regions caused the initial inventory guard to stop before OSM/history ingestion. No data corruption occurred. The first main push was rejected because a documentation handoff advanced the remote; it was merged normally, then pushed without rewriting history.

Temporary 8001/5175 review servers and the stale 5174 preview were stopped. Main 8000/5173 and PostGIS 55432 remain. Review database and local evidence retained. No SIH submission, deck modification, public release or paid resource was performed in this task.

## 27 September 2026 evening IST — P05 coordination and current submission check

Current refs were fetched and the branch task/code/history inspected. Main and origin/main were equal at `8adef15c56ba469b3f107e50a3449bc2a16f6324` with a clean tree. P05 had advanced to `579aaf3649306b61ddcd81ff16938c86b622d908`, including `f24a910` (date-proxy removal and tightened gates), but did not include reviewed main. The earlier 13-unpushed-commits warning is resolved.

- GitHub Actions [36314415781](https://github.com/ishowguts/thermoscope/actions/runs/36314415781), job 108606292697, independently checked as completed/success: install, install-ml, check and integration. This is branch CI evidence, not a new local execution or full P05 scientific review.
- Branch documentation reports 135 unit/API and 13 integration tests after its review fixes. Its dataset/case counts and lack of human reviews remain reported branch state, not a fresh database recount.
- The [official SIH PS table](https://www.sih.gov.in/sih2026PS) was opened in the browser and filtered to SIH26162: **140/500**, **30 September 2026**, checked around **21:58 IST, 27 September** (clock check 16:28:13 UTC). Direct text retrieval was blocked; the actual browser table supplied this evidence. No signed-in portal constraints were inspected.
- Current task/known-limit inspection identified outstanding history, independent evidence, geographic protocol, label metadata and Mac ML gates; these are explicit in internal record P05-RECONCILE. No newly reproduced code defect or final review verdict is claimed.
- This checkpoint changes documentation only. No application tests repeated; no database, secrets, paid resource, public release or submission changed. Complete pending-work list: `REMAINING_WORK.md`.
