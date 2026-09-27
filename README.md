# ThermoScope

Evidence-based analysis of industrial thermal sources for SIH 2026 problem statement **SIH26162**.

ThermoScope is designed to combine NASA FIRMS observations, industrial infrastructure, land cover and site history in a GIS workbench. The intended workflow separates likely source, unusual behaviour and analyst review priority, with evidence and uncertainty visible for each assessment.

**Status:** P02 implements genuine FIRMS ingestion, immutable source receipts, PostGIS storage, a bounded observations API and an interactive map/list with source evidence. The local pilot contains 13 real NOAA-20 observations across three regions. Duplicate imports, malformed rows and provider failures are checked. P03 (branch `p03-context`, in review) adds dated OpenStreetMap facility context with an approximate pixel area, dated ESA WorldCover land cover, and deterministic events and recurring sites. P04 (branch `p04-history`, in review) adds as-of history with real July–September observations and transparent rules for likely source, behaviour and review priority, shown with a 180-day timeline; these are heuristics with uncalibrated thresholds, not a trained model. P05 (branch `p05-model`, blocked on human review) adds NOAA-20 archive history for 14 Indian regions (about 24,000 detections, 10,318 episodes), a frozen case set with leak-free site-group splits, a blind label-review page and an XGBoost training and evaluation pipeline with baselines and a model card. No reviewed labels exist yet, so there is no evaluated model and no accuracy figure. Cloud deployment is a later milestone. The earlier college demonstration is a separate project.

## Read first

| Document | Purpose |
|---|---|
| [Decision brief](docs/00-BRIEFING.md) | Plain-language recommendation, scope, roles, time and submission priorities |
| [Architecture](docs/ARCHITECTURE.md) | Data contracts, classification, GIS, evaluation and operating design |
| [Eight milestones](docs/BUILD_PLAN.md) | Build sequence and acceptance gates |
| [Local development](docs/DEVELOPMENT.md) | Reproducible setup, checks, endpoints and database lifecycle |
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
