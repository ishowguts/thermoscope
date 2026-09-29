# ThermoScope

[![Project checks](https://github.com/ishowguts/thermoscope/actions/workflows/check.yml/badge.svg)](https://github.com/ishowguts/thermoscope/actions/workflows/check.yml)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)

**Evidence-first GIS workbench for industrial thermal sources.** Smart India Hackathon 2026, problem statement **SIH26162** (National Technical Research Organisation), Software / Disaster Management. Team **Git_Push_Pray**, IIIT Pune.

NASA FIRMS flags satellite heat detections every day, but each one is only a hot pixel roughly 375 m across. It could be a refinery flare, crop-residue burning, a forest fire or sunlight glinting off a roof. ThermoScope puts every detection next to the evidence an analyst needs and answers three separate questions, each with its reasons and its missing data:

1. **Likely source:** industrial, non-industrial or unknown?
2. **Behaviour:** is this new, recurring or persistent at this place?
3. **Review priority:** how soon should an analyst look?

When the evidence is thin, it says *unknown* instead of guessing.

## Status (release `v0.8.0-demo`)

- **Built and tested:** ingestion of real NASA FIRMS VIIRS (NOAA-20) detections with a SHA-256 receipt for every file; PostGIS context (approximate pixel area, mapped OpenStreetMap facilities, ESA WorldCover land cover); 7- to 180-day history with the days actually covered; transparent rules (`rules-v2`) with reason codes; a React + MapLibre workbench; CSV/GeoJSON evidence exports; a hashed offline demo package for two regions (Jamnagar and a Punjab comparison region).
- **Machine-learning lane:** built and tested (scikit-learn, XGBoost, 10,318 frozen cases with facility-grouped splits, blind review workflow), but **no model is served** and no accuracy is claimed until human-reviewed labels exist.
- **Not claimed:** live or real-time monitoring, alerts, confirmed incidents, calibrated probabilities or a hosted service. The demo is historical replay of saved real data.

## How it works

| Step | What happens | Tech | Output |
| --- | --- | --- | --- |
| 1. Fetch | VIIRS detections from the NASA FIRMS area API, in five-day windows per region | FIRMS API | CSV file |
| 2. Receipt | Each file is fingerprinted before import | SHA-256 | receipt (hash, time, status) |
| 3. Ingest | Every observation keeps its file hash and row; re-imports add no duplicates | PostgreSQL + PostGIS, SQLAlchemy | observations table |
| 4. Context | Approximate pixel area, nearby OSM facilities, land-cover mix | PostGIS, rasterio | context JSON |
| 5. History | Earlier activity within 750 m over 7, 30, 90 and 180 days, with coverage | PostGIS | time windows |
| 6. Assess | Source, behaviour and priority, each with a rule code and reasons | Python rules engine | assessment JSON |
| 7. Serve and export | REST API and GIS workbench; one case as GeoJSON, a window as CSV | FastAPI, React, MapLibre GL | workbench, CSV, GeoJSON |

A mapped facility near a detection is shown as context, never as a confirmed source.

## Tech stack

| Layer | Tools |
| --- | --- |
| Data | NASA FIRMS (VIIRS NOAA-20, NRT and SP), OpenStreetMap (Overpass), ESA WorldCover 2021, WRI Global Power Plant Database (review lane) |
| Storage and GIS | PostgreSQL 18 + PostGIS 3.6 (Docker), Alembic, SQLAlchemy 2, psycopg 3, rasterio, NumPy |
| Logic and API | Python 3.13 (uv-locked), FastAPI, Pydantic 2, Uvicorn |
| Interface | React 19, TypeScript, Vite, MapLibre GL |
| Machine learning | scikit-learn, XGBoost (built, not served) |
| Quality | pytest (164 unit/API + 23 PostGIS tests), Ruff, Prettier, GitHub Actions |

## Quick start

Needs Python 3.13, Node 24, uv and Docker with Compose. From the repository root:

```sh
make install      # locked Python and npm dependencies
make configure    # local .env with a random database password
make db-up        # PostGIS in Docker, bound to 127.0.0.1
make migrate
make check        # lint, format, 164 tests, TypeScript and production build
make dev-api      # terminal 1: API on 127.0.0.1:8000
make dev-web      # terminal 2: workbench on http://127.0.0.1:5173
```

Real observations are fetched with your own NASA FIRMS key (kept in `.env`, never committed): see [Local development](docs/DEVELOPMENT.md). To run the offline demo from a hashed package, see the [demo runbook](docs/DEMO_RUNBOOK.md).

## Repository layout

| Path | Contents |
| --- | --- |
| `backend/thermoscope/` | FastAPI app, FIRMS ingestion, context, history, rules, exports, offline replay, ML lane |
| `backend/tests/` | Unit, API and PostGIS integration tests |
| `backend/migrations/` | Alembic database migrations |
| `frontend/` | React + MapLibre workbench |
| `scripts/` | Local configuration, demo package, release audit |
| `docs/` | Architecture, data sources, development, release notes, evidence |

## Documentation

| Document | Purpose |
| --- | --- |
| [Architecture](docs/ARCHITECTURE.md) | Data contracts, classification, GIS and evaluation design |
| [Local development](docs/DEVELOPMENT.md) | Setup, checks, endpoints and database lifecycle |
| [Demo runbook](docs/DEMO_RUNBOOK.md) | Offline replay package, exports and demo commands |
| [Release notes](docs/RELEASE.md) | Release checks, data and model status, licences and claims |
| [Data sources](docs/DATA_SOURCES.md) | Every data source with its terms |
| [Evidence](docs/EVIDENCE.md) | Test runs, checks and measured results |
| [Decisions](DECISIONS.md) | Architecture decision records |

## Data and licences

The code is released under the [MIT licence](LICENSE). Data keeps its own terms and is not stored in this repository:

- NASA FIRMS: we acknowledge the use of data from NASA's Fire Information for Resource Management System (FIRMS), part of NASA's Earth Science Data and Information System (ESDIS).
- © OpenStreetMap contributors, available under the Open Database Licence (ODbL).
- © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium (CC BY 4.0).
- Global Power Plant Database v1.3.0, World Resources Institute and partners (CC BY 4.0).

## Team Git_Push_Pray

- **Bittu Mandal** (team leader: product direction, system architecture, integration and release), [@ishowguts](https://github.com/ishowguts)
- **Dev Krishan** (initial prototype (Part 1) and frontend), [@sa-mael451](https://github.com/sa-mael451)
- **Chinmay Ghule** (research: NASA FIRMS data and problem analysis), [@chinmayy777](https://github.com/chinmayy777)
- **Paridhi Shethia** (demo video and documentation), [@paridhi-shethia](https://github.com/paridhi-shethia)
- **Vedant Valsange** (testing and QA), [@Vedant102dev](https://github.com/Vedant102dev)
- **Khadeeja Reem** (presentation, pitch deck and submission content), [@rreeeeem](https://github.com/rreeeeem)

Indian Institute of Information Technology, Pune · SIH 2026 · Team ID 144613
