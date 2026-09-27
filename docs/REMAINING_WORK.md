# ThermoScope — complete remaining-work checklist

Checkpoint: 27 September 2026 IST. This is a delivery checklist, not a completion percentage or a promise of SIH selection. Implementation evidence lives in `EVIDENCE.md`; the authoritative phase order is `BUILD_PLAN.md`.

## What already exists

- P01–P04 are technically integrated on private GitHub main and verified on the Mac: genuine FIRMS ingestion, PostGIS, API/map, OSM/WorldCover context, events/sites, history and transparent rules with UNKNOWN outcomes. Main has 245 unique observations across three pilot regions. Rules are computed from data; they are uncalibrated heuristics, not learned probabilities or confirmed source truth.
- The integrated checks passed: 106 unit/API plus 15 PostGIS tests, lint, formatting, TypeScript and production build. Real provider reads and the built browser flow were checked. Five evidence defects were corrected. Human domain review remains pending.
- P05 exists separately at `579aaf3`: more saved data, frozen cases/splits, a blind annotation page and an XGBoost/baseline/calibration pipeline. Its latest Linux CI passed. It has not yet incorporated the reviewed main, passed the independent acceptance, or run on the Mac. No reportable learned-model performance exists. Predictions from that learned model are not served in the current app.
- FIRMS access is working and stored privately. The team leader reports a working Earthdata login. Registered identity is Git_Push_Pray / Bittu Mandal / 144613 / INDIAN INSTITUTE OF INFORMATION TECHNOLOGY, PUNE. Identity and login do not by themselves verify SPOC nomination or completed submission.

## A. Before the national idea submission — priority now

The [official PS table](https://www.sih.gov.in/sih2026PS), checked at approximately 21:58 IST on 27 September, displayed **140/500** and **30 September 2026** for SIH26162. This is a snapshot, not a reserved place. Aim for team review on the 28th and submission on the 29th; recheck the actual portal rather than relying on a deadline-hour assumption.

| Remaining action | Owner | Completion evidence |
| --- | --- | --- |
| Verify SPOC nomination, chosen PS and signed-in portal requirements: abstract length, PDF size, supporting links and edit-after-submit behaviour | Team leader provides authenticated access; the integrator can inspect available UI | Recorded current constraints; no passwords in chat |
| Rewrite the official six-slide presentation: problem, solution, technical approach, feasibility, impact and sources under template headings | The integrator | Editable deck and PDF; correct team details; built/proposed claims separated |
| Capture honest screenshots of real replay, industrial-context candidate, non-industrial comparison and uncertainty; choose understandable cases | The integrator; domain reviewer validates interpretation | Saved screenshot/source evidence; no old solar-as-industrial error; no dry-run accuracy |
| Write the portal abstract, architecture diagram, source references and a claim-to-evidence checklist | The integrator | Submission text and traceable claims |
| Render and inspect every final slide; check readability, font/layout and portal size limit | The integrator | Six-page PDF checked visually |
| Prepare a short demo script and, if useful/accepted by the portal, a roughly 2–3 minute video with captions | The integrator prepares; team can narrate | Playable, accurate supporting video. Optional support, not a verified mandatory field or guarantee |
| Make supporting material accessible to judges | Prepared; team chooses public scope | Logged-out link checks. Private GitHub is not a judge-accessible public demo; a reviewed video can avoid waiting for deployment |
| Approve the exact PDF/text, submit through the team account and retain proof | Team leader/team | Submitted PDF, acknowledgement/receipt and verified portal state |

Do **not** wait for P06–P08 or hundreds of reviews before preparing/submitting the idea. At current evidence level, say: “Real-data GIS, contextual rules and history demonstrated; labelling and training pipeline built on a separate branch; model not yet independently evaluated.” Do not imply that an unevaluated learned model is already operating. Selection remains the organizers' decision.

## B. P05 technical reconciliation — the implementer next

Full contract and paste prompt: P05-RECONCILE.md.

- [ ] Merge reviewed main into P05 in its separate checkout; preserve both histories and all review fixes.
- [ ] Check derived P05 features, weak labels and NOAA-20 SP/NRT handling against the corrected rules, coverage and solar safeguards.
- [ ] Regenerate affected context/features/artifacts with versioned provenance; preserve prior manifests, frozen splits and any submitted reviews. Report changed counts rather than inheriting old totals.
- [ ] Close or explicitly gate missing historical windows, genuinely independent evidence, geographic uncertainty/licence records, large-facility grouping and the held-out-region protocol.
- [ ] Check review blinding, append-only decisions and disagreement handling. Do not treat a shared token and self-entered name as production authentication.
- [ ] Audit the added ML dependencies and licences; rerun relevant tests and CI on the reconciled branch.
- [ ] Push P05 with reproducible commands and a precise technical/human blocker list. No change to canonical main.

“Everything except people is finished” is too broad while those documented technical/scientific gaps remain. Completing the engineering pipeline does not complete the P05 evidence gate.

## C. P05 independent review, Mac verification and integration — the integrator

- [ ] Independently inspect the reconciled code and reproduce material scientific/operational checks; address actionable findings.
- [ ] Verify frozen ML installation and XGBoost/OpenMP on this Mac. Linux CI does not cover it.
- [ ] Exercise migration 0006 on a disposable database with existing-data preservation and a usable backup/restore path; then apply to main only after acceptance.
- [ ] Import the exact hash-verified saved data needed for the accepted scope; reuse existing downloads. Verify counts, deduplication, case manifests and dependency versions.
- [ ] Run browser/API review checks with test fixtures, including token failures, two reviewers, disagreement and immutable records. Do not create fake real labels during testing.
- [ ] Configure a private annotation token without printing or committing it. Decide how real reviewers reach the app: localhost works only on that computer; remote access needs a suitable private service.
- [ ] Integrate accepted P05, run affected main checks and CI, and update the runnable handoff. Technical integration may finish before human labels, with model evaluation explicitly pending.

## D. Human evidence and genuine model evaluation

- [ ] Arrange two independent reviewers for test cases and a third person to resolve disagreements; obtain faculty/domain help for ambiguous industrial/cropland cases. Software can gather evidence and check itself, but cannot certify independent human truth.
- [ ] Complete the prepared P03 domain-review gate. Its three-case evidence sheet contains rule outcomes: do not use it as blind test-review material for overlapping P05 cases.
- [ ] Pilot the review instructions on practice cases outside the held-out test set. Measure actual review time and agreement before promising a total effort.
- [ ] Review with dated independent evidence, source identity, uncertainty and licence/provenance. OSM or plant-registry agreement alone cannot prove a model using those inputs is correct. “Cannot decide” is a valid outcome.
- [ ] Collect adequate eligible training, validation and test labels under the frozen protocol. Keep gold, silver and weak labels distinct; silver training labels are not independent test truth.
- [ ] Run real training and matched rules/simple-model/XGBoost comparisons. Fit/calibrate/select thresholds without test feedback. Report class support, confusion matrix, precision/recall/F1, calibration, abstention coverage, uncertainty intervals and error cases.
- [ ] Check unseen-site, known-site-future and held-out-region claims separately; verify temporal and facility-level leakage controls. Report results only for the supported population.
- [ ] Produce reproducible model/data cards and an acceptance decision. Keep a simpler baseline if the learned model does not justify adoption. Do not call industrial-source classification accident detection; a corroborated incident case study needs separate evidence.

The **~460 reviews / ~15 person-hours**, and **~1,100 reviews** for its promotion sample gate, are rough estimates based on rule-derived class mix and two minutes per review. They exclude some onboarding, investigation and disagreement effort. They guarantee neither enough usable labels nor a promoted model. Current code minimums (20 training, 5 validation and 10 test examples per class to run a report; 30 test examples per class plus a positive paired gain interval for promotion) are engineering gates, not proof of adequate scientific precision. Review support and uncertainty may demand more.

P05's current learner is **binary industrial versus non-industrial**. It is not yet a validated multi-class classifier for forest/agricultural fires, mines, flares and accidents. There is no scientifically defensible accuracy figure to put in the submission today.

## E. P06 — optional modern satellite experiment

- [ ] Test eligible AlphaEarth COG features against the same frozen cases; verify availability dates, quantization and missing-data behaviour.
- [ ] Measure added value, uncertainty, latency and cost with a matched ablation. Retain the simpler model if extra features do not help.
- [ ] Only if justified, test frozen Prithvi/HLS embeddings with proper masks/preprocessing and an approved compute budget. Programmatic Earthdata/HLS access would need verification then.

These are later experiments, not prerequisites for an honest idea submission. Earth Engine/Dynamic World and licensed Nightfire are optional alternatives, not accounts the leader must obtain now.

## F. P07 — complete the analyst product

- [ ] Serve only an appropriately accepted model with version/provenance and explicit fallback/abstention; distinguish source classification, unusual behaviour and review priority.
- [ ] Add analyst authentication/roles, append-only review and an alert lifecycle. Operational decisions must not silently become gold training labels.
- [ ] Add bounded GeoJSON/CSV exports, evidence links and attribution.
- [ ] Provide licensed cached/offline replay, clear live/replay/stale status, and a network-free demo path.
- [ ] Complete accessible map/list navigation, keyboard/mobile checks, WebGL failure handling and measured performance. Existing desktop list-only checks are only partial evidence.
- [ ] Complete dependable bounded ingestion/job scheduling, retries/resume, source freshness and degraded-provider behaviour for the deployment scope. Keep SP/NRT revisions and provenance explicit.

## G. P08 — deployment and release

- [ ] Choose provider/region/billing owner, explicit budget cap and shutdown/resource-lifetime controls before a paid resource starts.
- [ ] Package reproducible deployment with pinned environments, TLS, appropriate authentication, private database, origin/write restrictions, request/storage limits and secret-safe logs.
- [ ] Run current dependency/security/licence checks for the actual release, a fresh-clone install, deployment smoke tests and relevant browser/integration checks.
- [ ] Perform a real database backup/restore exercise; the current backup archive inspection is not a restore test.
- [ ] Configure monitoring and bounded retention; measure API/pipeline times separately from satellite acquisition/delivery delay.
- [ ] Finalize runbook, README, setup/troubleshooting, source licences, reproducible data/model evidence and offline fallback.
- [ ] Review the exact file/data allowlist and code licence before any public repository release. Preserve real authorship and dates; no invented human history or metrics.
- [ ] Verify the public/read-only demo and all judge links without an owner login; prepare team speaking notes, questions, limitations and an offline rehearsal.

Separate MODIS support, wider sensor/geographic coverage, multi-class/subtype models and confirmed-incident automation remain future scope unless a new task explicitly adopts them. They are not hidden prerequisites for this submission.

## What the team leader must supply, and what the developers can do

**Leader/team:** authenticated portal access or the verified field limits; real reviewers and their independent decisions; a private means to share reviewer access; provider/billing/budget choices if cloud spending becomes necessary; public-release/licence choices; final submission approval and team rehearsal/narration. Do not paste credentials in chat. Existing FIRMS and Earthdata setup need not be repeated.

**The developers can handle:** source collection, manifests, engineering review, Mac checks, migration/integration, private token generation, review-tool setup, evidence packets, deck/abstract/diagrams, visual QA, demo script, technical deployment preparation, tests and reproducible handoffs. It can execute approved cloud/publishing/submission actions once the exact target and necessary access are established. It cannot supply independent human labels or guarantee SIH selection.

**Next allocation:** the implementer works on section B; the integrator prioritizes section A while preparing section C for the handoff; the leader arranges section D's reviewers and portal verification. No additional a frontend contributor work is necessary right now. Assign it a separate bounded task only when that would help without overlapping ownership.
