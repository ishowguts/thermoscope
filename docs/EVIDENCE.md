# Evidence ledger

This ledger records completed verification, not planned checks. Large audit downloads and page renders remain in the local review workspace; provider data and secrets are not copied into Git.

## Planning audit — 25-26 September 2026

| Check | Observed result | Scope / limitation |
|---|---|---|
| Public GitHub source inspection | Main commit `e110fd19398d69631d8bf3c77f78bf413f3a3aa5`; fixed backend events/facilities/classification | Source read through GitHub connector; not a fresh runtime test |
| Local Git/source inspection | `thermalguard-ai` at `c36e47a`, clean tracked tree and no remote | Original source preserved; ignored environment values not read |
| Submitted deck inspection | Six slides; XML text, embedded figures and Canva design reviewed | Claims/branding issues listed in AUDIT.md; deck not modified |
| Official SIH sources | Current guidelines and blank template inspected; table showed 93/500 at ~23:31 IST, 25 September | Snapshot only; no slot reservation, portal submission or recurring monitor |
| Provider/model research | NASA, AlphaEarth, Prithvi, OSM and other primary documentation inspected | No model training or genuine-data experiment performed |
| Version lookup | Candidate release metadata checked against official registries | No dependency installation/compatibility certification |
| Briefing render | `render_docx.py ... --emit_pdf` completed; eight page PNGs visually inspected | Document-layout verification, not application evidence |
| GitHub identity | Connector and creation UI identify `ishowguts` | Does not imply access to another owner's private data |
| Fresh remote repository | Creation UI and connector confirm `ishowguts/thermoscope`, private, push/admin permission | No application deployment or public release |
| Specification package check | 21 text files; 12 relative Markdown links resolve; DOCX ZIP/XML valid; no credential-pattern findings after checking empty-setting false positives | Local structural/content scan, not a full application security audit |
| Ignore rules | `git check-ignore` confirms `.env`, `.env.local`, local objects and raw data excluded | `.env.example` contains empty/example settings only |
| Final briefing revision | Eight rendered pages; pages 1-6 and 8 unchanged by image hash; revised page 7 visually reviewed | Confirms the user's available team-leader login |

## Not yet performed

Fresh application installation, backend/frontend tests, PostGIS migration tests, NASA credential acceptance, live ingest, model training/evaluation, deployed browser tests, offline application replay, cloud restore or SIH submission. Do not cite this planning ledger as proof of those capabilities.

## Record format for future checks

Include timestamp/timezone, task, source commit, environment/lock versions, exact command or interaction, exit/result, important output counts and artifact URI/hash. Record failures and blocked checks alongside passes. Remove secret-bearing request URLs before storing evidence. A model score additionally needs data/split/model manifests and per-class support.
