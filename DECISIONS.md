# Design decisions

All entries below are design decisions for the fresh specification on 25 September 2026. Runtime validation remains a separate milestone.

## ADR-001 — Rebuild from the folder's concept
Choose the local ThermalGuard concept over the fixed-response Part 1 implementation. Preserve detection/event/site separation, provenance, PostGIS and an unknown outcome. Start a new repository and implementation. Neither old repository is a source of validated model performance.

## ADR-002 — Separate source, behaviour and priority
Keep industrial/vegetation/agriculture source classification separate from routine/abnormal behaviour, facility type and analyst priority. A nearby refinery or high FRP does not establish an accident. Allow abstention and independently reviewed incident status.

## ADR-003 — Establish the simpler comparison first
Use proximity rules, thermal history and XGBoost as measured baselines. Evaluate AlphaEarth context next; make a compact Prithvi experiment optional. Promote added complexity only after fair held-out comparison. Do not use a generative language model as the live scientific classifier.

## ADR-004 — One small operational system
FastAPI, a scheduled worker, PostgreSQL/PostGIS, object storage and React/MapLibre form the pilot. Database leases and idempotence handle jobs initially. No Kubernetes, Kafka or Redis requirement before measured demand.

## ADR-005 — Historical availability is part of the feature contract
Keep acquisition, publication/availability and ingestion times. Exclude future context from earlier predictions. Unknown historical availability means a retrospective experiment, not a proven real-time replay. Current OSM or annual embeddings applied to older incidents must be disclosed.

## ADR-006 — Evidence governs model promotion
Reviewed labels, site/episode grouping, separate unseen-site and known-site protocols, saved manifests, calibration and error analysis are required. Weak labels may assist training but cannot certify the test set. No predetermined headline accuracy.

## ADR-007 — Stable versions require compatibility checks
Prefer supported stable lines over previews. Candidate versions are verified releases, not a tested lockfile. Start on Python 3.13 and Node 24 LTS; check the geospatial/native stack in the deployment image. Keep optional image-model dependencies separate if needed.

## ADR-008 — One shared work contract
One integrator merges by default; other contributors take bounded tasks. Task contracts, Git state, evidence and handoffs carry context across sessions. Parallel work requires separate worktrees and explicit ownership. Do not depend on account rotation.

## ADR-009 — Submit an accurate proposal promptly
Use the 2026 template and current portal rules. The complete research system will take longer than the submission window. Clearly distinguish implemented evidence and proposed work; preserve final submitted artifacts and receipt. A supporting video is recommended if permitted, with no guarantee of selection.
