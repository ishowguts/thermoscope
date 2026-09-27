# Project state

Checkpoint: 27 September 2026, 16:30 IST, written. Stage: **P01 complete; P02 complete (local checks + clean-checkout CI passed); P03 on `p03-context`, P04 on `p04-history` and P05 on `p05-model` implemented and in review (not merged). P05's evaluation gate is blocked on human-reviewed labels.** Deadline: SIH idea submission 30 September 2026.

**Every session reads the internal handoff log first**: it says which tool last wrote, where it took over, where it stopped and the exact next action.

**Current split (owner's decisions, 27 September): the implementer built P03 (`p03-context`), P04 (`p04-history`) and P05 (`p05-model`), stacked in that order and all in review; the integrator owns the six-slide deck (internal record SUBMISSION-DECK). The implementer has not started the PPT.**

P03 on the branch adds dated OSM facility context with an approximate pixel area, ESA WorldCover 2021 land cover, and deterministic events/recurring sites (ADR-014–016). Branch checks: 77 unit/API and 10 PostGIS tests, four green CI runs, headless-browser flow. Open before "done": a person-reviewed adjacent industrial/cropland case (candidate: Jamnagar power-plant group) and a run on the owner's Mac (rasterio wheel needs macOS 14+). `main` still contains only P01/P02 code; the Mac database is at migration 0002.

P04 on `p04-history` (stacked on P03) adds as-of history using 232 real NOAA-20 observations from 1 July–21 September and transparent rules for likely source, behaviour and review priority with reasons, a retrospective/operational availability switch and a 180-day timeline (ADR-017). Branch checks: 104 unit/API and 11 PostGIS tests, green CI. Thresholds are uncalibrated defaults; no trained model or probability exists.

P05 on `p05-model` (stacked on P04, owner's request "start and finish p05") adds NOAA-20 SP history (30 March–30 June) for 14 regions plus NRT for 11 new ones (464 files, 23,746 detections), `event-site-v2` episodes (7-day maximum), a frozen case set `p05-pilot-v1` (10,318 cases, 2,462 site groups, leak-free splits, hashed manifest), WRI GPPD v1.3.0 registry evidence, a blind label-review page with adjudication, and an XGBoost pipeline with baselines, calibration, abstention, group-bootstrap intervals and a model card (ADR-018/019). **Zero human reviews exist**, so the only runs are `INSUFFICIENT_LABELS` and a rule-label `DRY_RUN_NOT_EVIDENCE`; there is no evaluated model or accuracy figure. About 460 reviews are needed before results can be reported (internal record P05-LABELS-MODEL). Branch checks: 135 unit/API and 13 PostGIS tests, green CI; an independent review found no high-severity defect and its fixes are in.

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

Engineering task in review: internal record P03-CONTEXT on branch `p03-context`, owner the implementer. Merging into `main` is the owner's decision; after a merge, run `make install`, `make migrate` and the `make context` commands in `docs/DEVELOPMENT.md` on the Mac. Read the P03 contract before collecting bounded OSM/land-cover context or defining events/sites. No classifier is built; history/rules are P04, trained structured model and evaluation P05. No MODIS/standard-product reconciliation, scheduler, raster features, cloud deployment or authentication is claimed by P02.

## Inputs still needed later

| Input | Needed for | Current state |
|---|---|---|
| Earthdata archive authorization | Historical/HLS retrieval | Web login confirmed; programmatic check pending |
| Portal limits and nomination confirmation | Final submission package | Team identity confirmed; portal fields not audited |
| Independent reviewers and incident evidence | Credible labels/evaluation | Review tool ready on `p05-model`; no reviewer has started; no gold labels, no incident evidence |
| Cloud provider, billing owner and bounded spend | Paid deployment/experiments | No resources provisioned |
| Code license and release allowlist | Public release | Undecided; repo private |

The corrected six-slide presentation/PDF and current portal requirements remain the immediate submission priority. The original PPT is unchanged; no submission or video has been produced by P02. Recheck dated SIH count/deadline information before submission.

## Local resources

API at `127.0.0.1:8000`, Vite development at `127.0.0.1:5173`, local PostGIS at `127.0.0.1:55432`; named volume `thermoscope_pgdata` retained. A temporary built-preview server used `127.0.0.1:5174` during P02 verification. The owner's `lsof` at 03:59 IST showed all four still listening (8000 python PID 68131, 5173 node PID 28282, 5174 node PID 68167, 55432 Docker). The 5174 preview is stale and should be stopped; keep the database. Recheck with `lsof -nP -iTCP -sTCP:LISTEN` before starting anything. All these are local processes, not public deployments. Inspect listeners before restarting duplicates. Stop task-owned servers normally and use `make db-stop` to retain database data.

## Restart checks

Inspect Git with lock-free reads (`git --no-optional-locks...`) when another tool might be active, run `make doctor`, and open the local observation view. A stray ignored copy of the settings file, `.env. Open.env`, exists at the repository root; it is not tracked and should be deleted by the owner, not copied or read by contributors. Retain `.env`, raw objects, manifests and development data. Do not rerun the provider unnecessarily to make the timestamps look newer. Every real receipt already has an immutable manifest. Unknown historical publication/availability remains unknown. Interrupted RUNNING attempts need manual investigation until scheduled job recovery is implemented.
