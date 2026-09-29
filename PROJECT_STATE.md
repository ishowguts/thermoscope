# Project state

Checkpoint: 29 September 2026 IST. **Release `v0.8.0-demo`: P01–P05 engineering (accepted on the Mac) plus the bounded P07 demo and local P08 release checks, integrated in `main` (`1e22d54`; release commit `78e73de`, CI green) with the owner's approval. Submission package v6 and a captioned demo video are on the Mac for team review. Human source/model validation is deferred at the owner's request (ADR-024).** Canonical workspace: `thermoscope`; private remote: https://github.com/ishowguts/thermoscope; branch `main`.

## Milestone status

| Milestone | Current state |
| --- | --- |
| P01 foundation | Complete |
| P02 observations/storage/API/map | Complete; original observations and receipts retained |
| P03 OSM, WorldCover, events/sites | Engineering accepted; independent human case interpretation deferred |
| P04 history and rules | Engineering accepted; uncalibrated heuristics, no learned inference |
| P05 labels/model pipeline | Engineering accepted after integration; Mac main updated, database 0008, saved data and artifacts verified. Scientific evaluation/promotion deferred: zero human reviews |
| P06 satellite experiment | Deferred until independent labels enable a meaningful comparison |
| P07 analyst product | Bounded demo task P07-SUB-001 **done and integrated** (`v0.8.0-demo`): offline replay package, bounded evidence exports, map-free fallback, status strip. The full milestone (authenticated review workflow, alerts, promoted model) remains unbuilt |
| P08 release/deployment | Local release checks (P08-REL-001) **done and integrated** as release `v0.8.0-demo` (`docs/RELEASE.md`); tag published from the Mac after the Mac verification passed (the cloud workspace cannot push tags). Wi-Fi-off rehearsal, code licence, public allowlist and any hosting remain open |

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

Detailed acceptance and local report paths: internal record P05-MAC-ACCEPTANCE (not published), `docs/EVIDENCE.md`. P03/P04 review fixes and original author histories remain preserved (ADR-020). This checkpoint changed documentation and local data, not application code.

## Exact next work

1. **Team review of submission package v6:** `../output/submission/ThermoScope_SIH26162_Git_Push_Pray_v6.pdf` (+ `.pptx`) and the texts in `../output/submission/v6/` (start with `READ_FIRST_v6.md`; the unversioned texts beside it are v5). The optional video `v6/ThermoScope_SIH26162_demo_offline.mp4` is not uploaded. No saved draft, final submission or receipt exists.
2. **Mac check and tag of `v0.8.0-demo`: done** (29 Sep 01:53 IST): verification all PASS (164 + 23, offline load), Mac `main` fast-forwarded, tag published. Optional: the runbook's Wi-Fi-off demo rehearsal. A redesign brief for a richer v7 deck (master prompt, image prompts, 14 real screenshots) is in `../output/submission/v7-brief/`.
3. **Hosting (optional):** only with a concrete provider, access scope and budget before provisioning; the local replay and the recorded video are the planning assumption. P06, public hosting and learned inference remain out of scope.
4. **Leader attention:** approve submission package v6, recheck the live PS count, save and inspect a draft, then submit; optionally upload the video (Unlisted, checked signed out). No new key, account, GPU, manual technical setup or expert recruitment is needed now. Full list: `docs/LEADER_ACTIONS.md`; all remaining product/scientific work: `docs/REMAINING_WORK.md`.

The signed-in portal was checked on 27 September around 22:19 IST: correct team and PS form accessible, six-member record, title 100 characters, description 50,000, summary 10,000, PDF up to 10 MB, optional YouTube link. No separate nomination badge appeared; no eligibility block was shown. The public table showed 140/500 and 30 September at that time. These are dated snapshots, not reserved capacity; recheck before submission. No portal fields, files, draft or submission were changed in this checkpoint.

Registered team: **Git_Push_Pray**, Bittu Mandal, Team ID **144613**, **INDIAN INSTITUTE OF INFORMATION TECHNOLOGY, PUNE**. FIRMS access is stored privately. Earthdata web login works per the user; programmatic HLS access remains untested and unnecessary for this checkpoint. No paid resource or public release was created.

## Local resources and restart

Main API `127.0.0.1:8000`; main Vite `127.0.0.1:5173`; PostGIS `127.0.0.1:55432`, named volume `thermoscope_pgdata` retained. Inspect listeners before restarting. P05 review worktree `../thermoscope-p05-review` and database `thermoscope_p05_review_20260928` are retained. No batch job remains running at this checkpoint.

Recovery backups: ignored `local/backups/pre-p05-20260928.dump` (restored for verification), `pre-p05-main-20260928.dump`, row-fingerprint and final acceptance reports. Model artifacts are in ignored `local/models/`. The verification clone `local/p05-verify/clone` and the earlier P03/P04 review workspace were not deleted.

Use lock-free Git reads first, then `make doctor`. Keep one writer per checkout. Never print credentials or read the stray `.env. Open.env` copy (left untouched at the owner's request). Do not refetch data to make receipt dates look newer. Historical publication/availability remains unknown unless evidenced.
