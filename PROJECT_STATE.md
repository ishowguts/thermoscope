# Project state

Checkpoint: 28 September 2026 IST, the implementer integrated P05 into `main` at the owner's request while the integrator was out of usage (after the submission-package checkpoint `1e3bb0a`). Read the internal handoff log first. Canonical workspace: `thermoscope`; private remote: https://github.com/ishowguts/thermoscope; branch `main`. **The Mac checkout and its database were not changed **: the checkout is still at `1e3bb0a` and its database at migration 0005 until someone pulls, backs up and runs `make migrate` (see HANDOFF).

## Milestone status

| Milestone | Current state |
| --- | --- |
| P01 foundation | Complete |
| P02 observations/storage/API/map | Complete; original 13 records and receipts preserved |
| P03 OSM, WorldCover, events/sites | Technically integrated and Mac-verified; full gate still needs independent human case review |
| P04 history and rules | Technically integrated and Mac-verified; uncalibrated heuristics, no learned model |
| P05 labels/model pipeline | Integrated into `main` (28 September): reconciled pipeline, NOAA-20 SP history backfill, personal reviewer accounts; two independent review passes; Mac-verified in an isolated clone (148 unit/API + 19 PostGIS tests, after `brew install libomp`). **Blocked on human reviews**: zero labels, no model evaluation. Independent acceptance on return still open |
| P06–P08 | Not implemented on main |

P03/P04 integration preserves the author commits. Review fixes: `329b716`; P03 merge: `3cd8893`; reviewed P04 merge: `53e56ba`; newer P05 handoff preserved in integration commit `b87fa86`. Five evidence defects were corrected with six regression cases: missing-history abstention, valid per-product coverage, OSM boundary coverage, adequate raster windows, and solar-source handling. Details: internal record P03-P04-REVIEW, ADR-020.

## Verified local implementation

- Frozen dependencies installed on macOS 26.3 arm64. Python 3.13.15, uv 0.12.19, Node 24.21.0, npm 11.19.0; rasterio and numpy work on this Mac.
- 106 unit/API and 15 disposable PostGIS integration tests passed, plus lint/format/typecheck and production build. Main implementation files exactly matched the tested review branch after merging. Known MapLibre bundle-size warning remains.
- Database migrated additively from 0002 to 0005. Original observation fingerprint unchanged; 33 preexisting receipts were retained. Backup: ignored `local/backups/pre-p03-p04-20260927.dump`; its archive directory was checked, but a full restore drill was not performed.
- 245 unique real observations: 13 recent + 232 history rows. Three reviewed regions only (Jamnagar, Singrauli, Punjab). 133 grouped events / 45 sites; 13 recent observations have WorldCover summaries. Most older observations do not have land-cover summaries, explicitly missing.
- Bounded OSM adapter fetch on Mac succeeded; 313 Jamnagar features, zero rejected. All 13 recent WorldCover windows read successfully. Duplicate history import inserted zero records (seven duplicates retained as receipts).
- Built browser verified solar abstention, operational versus retrospective evidence, historical timeline/table, Punjab comparison and list-only mode. No warning/error console entries. Main API ready and all 13 recent assessments checked after integration.
- Integrated main CI [36314032712](https://github.com/ishowguts/thermoscope/actions/runs/36314032712) succeeded on `b87fa86`; the final checkpoint is documentation only.
- Current rules return UNKNOWN for all seven recent observations around the mapped solar photovoltaic feature. Refineries, mine and cropland outputs remain heuristic proposals. No confirmed industrial fire, human labels, accuracy, calibrated probability or alert readiness is claimed.

## P05 as integrated (28 September)

- Code: frozen facility-aware case set `p05-pilot-v2` (10,318 cases, 2,437 site groups, TRAIN 6,488 / VALIDATION 2,060 / TEST 1,770), blind review page with personal accounts (ADR-023), evidence policy, history eligibility, held-out-region protocol, immutable P05 records (migrations 0006–0008), XGBoost `xgb-source-binary-v4` with baselines, calibration, abstention and bootstrap intervals. Decisions: ADR-018, ADR-019, ADR-021–023.
- Data (the workspace database, from saved hash-verified files): 51,354 observations across 14 regions, including the NOAA-20 SP history backfill from 30 December 2025 (252 files, 27,363 rows; ADR-022). `case-features-v4`: 10,035 of 10,318 cases history-complete; eligible TEST pool 1,718.
- Results: reviewed training `INSUFFICIENT_LABELS`; rule-label dry run `DRY_RUN_NOT_EVIDENCE` (withheld scores, never quote). No learned-model accuracy exists. Predictions from the learned model are not served in the app.
- The Mac's main database holds only the reviewed three-region P02–P04 data. To use P05 there: back up, `make migrate`, then import the saved P05 files and run the P05 commands in `docs/DEVELOPMENT.md` (`brew install libomp` once).
- Integration merge `3b12068`; main CI [36355168155](https://github.com/ishowguts/thermoscope/actions/runs/36355168155) succeeded.
- Evidence and checks: `docs/EVIDENCE.md` (P05 reconciliation; backfill, reviewer accounts and integration), `docs/COVERAGE_INVENTORY.md`, internal record P05-LABELS-MODEL.

## What remains

1. Submission package is **ready for team review**, owned (internal record SUBMISSION-DECK). A new editable six-slide PPTX, visually verified six-page PDF (562,150 bytes), all three portal text fields and a speaking/video script are in `../output/submission/`; manifest and checks: `docs/SUBMISSION_PACKAGE.md`. Video is not recorded. No draft or submission was created. Official public table checked around 21:58 IST on 27 September: SIH26162 **140/500**, deadline **30 September**. Signed-in form checked around 22:19 IST: title 100 characters, description 50,000, summary 10,000; PDF up to 10 MB; optional YouTube link. Details in `docs/SUBMISSION_DETAILS.md`; recheck at submission.
2. P05 is integrated in `main`. On return, the integrator may independently accept it (the reviews were) and bring the Mac checkout up to date. Its earlier uncommitted edits went into `1e3bb0a`, so the checkout was clean at the last look: `git pull`, back up the database, `make migrate` (0005 → 0008). No review/model gate is waived to meet the submission date.
3. The owner adds personal reviewer accounts (`make ml ARGS="add-reviewer --name …"`, one adjudicator) on the server reviewers will use, with `REVIEW_ONLY=true`, and passes each token privately.
4. Team leader arranges the human review: a domain reviewer for the prepared P03 sheet and two independent reviewers plus adjudication for P05 test labels (about 480 reviews to report results, 1,100 to promote a model; rough rule-proxy estimates). The P03 sheet contains rule outcomes and must not contaminate blind P05 test review.

The complete remaining-work inventory, including P06–P08 and the leader's responsibilities, is `docs/REMAINING_WORK.md`. Prepare the submission now; do not wait for the full product.

Registered team: **Git_Push_Pray**, Bittu Mandal, Team ID **144613**, **INDIAN INSTITUTE OF INFORMATION TECHNOLOGY, PUNE**. FIRMS access works and is stored privately. Earthdata web login works per the user; programmatic archive/HLS access remains untested. Signed-in portal identity, six-member record and access to the correct idea form are verified; no separate nomination badge was displayed. Portal warns against changes after final submission. No cloud billing account, paid resource, public release, draft or SIH submission was changed.

## Local resources and restart

Main API: `127.0.0.1:8000`; main Vite: `127.0.0.1:5173`; PostGIS: `127.0.0.1:55432`, named volume `thermoscope_pgdata` retained. Old P02 preview on 5174 was stopped. Isolated review checkout/database are retained for reproducibility; they are not the canonical app. Inspect listeners before restarting.

Use lock-free Git reads first, then `make doctor`. Keep one writer per checkout. Never print credentials or read the stray `.env. Open.env` copy (left untouched at the owner's request). Do not refetch data to make receipt dates look newer. Original objects/manifests remain available; historical publication/availability stays unknown unless evidenced.
