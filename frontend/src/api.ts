import type { FeatureCollection, Polygon } from "geojson";

export type DataMode = "HISTORICAL_REPLAY" | "LIVE";
export type Region = {
  id: string;
  name: string;
  bbox: string;
  start_date: string;
  end_date: string;
  total_stored: number;
};
export type Catalog = {
  regions: Region[];
  data_mode: DataMode;
  product: string;
};
export type Observation = {
  type: "Feature";
  id: string;
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: {
    acquired_at: string;
    ingested_at: string;
    first_ingested_at: string;
    source_published_at: string | null;
    first_available_at: string | null;
    availability_basis: string;
    data_mode: DataMode;
    frp_mw: number | null;
    brightness_i4_k: number | null;
    brightness_i5_k: number | null;
    scan_km: number | null;
    track_km: number | null;
    source_confidence: string | null;
    satellite: string;
    sensor: string;
    collection_version: string;
    daynight: string;
    provider: string;
    product: string;
    raw_sha256: string;
    snapshot_id: string;
    run_id: string;
    raw_row_number: number;
  };
};
export type ObservationPage = {
  type: "FeatureCollection";
  features: Observation[];
  meta: {
    data_mode: DataMode;
    product: string;
    bbox: [number, number, number, number];
    start_date: string;
    end_date: string;
    total_observations: number;
    next_offset: number | null;
    pagination_capped: boolean;
    limit: number;
    offset: number;
    latest_acquisition_at: string | null;
    latest_run: null | {
      id: string;
      status: string;
      origin: string;
      received_at: string | null;
      completed_at: string | null;
      started_at: string;
      error_code: string | null;
      total_rows: number;
      accepted_rows: number;
      inserted_rows: number;
      rejected_rows: number;
    };
  };
};

export async function readApi<T>(url: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal });
  if (!response.ok) {
    if (response.status === 422)
      throw new Error("Choose a valid date range of up to 31 days.");
    throw new Error(
      "Stored data is unavailable. Check the local API and database, then reload.",
    );
  }
  return response.json() as Promise<T>;
}

export function utc(value: string | null | undefined): string {
  if (!value) return "Not available";
  return (
    new Date(value).toLocaleString("en-GB", {
      timeZone: "UTC",
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }) + " UTC"
  );
}

export function measurement(
  value: number | null | undefined,
  unit: string,
): string {
  return value == null
    ? "Not supplied"
    : `${value.toLocaleString("en-GB", { maximumFractionDigits: 3 })} ${unit}`;
}

export function confidence(value: string | null): string {
  return (
    ({ l: "Low", n: "Nominal", h: "High" } as Record<string, string>)[
      value ?? ""
    ] ?? "Not supplied"
  );
}

export type FacilityCandidate = {
  osm_type: string;
  osm_id: number;
  osm_url: string;
  name: string | null;
  facility_type: string;
  primary_tag: string;
  geometry_kind: string;
  osm_last_edited_at: string | null;
  distance_m: number;
  contains_pixel_centre: boolean;
  support_overlap_fraction: number | null;
  relation: "INSIDE_SUPPORT" | "NEARBY";
};
export type ObservationEvent = {
  event_id: string;
  run_id: string;
  run_created_at: string;
  algorithm_version: string;
  started_at: string;
  ended_at: string;
  observation_count: number;
  overpass_count: number;
  max_frp_mw: number | null;
  ambiguous_links: number;
  site: {
    site_id: string;
    event_count: number;
    observation_count: number;
    first_seen_at: string;
    last_seen_at: string;
  };
};
export type ObservationContext = {
  observation_id: string;
  acquired_at: string;
  support_region: {
    version: string;
    radius_m: number;
    basis: "SCAN_TRACK" | "NOMINAL_VIIRS_I_BAND";
    geolocation_buffer_m: number;
    note: string;
    geometry: Polygon;
  };
  facility_snapshot: null | {
    id: string;
    region_id: string;
    osm_base_at: string;
    retrieved_at: string;
    facility_count: number;
    query_version: string;
    type_map_version: string;
    license: string;
    attribution: string;
  };
  context_timing: "RETROSPECTIVE" | "PRIOR_STATE" | null;
  association: {
    version: string;
    status:
      | "CONTEXT_NOT_COVERED"
      | "NO_MAPPED_FEATURE_NEARBY"
      | "NEARBY_ONLY"
      | "SINGLE_MAPPED_FEATURE"
      | "MULTIPLE_MAPPED_FEATURES";
    features_in_support: number;
    facility_types_in_support: string[];
    context_radius_m: number;
    candidates: FacilityCandidate[];
    candidates_truncated: boolean;
    note: string;
  };
  land_cover: LandCover | null;
  event: ObservationEvent | null;
  event_note: string;
};
export type LandCoverSummary = {
  radius_m: number;
  pixels: number;
  valid_pixels: number;
  nodata_pixels: number;
  valid_fraction: number;
  fractions: { class: string; fraction: number }[];
};
export type LandCover = {
  product: string;
  map_year: number;
  published_on: string;
  age_years_at_observation: number;
  status: "OK" | "INSUFFICIENT";
  tile_id: string;
  tile_edge_clipped: boolean;
  support: LandCoverSummary;
  context: LandCoverSummary;
  license: string;
  doi: string;
  attribution: string;
  accuracy_note: string;
  note: string;
};
export type FacilityCollection = FeatureCollection & {
  meta: {
    truncated: boolean;
    snapshots: {
      id: string;
      region_id: string;
      osm_base_at: string;
      retrieved_at: string;
      license: string;
      attribution: string;
    }[];
    note: string;
  };
};

export function distance(metres: number): string {
  return metres < 1000
    ? `${Math.round(metres)} m`
    : `${(metres / 1000).toLocaleString("en-GB", { maximumFractionDigits: 2 })} km`;
}

export function facilityType(value: string): string {
  return (
    (
      {
        REFINERY: "Refinery",
        PETROCHEMICAL: "Petrochemical",
        STEEL: "Steel",
        POWER: "Power plant",
        LNG: "LNG",
        MINE: "Mine / quarry",
        OTHER: "Other industrial",
        UNKNOWN: "Industrial, type unknown",
      } as Record<string, string>
    )[value] ?? value
  );
}

export function associationSummary(context: ObservationContext): string {
  const a = context.association;
  const nearest = a.candidates[0];
  switch (a.status) {
    case "MULTIPLE_MAPPED_FEATURES":
      return `${a.features_in_support} mapped features fall inside the approximate pixel area. Any of them could be related; none is confirmed as the source.`;
    case "SINGLE_MAPPED_FEATURE":
      return "One mapped feature falls inside the approximate pixel area. Being close to it does not prove it is the source.";
    case "NEARBY_ONLY":
      return `No mapped feature inside the pixel area. The nearest is ${distance(nearest.distance_m)} away.`;
    case "NO_MAPPED_FEATURE_NEARBY":
      return `No mapped industrial feature within ${distance(a.context_radius_m)}. That is not evidence that none exists.`;
    default:
      return "No facility snapshot covers this location yet.";
  }
}

export function landCoverClass(value: string): string {
  return (
    (
      {
        TREE_COVER: "Tree cover",
        SHRUBLAND: "Shrubland",
        GRASSLAND: "Grassland",
        CROPLAND: "Cropland",
        BUILT_UP: "Built-up",
        BARE_SPARSE_VEGETATION: "Bare / sparse vegetation",
        SNOW_ICE: "Snow and ice",
        PERMANENT_WATER: "Permanent water",
        HERBACEOUS_WETLAND: "Herbaceous wetland",
        MANGROVES: "Mangroves",
        MOSS_LICHEN: "Moss and lichen",
      } as Record<string, string>
    )[value] ?? value
  );
}

export function landCoverMix(summary: LandCoverSummary): string {
  if (!summary.fractions.length) return "No valid land-cover pixels";
  return summary.fractions
    .slice(0, 3)
    .map(
      (item) =>
        `${landCoverClass(item.class)} ${Math.round(item.fraction * 100)}%`,
    )
    .join(" · ");
}
