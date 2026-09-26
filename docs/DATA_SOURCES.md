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
