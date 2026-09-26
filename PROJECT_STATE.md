# Project state

Checkpoint: 26 September 2026 IST. Stage: **P01 foundation implemented; final repository/CI checkpoint in progress**.

Canonical workspace: the fresh `thermoscope` folder. Remote: https://github.com/ishowguts/thermoscope, created private on 26 September 2026 IST. Branch: `main`. Use the fresh repository for future work; originals remain historical references.

## Verified

- PS, submitted six-slide deck, public Part 1 source and local ThermalGuard architecture/work contract inspected.
- New build chooses the folder concept, with fresh implementation and a narrower evidence-led scope.
- Architecture v2 and one P01-P08 milestone sequence prepared.
- Eight-page readable briefing generated and visually reviewed.
- Candidate versions checked against official registries/documentation. The P01 subset is installed, frozen and tested; optional map/raster/ML dependencies remain candidates.
- GitHub connector identifies `ishowguts` and confirms push/admin access to the new private repository; old `sa-mael451/thermo-scope-part1` access is read-only.
- User is team leader and reports having SIH login access. No portal submission performed.
- User supplied Team ID **144613** and confirmed successful Earthdata login. Programmatic Earthdata/HLS authorization and download remain untested. Registered details confirmed: Git_Push_Pray, Bittu Mandal, INDIAN INSTITUTE OF INFORMATION TECHNOLOGY, PUNE.
- FIRMS MAP_KEY saved in ignored local settings and validated on 26 September 2026 at 10:36 UTC: NASA returned HTTP 200 with the expected VIIRS CSV schema. The bounded one-day Jamnagar-area query returned zero rows. This confirms access, not completed ingestion or usable model data. Programmatic Earthdata download remains untested.

- P01 API, frontend status screen, provenance migration and source/time contracts implemented. 21 unit/API tests and one real PostGIS integration scenario pass; frontend typecheck/build and fresh frozen installs pass. Browser checked with database up, down and recovered.
- Recent FIRMS inventory: 10 Jamnagar, 1 Singrauli, 2 Punjab observations; not application-ingested or classified. See `docs/COVERAGE_INVENTORY.md`.

## Current task

Current engineering task: internal record P01-FOUNDATION, status **review**, starting from `84fb66f7622a5a2c6479c6f6b26c404f6f71d752`. Read `docs/EVIDENCE.md` for checks that were actually performed.

This ledger cannot contain its own final commit hash without becoming stale. Resolve the checkpoint with `git log -1 -- PROJECT_STATE.md` and inspect `git status --short --branch`. Task handoffs record the base commit and subsequent evidence commits.

## Outstanding inputs

| Input | Needed for | Current state |
|---|---|---|
| FIRMS MAP_KEY | Live ingestion acceptance | Local credential/access check passed; application ingestion still pending |
| Earthdata login and selected archive authorization | Historical/HLS access | Login works per user; programmatic download untested |
| Team ID, registered name, current portal limits | Submission-ready deck | Registered identity confirmed; nomination and portal limits still to confirm |
| Pilot geography/date coverage | Data collection | Three small five-day windows checked; 13 real observations saved; no reviewed labels |
| Independent label reviewer(s) | Credible test set | Not arranged |
| Cloud provider, billing owner and bounded spend | Paid deployment/experiments | No resources provisioned |
| Code license and public-release scope | Public release | Undecided |

## Restart instruction

Inspect Git, run `make doctor`, and read internal record P02-FIRMS-MAP. P01 is the foundation; ingestion, map and classifier do not exist. P02 starts with the saved real Jamnagar CSV and a bounded NASA request. Preserve source hashes and distinguish historical replay from live ingestion. The parallel submission priority remains the six-slide PDF and verified portal requirements; the old PPT has not yet been edited or submitted.
