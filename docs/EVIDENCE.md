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
