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

## P04 history inventory — 27 September 2026 IST

FIRMS `data_availability` at 23:11 UTC on 26 September (saved as `local/history-fetch/data-availability-20260926T231103Z.csv`, SHA-256 `cd81fe4756279eb70cfba4186cb5caaec3b2e07058f4d31cca215216cccbc530`): `VIIRS_NOAA20_NRT` 2026-07-01 to 2026-09-26; `VIIRS_NOAA20_SP` 2018-04-01 to 2026-06-30; `VIIRS_NOAA21_NRT` from 2024-01-17. The NRT and SP ranges do not overlap for NOAA-20.

History retrieved: `VIIRS_NOAA20_NRT`, 1 July–21 September 2026, 17 requests per region (16 five-day windows and one three-day window), 51 requests in total, all HTTP 200 with the expected schema, retrieved 26 September 23:11–23:13 UTC through the owner's bridge shell with the FIRMS key read from `.env` and piped to curl (never printed or passed as an argument). Each response was checked for the key before saving. Imported as historical replay: 51 runs succeeded, 232 new observations, zero rejected rows.

| Region | Stored observations (1 Jul–25 Sep) | Active days | Night / day |
|---|---:|---:|---|
| Jamnagar | 106 | 38 | 87 / 19 |
| Singrauli | 114 | 28 | 106 / 8 |
| Punjab | 25 | 14 | 3 / 22 |

July–September is monsoon season; fewer clear-sky detections are expected and non-detection is not evidence of no heat. Rebuilt events (`event-site-v1`): Jamnagar 106 → 53 events at 13 sites; Singrauli 114 → 60 events at 12 sites; Punjab 25 → 20 events at 20 sites.

The first sidecar files recorded row counts one too low (the CSVs have no trailing newline); they were corrected on the owner's Mac and now total 232, matching the database.

<details><summary>All 51 history files and hashes</summary>

| File (`local/history-fetch/`) | Records | SHA-256 |
|---|---:|---|
| `jamnagar-VIIRS_NOAA20_NRT-2026-07-01-5.csv` | 7 | `38c2819acd84ecff7ca116193f5cc113f5b190a6cf49946ed190a9193ab02188` |
| `jamnagar-VIIRS_NOAA20_NRT-2026-07-06-5.csv` | 12 | `b22c33faf98331634d3b1971c49d67a530e3baa052838cbb3ffb818ce0339d52` |
| `jamnagar-VIIRS_NOAA20_NRT-2026-07-11-5.csv` | 3 | `c3bb8a26ca37ebcc4332e472d3acec92cdd59940afa785cb9309f8948c65bd79` |
| `jamnagar-VIIRS_NOAA20_NRT-2026-07-16-5.csv` | 5 | `ff67f26dfe4d89d17c9e984b3cda09476f5036dbc77f55a3f0cfc6d7db9a0cf4` |
| `jamnagar-VIIRS_NOAA20_NRT-2026-07-21-5.csv` | 0 | `2b11a44667d05367ecf77651b95fd3d34c545c7ec154856094b91245e41ae697` |
| `jamnagar-VIIRS_NOAA20_NRT-2026-07-26-5.csv` | 0 | `2b11a44667d05367ecf77651b95fd3d34c545c7ec154856094b91245e41ae697` |
| `jamnagar-VIIRS_NOAA20_NRT-2026-07-31-5.csv` | 4 | `6b93c9d4caf9eea118a76066ab76a8cdfaba605203e87e972ebbcc3f52662c8e` |
| `jamnagar-VIIRS_NOAA20_NRT-2026-08-05-5.csv` | 7 | `229c8b9f3598c4f5ec6b4880d909e08affddba599e7ba1c09f36290241dadddc` |
| `jamnagar-VIIRS_NOAA20_NRT-2026-08-10-5.csv` | 1 | `1f26dc31ef8504d0fd6ffe1ee90a22ca1b7b19076f4764c93a830aab8a425701` |
| `jamnagar-VIIRS_NOAA20_NRT-2026-08-15-5.csv` | 0 | `2b11a44667d05367ecf77651b95fd3d34c545c7ec154856094b91245e41ae697` |
| `jamnagar-VIIRS_NOAA20_NRT-2026-08-20-5.csv` | 3 | `c43e2a1b743861ba491cb6765eb2aee3aebf6625812bda4bde8c01bee5159b93` |
| `jamnagar-VIIRS_NOAA20_NRT-2026-08-25-5.csv` | 10 | `b464e4436e9d0ab7c8ea5eff8e949cbf4b7282917aa803bfd3760afdec2121bb` |
| `jamnagar-VIIRS_NOAA20_NRT-2026-08-30-5.csv` | 2 | `b33918afd819ba440783bb0fb711c8a1e580c9429459ea0ed5178babf0bff1b5` |
| `jamnagar-VIIRS_NOAA20_NRT-2026-09-04-5.csv` | 7 | `88f227b6027e61cf107c207512241d3f583b2169715a8649b19bd2cfbaad255c` |
| `jamnagar-VIIRS_NOAA20_NRT-2026-09-09-5.csv` | 18 | `05c9b1c6712c07dba9fe064ced2acb0061bcd0b15319a1a909a6401bd8da992a` |
| `jamnagar-VIIRS_NOAA20_NRT-2026-09-14-5.csv` | 5 | `e016acbeff982b60c7564752d3d3d9477871bce3ee081e38025a506728e4a718` |
| `jamnagar-VIIRS_NOAA20_NRT-2026-09-19-3.csv` | 12 | `eba3f1da562689f47db4b98d4ce5aa0882bd07d7a5f695a098ebc4e9b90a0b5d` |
| `punjab-VIIRS_NOAA20_NRT-2026-07-01-5.csv` | 1 | `86aa052c53ae7bdc4f663107408c321d9f07499b18d1bdbab570aeaaf3496f18` |
| `punjab-VIIRS_NOAA20_NRT-2026-07-06-5.csv` | 8 | `a4a29847579a56adf84227a507ce7e03be1343025587c4b2ddb867e732217820` |
| `punjab-VIIRS_NOAA20_NRT-2026-07-11-5.csv` | 2 | `b68436233728bd03e9e85d35295bfd127046ac295a0eb1f22d0e80ae261d7503` |
| `punjab-VIIRS_NOAA20_NRT-2026-07-16-5.csv` | 1 | `9c2ad36600d1dbd8e96b8ba570178458324ad726c33fccb02a3490d7353a4e0f` |
| `punjab-VIIRS_NOAA20_NRT-2026-07-21-5.csv` | 0 | `2b11a44667d05367ecf77651b95fd3d34c545c7ec154856094b91245e41ae697` |
| `punjab-VIIRS_NOAA20_NRT-2026-07-26-5.csv` | 0 | `2b11a44667d05367ecf77651b95fd3d34c545c7ec154856094b91245e41ae697` |
| `punjab-VIIRS_NOAA20_NRT-2026-07-31-5.csv` | 0 | `2b11a44667d05367ecf77651b95fd3d34c545c7ec154856094b91245e41ae697` |
| `punjab-VIIRS_NOAA20_NRT-2026-08-05-5.csv` | 0 | `2b11a44667d05367ecf77651b95fd3d34c545c7ec154856094b91245e41ae697` |
| `punjab-VIIRS_NOAA20_NRT-2026-08-10-5.csv` | 0 | `2b11a44667d05367ecf77651b95fd3d34c545c7ec154856094b91245e41ae697` |
| `punjab-VIIRS_NOAA20_NRT-2026-08-15-5.csv` | 2 | `5b46f3069ae2d9c6a34ceee0970fd57e5fb84ab27392b556e6b05966a9521849` |
| `punjab-VIIRS_NOAA20_NRT-2026-08-20-5.csv` | 0 | `2b11a44667d05367ecf77651b95fd3d34c545c7ec154856094b91245e41ae697` |
| `punjab-VIIRS_NOAA20_NRT-2026-08-25-5.csv` | 0 | `2b11a44667d05367ecf77651b95fd3d34c545c7ec154856094b91245e41ae697` |
| `punjab-VIIRS_NOAA20_NRT-2026-08-30-5.csv` | 1 | `9754547cfa620e0767aec40393e2133f63595d8ecfec71ed705709b4694846c1` |
| `punjab-VIIRS_NOAA20_NRT-2026-09-04-5.csv` | 0 | `2b11a44667d05367ecf77651b95fd3d34c545c7ec154856094b91245e41ae697` |
| `punjab-VIIRS_NOAA20_NRT-2026-09-09-5.csv` | 4 | `fa4b55880cc781460beb7769824a7b9c6c3ec596573bf95a6173c5f00df5d8b8` |
| `punjab-VIIRS_NOAA20_NRT-2026-09-14-5.csv` | 4 | `bd40ab70f03af10f8915b52d93fa56a6286a926fe5057a4c1cd44139d2e0d4e2` |
| `punjab-VIIRS_NOAA20_NRT-2026-09-19-3.csv` | 0 | `2b11a44667d05367ecf77651b95fd3d34c545c7ec154856094b91245e41ae697` |
| `singrauli-VIIRS_NOAA20_NRT-2026-07-01-5.csv` | 8 | `7ab5b09ebe829153ddcfe03014f45fd357b2bfa8de52097e8537f9c29ef509bc` |
| `singrauli-VIIRS_NOAA20_NRT-2026-07-06-5.csv` | 2 | `8d05e1f35996ff561941b7fceab7fddd4b6d5d496615d0e54fb59054689b0cff` |
| `singrauli-VIIRS_NOAA20_NRT-2026-07-11-5.csv` | 11 | `09643f963fa8160c0520fe53d8f5788e9f4983bcfc257c7a788805f8607fd0f8` |
| `singrauli-VIIRS_NOAA20_NRT-2026-07-16-5.csv` | 0 | `2b11a44667d05367ecf77651b95fd3d34c545c7ec154856094b91245e41ae697` |
| `singrauli-VIIRS_NOAA20_NRT-2026-07-21-5.csv` | 1 | `6463a807e1a0922f9d58adcf41e7f206ea317a1f4474cab8be406e757e06d0e9` |
| `singrauli-VIIRS_NOAA20_NRT-2026-07-26-5.csv` | 9 | `7ed03b1db4b0a83da2844c6d07a42dded17c88d90623d623bb8948854439016b` |
| `singrauli-VIIRS_NOAA20_NRT-2026-07-31-5.csv` | 8 | `421e74d96ef58505e859fed2d417852a71344facbcdfc87901ff5b71237956dd` |
| `singrauli-VIIRS_NOAA20_NRT-2026-08-05-5.csv` | 17 | `8a424f0d5662364cae581edb7a0ded93e5fb4f9155b7d4de0337869d7065754f` |
| `singrauli-VIIRS_NOAA20_NRT-2026-08-10-5.csv` | 13 | `f86055c10a1a2572bb347293a1a3ce3a7a121a002c385c8cdb6c0ed910a82223` |
| `singrauli-VIIRS_NOAA20_NRT-2026-08-15-5.csv` | 0 | `2b11a44667d05367ecf77651b95fd3d34c545c7ec154856094b91245e41ae697` |
| `singrauli-VIIRS_NOAA20_NRT-2026-08-20-5.csv` | 0 | `2b11a44667d05367ecf77651b95fd3d34c545c7ec154856094b91245e41ae697` |
| `singrauli-VIIRS_NOAA20_NRT-2026-08-25-5.csv` | 0 | `2b11a44667d05367ecf77651b95fd3d34c545c7ec154856094b91245e41ae697` |
| `singrauli-VIIRS_NOAA20_NRT-2026-08-30-5.csv` | 0 | `2b11a44667d05367ecf77651b95fd3d34c545c7ec154856094b91245e41ae697` |
| `singrauli-VIIRS_NOAA20_NRT-2026-09-04-5.csv` | 2 | `794d4fcb405205dadb2200a05bd168d51890608b98416f966afc22c37312e1be` |
| `singrauli-VIIRS_NOAA20_NRT-2026-09-09-5.csv` | 13 | `dcf6a8b7aafd8fe8f2b2b062d87d523ab10c526e808db85d79119a6e36d3bcdc` |
| `singrauli-VIIRS_NOAA20_NRT-2026-09-14-5.csv` | 16 | `0c92ace2a617d15f1e29458030446ade03f09594ecadff606caeef6ca2ea53fa` |
| `singrauli-VIIRS_NOAA20_NRT-2026-09-19-3.csv` | 13 | `ee48590e4f95a5add979319959ae0eb9f4b4a3f19a63cdd734bd0856934afe74` |

51 files, 232 records.

</details>

## P05 retrieval and case set — 27 September 2026 IST

**FIRMS.** 464 bounded 5-day requests, retrieved 27 September 09:26–09:56 UTC from the owner's bridge shell (FIRMS key read inside that shell and piped to curl, never printed; each response checked for it), all HTTP 200, saved with `.meta.json` sidecars in the Mac's ignored `local/p05-fetch/raw/` and imported as historical replay: 464 runs `SUCCEEDED`, 23,746 rows accepted and inserted, 0 quarantined. Per-file names, windows, times, row counts and SHA-256 hashes: [`docs/inventory/p05-firms-files.csv`](inventory/p05-firms-files.csv) (hashes re-verified against the files before import). NOAA-20 SP covers 30 March–30 June 2026 for all 14 regions; NRT covers 1 July–25 September for the 11 new regions (the three original regions keep their P04 NRT history to 21 September, plus the P02 Jamnagar samples).

| Region | SP files / rows | NRT files / rows | Inserted | Event input | Episodes | Sites |
|---|---|---|---|---|---|---|
| haldia | 19 / 161 | 18 / 34 | 195 | 195 | 61 | 14 |
| jamnagar | 19 / 643 | P04 (1 Jul–21 Sep) | 643 | 749 | 298 | 159 |
| jharia | 19 / 3,793 | 18 / 1,086 | 4,879 | 4,879 | 1,061 | 145 |
| kgbasin | 19 / 517 | 18 / 1 | 518 | 518 | 347 | 298 |
| korba | 19 / 1,868 | 18 / 169 | 2,037 | 2,037 | 962 | 621 |
| mathura | 19 / 287 | 18 / 10 | 297 | 297 | 213 | 183 |
| mumbai | 19 / 1,399 | 18 / 77 | 1,476 | 1,476 | 817 | 605 |
| panipat | 19 / 1,653 | 18 / 55 | 1,708 | 1,708 | 1,103 | 956 |
| paradip | 19 / 124 | 18 / 3 | 127 | 127 | 93 | 78 |
| punjab | 19 / 4,375 | P04 (1 Jul–21 Sep) | 4,375 | 4,400 | 3,009 | 2,372 |
| simlipal | 19 / 16 | 18 / 0 | 16 | 16 | 14 | 13 |
| singrauli | 19 / 2,187 | P04 (1 Jul–21 Sep) | 2,187 | 2,301 | 1,161 | 759 |
| talcher | 19 / 4,119 | 18 / 620 | 4,739 | 4,739 | 946 | 428 |
| vizag | 19 / 470 | 18 / 79 | 549 | 549 | 233 | 143 |
| **Total** | 266 / 21,612 | 198 / 2,134 | **23,746** | **23,991** | **10,318** | **6,774** |

Episodes and sites are `event-site-v2` (7-day maximum episode, ADR-019), NOAA-20 SP and NRT together. Detections are not confirmed fires; a request with no rows does not prove there was no fire (cloud, overpass timing, detection limits).

**OSM.** One `osm-industrial-v1` response per new region, fetched 27 September 09:57–10:04 UTC through the bridge shell (main server; the `maps.mail.ru` mirror for Haldia and Paradip when the main server was busy), saved in `local/context-fetch/` with sidecars.

| Region | OSM base time (UTC) | Elements | Facilities | Import | Content SHA-256 |
|---|---|---|---|---|---|
| haldia | 2026-09-27 10:01 | 568 | 568 | SUCCEEDED | `76099dc7b242373c7fc5f46975791cb90bb315abb81b3b76666cbff6f9393864` |
| jharia | 2026-09-27 09:56 | 734 | 734 | SUCCEEDED | `20575b19d44f9b91cd76368fa884a10f875e8a5d2342011194d4044ee36d6224` |
| kgbasin | 2026-09-27 10:01 | 153 | 153 | SUCCEEDED | `8c9198050e504f065be1c599b2e271cab9133c19b0631912347fa3852a1686f5` |
| korba | 2026-09-27 09:56 | 159 | 159 | SUCCEEDED | `8bd89c59a79ed3c70a54df2b919fbdd2bb2f4f24cab36cc6a43064eaf9427ed4` |
| mathura | 2026-09-27 09:57 | 396 | 396 | SUCCEEDED | `6358670ad259319ef4335f5565ed70916fbffca9000d57aa6f7098d50d0ebb83` |
| mumbai | 2026-09-27 10:02 | 1,702 | 1,700 | PARTIAL: 2 unclosed area ways quarantined (way/1390642253, way/1390642260) | `c05ab80c07660010d5b96d9ae9387d294d7ba62afec883585219ccd43c5585d3` |
| panipat | 2026-09-27 09:57 | 602 | 602 | SUCCEEDED | `ebc88cf98b2af1a87a1b747d058917fca7ff116b9a3c346142b3152599c70a80` |
| paradip | 2026-09-27 09:56 | 70 | 70 | SUCCEEDED | `328b81f4b1c8a6433af020222bbbb50f3071eca529494f8e923d5ec06fbf46c3` |
| simlipal | 2026-09-27 10:01 | 8 | 8 | SUCCEEDED | `1b9705674f802ed2642daed041152e6ecf6c3a9f6d9e4122c0ecfb4b77d43b0a` |
| talcher | 2026-09-27 09:56 | 97 | 97 | SUCCEEDED | `98f04c1c17a4db62649159357b0757d28357d36945106459d5ef173d3aa6b3d1` |
| vizag | 2026-09-27 09:58 | 434 | 434 | SUCCEEDED | `8326a6bc6c0a32412119bec518eb47a589a47b6c418e71e910ab1a474edd6a2d` |

OSM coverage differs sharply by region (Simlipal 8 features, Mumbai 1,700); mapped absence is not evidence of absence.

**Registry.** WRI GPPD v1.3.0: 388 Indian thermal plants imported (see DATA_SOURCES). No case in Singrauli or Talcher lies within 1.5 km of a registered plant, so their detections get no registry corroboration.

**Case set `p05-pilot-v1`.** 10,318 cases (one per episode) in 2,462 site groups; TRAIN 6,481 / VALIDATION 2,050 / TEST 1,787 cases; manifest SHA-256 recorded in the database and in `local/objects/manifests/`. Group sizes make some regional splits uneven (Talcher VALIDATION has 5 cases because a single 215-case group carried TRAIN past its share). Land cover was summarized for every representative detection. **No reviewed labels exist yet.**

## P05 reconciliation — history eligibility and case set v2 (27 September 2026, 23:30 IST)

No new retrieval. `p05-pilot-v2` (facility-aware grouping, 2,437 groups) supersedes the frozen `p05-pilot-v1` for review and evaluation; both contain the same 10,318 episodes. Under `history-eligibility-v1` a case is usable only when at least 80 % of the 90 days before it were retrieved. Because the saved archive starts on 30 March 2026, the first eligible episode is on 10 June.

| Region | Cases | History-complete | of which TEST |
|---|---|---|---|
| haldia | 61 | 25 | 0 |
| jamnagar | 298 | 90 | 29 |
| jharia | 1,061 | 478 | 35 |
| kgbasin | 347 | 8 | 2 |
| korba | 962 | 96 | 2 |
| mathura | 213 | 23 | 1 |
| mumbai | 817 | 75 | 10 |
| panipat | 1,103 | 67 | 38 |
| paradip | 93 | 5 | 3 |
| punjab | 3,009 | 83 | 5 |
| simlipal | 14 | 0 | 0 |
| singrauli | 1,161 | 110 | 3 |
| talcher | 946 | 220 | 19 |
| vizag | 233 | 41 | 2 |
| **Total** | **10,318** | **1,321** | **149** |

Complete windows for every case need NOAA-20 SP from **30 December 2025 to 29 March 2026**: 18 bounded five-day requests per region, 252 in total (fetched on 27–28 September; see below). 663 cases lie within 2 km of their region's OSM extract boundary, so their OSM inputs are missing rather than zero.

## NOAA-20 SP history backfill (28 September 2026 IST, ADR-022)

| Item | Coverage |
|---|---|
| Product | `VIIRS_NOAA20_SP` (NASA FIRMS area API, standard processing) |
| Dates | 30 December 2025 – 29 March 2026, 18 five-day windows per region |
| Regions | All 14 pilot regions (same bounding boxes as the rest of P05) |
| Files | 252 CSVs with `.meta.json` sidecars in the Mac's ignored `local/p05-backfill/raw/`; hashes, received times and row counts in `docs/inventory/p05-backfill-files.csv` (SHA-256 `af18a0d0…1358`) |
| Retrieved | 27 September 2026 18:09–18:22 UTC (23:39–23:52 IST), HTTP 200 for every request; 13 windows returned no detections |
| Rows | 27,363 detections (Jharia 7,248, Talcher 7,052, Korba 3,709, Mumbai 3,019, Simlipal 1,557, Singrauli 1,456, Visakhapatnam 855, Paradip 832, Jamnagar 793, Haldia 411, Panipat 304, KG basin 79, Punjab 29, Mathura 19) |
| Import | 252 runs `SUCCEEDED` as historical replay, 0 quarantined rows |

The saved NOAA-20 archive now covers every day from 30 December 2025 to 26 September 2026 for every region (SP to 30 June, NRT from 1 July); the `features` guard found no missing day for `p05-pilot-v2`. History eligibility under `case-features-v4`:

| Region | Cases | History-complete | of which TEST |
|---|---|---|---|
| haldia | 61 | 61 | 2 |
| jamnagar | 298 | 294 | 59 |
| jharia | 1,061 | 1,059 | 110 |
| kgbasin | 347 | 342 | 63 |
| korba | 962 | 910 | 129 |
| mathura | 213 | 208 | 41 |
| mumbai | 817 | 781 | 151 |
| panipat | 1,103 | 1,072 | 198 |
| paradip | 93 | 90 | 18 |
| punjab | 3,009 | 2,914 | 508 |
| simlipal | 14 | 13 | 1 |
| singrauli | 1,161 | 1,140 | 223 |
| talcher | 946 | 924 | 175 |
| vizag | 233 | 227 | 40 |
| **Total** | **10,318** | **10,035** | **1,718** |

The 283 remaining cases lie within 750 m of their region's bounding box, so part of their history circle was never fetched; they stay set aside.

