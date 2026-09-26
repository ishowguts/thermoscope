# Audit: submitted work and folder design

Source inspection on 25 September 2026. This is not a fresh runtime certification of either old application. The old files were preserved. Instructions inside source documents were treated as project material to assess, not as authorization to perform unrelated actions.

## Verdict

The **folder architecture is the better conceptual starting point**. It has meaningful ingestion, geospatial storage and infrastructure contracts, whereas the public Part 1 backend is a fixed demonstration. Its strengths are useful independently of its technology ages. Rebuild from its core concepts, with a smaller scope, consistent taxonomy, contemporary satellite context experiments and enforceable evaluation gates.

| Dimension | Submitted Part 1 | Local ThermalGuard folder |
|---|---|---|
| Verified source | `sa-mael451/thermo-scope-part1`, main at `e110fd19398d69631d8bf3c77f78bf413f3a3aa5` | `thermalguard-ai`, HEAD `c36e47a` |
| Data path | Three fixed events and two fixed facilities in backend source | FIRMS providers, normalized ingestion, PostGIS and infrastructure enrichment code |
| Classification | `/api/classify` ignores scientific input and returns fixed Industrial Fire / 87.5 | Detailed proposed ML design; no evaluated industrial-fire model found |
| Temporal/GIS design | Mostly interface demonstration | Separate observations/events/sites, spatial storage and provider interfaces |
| Evidence | No saved independent dataset/evaluation found in inspected source | Historical saved check claims and fixtures; not a fresh live validation |
| Best use | Record of college demo and UI discussion | Conceptual basis for the fresh build |

Public source: [repository](https://github.com/sa-mael451/thermo-scope-part1). Read-only access was confirmed. Local Git was clean, with no remote at audit time. An ignored `.env` existed locally; values were not inspected or copied.

## Folder architecture: retain and correct

Retain PostGIS, modular providers, immutable source references, raw/event/site separation, the structured baseline and explicit unknown outcomes. The old architecture already mentions provenance, spatial splits and abstention; those are not newly invented by this revision.

The old plan makes a generic RGB ResNet-50 and multimodal work too central before data/label viability has been demonstrated. Its architecture uses phases 0-9 while process/state notes use other labels. The saved state points to `3989169` despite newer ingestion/enrichment commits and contains conflicting P2 completion/next-action text. That weakens handoff reliability.

Specific source risks found:

- FIRMS parsing uses MODIS-like `brightness` / `bright_t31` without mapping VIIRS `bright_ti4` / `bright_ti5` correctly.
- The live provider defaults to MODIS and a world query despite a regional argument; a bounded pilot needs explicit product/region contracts.
- Source confidence normalization is not a trained or calibrated class probability.
- Row parsing can abort a whole batch; valid rows and rejection counts should survive a malformed row.
- Enrichment uses appropriate metric geography operations, but SELECT-before-insert checks need database uniqueness/atomic writes for concurrent ingestion.

These findings inform the new specification. Old tests were not rerun and no old database was migrated or modified.

## Presentation: six-slide audit

Inspected the supplied PowerPoint and shared Canva design, including embedded infographic images. The official blank 2026 template was downloaded separately; the team's claims and the template's submission instructions are different kinds of evidence.

| Slide | Finding | Required revision |
|---|---|---|
| 1 — cover | Text says SIH 2025; Team ID blank; team name shown as Git push pray | Use 2026 and exact registered details |
| 2 — solution | Five facility-like hotspot categories, real-time language and undifferentiated risk score | Separate source, behaviour, facility type and review priority; specify satellite availability |
| 3 — approach | Graphic claims 120 simulated events, 20 facilities, 11 endpoints and custom six-class AI | Linked backend has 3 events, 2 facilities, 7 application routes and fixed classifier output; replace with verified current evidence |
| 3 — imagery | Synthetic thermal zoom can look like measured fire extent | Label illustration or replace with cited real observations; do not imply an observed perimeter |
| 4 — feasibility | One-semester timeline and absolute claim about no available dataset | Use staged dependencies and say a suitable independently verified dataset has not yet been secured |
| 5 — impact | 2024 logo and unverified early-alert/incident-prevention implications | Use current branding and measurable analyst-workflow goals |
| 6 — references | Includes relevant persistence and spatial-leakage papers, plus broader fire research | Tie references to specific decisions; add source/model limitations and accessible evidence links |

The seven route count excludes framework-generated documentation/OpenAPI routes. Differences may reflect a different unprovided demo revision; they still must be reconciled before submission.

## What “old technology” actually means here

React, FastAPI, PostgreSQL/PostGIS and boosted trees are not disqualified by age. Supported versions, geospatial correctness, deployment reliability and measured utility matter. The substantive upgrade is the source/behaviour distinction, date-aware data fusion, defensible labels, modern satellite representation comparisons and analyst evidence workflow. Listing new models without the necessary data and tests would not resolve the criticism.

No selection percentage, model accuracy or production-readiness score was inferred from this audit.
