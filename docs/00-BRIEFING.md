# ThermoScope: the rebuild decision
SIH26162 | Briefing for Git push pray | 25 September 2026

## My recommendation
Start fresh from the folder architecture's core idea. Keep the separation between satellite detections, short events, recurring sites, and evidence. Replace its broad research wish list with a smaller, measurable system. The submitted Part 1 is useful as a record of the college demo, but its code is not a sound intelligence baseline.

The strongest pitch is: **ThermoScope helps an analyst distinguish routine industrial heat from unusual thermal activity, and shows the evidence and uncertainty behind every decision.** We should demonstrate this on Indian sites before expanding the scope.

FastAPI, PostgreSQL/PostGIS, React and boosted-tree models are reasonable choices. Their age is not evidence that the design is obsolete. The weaknesses are unverified labels, simulated results, a broad taxonomy, and insufficient proof that the system improves an analyst's decisions. A newer model helps only if a fair comparison shows a benefit.

## Submission is the immediate priority
The official 2026 guide gives **30 September 2026** as the deadline and a **500-idea limit per PS**. The live PS26162 table showed **93/500 at approximately 23:31 IST on 25 September**. This snapshot does not reserve a slot. [S1, S2]

Prepare the submission in the next 24-48 hours. A polished, truthful proposal with a small verified workflow is preferable to missing the submission window while attempting the whole build. Do not assume a submitted entry can be edited; verify that in the team leader's portal.

## What this audit established
The public prototype at commit e110fd1 contains three fixed thermal events, two fixed facilities and a fixed classification response. The folder repository at c36e47a has a more substantial ingestion, PostGIS and infrastructure foundation. Its saved test claims are historical; no fresh runtime certification was performed in this audit. Neither inspected codebase contains an evaluated industrial-fire classifier.

<!-- page -->

# What the new system will do

An analyst opens a map, selects a hotspot and sees its thermal history, nearby industrial features, land-cover context, supporting imagery and the reason it was prioritized. They can review or correct the assessment and export a case report.

## Three decisions, kept separate
- **Likely source:** industrial activity, vegetation/agricultural burning, another source, or insufficient evidence.
- **Behaviour:** recurring within its observed baseline, unusual compared with that baseline, new, or insufficient history.
- **Review priority:** which cases deserve attention first. This is not a probability of an accident or a measure of physical damage.

A refinery's normal flare and a possible abnormal event near that refinery must not receive the same treatment. A field burn next to an industrial estate is a deliberate hard test, rather than an example we hide.

## The technical upgrade
Use NASA FIRMS detections, cached OSM infrastructure, land cover and a site's past observations. Establish rules and an XGBoost baseline first. Then test **AlphaEarth annual satellite embeddings** as additional geographic context: ready-made numerical summaries of a place that reduce the need to train a large image model. They are annual context, not a live fire sensor. [S3, S4]

For later experiments, use a compact **Prithvi-EO-2.0** satellite model on correctly prepared multispectral imagery, instead of making a generic RGB ResNet-50 mandatory. Keep this branch only if it improves held-out results within the resource budget. No model's published benchmark becomes our claimed accuracy. [S5]

## What makes the proposal distinctive
The proposed contribution is the combination of site history, geographic context, uncertainty-aware classification and an auditable analyst workflow for Indian industrial hotspots. A time-based replay will show what the system could have known at each moment, with later corroborating evidence clearly separated.

NASA already offers mapping and alerts, and standard-quality products include broad hotspot-type information. Gas-flare products also exist. Our comparison must acknowledge them; “the first system to classify heat” would be an unsupported claim. [S6, S7]

<!-- page -->

# How the team will work

## Recommended division of work
**Lead integrator:** the architecture, ingestion, geospatial logic, evaluation, integration and release checks, plus the frontend and documentation. One lead is sufficient to carry the engineering work; more contributors are optional rather than a dependency.

**Independent reviewer:** inspect the evaluation design, data leakage, difficult backend changes and release diff. The useful role is to challenge the implementation. Agreeing with an untested claim is not verification.

**Frontend contributor:** take a bounded frontend or browser-testing task once the API contract is stable. The same acceptance checks apply. Do not let two people edit the same checkout simultaneously.

These are proposed responsibilities. Use explicit handoffs between contributors.

## The work contract prevents lost work
Each task will record its goal, allowed files, input contracts, acceptance checks and blocked prerequisites. Before switching sessions, commit coherent changes and record the commit, unfinished changes, commands, results and next action. A new session checks the repository instead of trusting a chat summary.

Use one branch/worktree per concurrent task and one integrator. Account changes should preserve repository continuity through these files; they are not a substitute for saved changes, checks or provider access. Plan for normal service limits and interruptions, without relying on automatic account rotation.

## Your team still has essential work
You need to supply account access, make spending and submission decisions, help verify ambiguous examples with a mentor, and understand the demo well enough to defend it. Independent incident labels cannot be created by confidence alone.

For the final presentation, each member should be able to explain one subsystem, one failure case and one limitation. A team-recorded narration is preferable for the video. We can prepare the script, recording steps and practice questions.

<!-- page -->

# Time, resources and cost

These are planning estimates for focused work with accounts available, not delivery guarantees. Label verification and missing data can extend them. More spending cannot remove satellite coverage gaps or manufacture ground truth.

| Outcome | Realistic effort | Main dependency |
| --- | --- | --- |
| Correct submission deck, abstract and evidence plan | 1-2 focused days | Team ID, portal access and team review |
| Small real-data regional workflow | 3-5 focused days | FIRMS access, usable historical data |
| Evaluated classifier and reliable replay | 2-3 weeks total | Independently checked labels and held-out sites |
| Stronger imagery experiments and finale hardening | 4-6 weeks total | Data coverage, evaluation, reviewer feedback |

The complete research system is not a responsible promise before the current submission deadline. The near-term deck must distinguish what is demonstrated from what is proposed.

## Tools needed
GitHub, a local editor, Git, Docker/Compose, Python with uv, Node LTS, PostgreSQL/PostGIS and a browser are sufficient for the core workflow. Cloud CPU compute and object storage handle development and hosting. Optional GPU sessions are for image experiments; the map and structured classifier should run without a GPU or paid language-model API.

## Sensible planning allowances
- **Local development and public-data exploration:** no additional hosting charge if existing resources suffice; storage and bandwidth still need checking.
- **Small cloud demo:** reserve roughly INR 3,000-10,000 per month as a planning allowance, depending on compute, database, storage and egress.
- **Optional GPU experiments:** reserve INR 2,000-8,000 for bounded trials, with automatic shutdown.
- **Coding subscriptions:** separate from hosting; existing subscriptions may suffice. No new purchase is required for this planning stage.

These allowances are estimates, not current vendor quotations. Before provisioning, select the provider, inspect its current calculator, state a maximum charge and obtain approval for that exact run. Prefer a modest CPU deployment first. Unlimited budget should not become unbounded resource use.

## Version policy
Use maintained stable releases, exact lockfiles and repeatable container builds. Current registry versions were checked during this audit. Their mutual compatibility still needs the first clean build and tests. The engineering package records candidates and that verification gate; it does not label untested combinations “production ready.”

<!-- page -->

# What needs to change in the PPT

Use the official template's six content positions and export the submission as PDF. Its instruction page sets a six-slide maximum including the title and preserves the supplied idea-detail headings. [S8]

## 1. Title
Correct the cover year to 2026, fill the registered Team ID and confirm the exact team name. Slide 5 also contains a 2024 logo. Use one consistent project name, ThermoScope, and the current official template assets.

## 2. Proposed solution
Explain the analyst's problem and show the recurring-source versus abnormal-event distinction. Replace the five facility-like “hotspot types” with a consistent source/behaviour taxonomy. Say “near-real-time, subject to satellite availability.” Put implemented and proposed capabilities in distinct language.

## 3. Technical approach
Replace the large technology collage with a readable data-to-decision flow and one genuine, labeled screenshot. The embedded graphic claims 120 simulated events, 20 facilities and 11 endpoints; the linked backend instead has 3 events, 2 facilities and 7 application routes. The same graphic claims six-category classification and a custom AI engine that the code does not implement. Reconcile every claim with the release being shown.

The synthetic thermal zoom is an illustration, not a verified satellite fire footprint. Label it accordingly or replace it with cited real imagery. “4 pages” and “15+ components” do not help establish scientific value.

## 4. Feasibility and viability
Replace “one semester” with a staged schedule and explicit data dependencies. Show how we handle clouds, incomplete industrial maps, insufficient history and scarce incident labels. Describe a held-out evaluation and the baseline we must beat. “No ready-made dataset exists” is too absolute; say a suitable, verified dataset has not yet been secured.

## 5. Impact and benefits
Show the operator workflow and measurable evaluation goals: fewer unnecessary reviews at fixed incident recall, time to inspect a case, and reliable handling of missing data. Do not promise lives saved, prevented explosions or earlier detection without evidence. Recurring heat itself is not an emergency.

## 6. Research and references
Retain directly relevant persistence and spatial-leakage research. Add NASA data limitations and the selected satellite model/data documentation. Use readable links. Keep the demo/repository link accessible, and verify all links from a signed-out browser before submission.

<!-- page -->

# Evidence that can strengthen shortlisting

Selection cannot be guaranteed or assigned a defensible percentage. The useful strategy is to make the proposal easy to assess and difficult to dismiss: exact PS fit, a clear differentiator, feasible data access, credible evidence and a team that can explain its work.

## The minimum persuasive demonstration
Show three complete cases: a recurring industrial source; an independently documented abnormal industrial incident if a matching satellite observation exists; and a vegetation/agricultural event near industry. Add one uncertainty case with cloud, missing history or conflicting context. Do not claim a match when the satellite did not detect the documented incident.

Each case should expose timestamps, source links, model/rule version, history and the reason for its classification. Record one failure example. A saved replay makes the demo dependable when the network fails, provided it is clearly marked as historical data.

## Evidence before accuracy claims
Compare a simple proximity rule, a thermal/history baseline and the proposed contextual model on the same site-disjoint test set. Report class counts, precision, recall, macro-F1, abstention and false alerts. Keep repeated observations from one facility out of both training and testing. We should publish a model card and a short error analysis alongside any score.

The first goal is a reproducible result, not a chosen headline accuracy. If independent industrial-incident labels are too few, report a case study and a limited source-classification experiment instead of pretending to have validated incident detection.

## Video recommendation
**Yes: prepare a short demo video if the portal allows a supporting link.** The guide's listed idea-submission fields require a PDF and do not establish a mandatory student demo video. A video is therefore supporting evidence until the actual portal says otherwise. It may help explain the workflow, but there is no verified selection uplift. [S1]

Suggested 2.5-3 minute sequence: 20 seconds on the decision problem; 35 seconds on routine heat; 40 seconds on an abnormal or uncertain case; 30 seconds on the comparison and limitations; 25 seconds on review/export; 15 seconds on deployment and next steps. These are editorial recommendations, not SIH limits.

Use team narration, readable screen recording and captions. Show genuine application behaviour. Avoid long introductions and animations that consume time needed for evidence. Test the unlisted/public viewing link without signing in; never make the PDF depend on a judge watching it.

<!-- page -->

# Prerequisites and the first handoff

## Needed before a live-data build
- **FIRMS MAP_KEY:** free request through NASA. Store it only in local secrets or the deployment secret manager. Test one small region and retain no key-bearing URL in logs. [S3]
- **NASA Earthdata account:** for historical and HLS access where required. Keep login and any tokens out of chat, documents and Git.
- **Cloud account and run budget:** identify the provider and billing owner before starting a paid machine. Set resource lifetime and shutdown controls.
- **Map and imagery access:** use public/cached sources where permitted. If a Copernicus account or map-provider key becomes necessary, obtain it before the dependent milestone.
- **Review help:** one faculty/domain reviewer for a small label sample, difficult cases and interpretation. The developers can prepare the evidence bundle and annotation form.

AlphaEarth's public cloud-optimized files provide an alternative to making Earth Engine registration a core dependency. Earth Engine is optional for Dynamic World experiments. The licensed VIIRS Nightfire service is optional and should not block the core build. [S4, S7]

## Needed before submission
You confirmed that the team-leader login is available. Verify nomination status, Team ID and registered team name in the portal. Inspect its file-size limit, abstract limits, supporting-link fields and edit-after-submit behaviour. Keep the official template's PDF requirement. Save the final submitted PDF and receipt after the team approves them.

## Repository arrangement
Use a fresh repository under **ishowguts**, retaining both the old public prototype and the local ThermalGuard folder as historical references. The new workspace will contain the briefing, architecture, build milestones, work contract, state ledger, version baseline and submission guidance. It initially contains specifications, not a completed application.

Keep documentation specific and short, commits meaningful, examples clearly marked, tests relevant and setup reproducible. Preserve real authorship and dates. Professional repository presentation does not require fabricated commit history, fake metrics or concealment of tools used.

## First implementation task
Read the architecture and work contract; establish the environment and frozen dependencies; ingest one small real FIRMS sample with correct units and provenance; show it through PostGIS and the API; verify duplicate ingestion and a provider failure. Only then extend the features and model.

The immediate parallel priority is the corrected six-slide submission narrative. The full build can continue after submission, while all claims in that submission remain accurate at the time it is sent.

<!-- page -->

# Sources and audit references

Public sources checked on 25 September 2026. Product-specific limitations and release numbers must be rechecked when implementation begins. Recommendations, schedules and budget allowances are project judgments.

- **S1. SIH 2026 Guidelines**, especially PDF pages 16-20: https://sih.gov.in/letters/2026/SIH%202026%20Guidelines.pdf
- **S2. Live problem statements**, filter SIH26162: https://www.sih.gov.in/sih2026PS
- **S3. FIRMS Area API**: https://firms.modaps.eosdis.nasa.gov/api/area/
- **S4. AlphaEarth public COG dataset and handling instructions**: https://developers.google.com/earth-engine/guides/aef_on_gcs_readme
- **S5. Prithvi compact model card**: https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-tiny-TL
- **S6. NASA VIIRS product fields and limitations**: https://modaps.modaps.eosdis.nasa.gov/services/about/products/viirs-land-c2-nrt/vj114imgtdl_nrt.html
- **S7. VIIRS Nightfire and its current access terms**: https://eogdata.mines.edu/products/vnf/
- **S8. Official SIH 2026 presentation template**: https://sih.gov.in/letters/2026/SIH2026-IDEA-Presentation-Format.pptx
- **S9. FIRMS delivery timing and existing services**: https://firms.modaps.eosdis.nasa.gov/
- **S10. Spatial leakage study, 2026**: https://doi.org/10.3390/geohazards7030090
- **S11. Persistent hotspot research, 2018**: https://doi.org/10.3390/rs10071118
- **S12. Dynamic World data documentation**: https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1

## Inspected project materials
Public source: https://github.com/sa-mael451/thermo-scope-part1 at e110fd19398d69631d8bf3c77f78bf413f3a3aa5. Backend routes and fixed responses were inspected directly through the GitHub connector.

Local source: thermalguard-ai at c36e47a, including architecture, process notes, state, decisions, dependency manifests, ingestion and enrichment code. The tracked working tree was clean and no remote was configured at audit time. An ignored local environment file was present; its values were not read.

Presentation: the supplied six-slide PowerPoint and the shared Canva design. Text and embedded figures were inspected. The official blank template was separately downloaded to distinguish submission requirements from the team's claims.

GitHub connection: ishowguts is authenticated. Access to sa-mael451/thermo-scope-part1 is read-only. The fresh project is intentionally separate.
