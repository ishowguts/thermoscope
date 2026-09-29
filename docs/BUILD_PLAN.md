# Eight build milestones

This is the single milestone sequence. P01-P08 replace all old phase labels. Times are planning estimates for focused work with access available; data verification is the main uncertainty. P01-P04 target a small regional workflow in approximately 3-5 working days, P05 an evaluated baseline in roughly 2-3 weeks total, and optional P06 plus hardening roughly 4-6 weeks total. Do not add the phase estimates as independent promises.

The submission track starts immediately: revise the six-slide story and abstract, verify portal constraints, then attach only evidence that exists. Do not wait for P08 to prepare the idea submission. The publicly documented deadline is 30 September 2026, subject to the PS cap and any official changes.

## P01 — Environment, contracts and coverage inventory

**Build:** minimal backend/frontend structure, disposable PostGIS, configuration, CI, frozen dependencies, source/time schemas and documented commands. Start the label/source inventory now: candidate regions, periods, facility evidence and potential incident reports. Obtain credentials before dependent tasks.

**Gate:** clean install on selected architecture; API health/readiness; migration and geographic-distance check; UI typecheck/build; sanitized secret handling; coverage inventory with explicit unavailable sources. Small synthetic fixtures are labeled and contain no invented real incident claims. No classifier badge yet.

**Owner:** lead integrator. Task: internal record P01-FOUNDATION (not published).

## P02 — Genuine FIRMS ingestion through to the map

**Build:** narrow region/product request, immutable raw object and manifest, VIIRS NRT normalization (P02 scope; a separate MODIS adapter remains deferred), per-row quarantine, atomic deduplication, ingestion status, bounded observations API and basic map/list. Before events exist, use an explicitly named observations endpoint; do not mislabel raw points as resolved incidents. Implement a saved historical sample for repeatable tests.

**Gate:** ingest a real sample twice without duplication; preserve time/FRP/temperature/confidence semantics; handle an invalid row and a provider failure; show last acquisition versus update time. A real-data map and historical replay badge can now be demonstrated. No fixed AI classification response.

## P03 — Context, events and recurring sites

**Build:** regional OSM cache, dated land-cover extraction, uncertainty support region, multiple facility associations, deterministic event/site linkage and event API contract. Add feature-source manifests and availability times. Select final pilot windows from actual coverage.

**Gate:** metre-distance and CRS tests; adjacent industrial/agricultural hard case; missing OSM and raster nodata; neighbour separation, late arrival and split/merge lineage. Reprocessing produces deterministic memberships for a fixed version.

## P04 — History, rules and evidence panel

**Build:** historical windows, sensor-aware robust baseline, explicit insufficient-history state, transparent proximity/history rules, three output axes, source/evidence panel and timeline. Implement availability-filtered replay; mark unknown historical publication time as retrospective.

**Gate:** no future features; no false model-probability label on a rule; a recurring industrial case, a non-industrial comparison and an uncertainty case can be inspected end-to-end. Test MAD=0, sensor changes and no-observation gaps. This is the first coherent analyst workflow, still not a validated learned classifier.

## P05 — Reviewed labels and structured classifier

**Build:** annotation/evidence package, reviewer disagreement process, frozen site/episode splits, rules and thermal/history baselines, XGBoost context model, calibration, abstention and model card. Label collection began in P01 and continues here.

**Gate:** independent test evidence; no site or episode overlap; train-only preprocessing; per-class support, confusion matrix, precision/recall/F1, coverage/calibration and error examples. Compare identical test cases. If incident support is insufficient, publish a limited source-classification result and incident case study. Do not manufacture a 95% target to fill a slide.

## P06 — Modern satellite context experiment

**Submission scope, 28 September (ADR-024):** human validation is deferred at the owner's request. Do not start P06's comparison without independent labels. The independent demo portions of P07 and release checks of P08 may proceed under internal record P07-SUBMISSION-DEMO (not published); this does not complete the full P05 scientific gate or P07/P08 production scope. Submit an accurate earlier release if those demo improvements would delay the entry.

**Build:** eligible AlphaEarth COG extraction and matched ablation. Only after this comparison, optionally add frozen Prithvi tiny embeddings on correctly prepared HLS. Freeze model revisions and optional environment. Keep the no-imagery path usable.

**Gate:** annual-layer availability/quantization checks; patch quality and masks; matched test subset and geography ablation; measured gain, resource use and uncertainty. Keep the simpler model if extra context does not improve the relevant held-out outcome. A negative result is a valid completed experiment.

## P07 — Analyst review, exports and dependable replay

**Build:** authenticated append-only review, alert lifecycle, bounded exports, accessible map/list workflow, source freshness and historical/offline bundle with permitted assets. Integrate the promoted model with clear provenance.

**Gate:** browser selection/history/evidence/review/export; role checks; missing-source and WebGL fallback; network-free case replay; attribution. Reviews do not overwrite past model output or silently become gold labels.

## P08 — Release and evidence package

**Build:** chosen cloud pilot after bounded approval, TLS/read-only public demo, resource limits, backup/restore exercise, release runbook, model/data cards and final demonstration material. Keep an offline fallback.

**Gate:** fresh clone and frozen install; CI and relevant security checks; deployment smoke check; measured API/pipeline timings with satellite delay separate; database restore; reproducible evaluation from manifest; reviewed claims and links. Public release requires a scanned exact file allowlist and correct data rights. Submission uses the release actually shown, even if it is an earlier milestone.

## Ownership and dependencies

The lead integrator owns schemas, migrations, lockfiles and merged state. An independent reviewer may review P05/P06 evidence read-only. A frontend contributor may own a bounded P07 UI task after the API contract stabilizes. Additional contributors are optional and must be assigned explicitly; separate worktrees prevent concurrent file edits.

Each task records start state, allowed files, acceptance evidence and handoff. When a prerequisite blocks one branch, work on independent authorized tasks; do not replace a real-data acceptance check with a fixture and call it complete.
