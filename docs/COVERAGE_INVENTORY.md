# Initial source and label inventory

Checked 26 September 2026, 11:36 UTC. These are candidate sampling windows, not a representative evaluation dataset. NASA access checks are separate from application ingestion.

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

P02 should use the saved Jamnagar CSV as a genuine historical-replay integration case, preserve all source units/times, quarantine invalid rows and verify repeat ingestion. Region/date expansion must follow coverage rather than a desired class balance invented in code. Historical data and independent labels remain prerequisites for P04/P05.
