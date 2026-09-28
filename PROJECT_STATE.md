# Project state

Checkpoint: 28 September 2026 IST. **P01–P05 engineering is integrated and independently accepted on the Mac. Human source/model validation is deferred at the owner's request (ADR-024).** Canonical workspace: `thermoscope`; private remote: https://github.com/ishowguts/thermoscope; branch `main`. Accepted implementation `d9ca117` (P05 integration merge `3b12068`), followed by this documentation checkpoint. Read the internal handoff log first.

## Milestone status

| Milestone | Current state |
| --- | --- |
| P01 foundation | Complete |
| P02 observations/storage/API/map | Complete; original observations and receipts retained |
| P03 OSM, WorldCover, events/sites | Engineering accepted; independent human case interpretation deferred |
| P04 history and rules | Engineering accepted; uncalibrated heuristics, no learned inference |
| P05 labels/model pipeline | Engineering accepted after integration; Mac main updated, database 0008, saved data and artifacts verified. Scientific evaluation/promotion deferred: zero human reviews |
| P06 satellite experiment | Deferred until independent labels enable a meaningful comparison |
| P07 analyst product | Full milestone unbuilt. Bounded demo task P07-SUB-001 implemented on branch `p07-demo` (offline replay package, bounded evidence exports, map-free fallback, status strip); **in review**, not integrated |
| P08 release/deployment | Not complete; local demo-release checks recommended after bounded P07; public hosting optional and unprovisioned |

## Verified local implementation

- Frozen Python 3.13.15, uv 0.12.19, Node 24.21.0, API/UI/raster and optional ML environment on macOS 26.3 arm64. XGBoost 3.4.1 works with the owner's installed libomp 23.1.2.
- Independent final-code checks: **148 unit/API + 19 PostGIS tests**, lint, format, TypeScript and production build passed. Main CI [36355168155](https://github.com/ishowguts/thermoscope/actions/runs/36355168155) confirmed successful. Known MapLibre bundle-size warning remains.
- Backup restored into an isolated review database; migrations tested there, then canonical main backed up and migrated 0005 → 0008. Verified data added with duplicate-safe INSERT transactions and integrity constraints enabled. Every pre-import row across 24 application tables remains unchanged; no data volume was removed.
- Main now holds **51,354 genuine observations across 14 pilot regions**, 388 registered thermal plants and 10,325 land-cover summaries. All 464 original P05 plus 252 backfill FIRMS files matched their inventories/hashes. Source files, objects and receipts are retained locally, outside Git.
- Frozen `p05-pilot-v2`: **10,318 cases / 2,437 facility-aware groups**, TRAIN 6,488 / VALIDATION 2,060 / TEST 1,770. Superseded v1 retained. Grouping audit found zero mapped facilities crossing splits. Cases were reproduced before the historical backfill; their boundaries were not redefined afterward.
- `case-features-v4`: **10,035 history-complete** cases and 1,718 eligible test cases; 283 region-edge cases remain ineligible. All case representatives have land-cover summaries. Episode, split and feature content fingerprints exactly match the recorded results and match between the review and main databases.
- Main reviewed-label training returns `INSUFFICIENT_LABELS`; a weak-rule execution run returns `DRY_RUN_NOT_EVIDENCE`. Artifact hashes verified. **Zero real reviews, reviewer accounts or adjudication views. No reportable learned-model accuracy and no learned predictions served.** Registry/rule-derived labels are not independent test truth.
- Browser/API checked on main: health/schema ready; protected review routes return 401 without credentials; v2 and superseded v1 shown; no-account review status; real Jharia measurements, context, WorldCover, historical timeline and rule explanations load. No browser warning/error entries in this check.
- Mumbai OSM remains PARTIAL (1,700 accepted features, two unclosed ways quarantined). Context is retrospective; WorldCover describes 2021. Inference remains a research preview, not confirmed industrial-incident detection.

Detailed acceptance and local report paths: internal record P05-MAC-ACCEPTANCE, `docs/EVIDENCE.md`. P03/P04 review fixes and original author histories remain preserved (ADR-020). This checkpoint changed documentation and local data, not application code.

## Exact next work

1. **Submission refresh:** v2 PPTX/PDF and portal text exist in `../output/submission/`, but the old separate-branch P05 wording is stale. The integrator updates the claims to the accepted release, exports/visually checks the new PDF, then the team approves that exact content. No video, saved draft, final submission or receipt exists.
2. **Bounded P07:** implemented on branch `p07-demo` (28 September; see the task Result and `docs/DEMO_RUNBOOK.md`). The integrator verifies it on the Mac with the network off, then integrates or returns findings. The integrator retains canonical main and submission ownership. P06, public hosting and learned inference remain out of scope.
3. **Bounded P08:** clean-checkout reproduction, release/security/licence/runbook checks and a genuine demo rehearsal after P07. Local replay plus recording is the planning assumption; hosting requires a concrete provider, access scope and budget before provisioning.
4. **Leader attention:** approve the refreshed submission content and authorize or perform final submission; optional narration. No new key, account, GPU, manual technical setup or expert recruitment is needed now. Full list: `docs/LEADER_ACTIONS.md`; all remaining product/scientific work: `docs/REMAINING_WORK.md`.

The signed-in portal was checked on 27 September around 22:19 IST: correct team and PS form accessible, six-member record, title 100 characters, description 50,000, summary 10,000, PDF up to 10 MB, optional YouTube link. No separate nomination badge appeared; no eligibility block was shown. The public table showed 140/500 and 30 September at that time. These are dated snapshots, not reserved capacity; recheck before submission. No portal fields, files, draft or submission were changed in this checkpoint.

Registered team: **Git_Push_Pray**, Bittu Mandal, Team ID **144613**, **INDIAN INSTITUTE OF INFORMATION TECHNOLOGY, PUNE**. FIRMS access is stored privately. Earthdata web login works per the user; programmatic HLS access remains untested and unnecessary for this checkpoint. No paid resource or public release was created.

## Local resources and restart

Main API `127.0.0.1:8000`; main Vite `127.0.0.1:5173`; PostGIS `127.0.0.1:55432`, named volume `thermoscope_pgdata` retained. Inspect listeners before restarting. P05 review worktree `../thermoscope-p05-review` and database `thermoscope_p05_review_20260928` are retained. No batch job remains running at this checkpoint.

Recovery backups: ignored `local/backups/pre-p05-20260928.dump` (restored for verification), `pre-p05-main-20260928.dump`, row-fingerprint and final acceptance reports. Model artifacts are in ignored `local/models/`. The verification clone `local/p05-verify/clone` and the earlier P03/P04 review workspace were not deleted.

Use lock-free Git reads first, then `make doctor`. Keep one writer per checkout. Never print credentials or read the stray `.env. Open.env` copy (left untouched at the owner's request). Do not refetch data to make receipt dates look newer. Historical publication/availability remains unknown unless evidenced.
