# Research and technology decisions

Primary sources checked 25 September 2026. Recommendations below are project judgments, not claims that any model has already been tested in ThermoScope. Provider terms and release compatibility must be rechecked at implementation.

## Decisions that affect the build

| Candidate | Decision | Evidence and limitation |
|---|---|---|
| FIRMS VIIRS / MODIS | Core observations | Global near-real-time delivery is generally within about three hours of overpass, not ignition. Preserve sensor schema and source confidence. [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) |
| NASA standard-product source types | Retain and benchmark where available | Broad vegetation/volcano/static/offshore types exist in standard-quality data; the field is not part of the same NRT contract. It does not establish an industrial accident. [VIIRS fields](https://modaps.modaps.eosdis.nasa.gov/services/about/products/viirs-land-c2-nrt/vj114imgtdl_nrt.html) |
| XGBoost plus history/context | First learned baseline | Suitable candidate for structured features and limited labels; actual performance is unknown. Must beat simpler rules on held-out cases. [XGBoost documentation](https://xgboost.readthedocs.io/en/stable/) |
| AlphaEarth annual embeddings | First modern context experiment | Public annual COGs, 64-dimensional context at 10 m; valid year, release availability and correct quantization matter. Not a live thermal sensor. [Catalogue](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL) |
| Prithvi-EO-2.0 tiny-TL | Optional compact imagery experiment | Satellite-pretrained representation candidate, not an industrial-fire classifier. Freeze model revision and use correct multispectral preprocessing. [Model card](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-tiny-TL) |
| Generic RGB ResNet-50 | Remove as mandatory component | RGB screenshots discard multispectral/context information. An RGB baseline can be tested if useful, but is not a prerequisite for a working system. |
| Dynamic World | Optional recent land-cover context | Dated 10 m class probabilities; cloud/missingness and Earth Engine access remain relevant. [Official catalogue](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1) |
| VIIRS Nightfire | Optional comparison/corroboration | Existing flare product; access is licensed from January 2025. Do not assume free commercial/academic redistribution. [EOG product](https://eogdata.mines.edu/products/vnf/) |
| Generative LLM in inference | Exclude from core | No demonstrated advantage for calibrated sensor classification; cost and unverifiable explanations would add dependencies. Coding/review assistance is a separate use. |
| Very large/multimodal foundation model | Defer | Limited labels and deadline favour a measurable compact experiment. This is a scope decision, not a claim that larger models are ineffective. |

## Source details that must become tests

**FIRMS:** nominal VIIRS resolution is not an exact incident perimeter. Preserve scan/track support, kelvin brightness temperatures and MW fire radiative power. Area API currently documents 1-5 days per request; check product availability and use appropriate archive access for long backfills. The key is embedded in URLs and must be redacted. [Area API](https://firms.modaps.eosdis.nasa.gov/api/area/)

**AlphaEarth:** the public COG guide now lists 2017-2025. It describes signed int8 storage, `-128` nodata, and inverse quantization `sign(x) * (x / 127.5)^2`; aggregate valid vectors and normalize as documented. The provider's public access arrangement changed in July 2026. Use completed, available context years only and retain tile/version/attribution. An old event reanalysed with a newly released representation is a retrospective experiment. [COG guide](https://developers.google.com/earth-engine/guides/aef_on_gcs_readme)

**Prithvi:** the compact tiny candidate has approximately 5M parameters. The family uses six prepared HLS bands (blue, green, red, narrow NIR, SWIR1, SWIR2) and temporal/location information. Confirm the tiny checkpoint's exact configuration rather than transferring assumptions from another size. Correct reflectance scaling, masks and available acquisition dates are part of the model. Location information warrants a geographic-leakage ablation. Published pretrained benchmarks do not transfer to this task. [Family card](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-300M-TL), [IBM compact-model announcement](https://research.ibm.com/blog/terramind-prithvi-tiny-small-models-geospatial)

**Imagery:** use a provider adapter and recorded STAC items rather than hardcoded URLs. Sentinel-2 optical/SWIR imagery supplies context; it does not have a thermal infrared band. Cloud tests must cover the actual patch, not only a whole-scene percentage. [Copernicus STAC](https://documentation.dataspace.copernicus.eu/APIs/STAC.html)

## Existing work and the novelty boundary

FIRMS already supplies mapping and alerts. Nightfire and published persistent-hotspot work already address recurring thermal sources. The proposed contribution is a tested combination of Indian industrial context, site history, uncertainty and evidence-led review, with comparisons against simpler existing approaches. Do not call it the first AI fire map or the first system to classify heat.

The team's persistent-source reference, [Caseiro et al. (2018)](https://doi.org/10.3390/rs10071118), is directly relevant to separating recurring thermal activity. The 2026 [spatial-leakage study](https://doi.org/10.3390/geohazards7030090) supports caution about geographic shortcuts; it motivates grouping and held-out regions, not a transferable performance number for this project.

The team's broader CNN forest-fire and YOLO references concern different data/tasks. Retain them only when the slide explains a relevant methodological connection; they cannot validate ThermoScope's satellite-based industrial classification.

## Work organisation

The proposed roles are an engineering workflow, not a benchmark ranking: one integrator, optional independent review and bounded UI work. Repository checkpoints carry context between contributors.

## Official submission sources

- [SIH 2026 guidelines](https://sih.gov.in/letters/2026/SIH%202026%20Guidelines.pdf), especially PDF pages 16-20.
- [Live problem-statement table](https://www.sih.gov.in/sih2026PS): SIH26162 showed 93/500 at approximately 23:31 IST on 25 September 2026. This is a timestamped observation, not a reserved slot or continuing monitor.
- [Official presentation template](https://sih.gov.in/letters/2026/SIH2026-IDEA-Presentation-Format.pptx).

The official sources resolve the current deadline, cap and format; anecdotal Reddit/Quora advice is not needed to override them. Actual portal file-size/link/editing constraints still require the team leader's signed-in review.
