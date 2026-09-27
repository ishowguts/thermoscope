# Project state

Checkpoint: 27 September 2026, 23:45 IST, written on branch `p05-model` after the P05 reconciliation (internal record P05-RECONCILE). On canonical `main` the previous checkpoint (`52c91f0`) remains authoritative until the integrator integrates this branch. Read the internal handoff log first. Canonical workspace: `thermoscope`; private remote: https://github.com/ishowguts/thermoscope; branch `main`.

## Milestone status

| Milestone | Current state |
| --- | --- |
| P01 foundation | Complete |
| P02 observations/storage/API/map | Complete; original 13 records and receipts preserved |
| P03 OSM, WorldCover, events/sites | Technically integrated and Mac-verified; full gate still needs independent human case review |
| P04 history and rules | Technically integrated and Mac-verified; uncalibrated heuristics, no learned model |
| P05 labels/model pipeline | Reconciled with reviewed main on the branch `p05-model` (P05-RECONCILE in review); needs the independent acceptance, Mac verification, a recommended history backfill and human-reviewed labels |
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

## P05 on `p05-model` (reconciled)

The implementer merged reviewed main (`52c91f0`) into `p05-model` without rewriting history and applied ADR-020's safeguards to the P05 paths (ADR-021). NOAA-20 SP and NRT form one history stream without double counting; non-thermal power never counts as industry; OSM inputs are missing without full coverage; land cover uses the larger ADR-020 window. The original case set `p05-pilot-v1` is kept frozen but superseded: its 2 km grouping let 14 large facilities (360 cases) cross splits. `p05-pilot-v2` uses facility-aware grouping (same 10,318 episodes, 2,437 groups, grouping audit clean). Only cases with a complete 90-day history are trained or evaluated (1,321 now, from 10 June). An enforced evidence policy makes only dated imagery or official/company sources, with the source inside the pixel area and at least medium certainty, eligible for GOLD. A held-out-region protocol was added. Cases, splits, reviews, features and model records are immutable in the database. `REVIEW_ONLY=true` hides rule assessments from reviewers.

Real-data runs in the workspace: reviewed policy `INSUFFICIENT_LABELS`; weak-label run `DRY_RUN_NOT_EVIDENCE` (execution check only; no score may be quoted). Zero human reviews exist. Checks: 146 unit/API and 18 PostGIS tests, fixture browser flow, ML advisory audit (none known), two independent read-only reviews with fixes applied. Linux only; Mac/OpenMP verification is the. Details: internal record P05-RECONCILE → Result, `docs/EVIDENCE.md` → "P05 reconciliation".

Technical blockers: independent acceptance and Mac verification; NOAA-20 SP backfill 2025-12-30 → 2026-03-29 (252 requests, owner's key) for complete history; reviewer authentication beyond a shared token. Human blockers: two independent reviewers plus an adjudicator; roughly 310 reviews before any result can be reported (rule-proxy estimate), and the non-industrial test class may stay below 30 without the backfill. No accuracy exists for the deck.

## What remains

1. Submission deck and portal package, owned (internal record SUBMISSION-DECK). The PPT/PDF/video are not revised or submitted yet. Official public table checked around 21:58 IST on 27 September: SIH26162 **140/500**, deadline **30 September**. Recheck when submitting; portal field limits remain unverified.
2. ~~the implementer reconciles P05 under internal record P05-RECONCILE~~ Done on `p05-model` (27 September, 23:45 IST); in review.
3. The integrator independently reviews the returned P05 branch, verifies Mac compatibility and integrates accepted changes. No review/model gate is waived to meet the submission date.
4. Team leader arranges the human review: a domain reviewer for the prepared P03 sheet and two independent reviewers plus adjudication for P05 test labels. The P03 sheet contains rule outcomes and must not contaminate blind P05 test review.

The complete remaining-work inventory, including P06–P08 and the leader's responsibilities, is `docs/REMAINING_WORK.md`. Prepare the submission now; do not wait for the full product.

Registered team: **Git_Push_Pray**, Bittu Mandal, Team ID **144613**, **INDIAN INSTITUTE OF INFORMATION TECHNOLOGY, PUNE**. FIRMS access works and is stored privately. Earthdata web login works per the user; the current turn did not test programmatic archive/HLS access. Portal nomination/field limits remain unaudited. No cloud billing account, paid resource, public release or SIH submission was changed.

## Local resources and restart

Main API: `127.0.0.1:8000`; main Vite: `127.0.0.1:5173`; PostGIS: `127.0.0.1:55432`, named volume `thermoscope_pgdata` retained. Old P02 preview on 5174 was stopped. Isolated review checkout/database are retained for reproducibility; they are not the canonical app. Inspect listeners before restarting.

Use lock-free Git reads first, then `make doctor`. Keep one writer per checkout. Never print credentials or read the stray `.env. Open.env` copy (left untouched at the owner's request). Do not refetch data to make receipt dates look newer. Original objects/manifests remain available; historical publication/availability stays unknown unless evidenced.
