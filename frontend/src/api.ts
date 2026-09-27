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

/** Thrown when the personal reviewer token is missing, wrong, rotated or deactivated. */
export class SignInRequired extends Error {}

/** Reads a reviewer-only endpoint with the signed-in reviewer's personal token. */
export async function readAsReviewer<T>(
  url: string,
  token: string,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(url, {
    signal,
    headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 401)
    throw new SignInRequired("Your reviewer sign-in was not accepted.");
  if (!response.ok)
    throw new Error(
      "Stored data is unavailable. Check the local API and database, then reload.",
    );
  return response.json() as Promise<T>;
}

export type Reviewer = { name: string; can_adjudicate: boolean };

/** Thrown when the case changed after it was opened (someone else saved first). */
export class CaseChanged extends Error {}

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
  power_source: string | null;
  thermal_source_candidate: boolean;
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

export type Basis = "RETROSPECTIVE" | "OPERATIONAL";
export type RuleOutcome = {
  label: string;
  rule?: string;
  subtype?: string;
  reason_code?: string;
  direction?: "HIGHER" | "LOWER" | null;
  heuristic_support?: number;
  reasons: string[];
};
export type WindowFeatures = {
  days: number;
  covered_days: number;
  coverage_fraction: number;
  detections: number;
  overpasses: number;
  active_days: number;
  days_since_last_detection: number | null;
};
export type Assessment = {
  observation_id: string;
  as_of: string;
  basis: Basis;
  rules_version: string;
  feature_version: string;
  not_a_model: string;
  source: RuleOutcome;
  behaviour: RuleOutcome;
  priority: { label: string; rule: string; note: string | null };
  features: {
    windows: Record<string, WindowFeatures>;
    excluded_after_as_of: number;
    excluded_unknown_availability: number;
  };
  thresholds: Record<string, string | number>;
  missing_or_limited: string[];
  feature_snapshot_sha256: string;
};
export type TimelinePass = {
  acquired_at: string;
  satellite: string;
  daynight: "D" | "N";
  group: string;
  detections: number;
  max_frp_mw: number | null;
};
export type Timeline = {
  observation_id: string;
  as_of: string;
  basis: Basis;
  radius_m: number;
  episode_start: string;
  overpasses: TimelinePass[];
  days: {
    date: string;
    retrieved: boolean;
    detections: number;
    max_frp_mw: number | null;
  }[];
  note: string;
};

const LABELS: Record<string, string> = {
  INDUSTRIAL: "Industrial (heuristic)",
  AGRICULTURAL_BURN: "Agricultural burning (heuristic)",
  VEGETATION_FIRE: "Vegetation fire (heuristic)",
  OTHER: "Other",
  UNKNOWN: "Unknown — not enough consistent evidence",
  GAS_FLARE: "gas flare",
  MINING_HEAT: "mining heat",
  OTHER_PERSISTENT_HEAT: "persistent heat",
  UNRESOLVED: "type unresolved",
  RECURRENT_WITHIN_BASELINE: "Within its observed record",
  ABNORMAL_RELATIVE_TO_BASELINE: "Unusual compared with its record",
  NEW_OR_TRANSIENT: "New or transient here",
  INSUFFICIENT_HISTORY: "Not enough comparable history",
  HIGH: "High",
  REVIEW: "Needs review",
  MEDIUM: "Medium",
  LOW: "Low",
};

export function ruleLabel(value: string | undefined | null): string {
  return value ? (LABELS[value] ?? value) : "";
}

export type CaseSet = {
  id: string;
  name: string;
  data_mode: DataMode;
  case_count: number;
  manifest_sha256: string;
  created_at: string;
  reviews: number;
  grouping: string;
  superseded_by: string | null;
};
export type QueueItem = {
  case_id: string;
  split: "TRAIN" | "VALIDATION" | "TEST";
  region_id: string;
  as_of: string;
  reviews: number;
  needs: number;
  history_complete: boolean;
  role: "REVIEWER" | "ADJUDICATOR";
};
export type ReviewQueue = {
  case_set_id: string;
  reviewer: string;
  can_adjudicate: boolean;
  superseded_by: string | null;
  queue_order: string;
  adjudication: QueueItem[];
  review: QueueItem[];
  your_reviews: number;
  remaining_reviews: number;
  /** Shown to adjudicators only. */
  remaining_adjudications: number | null;
};
export type EarlierReview = {
  role: string;
  source_label: string;
  industrial_subtype: string | null;
  certainty: string;
  evidence: {
    items?: {
      url: string;
      kind: string;
      observed_on: string | null;
      independent: boolean;
    }[];
  };
  evidence_date: string | null;
  notes: string | null;
  reviewed_at: string;
};
export type RegistryRecord = {
  source: string;
  record_id: string;
  name: string | null;
  category: string;
  fuel: string | null;
  capacity_mw: number | null;
  distance_m: number;
  attribution: string;
};
export type ReviewCase = {
  case_id: string;
  case_set_id: string;
  split: string;
  region_id: string;
  review_slots: number;
  as_of: string;
  started_at: string;
  location: { longitude: number; latitude: number; support_radius_m: number };
  observations: {
    id: string;
    acquired_at: string;
    lon: number;
    lat: number;
    frp_mw: number | null;
    daynight: string;
    confidence: string | null;
    product: string;
  }[];
  mapped_features: FacilityCandidate[];
  osm_snapshot: { osm_base_at: string; attribution: string } | null;
  registry_records_within_5km: RegistryRecord[];
  land_cover: LandCover | null;
  links: { label: string; url: string }[];
  blind: boolean;
  reviews_recorded: number;
  reviewed_by_you: boolean;
  your_role: "REVIEWER" | "ADJUDICATOR";
  adjudication: { needed: boolean; earlier_reviews: EarlierReview[] } | null;
  guidance: string;
  evidence_policy: {
    version: string;
    kinds: string[];
    independent_kinds: string[];
    imagery_window_days: { before: number; after: number };
    gold_needs: string;
    source_locations: string[];
  };
  labels: string[];
  subtypes: string[];
};
export type LabelSummary = {
  case_set: { id: string; name: string; case_count: number };
  label_policy: string;
  gold_test_labels: Record<string, number>;
  double_reviewed_cases: number;
  binary_agreement_kappa: number | null;
  kappa_pairs: number;
  pending_adjudication: number;
  reviews_total: number;
};

export const SOURCE_LABEL_TEXT: Record<string, string> = {
  INDUSTRIAL: "Industrial heat source",
  VEGETATION_FIRE: "Vegetation or forest fire",
  AGRICULTURAL_BURN: "Agricultural burning",
  OTHER: "Other, not industrial",
  UNRESOLVED: "Cannot decide from the evidence",
};
export const SUBTYPE_TEXT: Record<string, string> = {
  GAS_FLARE: "Gas flare",
  MINING_HEAT: "Mining or coal-seam heat",
  OTHER_PERSISTENT_HEAT: "Plant, furnace or kiln heat",
  UNRESOLVED: "Industrial, type unclear",
};

export async function postReview(
  caseSet: string,
  token: string,
  body: Record<string, unknown>,
): Promise<{ review_id: string; role: string; review_tier: string }> {
  const response = await fetch(
    `/api/v1/annotation/${encodeURIComponent(caseSet)}/reviews`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    },
  );
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401)
      throw new SignInRequired("Your reviewer sign-in was not accepted.");
    if (response.status === 409 && payload.code === "CASE_CHANGED")
      throw new CaseChanged(payload.message);
    if (response.status === 422 && payload.code === "INVALID_QUERY")
      throw new Error(
        "Check the links, types, dates and notes, then try again.",
      );
    throw new Error(
      payload.message ?? "The review could not be saved. Try again.",
    );
  }
  return payload;
}
