# Project state

Checkpoint: 27 September 2026 IST (verification began 26 September UTC). Stage: **P01 complete; P02 implemented and locally verified, remote CI pending**.

Canonical workspace: the fresh `thermoscope` folder. Remote: https://github.com/ishowguts/thermoscope, private. Branch: `main`. Original Part 1 and ThermalGuard projects remain historical references.

## Verified implementation

- P01 API, source/time contracts, local PostGIS, migration setup, dependency locks and CI foundation.
- P02 VIIRS NRT adapter, content-addressed raw CSVs, per-run immutable manifests, atomic deduplication, quarantine and sanitized provider failure handling.
- Bounded GeoJSON API with spatial/time/mode filters, pagination and separate acquisition/ingestion status; one request uses repeatable-read isolation.
- MapLibre map and observation list with point/row selection, units, NASA confidence, acquisition/receipt/availability, raw hash and source receipt. Replay and manual provider fetch remain explicit modes.
- Real local data: 10 Jamnagar + 1 Singrauli + 2 Punjab observations. Reimport inserts no duplicates. A fresh NASA Jamnagar fetch returned the same ten observations and added live receipts. These are observations, not confirmed fires or reviewed labels.
- `make check`: 41 unit/API tests, Python lint/format, frontend formatting, typecheck and production build passed. `make integration`: six real PostGIS scenarios passed before the final parser-only edge-case guard; CI will repeat the complete suite from a fresh checkout.
- Browser checked WebGL map rendering, point/list selection, live/replay evidence, regional counts, native date editing/filtering, invalid and empty ranges, and list-only mode. Built frontend preview also rendered and selected the correct evidence with no warning/error console entries. Automatic GPU context-loss recovery was not forced.

## Accounts and planning already completed

Architecture, eight milestones, shared work contract and eight-page decision brief exist. The GitHub account is `ishowguts`. FIRMS access and real app fetch work; its credential is in ignored owner-only local settings. Earthdata web login works per the user; programmatic HLS/archive access remains untested.

Registered team: **Git_Push_Pray**, leader **Bittu Mandal**, Team ID **144613**, **INDIAN INSTITUTE OF INFORMATION TECHNOLOGY, PUNE**. The user has SIH team-leader login access. No SIH portal submission has been performed.

## Task and handoff

Current task: internal record P02-FIRMS-MAP; base `6358bd94394cc81bfd45963dc7302841c3fd1fda`. Local implementation/checks are complete; commit/push and remote CI are the remaining P02 verification step. Read `docs/EVIDENCE.md` for actual receipts and checks. Resolve the eventual checkpoint commit with `git log -1 -- PROJECT_STATE.md`, then inspect `git status --short --branch`.

Next engineering task: internal record P03-CONTEXT (planned). Read the P03 contract before collecting bounded OSM/land-cover context or defining events/sites. No classifier is built; history/rules are P04, trained structured model and evaluation P05. No MODIS/standard-product reconciliation, scheduler, raster features, cloud deployment or authentication is claimed by P02.

## Inputs still needed later

| Input | Needed for | Current state |
|---|---|---|
| Earthdata archive authorization | Historical/HLS retrieval | Web login confirmed; programmatic check pending |
| Portal limits and nomination confirmation | Final submission package | Team identity confirmed; portal fields not audited |
| Independent reviewers and incident evidence | Credible labels/evaluation | Not arranged; no gold labels |
| Cloud provider, billing owner and bounded spend | Paid deployment/experiments | No resources provisioned |
| Code license and release allowlist | Public release | Undecided; repo private |

The corrected six-slide presentation/PDF and current portal requirements remain the immediate submission priority. The original PPT is unchanged; no submission or video has been produced by P02. Recheck dated SIH count/deadline information before submission.

## Local resources

API at `127.0.0.1:8000`, Vite development at `127.0.0.1:5173`, local PostGIS at `127.0.0.1:55432`; named volume `thermoscope_pgdata` retained. A temporary built-preview server uses `127.0.0.1:5174` during verification and will be stopped before handoff. All these are local processes, not public deployments. Inspect listeners before restarting duplicates. Stop task-owned servers normally and use `make db-stop` to retain database data.

## Restart checks

Inspect Git, run `make doctor`, and open the local observation view. Retain `.env`, raw objects, manifests and development data. Do not rerun the provider unnecessarily to make the timestamps look newer. Every real receipt already has an immutable manifest. Unknown historical publication/availability remains unknown. Interrupted RUNNING attempts need manual investigation until scheduled job recovery is implemented.
