# ThermoScope — complete remaining-work checklist

Checkpoint: 29 September 2026 01:45 IST (release `v0.8.0-demo` and submission package v6). This is a delivery checklist, not a completion percentage or a promise of SIH selection. Implementation evidence lives in `EVIDENCE.md`; the authoritative phase order is `BUILD_PLAN.md`.

## What already exists

- P01–P04 are technically integrated on private GitHub main and verified on the Mac: genuine FIRMS ingestion, PostGIS, API/map, OSM/WorldCover context, events/sites, history and transparent rules with UNKNOWN outcomes. Main now has 51,354 genuine observations across 14 pilot regions after P05 acceptance. Rules are computed from data; they are uncalibrated heuristics, not learned probabilities or confirmed source truth.
- The final P05 implementation independently passed 148 unit/API plus 19 PostGIS tests on the Mac, along with lint, formatting, TypeScript and production build. Real provider reads and the built browser flow were checked. Five evidence defects were corrected. Human domain review is deferred at the owner's request.
- P05 is integrated in `main` (28 September, at the owner's request): 14-region NOAA-20 archive from 30 December 2025, frozen facility-aware case set (10,318 cases; 10,035 history-eligible), evidence policy, blind review page with personal reviewer accounts, and an XGBoost/baseline/calibration pipeline. Separate review passes and isolated-clone checks are followed by an independent acceptance, canonical Mac migration/data integration and verified real-data runs (see internal record P05-MAC-ACCEPTANCE, not published). Zero human labels, so no reportable learned-model performance; learned predictions are not served in the app.
- Release `v0.8.0-demo` (29 September, with the owner's approval): the bounded P07 demo (hashed two-region offline replay package, bounded CSV/GeoJSON evidence exports, map-free mode) and the local P08 checks (fresh clone, dependency/licence audit, secret safety, backup/restore, links) integrated in `main` at `78e73de`, CI green; 164 unit/API + 23 PostGIS tests. The tag is published from the Mac by the owner's script. See `RELEASE.md`.
- FIRMS access is working and stored privately. The team leader reports a working Earthdata login. Registered identity is Git_Push_Pray / Bittu Mandal / 144613 / INDIAN INSTITUTE OF INFORMATION TECHNOLOGY, PUNE. On 27 September around 22:19 IST, signed-in team details, submission access and form limits were verified. No separate nomination badge appeared; draft and submitted-idea lists were empty. See `SUBMISSION_DETAILS.md`.

## A. Before the national idea submission — priority now

The [official PS table](https://www.sih.gov.in/sih2026PS), checked at approximately 21:58 IST on 27 September, displayed **140/500** and **30 September 2026** for SIH26162. This is a snapshot, not a reserved place. Aim for team review on the 28th and submission on the 29th; recheck the actual portal rather than relying on a deadline-hour assumption.

| Remaining action | Owner | Completion evidence |
| --- | --- | --- |
| Portal access/form inspection completed; recheck before final submission | Done using the leader's signed-in session | Correct SIH26162 form accessible; limits recorded in `SUBMISSION_DETAILS.md`; no draft/submission created and no separate nomination badge displayed |
| Refresh the prepared six-slide presentation to the release; team review follows | Done (v6); team reviews | `ThermoScope_SIH26162_Git_Push_Pray_v6.pdf`/`.pptx` in `../output/submission/`; `SUBMISSION_PACKAGE.md` |
| Genuine screenshots captured; refresh the optional comparison clip | Done; human interpretation deferred | v2 uses actual refinery map/history; solar UNKNOWN comparison is in the video shot list; no dry-run accuracy or independent source verdict |
| Refresh prepared portal text and claim ledger against the final demonstrated release | Done (v6); team reviews | Title 72, summary 1,983 and description 7,451 characters in `../output/submission/v6/` |
| Export and inspect the refreshed final PDF | Done | v6: six pages inspected, 741,200 bytes, six reference links resolve; independent reviewer: no blocker |
| Record and caption the optional roughly 2–3 minute demo video | Recorded; team uploads if wanted | `v6/ThermoScope_SIH26162_demo_offline.mp4`, 2 min 4 s, captioned, no audio; not uploaded. No selection guarantee |
| Make supporting material accessible to judges | Prepared; team chooses public scope | Logged-out link checks. Private GitHub is not a judge-accessible public demo; a reviewed video can avoid waiting for deployment |
| Approve the exact PDF/text, submit through the team account and retain proof | Team leader/team | Submitted PDF, acknowledgement/receipt and verified portal state |

Do **not** wait for P06–P08 or hundreds of reviews before preparing/submitting the idea. At current evidence level, say: “Real-data GIS, contextual rules and history demonstrated; labelling and training pipeline integrated; model not yet independently evaluated.” Do not imply that an unevaluated learned model is already operating. Selection remains the organizers' decision.

## B. P05 technical reconciliation — done and accepted

Full contract and paste prompt: P05-RECONCILE.md (internal, not published).

Implemented and reviewed on 27–28 September, then independently accepted on 28 September. The earlier review and the acceptance checks are recorded separately.

- [x] Merge reviewed main into P05 in its separate checkout; preserve both histories and all review fixes. (`09fb77b`; later `1e3bb0a` merged the same way)
- [x] Check derived P05 features, weak labels and NOAA-20 SP/NRT handling against the corrected rules, coverage and solar safeguards.
- [x] Regenerate affected context/features/artifacts with versioned provenance; preserve prior manifests, frozen splits and any submitted reviews. Report changed counts rather than inheriting old totals.
- [x] Close or explicitly gate missing historical windows (NOAA-20 SP backfilled from 30 December 2025, ADR-022: 10,035 of 10,318 cases eligible), genuinely independent evidence, geographic uncertainty/licence records, large-facility grouping and the held-out-region protocol.
- [x] Check review blinding, append-only decisions and disagreement handling; replace the shared token and typed names with personal accounts (ADR-023). Still not production authentication (P07).
- [x] Audit the added ML dependencies and licences; rerun relevant tests and CI.
- [x] Push P05 with reproducible commands and a precise technical/human blocker list.

## C. P05 independent review, Mac verification and integration — done

- [x] P05 integrated with main CI; the final implementation was inspected and CI independently confirmed.
- [x] Installed frozen ML dependencies and ran a synthetic XGBoost fit, 148 unit/API tests, 19 PostGIS tests, lint, format, TypeScript and production build on the Mac.
- [x] Restored the original backup into an isolated database; tested migrations and preservation. Backed up canonical main and applied migrations through 0008.
- [x] Verified 464 original and 252 backfill FIRMS files by inventory/hash; reproduced frozen cases, facility grouping, land cover and v4 features. All episode/split/feature fingerprints match the recorded results.
- [x] Added verified data to main with constraints enabled and no replacement of old rows: 51,354 observations. Every original row across 24 application tables remains unchanged.
- [x] Exercised real main training: `INSUFFICIENT_LABELS` and `DRY_RUN_NOT_EVIDENCE`; artifact hashes pass. No accuracy claims. Zero real reviews/accounts.
- [x] Browser/API checks: v2 and superseded v1, sign-in protections, genuine newly integrated observations/context/history and clear rule-only messaging. Full acceptance: P05-MAC-ACCEPTANCE.md (internal, not published).

## D. Human evidence and genuine model evaluation — deferred

**Owner decision, 28 September (ADR-024): no reviewer recruitment or manual labels are required before submission.** These are later scientific acceptance tasks. Engineering acceptance does not satisfy them, and AI guesses cannot replace independent labels. Real reviewer accounts and private HTTPS are unnecessary until actual people will review.

- [ ] Arrange two independent reviewers for test cases and a third person to resolve disagreements; obtain faculty/domain help for ambiguous industrial/cropland cases. Software can gather evidence and check itself, but cannot certify independent human truth.
- [ ] Complete the prepared P03 domain-review gate. Its three-case evidence sheet (internal, not published) contains rule outcomes: do not use it as blind test-review material for overlapping P05 cases.
- [ ] Pilot the review instructions on practice cases outside the held-out test set. Measure actual review time and agreement before promising a total effort.
- [ ] Review with dated independent evidence, source identity, uncertainty and licence/provenance. OSM or plant-registry agreement alone cannot prove a model using those inputs is correct. “Cannot decide” is a valid outcome.
- [ ] Collect adequate eligible training, validation and test labels under the frozen protocol. Keep gold, silver and weak labels distinct; silver training labels are not independent test truth.
- [ ] Run real training and matched rules/simple-model/XGBoost comparisons. Fit/calibrate/select thresholds without test feedback. Report class support, confusion matrix, precision/recall/F1, calibration, abstention coverage, uncertainty intervals and error cases.
- [ ] Check unseen-site, known-site-future and held-out-region claims separately; verify temporal and facility-level leakage controls. Report results only for the supported population.
- [ ] Produce reproducible model/data cards and an acceptance decision. Keep a simpler baseline if the learned model does not justify adoption. Do not call industrial-source classification accident detection; a corroborated incident case study needs separate evidence.

Current estimates after the backfill, **~480 reviews / ~16–24 person-hours** to report results and **~1,100 reviews** for its promotion sample gate, are rough estimates based on rule-derived class mix and two to three minutes per review. They exclude some onboarding, investigation and disagreement effort. They guarantee neither enough usable labels nor a promoted model. Current code minimums (20 training, 5 validation and 10 test examples per class to run a report; 30 test examples per class plus a positive paired gain interval for promotion) are engineering gates, not proof of adequate scientific precision. Review support and uncertainty may demand more.

P05's current learner is **binary industrial versus non-industrial**. It is not yet a validated multi-class classifier for forest/agricultural fires, mines, flares and accidents. There is no scientifically defensible accuracy figure to put in the submission today.

## E. P06 — optional modern satellite experiment — defer

Wait for independently reviewed labels before starting the matched comparison. Adding embeddings now cannot establish an improvement.

- [ ] Test eligible AlphaEarth COG features against the same frozen cases; verify availability dates, quantization and missing-data behaviour.
- [ ] Measure added value, uncertainty, latency and cost with a matched ablation. Retain the simpler model if extra features do not help.
- [ ] Only if justified, test frozen Prithvi/HLS embeddings with proper masks/preprocessing and an approved compute budget. Programmatic Earthdata/HLS access would need verification then.

These are later experiments, not prerequisites for an honest idea submission. Earth Engine/Dynamic World and licensed Nightfire are optional alternatives, not accounts the leader must obtain now.

## F. P07 — complete the analyst product

**Recommended next:** the bounded submission demo task (internal, not published): genuine replay, bounded exports, clear evidence/uncertainty and browser fallback/accessibility checks. It keeps one writer per checkout. The full product list below remains broader than that task.

- [ ] Serve only an appropriately accepted model with version/provenance and explicit fallback/abstention; distinguish source classification, unusual behaviour and review priority.
- [ ] Add analyst authentication/roles, append-only review and an alert lifecycle. Operational decisions must not silently become gold training labels.
- [x] Add bounded GeoJSON/CSV exports, evidence links and attribution. (P07-SUB-001)
- [x] Provide licensed cached/offline replay, clear live/replay/stale status, and a network-free demo path. (P07-SUB-001: two regions, historical replay, no offline basemap; Mac Wi-Fi-off run pending)
- [ ] Complete accessible map/list navigation, keyboard/mobile checks, WebGL failure handling and measured performance. Existing desktop list-only checks are only partial evidence.
- [ ] Complete dependable bounded ingestion/job scheduling, retries/resume, source freshness and degraded-provider behaviour for the deployment scope. Keep SP/NRT revisions and provenance explicit.

## G. P08 — deployment and release

The local demo-release checks are done (P08-REL-001, `RELEASE.md` §3); the items below remain for a deployment or public release. Hosting is optional for submission; a reviewed recording with local replay can be sufficient supporting material. Deployment-only checks apply when a concrete hosting target is authorized.

- [ ] Choose provider/region/billing owner, explicit budget cap and shutdown/resource-lifetime controls before a paid resource starts.
- [ ] Package reproducible deployment with pinned environments, TLS, appropriate authentication, private database, origin/write restrictions, request/storage limits and secret-safe logs.
- [ ] Run current dependency/security/licence checks for the actual release, a fresh-clone install, deployment smoke tests and relevant browser/integration checks.
- [ ] Rehearse backup/restore for the final release/deployment target. A real baseline backup was already restored for P05 acceptance; that does not verify a future cloud backup configuration.
- [ ] Configure monitoring and bounded retention; measure API/pipeline times separately from satellite acquisition/delivery delay.
- [ ] Finalize runbook, README, setup/troubleshooting, source licences, reproducible data/model evidence and offline fallback.
- [ ] Review the exact file/data allowlist and code licence before any public repository release. Preserve real authorship and dates; no invented human history or metrics.
- [ ] Verify the public/read-only demo and all judge links without an owner login; prepare team speaking notes, questions, limitations and an offline rehearsal.

Separate MODIS support, wider sensor/geographic coverage, multi-class/subtype models and confirmed-incident automation remain future scope unless a new task explicitly adopts them. They are not hidden prerequisites for this submission.

## What the team leader must supply, and what the developers can do

**Leader/team now:** choose recording/local replay versus a hosted demo, approve the refreshed submission package, and authorize or perform final submission. Narration is optional. Provider/billing/budget and public-release choices are needed only if hosting or publication is chosen. **Later:** arrange independent reviews and a private means to share reviewer access if pursuing model validation. Portal access was supplied and form limits were inspected; sign in again only if the session expires. Do not paste credentials in chat. Existing FIRMS and Earthdata setup need not be repeated.

**The developers can handle:** source collection, manifests, engineering review, Mac checks, migration/integration, private token generation, review-tool setup, evidence packets, deck/abstract/diagrams, visual QA, demo script, technical deployment preparation, tests and reproducible handoffs. It can execute approved cloud/publishing/submission actions once the exact target and necessary access are established. It cannot supply independent human labels or guarantee SIH selection.

**Next allocation:** P07-SUB-001 and the local P08 checks are integrated and the submission package is refreshed (v6); the owner runs the two Mac scripts, the team reviews and submits. Sections D/E are deferred, not secretly completed. Portal inspection is recorded; final submission remains pending.
