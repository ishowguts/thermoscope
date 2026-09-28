# ThermoScope

Evidence-based analysis of industrial thermal sources for SIH 2026 problem statement **SIH26162**.

ThermoScope is designed to combine NASA FIRMS observations, industrial infrastructure, land cover and site history in a GIS workbench. The intended workflow separates likely source, unusual behaviour and analyst review priority, with evidence and uncertainty visible for each assessment.

**Status:** P01–P05 engineering is integrated and independently verified on the Mac. The local research pilot contains 51,354 genuine NOAA-20 observations across 14 Indian regions, backed by source receipts and PostGIS. The map/list shows measurements, dated OSM and WorldCover context, grouped episodes and sites, historical timelines, and transparent source/behaviour/review-priority rules. Those rules have uncalibrated thresholds; the app does not serve a learned classifier or confirm industrial accidents.

P05 provides 10,318 frozen cases with facility-aware splits, a blind review workflow with personal sign-in, and a working XGBoost/baseline/evaluation pipeline. Human validation is deferred: there are no human reviews, no independently evaluated model and no reportable accuracy. A weak-rule run checks execution only. macOS XGBoost needs `brew install libomp`. See [current state](PROJECT_STATE.md), independent acceptance and [remaining work](docs/REMAINING_WORK.md). P06 is deferred. The bounded P07 demo (offline replay package, evidence exports, map-free mode) and the local P08 release checks are integrated in `main` as release `v0.8.0-demo` (commit `78e73de`; the tag is published from the owner's Mac); see the demo runbook and [release notes](docs/RELEASE.md). Cloud deployment remains unbuilt. The earlier college demonstration is a separate project.

## Read first

| Document | Purpose |
|---|---|
| [Decision brief](docs/00-BRIEFING.md) | Plain-language recommendation, scope, roles, time and submission priorities |
| [Architecture](docs/ARCHITECTURE.md) | Data contracts, classification, GIS, evaluation and operating design |
| [Eight milestones](docs/BUILD_PLAN.md) | Build sequence and acceptance gates |
| [Local development](docs/DEVELOPMENT.md) | Reproducible setup, checks, endpoints and database lifecycle |
| Demo runbook | Offline replay package, exports, exact demo commands and click path |
| [Release notes](docs/RELEASE.md) | Release candidate checks, data/model status cards, licences and claims |
| [Team update](docs/TEAM_UPDATE.md) | What changed, what is built before submission and how the model will be trained |
| [Access setup](docs/ACCESS_SETUP.md) | FIRMS, Earthdata and other prerequisites |
| [Submission guide](docs/SUBMISSION_GUIDE.md) | Six-slide revision and demo-video outline |
| [Audit](docs/AUDIT.md) | What the earlier code and presentation actually contain |
| [Research](docs/RESEARCH.md) | Primary sources and technology decisions |

For implementation sessions, read the contributor guide, the work contract and [current state](PROJECT_STATE.md). Verified P01/P02 versions and remaining candidates are recorded in [ENVIRONMENT.md](ENVIRONMENT.md). See [evidence](docs/EVIDENCE.md) for the checks actually performed.

## What success means

A repeatable workflow that ingests genuine observations, distinguishes industrial and non-industrial candidates, compares activity with its past baseline, and lets an analyst inspect and export the supporting evidence. Any accuracy claim must identify the reviewed dataset, held-out sites, model version and reproducible evaluation.

Satellite observation gaps, incomplete facility maps and scarce incident labels are part of the design. A thermal anomaly is not automatically an industrial accident.

Data and model terms are tracked separately in [DATA_SOURCES.md](docs/DATA_SOURCES.md). No data redistribution or application-code license is implied by this planning package.
