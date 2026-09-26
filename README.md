# ThermoScope

Evidence-based analysis of industrial thermal sources for SIH 2026 problem statement **SIH26162**.

ThermoScope is designed to combine NASA FIRMS observations, industrial infrastructure, land cover and site history in a GIS workbench. The intended workflow separates likely source, unusual behaviour and analyst review priority, with evidence and uncertainty visible for each assessment.

**Status:** fresh rebuild specification. This repository does not yet contain a running application, trained model, benchmark results or deployment. Implementation starts with P01; the earlier college demonstration is a separate project.

## Read first

| Document | Purpose |
|---|---|
| [Decision brief](docs/00-BRIEFING.md) | Plain-language recommendation, scope, roles, time and submission priorities |
| [Architecture](docs/ARCHITECTURE.md) | Data contracts, classification, GIS, evaluation and operating design |
| [Eight milestones](docs/BUILD_PLAN.md) | Build sequence and acceptance gates |
| [Access setup](docs/ACCESS_SETUP.md) | FIRMS, Earthdata and other prerequisites |
| [Submission guide](docs/SUBMISSION_GUIDE.md) | Six-slide revision and demo-video outline |
| [Audit](docs/AUDIT.md) | What the earlier code and presentation actually contain |
| [Research](docs/RESEARCH.md) | Primary sources and technology decisions |

For implementation sessions, read the contributor guide, the work contract and [current state](PROJECT_STATE.md). Candidate versions are recorded in [ENVIRONMENT.md](ENVIRONMENT.md); installation and compatibility checks are still pending.

## What success means

A repeatable workflow that ingests genuine observations, distinguishes industrial and non-industrial candidates, compares activity with its past baseline, and lets an analyst inspect and export the supporting evidence. Any accuracy claim must identify the reviewed dataset, held-out sites, model version and reproducible evaluation.

Satellite observation gaps, incomplete facility maps and scarce incident labels are part of the design. A thermal anomaly is not automatically an industrial accident.

Data and model terms are tracked separately in [DATA_SOURCES.md](docs/DATA_SOURCES.md). No data redistribution or application-code license is implied by this planning package.
