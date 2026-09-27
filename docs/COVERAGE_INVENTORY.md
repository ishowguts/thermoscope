# Initial source and label inventory

Checked 26 September 2026, 11:36 UTC. These are candidate sampling windows, not a representative evaluation dataset. The original access check is separate from the completed P02 application ingestion recorded below.

## Recent thermal observations

Three bounded NASA FIRMS Area CSV requests used `VIIRS_NOAA20_NRT`, the five-day window ending on the current UTC day (22–26 September). Each returned HTTP 200 and the expected VIIRS schema; all rows fell within the requested bounds. Original CSVs and sanitized manifests are saved in ignored `local/access-checks/`. No credential or request URL is retained here.

| Candidate region | Bounds west, south, east, north | Rows | Acquisition dates observed | Initial interpretation |
|---|---|---:|---|---|
| Jamnagar | 69.5, 22, 70.5, 23 | 10 | 22–25 September | Populated sample for P02; source identities still unverified |
| Singrauli | 82, 23.5, 83, 24.5 | 1 | 22 September | Too sparse for a historical behaviour baseline |
| Punjab comparison | 74.5, 30, 75.5, 31 | 2 | 23–24 September | Geographic comparison candidate; do not assume agriculture from location |

These are observations, not 13 fires, independent events or labelled examples. No deduplication across sensors/products, independent incident matching, cloud-opportunity analysis or historical availability reconstruction has been performed. A sparse/empty window does not prove absence of thermal activity.

| Saved raw sample | SHA-256 |
|---|---|
| `jamnagar-noaa20-20260926T113602Z.csv` | `d2185a5fc74871782f4dc9feca73932f6d288d925b5f285514c425fadd73870d` |
| `singrauli-noaa20-20260926T113604Z.csv` | `581f9023051e0b81a1d9cc10ba9b867cedb493022831d7f338ef2a6e033e6a26` |
| `punjab-noaa20-20260926T113606Z.csv` | `373ed90e0550c537c2434fb6868ab64b2f03ee73888c665e6ea33de571eed989` |

## Independent evidence and gaps

| Source | Evidence available | Still needed |
|---|---|---|
| [Reliance manufacturing locations](https://www.ril.com/about/manufacturing-locations) | Official Jamnagar manufacturing-division identity/address | Dated footprint, association with a specific observed pixel, source/incident review |
| [NTPC Singrauli region](https://ntpc.co.in/about-us/corporate-functions/corporate-citizenship/ntpc-singrauli-region) | Official identity of Singrauli-region thermal power facilities | Geometric matching, dated evidence and reviewed source interpretation |
| OSM | Planned regional cache | Extract, license/attribution record, footprint completeness assessment |
| FIRMS historical archive | Earthdata web login works per user | Programmatic authorization, selected historical dates, downloaded and validated archive sample |
| HLS / land cover / AlphaEarth | Documented candidate sources | Actual pilot coverage, masks, release/availability dates and extraction checks |
| Industrial incident reports | No matched incident evidence collected yet | Dated official report, location confidence and matching satellite observation |
| Agriculture/vegetation comparison | Two recent Punjab observations only | Independent source evidence and diverse held-out sites/episodes |
| Human review | Not arranged | One domain/faculty reviewer to start; independent second review for the evaluation set |

Facility identity alone does not label a hotspot or confirm an industrial accident. OSM/rule outputs may propose weak training labels but cannot independently validate a model using those same features. No gold labels exist in this inventory.

P02 ingested all three hashed samples into the application. Jamnagar reimport inserted zero new observations; the 26 September 21:53 UTC provider fetch returned the same ten observations and created distinct live receipts. The database contains 13 unique real observations, not a training/evaluation dataset. Original collection units and unknown historical availability remain visible. Region/date expansion must follow coverage rather than a desired class balance invented in code. Historical data and independent labels remain prerequisites for P04/P05.

## P03 context inventory — 27 September 2026 IST

OSM snapshots, retrieved with the adapter's exact query text (curl POST from the bridge shell, then imported with `import-osm` and the recorded retrieval time). Raw files are in ignored `local/context-fetch/` on the owner's Mac with `.meta.json` sidecars.

| Region | Query SHA-256 | Response SHA-256 | OSM base (UTC) | Retrieved (UTC) | Elements accepted |
|---|---|---|---|---|---:|
| Jamnagar | `c2b34d81f39cd0bfd413d36d59eee02561cd34c2b03d4b217145ccef07d7123b` | `f2a94cfd47f3f2e3068afde6bf1faa1cfb632cfc1bb2d9b748d5a8303fe9c2a7` | 2026-09-26 22:38:51 | 22:41:00 | 313 of 313 |
| Singrauli | `e9a7d1b052fe1cd7d3cd9fbbc17cacc105f524d2512e2cac549eaba96653a792` | `8567c9c7366d39b978f9774e6b0b0fd9d3894647a22d7e91ba69ded28969d6ff` | 2026-09-26 22:39:54 | 22:41:14 | 208 of 208 |
| Punjab | `d70af6dcc24cafc8d95588c18c89dbfe2fa00faf17fb041c921b4a105eefaf1f` | `d2197995cbfdfa364d154b74173374529527de4260c34ae9122d53586a3caaf1` | 2026-09-26 22:39:54 | 22:41:20 | 126 of 126 |

WorldCover tiles read: N21E069 (Jamnagar), N24E081 (Singrauli), N30E072 and N30E075 (Punjab). All 13 support windows were 100% valid.

What the context says about the 13 real observations (context, not labels):

| Group | Observations | Mapped context in the pixel area | Land cover in the pixel area (2021) |
|---|---:|---|---|
| Jamnagar, Reliance refinery | 3 | Inside the mapped refinery polygon; chimneys within 170–330 m; one has a flare 750 m away | 96% built-up (two); 38% built-up / 35% shrub (one) |
| Jamnagar, around a mapped power plant at ~22.934 N, 69.698 E | 7 | 3 have a thin mapped power-plant polygon inside the circle (270–440 m); 4 have it only nearby (610–770 m) | Mixed: cropland 14–43%, built-up 15–30%, with grass, bare ground or trees |
| Singrauli | 1 | Jhingurdah Mine polygon 122 m away (inside circle) | Tree 49%, grass 32%, bare 17% |
| Punjab | 2 | No mapped industrial feature within 2 km | Cropland 99% and 71% |

The Jamnagar power-plant group mixes cropland and a mapped industrial feature at the edge of the pixel area. It is the only candidate for the P03 "adjacent industrial/agricultural hard case" and has **not** been reviewed by a person; its source remains unknown.

Events (`event-site-v1`, historical replay): Jamnagar 10 observations → 5 events at 3 recurring sites (the power-plant group splits into two events at a 25 h gap: 2 observations 22–23 September, 5 observations over 3 overpasses 24–25 September); Singrauli 1 event; Punjab 2 events at 2 sites.
