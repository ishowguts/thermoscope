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
