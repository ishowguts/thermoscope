# Project state

Checkpoint: 27 September 2026, the integrator P05 coordination audit after completed P03/P04 integration. Read the internal handoff log first. Canonical workspace: `thermoscope`; private remote: https://github.com/ishowguts/thermoscope; branch `main`. Main and origin/main were clean and equal at `8adef15` before this documentation-only update; the previous push/conflict issue is resolved.

## Milestone status

| Milestone | Current state |
| --- | --- |
| P01 foundation | Complete |
| P02 observations/storage/API/map | Complete; original 13 records and receipts preserved |
| P03 OSM, WorldCover, events/sites | Technically integrated and Mac-verified; full gate still needs independent human case review |
| P04 history and rules | Technically integrated and Mac-verified; uncalibrated heuristics, no learned model |
| P05 labels/model pipeline | branch `p05-model` at `579aaf3`; latest branch CI passed; needs reconciliation with reviewed main, independent acceptance, Mac verification and human evidence |
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

## The newer P05 work

The branch records 464 additional FIRMS files, 14 regions, SP history, WRI registry evidence, a frozen 10,318-case set, a blind review page and an XGBoost training/evaluation pipeline. These counts are reported branch state, not independently reproduced data acceptance. Latest fixes `f24a910` remove date-proxy inputs and tighten gates; the pipeline records 42 inputs. CI [36314415781](https://github.com/ishowguts/thermoscope/actions/runs/36314415781) independently checked as successful (frozen install, ML install, check and integration). Full scientific/code acceptance remains open. The branch reports zero human reviews; its rule-label dry run is not evaluation evidence. Do not put dry-run scores or an accuracy claim in the deck.

P05's own task records technical/scientific gaps beyond missing people: truncated early history, evidence independence, large-facility grouping, no held-out-region protocol and missing label uncertainty/licence metadata. Binary source classification also excludes accident labels and serving learned predictions in the app. The rough 460/1,100 review counts are not guarantees of sufficient evidence or promotion.

P05 branches from the old P04 implementation and must incorporate the review safeguards before its own integration. ADR-018/019 are reserved for the P05 decisions; this review uses ADR-020. New retrievals in `local/p05-fetch/`, `local/context-fetch/` and registry storage were preserved, not imported into the reviewed three-region main app.

## What remains

1. Submission deck and portal package, owned (internal record SUBMISSION-DECK). The PPT/PDF/video are not revised or submitted yet. Official public table checked around 21:58 IST on 27 September: SIH26162 **140/500**, deadline **30 September**. Recheck when submitting; portal field limits remain unverified.
2. The implementer reconciles P05 under internal record P05-RECONCILE in its separate clone. Do not repeat P03/P04, rewrite published history, or change the Mac checkout/database.
3. The integrator independently reviews the returned P05 branch, verifies Mac compatibility and integrates accepted changes. No review/model gate is waived to meet the submission date.
4. Team leader arranges the human review: a domain reviewer for the prepared P03 sheet and two independent reviewers plus adjudication for P05 test labels. The P03 sheet contains rule outcomes and must not contaminate blind P05 test review.

The complete remaining-work inventory, including P06–P08 and the leader's responsibilities, is `docs/REMAINING_WORK.md`. Prepare the submission now; do not wait for the full product.

Registered team: **Git_Push_Pray**, Bittu Mandal, Team ID **144613**, **INDIAN INSTITUTE OF INFORMATION TECHNOLOGY, PUNE**. FIRMS access works and is stored privately. Earthdata web login works per the user; the current turn did not test programmatic archive/HLS access. Portal nomination/field limits remain unaudited. No cloud billing account, paid resource, public release or SIH submission was changed.

## Local resources and restart

Main API: `127.0.0.1:8000`; main Vite: `127.0.0.1:5173`; PostGIS: `127.0.0.1:55432`, named volume `thermoscope_pgdata` retained. Old P02 preview on 5174 was stopped. Isolated review checkout/database are retained for reproducibility; they are not the canonical app. Inspect listeners before restarting.

Use lock-free Git reads first, then `make doctor`. Keep one writer per checkout. Never print credentials or read the stray `.env. Open.env` copy (left untouched at the owner's request). Do not refetch data to make receipt dates look newer. Original objects/manifests remain available; historical publication/availability stays unknown unless evidenced.
