# Project state

Checkpoint: 27 September 2026, 03:55 IST, written after taking over. Stage: **P01 complete; P02 complete (local checks + clean-checkout CI passed); P03 not started**. Deadline: SIH idea submission 30 September 2026.

**Every session reads the internal handoff log first**: it says which tool last wrote, where it took over, where it stopped and the exact next action.

**Current split (owner's decision, 27 September 04:00 IST): the implementer is building P03 on branch `p03-context`; the integrator owns the six-slide deck (internal record SUBMISSION-DECK). The implementer has not started the PPT.**

Canonical workspace: the fresh `thermoscope` folder. Remote: https://github.com/ishowguts/thermoscope, private. Branch: `main`. Original Part 1 and ThermalGuard projects remain historical references.

## Verified implementation

- P01 API, source/time contracts, local PostGIS, migration setup, dependency locks and CI foundation.
- P02 VIIRS NRT adapter, content-addressed raw CSVs, per-run immutable manifests, atomic deduplication, quarantine and sanitized provider failure handling.
- Bounded GeoJSON API with spatial/time/mode filters, pagination and separate acquisition/ingestion status; one request uses repeatable-read isolation.
- MapLibre map and observation list with point/row selection, units, NASA confidence, acquisition/receipt/availability, raw hash and source receipt. Replay and manual provider fetch remain explicit modes.
- Real local data: 10 Jamnagar + 1 Singrauli + 2 Punjab observations. Reimport inserts no duplicates. A fresh NASA Jamnagar fetch returned the same ten observations and added live receipts. These are observations, not confirmed fires or reviewed labels.
- `make check`: 41 unit/API tests, Python lint/format, frontend formatting, typecheck and production build passed. `make integration`: six real PostGIS scenarios passed. The same full suite passed from a fresh checkout in [GitHub Actions run 36275992464](https://github.com/ishowguts/thermoscope/actions/runs/36275992464) on commit `43cf2b0`.
- Browser checked WebGL map rendering, point/list selection, live/replay evidence, regional counts, native date editing/filtering, invalid and empty ranges, and list-only mode. Built frontend preview also rendered and selected the correct evidence with no warning/error console entries. Automatic GPU context-loss recovery was not forced.

## Accounts and planning already completed

Architecture, eight milestones, shared work contract and eight-page decision brief exist. The GitHub account is `ishowguts`. FIRMS access and real app fetch work; its credential is in ignored owner-only local settings. Earthdata web login works per the user; programmatic HLS/archive access remains untested.

Registered team: **Git_Push_Pray**, leader **Bittu Mandal**, Team ID **144613**, **INDIAN INSTITUTE OF INFORMATION TECHNOLOGY, PUNE**. The user has SIH team-leader login access. No SIH portal submission has been performed.

## Task and handoff

Last completed task: internal record P02-FIRMS-MAP — **done**. Implementation commit `43cf2b0453a559a4841a05de73413211d9200e3e`, pushed; CI success. Read `docs/EVIDENCE.md` for actual receipts and checks. Resolve the latest checkpoint commit with `git log -1 -- PROJECT_STATE.md`, then inspect `git --no-optional-locks status --short --branch`.

Priority order until 30 September: (1) submission deck and portal package, (2) P03 (in parallel on its own branch). The deck is not in this repository; the original PPT and official template live outside this folder.

Engineering task in progress: internal record P03-CONTEXT, owner the implementer, branch `p03-context`. Read the P03 contract before collecting bounded OSM/land-cover context or defining events/sites. No classifier is built; history/rules are P04, trained structured model and evaluation P05. No MODIS/standard-product reconciliation, scheduler, raster features, cloud deployment or authentication is claimed by P02.

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

API at `127.0.0.1:8000`, Vite development at `127.0.0.1:5173`, local PostGIS at `127.0.0.1:55432`; named volume `thermoscope_pgdata` retained. A temporary built-preview server used `127.0.0.1:5174` during P02 verification. The owner's `lsof` at 03:59 IST showed all four still listening (8000 python PID 68131, 5173 node PID 28282, 5174 node PID 68167, 55432 Docker). The 5174 preview is stale and should be stopped; keep the database. Recheck with `lsof -nP -iTCP -sTCP:LISTEN` before starting anything. All these are local processes, not public deployments. Inspect listeners before restarting duplicates. Stop task-owned servers normally and use `make db-stop` to retain database data.

## Restart checks

Inspect Git with lock-free reads (`git --no-optional-locks...`) when another tool might be active, run `make doctor`, and open the local observation view. A stray ignored copy of the settings file, `.env. Open.env`, exists at the repository root; it is not tracked and should be deleted by the owner, not copied or read by contributors. Retain `.env`, raw objects, manifests and development data. Do not rerun the provider unnecessarily to make the timestamps look newer. Every real receipt already has an immutable manifest. Unknown historical publication/availability remains unknown. Interrupted RUNNING attempts need manual investigation until scheduled job recovery is implemented.
