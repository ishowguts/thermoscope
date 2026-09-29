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

Programmatic Earthdata download, model evaluation on reviewed labels (the P05 pipeline exists and refuses to report without them), cloud deployment, offline basemap replay, cloud restore and SIH submission remain unperformed. Completed P01/P02 local ingestion, storage, API and browser evidence is recorded below.

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

## P05 implementation and verification — 27 September 2026 IST (branch `p05-model`)

Base `f7e99dc` (P04 handoff). Commits `c17a888` (data, events v2, batch jobs), `ad882aa` (labels, API, model pipeline), `f62d15c` (review page), `956b352` (documentation), plus the handoff commit. Linux x86_64 cloud workspace, Python 3.13.15, PostGIS 18-3.6 (digest-pinned), Node 24.21.0. **Not run on the owner's Mac.**

| Check | Observed result | Scope / limitation |
|---|---|---|
| FIRMS retrieval | 464 of 464 bounded requests HTTP 200 (SP 30 Mar–30 Jun for 14 regions; NRT 1 Jul–25 Sep for 11 new regions), 09:26–09:56 UTC; key read inside the bridge shell, piped to curl, never printed; each response checked for it | Hashes in `docs/inventory/p05-firms-files.csv`, re-verified before import |
| FIRMS import | 464 runs `SUCCEEDED`, 23,746 inserted, 0 quarantined | Historical replay; availability unknown by design |
| OSM | 11 new snapshots imported: 10 `SUCCEEDED`, Mumbai `PARTIAL` (2 unclosed area ways quarantined) | Two Mumbai attempts were truncated at 50 s and rejected before a 160 s attempt succeeded |
| GPPD | `global_power_plant_database.csv` v1.3.0, SHA-256 `4b1f93e0…ba7fc`; re-downloaded at 10:33 UTC with the identical hash; 388 Indian thermal plants imported | Registry dated 2021 |
| Events `event-site-v2` | 14 regions, 23,991 inputs → 10,318 episodes, 6,774 sites in 53 s (earlier attempt hit the 2 s API timeout; fixed with batch jobs and an indexed pair query) | Groupings, not confirmed fires |
| Case set `p05-pilot-v1` | 10,318 cases, 2,462 site groups, TRAIN 6,481 / VALIDATION 2,050 / TEST 1,787; **0 site groups span two splits**; manifest SHA-256 `fd1e627a…27068` | An earlier build (same splits, TEST-first review order) was deleted before any review and rebuilt with the interleaved order |
| Land cover and features | WorldCover summaries for all 10,318 representatives (0 failed); features for 10,318 cases in 9 m 27 s; 9,628 rule labels, 240 registry corroborations | Singrauli and Talcher have no case within 1.5 km of a registered plant |
| Training, reviewed policy | `INSUFFICIENT_LABELS` (model `xgb-source-binary-v2`, version `683e2e9b…`, artifact manifest `0dcd4217…`): 33 industrial / 0 non-industrial training cases, 0 GOLD test cases | Correct refusal |
| Training, `--dry-run-weak` | `DRY_RUN_NOT_EVIDENCE` (`252331fd…`, `2362e323…`), 42 inputs, 6,103 train / 1,892 validation / 1,659 test rule-labelled cases; model card and model list withhold scores; metrics carry a do-not-quote notice | Circular by design: proves only that the pipeline runs. The earlier v1 runs (45 inputs) were deleted after the review below |
| Independent review (separate read-only pass, no prior context) | No high-severity defect. Fixed: coverage and 180-day history inputs acted as a date proxy (removed; model v2); validation gate now needs 5 cases per class; agreement kappa now ignores "cannot decide" pairs; dry-run scores no longer stored in the model list; known-site-future now has support minimums and test-eligible labels; OSM provider follows the data mode. Documented: truncated early history, reviewers see rule inputs, blindness needs reviewers to avoid the Observations page, 2 km site grouping | Re-tested: 135 unit/API, 13 PostGIS; GitHub Actions run 36314415781 on `f24a910`: success |
| `make check` | Ruff clean; **133 passed** (new: split/group, review order, tiers, kappa, review validation, token/CORS, feature leakage guard, metrics, abstention, calibration, group bootstrap, dry-run card, synthetic end-to-end training); Prettier; `tsc`; Vite build (review page is a separate 14 kB chunk) | Map chunk still over 500 kB |
| `make integration` | **13 passed** (new: registry import idempotency/conflict, case-set freeze and manifest hash, features, blind case payload, two reviews → disagreement → adjudication, duplicate and excess reviews refused, summary, training gate and artifacts; NRT+SP one stream and overlap refusal) | Disposable databases |
| GitHub Actions | Run 36313643893 on `956b352`: **completed / success** — clean Ubuntu install including `make install-ml` (xgboost-cpu 3.4.1), 133 unit/API and 13 PostGIS tests passed with none skipped | Linux only |
| Saved-data importer | Scratch database: 2 FIRMS files + 1 OSM response imported, second run inserted 0 | Then dropped |
| API timing (10,318 cases) | Queue 0.12–0.16 s, summary 0.06 s, blind case 0.04 s | Local workspace |
| Browser (headless Chromium) | Review page at 1440 px and 390 px: queue, blind evidence, detections table, validation message, wrong token → "The review token was not accepted.", navigation back to observations; no page errors (only the expected 401 and SwiftShader WebGL warnings). Screenshots outside Git: `review-case-wide.png` `6c78caeb…`, `review-case-phone.png` `e1fb009d…`, `review-case2-wide.png` `5a594031…`, `review-validate-wide.png` `c25e67e0…` | **No review was submitted to the real case set**: labels come only from people |
| Fixes found during verification | Aborted requests shown as errors under React StrictMode; date suffix comma; queue wording; review order starved training/validation until all TEST cases were done (now interleaved); registry re-import with a different file under the same version (now refused); queue matched reviewer names case-sensitively | All re-checked |

Open items: human reviews (about 460 to report, 1,100 to promote — rough estimate from rule labels); a Mac run (XGBoost may need `libomp`); a held-out-region protocol.

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

## P05 reconciliation — 27 September 2026, 22:10–23:45 IST (branch `p05-model`)

Fetched `origin/main` `52c91f0` and merged it into `p05-model` (`09fb77b`; no rebase). Linux x86_64 cloud workspace, Python 3.13.15, uv 0.12.19, Node 24.21.0, digest-pinned PostGIS 18-3.6; workspace database migrated 0006 → 0007. **Not run on the owner's Mac; Mac and OpenMP verification is separate.** No FIRMS or Overpass request was made; inputs were the saved, hash-verified objects.

| Check | Observed result | Scope / limitation |
|---|---|---|
| Before fingerprints | `p05-pilot-v1`: 10,318 cases, manifest `fd1e627a…27068`, episodes `bf37782d…3ef7f`, splits `43b03d45…7870a`, `case-features-v1` 10,318 rows (9,628 rule, 240 registry labels), `landcover-summary-v1` 10,430, 23,991 observations, 0 reviews | Workspace database |
| Grouping audit of v1 | 14 mapped facilities, 360 nearby cases, in two or three splits (Jayant Mine, Visakhapatnam Steel Plant, Tetulmari coal mine, Reliance Refinery TEST/TRAIN, Block-B coal mine, Amlohri, Balaram, Vadinar Refinery, Kusmunda, Gangavaram port, Haldia Dock Complex, …) | 500 m of a mapped area or point; 1.5 km of a registered plant |
| Land cover | `landcover-summary-v2` for all 10,318 representatives, 0 failed, 2 m 31 s; v1 rows retained | Public WorldCover tiles |
| Events | Case-set build reused the same 14 event runs (identical input hashes); 20 runs in total, none rewritten | `event-site-v2` |
| New case set | `p05-pilot-v2`, `facility-aware-v1`, 2,437 groups, TRAIN 6,488 / VALIDATION 2,060 / TEST 1,770, manifest `94eebb40…7cb0`, episodes `bf37782d…` (same), splits `05992876…4e505`; 460 episodes sit in a different split than in v1; supersession and reason recorded in its manifest | Decided before any review or score |
| Grouping audit of v2 | 0 facilities (areas, points or plants) cross splits: `safe_for_unseen_site_claims: true` | Same rule as above |
| v1 after | Fingerprint identical to before; refuses reviews (409) and training | Frozen by triggers |
| Features | `case-features-v3`: 10,318 rows in 2 m 44 s, 4,376 rule labels, 240 registry, **1,321 history-complete**, 663 without full OSM coverage (inputs missing), 22 with non-thermal power in the pixel area, 0 NRT detections superseded by SP; feature sha `b453edc6…c5620`. `case-features-v2` (intermediate) retained | First run took over 15 minutes; an indexed pre-filter fixed it (same results) |
| Rule-label change v1 → v3 | Agricultural 5,147 → 139, vegetation 2,387 → 2,191, industrial 2,094 → 2,046; new abstentions: `INSUFFICIENT_RECURRENCE_COVERAGE` 4,593, `CONTEXT_UNAVAILABLE_AS_OF` 663, `NON_THERMAL_POWER_CONTEXT` 21 | Heuristic labels, never test truth |
| Training, reviewed | `INSUFFICIENT_LABELS`, `xgb-source-binary-v4` (`c0f6129c…`, manifest `419cdcf0…`); eligible support train 11/0, validation 77/0, test 0/0 | Correct refusal |
| Training, dry run | `DRY_RUN_NOT_EVIDENCE` (`91e3032d…`, `f0eb0e9a…`); 43 inputs; history policy excluded 8,997 cases; held-out-region and known-site-future executed; card and model list carry no scores | Execution check only; never quote |
| `make check` | Ruff clean; **146 passed**; Prettier; `tsc`; Vite build | Map chunk warning unchanged |
| `make integration` | **18 passed** (new: SP/NRT stream and overlap, supersession, grouping audit, fingerprints, evidence records, database immutability and case-insensitive uniqueness, history gate) | Disposable databases |
| Browser (headless Chromium, fixture database only) | Review-only server: no Observations link; wrong token refused; reviewer A and B saved blind (B saw nothing of A); disagreement sent to adjudicator C, who saw both answers and evidence without names; summary 1 GOLD test label, kappa over 1 pair; superseded set flagged; form fits 390 px and 1440 px. Only console entry: the expected 401. Screenshots outside Git: `4-adjudication.png` `c1d29874…`, `1-form-filled.png` `bd1b8670…`, `6-superseded.png` `40568db8…`, `7-review-only-root.png` `d92276f9…`, `8-form-phone.png` `c1390936…` | Fixture reviewers named "Fixture …"; the fixture database was dropped afterwards. **No review was written to a real case set.** |
| Fixture CLI | `train` → `INSUFFICIENT_LABELS` with one GOLD test label but no history-eligible case; superseded set refused; `UPDATE label_cases` and `DELETE FROM label_reviews` rejected by the triggers | Same fixture database |
| ML dependency audit | `pip-audit` 2.9.0 against the locked ML packages (scikit-learn 1.9.1, xgboost/xgboost-cpu 3.4.1, SciPy 1.18.1, joblib 1.6.0, threadpoolctl 3.7.0, cloudpickle 3.1.2, narwhals 2.26.0) with both the PyPI and OSV services: **no known vulnerabilities** at 17:06 UTC. Evidence file outside Git `ml-audit-evidence.txt` `cd8f073b…` | Point-in-time; licences in `ENVIRONMENT.md` |
| Independent reviews | Two separate read-only passes without prior context: no high-severity defect. Fixed after review: evidence host tricks (trailing dot, FIRMS/Overpass mirrors, raw GPPD, short-link/Esri basemaps), undated or thermal-only Worldview links, second reviewer's location ignored, operational SP precedence, whole-day SP precedence from partial SP runs, `days_since_last` reaching the archive start, training without a grouping audit, supersession race, solar counted in rule reasons | Re-tested |
| Secret scan | Workspace database password, Postgres password and both review tokens: zero matches in every commit | The Mac's FIRMS key never entered the workspace |

Open: human reviews; NOAA-20 SP backfill 2025-12-30 → 2026-03-29 for complete history; Mac verification; independent acceptance.

## 27 September 2026 approximately 22:19 IST — authenticated portal inspection

User completed login personally. Browser read-only navigation verified team identity and six registered members, empty Draft Idea List and View Submitted Idea tables, SIH26162 / NTRO / Software / Disaster Management at 140/500, and the matching blank submission form. No separate nomination-status badge appeared; successful form access is the evidence, not a claim to have audited the SPOC backend.

Observed form: title maximum 100 characters; description 50,000; abstract/summary 10,000; PDF up to 10 MB; optional YouTube link; technology dropdown including the combined AI/ML, Cloud Computing, Blockchain option; Save as Draft. No dedicated GitHub/website field was visible. Draft list states two ideas maximum and warns against changes after submission; form warns against post-submit changes over email/call. Actual final-submit controls/editing were not tested because no draft exists.

Sources: `/teamDetail`, `/teamDraftIdeas`, `/teamIdeas`, signed-in PS search, and [SIH26162 form](https://www.sih.gov.in/participate/MjYxNjI=). Only nonsensitive constraints and already-authorized team identity were recorded; no passwords or member contact data saved. No form changes, uploads, draft save or final submission. Clock check: 16:48:58 UTC. Canonical field checklist: `SUBMISSION_DETAILS.md`.

## 27–28 September 2026 — prepared six-slide submission package

New files were prepared outside Git in workspace `output/submission/`, leaving the original PPT and Canva unchanged. Base main: `52c91f0`; application implementation remains reviewed P03/P04 `b87fa86`. Existing local API/Vite/PostGIS were started for actual browser screenshots without changing code or importing more data. Screenshot subjects: the Jamnagar refinery candidate (2.17 MW, observation `903e66bf0e04ceebdc6ffd140c54c17a70d6803140523bb44be86e3694660f80`) and its retrospective rules/history with seven earlier active days. Human source confirmation remains pending.

| Check | Result | Boundary |
| --- | --- | --- |
| Official template import | Six content slides kept, instruction page omitted; official headings/artwork/dimensions retained | Original deck preserved |
| ArtifactTool finalization | Package/layout checks pass with zero findings/warnings; six-slide re-import passes | Not native Microsoft PowerPoint rendering |
| PDF export | LibreOffice 26.2.3.2; six pages, 562,150 bytes | First sandbox export failed; approved local retry succeeded |
| Visual inspection | Poppler rendered all six final PDF pages; each inspected for layout, identity, screenshots, arrows and references | No clinical/safety or model-accuracy claim implied |
| PDF text/link checks | Exact team/PS identity, 245 count and evaluation-pending wording present; five source links preserved | Research links are references, not ThermoScope performance evidence |
| Portal lengths | Title 72/100; summary 1,570/10,000; description 6,007/50,000 characters | Excludes final newline; including it remains within limits |
| Claim review | Main GIS/rules shown as built; P05 explicitly a separate branch; independent evaluation pending; AlphaEarth proposed | No dry-run scores, confirmed accidents, measured impact or production-readiness claims |

Final PDF SHA-256: `e2de296e47bd71f2ee7bf6bb4a83f7d2473189b6ba695d41c8a1455489991d94`. PPTX: `d5d2deda29451836e49ac5477d1411ed51584d520b3730df45ed5183a2e2e3b0`. Detailed manifest: `SUBMISSION_PACKAGE.md`; local builder, finalization receipt, renders and package verification: workspace `.review/submission-build/`. A speaking/video script exists; a recorded video does not. No portal entry/upload/save/submission or public publication occurred. Application tests were not repeated for unchanged code.

Checkpoint fetch found P05 advanced from `579aaf3` to `a243d29`. `git merge-base --is-ancestor 52c91f0 origin/p05-model` returned success. Its handoff reports 146 unit/API + 18 integration tests, migrations through 0007 and zero real reviews. Only ref/history/handoff inspected here; fresh CI confirmation, independent acceptance and Mac verification are still pending. Submission claims were not upgraded from this report.

## 27–28 September 2026, 23:35–04:30 IST — P05 backfill, reviewer accounts, independent review, Mac check and integration

At the owner's request ("can you solve these"). Linux x86_64 cloud workspace (Python 3.13.15, uv 0.12.19, Node 24.21.0, digest-pinned PostGIS 18-3.6) plus the owner's Mac through the desktop bridge. The Mac's main checkout and database were not changed; Mac tests ran in an isolated clone under ignored `local/p05-verify/`.

| Check | Observed result | Scope / limitation |
|---|---|---|
| SP history backfill | 252 of 252 FIRMS area requests (`VIIRS_NOAA20_SP`, 14 regions × 18 five-day windows, 30 December 2025–29 March 2026), HTTP 200, VIIRS header, key absent from every response and saved file; 27,363 rows; retrieved 27 September 18:09–18:22 UTC. Inventory `docs/inventory/p05-backfill-files.csv` (`af18a0d0…1358`) | Key read from the Mac's `.env` inside the bridge shell and passed to curl on stdin; never printed |
| Import | Workspace database backed up first (`pre-backfill-*.dump`); `import_saved.py`: 252 `SUCCEEDED`, 27,363 inserted, 0 problems, 49 s; observations 23,991 → 51,354 | Historical replay |
| Archive continuity | New `features` guard: every UTC day from 90 days before each region's first case to its last case has a qualifying NOAA-20 run; 14 regions, 0 missing days | 15 s query |
| Features | `case-features-v4` (unchanged code, ADR-022): 10,318 rows in 2 m 51 s; **10,035 history-complete** (was 1,321); 283 set aside, all within 750 m of a region edge; 9,131 rule labels (were 4,376; rules can now use recurrence), 240 registry; sha `b178a6e0…b6454`. v3 rows unchanged; recomputing v4 reports 10,318 unchanged | Rule labels are dry-run only |
| Fingerprints | `p05-pilot-v1` and `p05-pilot-v2` manifests, episodes and splits identical to before (`fd1e627a…`, `94eebb40…`, `bf37782d…`, `43b03d45…`, `05992876…`); 0 reviews | Frozen sets untouched |
| Training, reviewed | `INSUFFICIENT_LABELS` (`2e4fa530…`, manifest `f2d7fcbc…`); support train 34/0, validation 191/0 (registry SILVER only), test 0/0 | Correct refusal |
| Training, dry run | `DRY_RUN_NOT_EVIDENCE` (`2153b3e0…`, `5b2bcbe3…`); rule-labelled support 5,733 / 1,884 / 1,535; card carries no scores; 283 cases set aside | Execution check only; never quote |
| Review estimate | Eligible TEST pool 1,718 (rule proxy ≈ 168 industrial, 1,359 non-industrial, 191 unknown); ≈ 480 reviews to report, ≈ 1,100 to promote along the frozen queue | Rough; rules are not truth |
| Reviewer accounts | Migration 0008 applied to the workspace database after a backup (0 accounts); per-person tokens (256-bit, SHA-256 stored, owner-only files, never printed); identity from `Authorization: Bearer`; adjudicator role; view log; voiding; rotation/reactivation; refusal to downgrade with accounts | Team-pilot sign-in, not SSO |
| Independent review, pass 1 | Separate read-only pass on `origin/main..p05-model`: no auth bypass or token leak; **high**: a blind review could become the deciding adjudication; **medium**: reviewers could infer agreement from progress counters; archive version could be computed without the backfill; low: stale card text, no remedy for misused tokens, downgrade losing account links, token loss on file-write failure, script safety wording, sign-in edge cases. All fixed in `f36d292` | Probes on disposable databases |
| Independent review, pass 2 | The same pass verified `f36d292`: finding 1 fixed without a new agreement channel; new medium: after a void, an adjudicator who had read both reviews could review the case "blind"; archive guard checked only the earliest run; low: HTTP summary still public on default servers, CLI error mapping, stored-token clearing on any failure, in-place migration edit. All fixed in `0e49e82` | Re-tested |
| `make check` (workspace) | Ruff clean; **148 passed**; Prettier; `tsc`; Vite build | Map chunk warning unchanged |
| `make integration` (workspace) | **19 passed** (new: personal accounts end to end, stale-role refusal, adjudication-view log, voiding, archive guard, CLI token files, downgrade refusal) | Disposable databases |
| Browser (headless Chromium, fixture database only) | Sign-in rejects wrong/malformed tokens; four accounts open the same case: A and B save, adjudicator C's blind save is refused (409) and the page reloads the adjudication view with an empty form, D (non-adjudicator) is refused and never sees the disagreement; C adjudicates without names; reviewers see only their own progress ("Hidden" label totals); expired sign-in keeps the draft for the same person only; deactivation signs the page out; superseded set flagged; no horizontal scroll at 390 px; no token in page HTML. Screenshots outside Git: `shots2/2-rejected.png` `8fb203b0…`, `shots2/7-queue-phone.png` `537a789c…`, `shots3/1-stale-reloaded.png` `4ebde50f…` | Fixture reviewers only; fixture database dropped. **No review was written to a real case set** |
| Mac, before `libomp` | Isolated clone at `f36d292`: install and ML install passed; XGBoost failed to load (`@rpath/libomp.dylib` not found; rpath only `/opt/homebrew/opt/libomp/lib`; Homebrew present, libomp not installed; scikit-learn's bundled libomp not used); `make check` 146 passed / 2 failed (both XGBoost); `make integration` 19 passed. Report `report-1-before-libomp.txt` `579307df…` | macOS 26.3 arm64 |
| Mac, after `brew install libomp` (23.1.2, by the owner) | Isolated clone at `e2b2739`: both XGBoost probes passed; `make check` **148 passed** plus lint, format, typecheck and build; `make integration` **19 passed**. Report `report.txt` `8e168bf6…` | Secrets redacted; none present |
| Secret scan | Every commit and both Mac reports checked for the FIRMS key, Postgres and database passwords (on the Mac) and the workspace database password (in the cloud): zero matches | Tokens for fixtures were deleted after use |
| GitHub Actions | `p05-model` `4b4f375`: run [36355063881](https://github.com/ishowguts/thermoscope/actions/runs/36355063881) success; integration merge on `main` `3b12068`: run [36355168155](https://github.com/ishowguts/thermoscope/actions/runs/36355168155) success (frozen install, ML install, `make check`, `make integration`) | Ubuntu; the Mac result is the row above |

## 28 September 2026 IST — independent P05 Mac acceptance and main data integration

Accepted implementation `d9ca117`, incorporating `3b12068` / `4b4f375`. Initial `a243d29` checks passed 146 unit/API and 18 PostGIS tests; after the final handoff, its delta was inspected and final checks passed **148 unit/API and 19 PostGIS tests**, lint/format/type/build. A synthetic XGBoost fit and the real weak-rule pipeline executed on Mac with libomp already installed. Main CI [36355168155](https://github.com/ishowguts/thermoscope/actions/runs/36355168155) was independently verified successful. These checks are separate from the preceding evidence.

- Original main backup fully restored into isolated PostGIS; migrations checked; original 15-table content fingerprints unchanged at the initial migration gate. Fresh canonical backup then migration 0005 → 0008.
- Exact inventory/SHA checks for 464 P05 files and 252 backfill files passed. Reproduced 10,318 frozen cases / 2,437 groups; v1 retained and superseded; zero mapped facilities crossing v2 splits. All representative observations have land cover (10,312 new summaries, zero failures; six existing summaries reused).
- v4: 10,035 history-complete; 9,131 weak and 240 registry/silver labels. All 14 archive regions continuous; no partial-history override. Episode/split/feature fingerprints exactly match the reported content hashes (full values in internal record P05-MAC-ACCEPTANCE). 283 edge cases remain excluded; eligible test pool 1,718.
- Verified data transferred into main with additive INSERT transactions and all integrity constraints active. No UPDATE/DELETE/TRUNCATE or system-sequence change. Every original row across 24 application tables retained unchanged; 11,651 object files hash-checked. Final main: 51,354 observations, 10,325 land-cover summaries, 388 registry plants, 10,318 v4 feature rows. Mumbai OSM has two quarantined unclosed ways; this is retained as PARTIAL.
- Main reviewed run `6b7371a9-fcab-41f6-9828-1af2921a9995`: `INSUFFICIENT_LABELS`; weak run `e4a14259-d243-4dd3-ae7b-d6684f7e385f`: `DRY_RUN_NOT_EVIDENCE`. Every artifact manifest/file hash passes. Zero real reviews, accounts or adjudication views. No performance scores quoted or learned predictions served.
- Health/status/case-set/models HTTP 200; protected queue/identity HTTP 401 without credentials. No score fields in model-list responses. Browser: v2 plus superseded v1, no-account sign-in status, real Jharia observations and selected mine-context example, measurements/units/provenance, WorldCover and historical rule assessment. Warnings/errors: none in the observed browser flow. This does not independently confirm the heat source.

Acceptance report and local evidence/recovery paths: internal record P05-MAC-ACCEPTANCE. Human validation explicitly deferred (ADR-024). No P06–P08 application change, submission artifact refresh, public deployment or portal mutation in this checkpoint. v2's separate-branch P05 wording remains to be refreshed before approval. No old author commits, data volumes or verification clones were removed.

## 28 September 2026, 17:25–19:10 IST — P07-SUB-001 offline demo and evidence exports (branch `p07-demo`)

Base `c1d48b8`; branch commits listed in the handoff entry. Linux x86_64 cloud workspace (2 vCPU, Python 3.13.15, uv 0.12.19, Node 24.21.0, digest-pinned PostGIS 18-3.6) with its full historical-replay database (51,354 observations). The Mac checkout, its database and the submission files were not touched. Full table, screenshot and download hashes: internal record P07-SUBMISSION-DEMO (Result); commands: `docs/DEMO_RUNBOOK.md`.

| Check | Observed result | Scope / limitation |
|---|---|---|
| `make check` | Ruff; **155 passed**; Prettier; `tsc`; Vite build | Map chunk warning unchanged |
| `make integration` | **23 passed** (4 new P07 PostGIS tests, including tamper, traversal, symlink, forged land cover and expected-hash refusal) | Disposable databases |
| Independent review | Separate read-only pass on `c1d48b8..c9016d7`: no high finding; 6 medium (SP land cover not packaged; verification bypassable by rewritten metadata/paths/status; offline guard overclaimed; `load` could target the main database; context attribution missing from rule exports; zsh-incompatible commands) and 9 low; all fixed with tests. Second pass on `c9016d7..28bb9f9`: fixes verified; new medium (reload reported `ok: false`), low (top-level manifest fields and README unhashed, `hostaddr` bypass, reverse lookups) and nits; all fixed with tests | Second-pass fixes not reviewed again |
| Demo package | `thermoscope-demo-v1`: 3,420 listed files, 12,642,434 bytes, content `e5117f72…0464`, identical on rebuild; inventory `inventory/demo-v1-files.csv` | Jamnagar, Punjab; historical replay |
| Offline load | New database with the process guard: 110 FIRMS files / 5,971 rows, 2 OSM extracts, 3,307/3,307 land-cover summaries reproduced from chips, events rebuilt, `ok: true`, 52.8 s; reload `ok: true`, nothing inserted, 47.2 s. Versus the full database: all detections and land-cover rows identical; rule labels/inputs/missing data identical for all 131 NRT and 300 sampled SP; context and timeline identical for the NRT | Workspace, not the Mac |
| Browser (headless Chromium, network refused by dead proxy and DNS blackhole) | Five demo cases, evidence/window exports, empty region, keyboard, 1920/1366/390 widths without horizontal scroll, WebGL-disabled fallback; 54 tile requests attempted, 0 completed; reload with the fallback remembered makes 0 external requests; online partial tile failure keeps the basemap with a notice | Machine not physically disconnected; Mac Wi-Fi-off run pending |
| Timings | API list 0.05 s; window export 0.04–0.05 s (57 obs), with rules 3.6–3.8 s; assessment 0.06–0.08 s; evidence 0.22–0.28 s; first rows in the browser 0.8–1.8 s | Measured, no targets |
| Secret scan | Branch diff, tracked files, package and downloads: 0 password matches, 0 FIRMS API URLs | FIRMS key not present in this workspace |
| GitHub Actions | `8f410e5` run [36422194564](https://github.com/ishowguts/thermoscope/actions/runs/36422194564), `28bb9f9` run [36427057590](https://github.com/ishowguts/thermoscope/actions/runs/36427057590), tested tip `ab370da` run [36429320251](https://github.com/ishowguts/thermoscope/actions/runs/36429320251): all success (frozen install, ML install, `make check`, `make integration`) | Ubuntu |

## 28–29 September 2026, 19:27–01:00 IST — P08-REL-001 local release checks (branch `p08-release`)

Stacked on `p07-demo` `1f951f1`; tested tip `05a2431`. Cloud workspace as in the P07 entry. No change to `main`, the Mac or the submission files; no tag, release, upload or deployment. Details, data/model cards and the claims delta: `RELEASE.md`; task record: internal record P08-RELEASE-CHECKS. Evidence files are outside Git in the cloud workspace (`fresh2/`, `p08/`).

| Check | Observed result | Scope / limitation |
|---|---|---|
| Fresh clones | Final tip `05a2431`: install 9.9 s, ML 1.1 s, `make check` **164 passed**, `make integration` **23 passed**, audit exit 0. `c17ba3b` (full demo run): 162 + 23, doctor ok; `1f951f1`: 155 + 23 | Linux, empty caches; not the Mac |
| Demo from the clone | Verified package; offline loads 65.8 / 77.7 s (`ok: true`), reload `ok: true`; API 200s; production build offline: 57 rows 0.75 s, 0 external requests, 0 console errors | Headless Chromium, network refused by dead proxy |
| Dependency audit | OSV: 0 known vulnerabilities in 48 Python + 93 npm locked versions; `npm audit` 0; licences permissive except reviewed MPL/LGPL exceptions; installed = locked; report `e2e48a3b…` | Snapshot, not legal clearance; wheel-bundled native libraries not inspected |
| Secret safety | 5 tests (API normal/review-only with well-formed fake token and key, provider failures incl. tracebacks, six failing commands); mutation logging the token is caught | Fake credentials; the real FIRMS key is not in this workspace |
| Public-release review | 131 files at `9ccc49c`: 0 credentials/key URLs by the screen; 21 with team/personal identity, 1 local user path, 19 internal process records; no code licence | Screen, not proof; nothing published; owner decides |
| Backup/restore | Fresh-clone demo DB: dump 0.96 s (3.1 MB), restore 1.96 s; 25 tables / 34,471 rows identical; 11 API responses identical; 3,403 objects restored with matching hashes | Demo database, not a cloud backup |
| Pipeline timings | Four saved loads: FIRMS 12.7–17.3 s, OSM 0.8–0.9 s, land cover 33–42 s, events 10.1–18.8 s; 57–78 s into empty databases, 55 s reload | Satellite/provider delay not measurable from historical replay |
| P05 artifacts | 10 runs, all manifests and files match; 5 `INSUFFICIENT_LABELS`, 5 `DRY_RUN_NOT_EVIDENCE` | No evaluation exists |
| Links (signed out) | FIRMS, OSM copyright, OSMF tile policy, CC BY 4.0, WorldCover (+Zenodo DOI), WRI GPPD load; private repo 404; `sih.gov.in` 403 to automated fetchers — not verified | Deck PDF links not checked (separate file) |
| Independent review | Separate read-only pass on `5735ef5`: 0 high, 4 medium, 9 low, addressed in `c17ba3b`; second pass: fixes confirmed, 1 medium (credential screen) and 7 low, addressed in `ca20848`/`9ccc49c`/`05a2431` | Last fixes not re-reviewed |
| GitHub Actions | `5735ef5` [36461408662](https://github.com/ishowguts/thermoscope/actions/runs/36461408662), `c17ba3b` [36463846196](https://github.com/ishowguts/thermoscope/actions/runs/36463846196), `2e82906` [36464799347](https://github.com/ishowguts/thermoscope/actions/runs/36464799347), tested tip `05a2431` [36466090643](https://github.com/ishowguts/thermoscope/actions/runs/36466090643): all success | Ubuntu |


## 29 September 2026, 00:38–01:45 IST — integration, release `v0.8.0-demo`, demo video and submission package v6

Owner approval: "merge and tag"; access to `sih 2026/output` on the Mac granted. No portal entry, draft, submission, video upload, public release or hosting.

| Check | Observed result | Scope / limitation |
|---|---|---|
| Integration | `p08-release` (`fa4beb7`, containing `p07-demo` `1f951f1`) merged into `main` as `1e22d54`; merged tree `make check` **164 passed**, `make integration` **23 passed**; records commit `78e73de`; application code identical to `fa4beb7` (docs-only difference) | Cloud workspace |
| GitHub Actions on `main` | `78e73de` run [36472978149](https://github.com/ishowguts/thermoscope/actions/runs/36472978149): success | Ubuntu |
| Release tag | The cloud workspace's Git proxy refused tag pushes (HTTP 403). The owner ran `local/p08-verify/finish_release_mac.sh` (SHA-256 `1ebd44ca…c307`) after the Mac verification: Mac `main` fast-forwarded `c1d48b8` → `6ae3be2`; annotated tag **`v0.8.0-demo` published** (tag object `28871b6`, peeled to `78e73de`), confirmed with `git ls-remote` from the cloud | Private repository; no GitHub release page |
| Mac verification (owner, 29 Sep 01:53 IST) | `verify_release_mac.sh` on macOS 26.3 arm64, isolated clone of `fa4beb7`: every step PASS; `make check` **164 passed** (45 s), `make integration` **23 passed** (101 s); demo package built from the Mac main database: content `90823522…51eb`, 3,426 files; 110 FIRMS files and 2 OSM extracts identical to the cloud build, land-cover summaries differ (3,313 chips on the Mac vs 3,307 in the cloud build); verified with its hash and loaded into `thermoscope_demo_mac` with the network guard on (67 s); API on 8010: health, status, observations, CSV and evidence exports all 200 (0.002–1.06 s). Main checkout and database unchanged | Wi-Fi-off browser rehearsal not yet done |
| Demo video | `ThermoScope_SIH26162_demo_offline.mp4`: 2 min 4 s, 1366 × 768 H.264, no audio, 11,777,746 bytes, SHA-256 `ecbec201…2dd4`; production build served from the loaded demo package with internet access refused (0 external requests); captions are overlays on the running app | Cloud workspace, not the Mac; not uploaded |
| Submission package v6 | From v5: 10 of 69 PPTX parts changed (slides 2, 4, 5, six notes pages, core properties); package validator passes against v5; PDF exported by LibreOffice, all six pages rendered and inspected; PDF 741,200 bytes (`cc2b630d…f415`), PPTX 8,740,961 bytes (`16d7a07e…7a82`); summary 1,983, description 7,451, title 72 characters | No native PowerPoint render; slide 1 heading shows a serif substitute for Garamond |
| Independent review of v6 | Separate read-only pass: 0 blockers; 4 should-fix (single-case export is GeoJSON only; 2-region offline scope; "map extracts" ambiguity; Mac re-check tense) and nits, all fixed before delivery | Not re-reviewed after the fixes |
| Deck reference links | The six slide 6 links resolve to the named pages (FIRMS, Zenodo WorldCover record, Nature Scientific Data, two MDPI articles, Earth Engine catalog), web fetcher, 29 September | `sih.gov.in` still unverified |
| Files on the Mac | `output/submission/ThermoScope_SIH26162_Git_Push_Pray_v6.{pdf,pptx}`, `READ_FIRST_v6.md` and `v6/` (texts, ledger, talk track, video): SHA-256 on the Mac match the sources. v2–v5 and the unversioned v5 texts unchanged. The first copy of the video arrived altered (11,783,621 bytes) and was replaced from the verified copy in `local/p08-verify/` | — |
| v7 redesign brief (02:00–02:40 IST) | `output/submission/v7-brief/`: MASTER_PROMPT.md (fact sheet, never-claim list, slide-by-slide diagram spec), IMAGE_PROMPTS.md (concept art only; no fake screenshots, data, charts, news or logos) and 14 real screenshots at 2× from the release build on the cloud demo database with the OpenStreetMap basemap online (109 tile requests completed, 16 failed; no gaps seen in the images inspected). Markdown hashes match on the Mac; the PNG files were re-encoded in transfer but their pixels are identical (checked on three) | The v7 deck itself is built separately and needs its own check |
| Explainer video v2 (29 Sep, 12:20–13:25 IST) | `output/submission/video-v2/ThermoScope_SIH26162_explainer_1440p.mp4`: 2560 × 1440, 30 fps H.264 + AAC, 5 min 36 s, 119,582,717 bytes, SHA-256 `627f1483…3696`, −14 LUFS. Nine chapters (problem, approach, architecture, ML gate, real walkthrough of four cases, built today, six future items each with its reason, limits). App footage = camera moves over 2× full-page screenshots of the release build (demo database, OpenStreetMap basemap online); concept art labelled; synthetic narration (Kokoro TTS, open model) and generated music, both disclosed on the end card. Captions burned in and as `.srt`; narration script and YouTube description with chapters beside it. A separate read-only pass checked narration and on-screen text against the repository: 1 must-fix (history described as site grouping over 180 days; rules compare 750 m over 90 days) and 6 should-fix (solar glint, two-region offline scope, facility listing, outcome lists, timeline wording, shot dates), all fixed before the final render | Not uploaded; the Mac copy's hash matches (the transfer altered MP4 headers, so it was sent compressed in parts and reassembled) |
