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

Programmatic Earthdata download, application FIRMS ingestion, model training/evaluation, deployed browser tests, offline application replay, cloud restore and SIH submission remain unperformed. P01 local installation, tests, migration and browser evidence are recorded below.

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
