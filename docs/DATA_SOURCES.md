# Data and model register

No bulk dataset or trained model has been acquired for the fresh build yet. Record exact terms, version, retrieval date, checksum and redistribution decision in each source manifest before collection. This register is a planning inventory, not a blanket license grant.

| Source | Purpose | Attribution/access and guardrail |
|---|---|---|
| [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) | Thermal detections and history | Cite NASA/provider/product/collection; retain source metadata. MAP_KEY stays server-side. Separate NRT and standard revisions. |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | Industrial context | ODbL and attribution obligations apply; assess derivative database sharing separately from code. Preserve source IDs and dated extracts. |
| [OSM standard tiles](https://operations.osmfoundation.org/policies/tiles/) | Optional online basemap | Follow tile policy; no bulk prefetch/offline packs from this service. Use permitted/self-hosted assets for offline demo. |
| [ESA WorldCover](https://esa-worldcover.org/en/data-access) | Dated baseline land cover | Record release/year, applicable CC BY terms and ESA attribution before distributing an extract. Old land cover is visibly dated. |
| [Copernicus Data Space](https://documentation.dataspace.copernicus.eu/APIs/STAC.html) | Optional Sentinel-2 context | Pin collection/item IDs; inspect data and service terms; credentials depend on selected endpoint. |
| [NASA HLS](https://hls.gsfc.nasa.gov/) | Prepared multispectral imagery | Record product, collection, QA and provider citation; Earthdata authorization may be required. |
| [AlphaEarth public COGs](https://developers.google.com/earth-engine/guides/aef_on_gcs_readme) | Annual geographic embeddings | CC BY 4.0 attribution per provider; retain year/tile and availability. Preserve required attribution in exports. |
| [Dynamic World](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1) | Optional recent land cover | Record CC BY terms and source attribution; Earth Engine platform terms/access are separate. |
| [Prithvi tiny-TL](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-tiny-TL) | Optional representation model | Verify pinned revision's Apache-2.0 license/model card and dependencies; preserve notices and model hash. |
| [EOG Nightfire](https://eogdata.mines.edu/products/vnf/) | Optional flare comparison | Licensed access; do not assume redistribution rights. Core release must work without it. |
| [World Bank flaring data](https://www.worldbank.org/en/programs/gasflaringreduction/global-flaring-data) | Optional annual flare context | Verify specific downloaded dataset's terms and date; annual estimates do not label individual accidents. |
| Official incident/facility reports | Independent labels | Store citations and limited necessary evidence, with uncertainty and lawful reuse; do not republish whole copyrighted reports. |

Dataset manifests must distinguish observed data, synthetic fixtures, weak labels and independent reviewed labels. Small fixtures must not copy credentials or imply that invented coordinates identify real incidents. Public case packs require a reviewed file allowlist and source-rights check.

Application code licensing remains a team decision. It does not replace any source/model obligations.

## P02 online basemap use

MapLibre uses `https://tile.openstreetmap.org/{z}/{x}/{y}.png` with visible OpenStreetMap contributor attribution. Normal browser caching and referrer behavior are retained; no tile prefetch, offline export or proxy that hides the client is introduced. Small interactive local testing was performed. `VITE_TILE_URL` and `VITE_TILE_ATTRIBUTION` can select a permitted alternative at build time. A public deployment needs a provider/capacity decision; the OSM service has no promised SLA. The observation list works without map rendering, but the current raster basemap still needs network access.

## P03 context sources — 27 September 2026 IST

| Source | Exact use | Terms and handling |
|---|---|---|
| OpenStreetMap via Overpass API (`overpass-api.de`, fallback `maps.mail.ru` mirror) | One fixed query per pilot region (`osm-industrial-v1`), stored as immutable raw JSON with query hash, OSM base time and retrieval time | [ODbL 1.0](https://www.openstreetmap.org/copyright); attribution "© OpenStreetMap contributors" is shown beside the map and in every context response. The raw responses include OSM usernames from `out meta`; only element IDs, versions, timestamps, tags and geometry are copied into the database. Extracts stay in ignored `local/objects`; sharing a derived database publicly needs a separate ODbL share-alike review. |
| ESA WorldCover 10 m 2021 v200 (`esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/`) | Bounded windows around each observation; class fractions and small GeoTIFF chips in ignored `local/objects` | CC BY 4.0, published 28 October 2022, DOI [10.5281/zenodo.7254221](https://zenodo.org/records/7254221). Required map attribution: "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium". Legend and nodata value confirmed from the [product user manual](https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/docs/WorldCover_PUM_V2.0.pdf) (SHA-256 `4301a3d95260d88bd4315f43ccf2a12ef74ad391109b9f36e22b6e51d8490107`) and the file itself (EPSG:4326, uint8, nodata 0). |

Neither source labels a heat source. OSM tags propose what a mapped feature is; WorldCover 2021 describes surroundings five years before the pilot observations.
