import {
  StrictMode,
  Suspense,
  lazy,
  useCallback,
  useEffect,
  useState,
} from "react";
import type { ReactNode } from "react";
import { createRoot } from "react-dom/client";
import {
  EXPORT_LIMITS,
  associationSummary,
  confidence,
  distance,
  downloadExport,
  facilityType,
  landCoverMix,
  measurement,
  readApi,
  ruleLabel,
  utc,
} from "./api";
import type {
  Assessment,
  Basis,
  Catalog,
  DataMode,
  FacilityCollection,
  Observation,
  ObservationContext,
  ObservationPage,
  ServiceStatus,
  Timeline as TimelineData,
} from "./api";
import { Rail } from "./Rail";
import { Timeline } from "./Timeline";
const MapView = lazy(() =>
  import("./MapView").then((module) => ({ default: module.MapView })),
);
const ReviewPage = lazy(() =>
  import("./Review").then((module) => ({ default: module.ReviewPage })),
);
import "./style.css";

type Query = {
  bbox: string;
  start_date: string;
  end_date: string;
  offset: number;
};

function overlap(fraction: number | null): string {
  if (fraction == null) return "";
  if (fraction > 0 && fraction < 0.01) return " · covers under 1% of it";
  return ` · covers ${Math.round(fraction * 100)}% of it`;
}

function Context({
  context,
  failed,
}: {
  context: ObservationContext | null;
  failed: boolean;
}) {
  if (failed)
    return (
      <section className="context" aria-label="Mapped context">
        <h3>Mapped context</h3>
        <p className="help">
          Context could not be loaded. The observation itself is unaffected.
        </p>
      </section>
    );
  if (!context)
    return (
      <section className="context" aria-label="Mapped context">
        <h3>Mapped context</h3>
        <p className="help">Loading mapped context…</p>
      </section>
    );
  const a = context.association;
  const snapshot = context.facility_snapshot;
  const s = context.support_region;
  const event = context.event;
  const land = context.land_cover;
  return (
    <section className="context" aria-label="Mapped context">
      <div className="context-grid">
        <div>
          <h3>Mapped facilities near this pixel</h3>
          <p className="context-status">{associationSummary(context)}</p>
          {context.context_timing === "RETROSPECTIVE" && snapshot && (
            <p className="retrospective">
              Retrospective context: this map data is from{" "}
              {utc(snapshot.osm_base_at)}, after the satellite observation.
              Facilities may have been added or changed since.
            </p>
          )}
          {a.candidates.length > 0 && (
            <ul className="candidates">
              {a.candidates.slice(0, 6).map((c) => (
                <li
                  key={`${c.osm_type}/${c.osm_id}`}
                  className={c.relation === "INSIDE_SUPPORT" ? "inside" : ""}
                >
                  <span>
                    <strong>{facilityType(c.facility_type)}</strong>
                    {c.power_source ? ` · ${c.power_source}` : ""}
                    {c.name ? ` · ${c.name}` : ""}
                  </span>
                  <span className="where">
                    {c.contains_pixel_centre
                      ? "Pixel centre inside"
                      : distance(c.distance_m)}
                  </span>
                  <small>
                    {c.relation === "INSIDE_SUPPORT"
                      ? "Inside approximate pixel area"
                      : "Nearby, outside pixel area"}
                    {overlap(c.support_overlap_fraction)} · OSM {c.primary_tag}{" "}
                    ·{" "}
                    <a href={c.osm_url} target="_blank" rel="noreferrer">
                      {c.osm_type}/{c.osm_id}
                    </a>
                  </small>
                  {!c.thermal_source_candidate && (
                    <small>
                      Retained as mapped context; not used as evidence of an
                      industrial heat source.
                    </small>
                  )}
                </li>
              ))}
            </ul>
          )}
          {a.candidates.length > 6 && (
            <p className="help">
              {a.candidates.length - 6} more mapped feature(s) within{" "}
              {distance(a.context_radius_m)}.
            </p>
          )}
          <p className="help">{a.note}</p>
        </div>
        <div>
          <h3>Approximate pixel area</h3>
          <dl>
            <dt>Radius</dt>
            <dd>
              {distance(s.radius_m)} ·{" "}
              {s.basis === "SCAN_TRACK"
                ? "from scan/track size"
                : "nominal pixel size"}{" "}
              + {distance(s.geolocation_buffer_m)} location buffer
            </dd>
            <dt>Map data</dt>
            <dd>
              {snapshot
                ? `OpenStreetMap as of ${utc(snapshot.osm_base_at)}`
                : "No snapshot for this location"}
            </dd>
            <dt>Land cover in area</dt>
            <dd>
              {land
                ? land.status === "OK"
                  ? landCoverMix(land.support)
                  : `Too few valid pixels (${Math.round(land.support.valid_fraction * 100)}% valid)`
                : "Not extracted yet"}
            </dd>
            <dt>Within 1 km</dt>
            <dd>{land ? landCoverMix(land.context) : "—"}</dd>
            <dt>Land-cover date</dt>
            <dd>
              {land
                ? `ESA WorldCover ${land.map_year} (${land.age_years_at_observation} years before this observation)`
                : "—"}
            </dd>
            <dt>Event</dt>
            <dd>
              {event
                ? `${event.observation_count} observation(s) over ${event.overpass_count} overpass(es), ${utc(event.started_at)} – ${utc(event.ended_at)}`
                : "Not grouped yet"}
            </dd>
            <dt>Recurring site</dt>
            <dd>
              {event
                ? `${event.site.event_count} event(s) here since ${utc(event.site.first_seen_at)}`
                : "—"}
            </dd>
          </dl>
          <p className="help">
            {s.note} {context.event_note}
          </p>
          {land && (
            <p className="help">
              {land.note} {land.accuracy_note}. {land.attribution} (
              {land.license}).
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

const PRIORITY_MARK: Record<string, string> = {
  HIGH: "▲",
  REVIEW: "◆",
  MEDIUM: "●",
  LOW: "▽",
};

function AssessmentPanel({
  assessment,
  timeline,
  failed,
  basis,
  onBasis,
}: {
  assessment: Assessment | null;
  timeline: TimelineData | null;
  failed: boolean;
  basis: Basis;
  onBasis: (basis: Basis) => void;
}) {
  const window90 = assessment?.features.windows["90"];
  return (
    <section className="assessment" aria-label="Rule-based assessment">
      <div className="assessment-heading">
        <div>
          <h3>Assessment</h3>
          <p className="help">
            Transparent rules with uncalibrated thresholds. Not a trained model
            and not a probability.
          </p>
        </div>
        <div className="mode-buttons" aria-label="History availability">
          <button
            aria-pressed={basis === "RETROSPECTIVE"}
            onClick={() => onBasis("RETROSPECTIVE")}
          >
            Retrospective
          </button>
          <button
            aria-pressed={basis === "OPERATIONAL"}
            onClick={() => onBasis("OPERATIONAL")}
          >
            Operational replay
          </button>
        </div>
      </div>
      <p className="help basis-note">
        {basis === "RETROSPECTIVE"
          ? "Retrospective uses everything acquired before this observation, including data this application only retrieved later."
          : "Operational replay uses only data this application had on record at the time of this observation."}
      </p>
      {failed && (
        <p className="help">
          The assessment could not be loaded. The evidence below is unaffected.
        </p>
      )}
      {!failed && !assessment && <p className="help">Loading assessment…</p>}
      {assessment && (
        <>
          <div className="axes">
            <article>
              <span className="axis-name">Likely source</span>
              <strong>
                {ruleLabel(assessment.source.label)}
                {assessment.source.subtype
                  ? ` · ${ruleLabel(assessment.source.subtype)}`
                  : ""}
              </strong>
              <ul>
                {assessment.source.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
              <small>
                {assessment.source.rule ?? assessment.source.reason_code}
              </small>
            </article>
            <article>
              <span className="axis-name">Behaviour</span>
              <strong>
                {ruleLabel(assessment.behaviour.label)}
                {assessment.behaviour.direction
                  ? ` (${assessment.behaviour.direction.toLowerCase()})`
                  : ""}
              </strong>
              <ul>
                {assessment.behaviour.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
              <small>{assessment.behaviour.rule}</small>
              <small className="safety-note">
                Recurring or persistent heat is not evidence that a site is
                safe.
              </small>
            </article>
            <article
              className={`priority priority-${assessment.priority.label.toLowerCase()}`}
            >
              <span className="axis-name">Review priority</span>
              <strong>
                <span aria-hidden="true">
                  {PRIORITY_MARK[assessment.priority.label]}
                </span>{" "}
                {ruleLabel(assessment.priority.label)}
              </strong>
              {assessment.priority.note && (
                <ul>
                  <li>{assessment.priority.note}</li>
                </ul>
              )}
              <small>
                {assessment.priority.rule} · review order, not accident
                likelihood
              </small>
            </article>
          </div>
          {window90 && (
            <p className="help history-line">
              Last 90 days within 750 m: {window90.active_days} active day(s),{" "}
              {window90.overpasses} overpass(es); {window90.covered_days} of 90
              days retrieved.
              {assessment.features.excluded_after_as_of > 0 &&
                ` ${assessment.features.excluded_after_as_of} later detection(s) ignored.`}
            </p>
          )}
          {assessment.missing_or_limited.length > 0 && (
            <ul className="limits" aria-label="Missing or limited evidence">
              {assessment.missing_or_limited.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
        </>
      )}
      {timeline && <Timeline data={timeline} />}
      {assessment && (
        <p className="help">
          {assessment.rules_version} · {assessment.feature_version} · feature
          snapshot {assessment.feature_snapshot_sha256.slice(0, 12)}…
        </p>
      )}
    </section>
  );
}

function Evidence({
  observation,
  context,
  contextFailed,
  assessment,
  mode,
  basis,
}: {
  observation: Observation | undefined;
  context: ObservationContext | null;
  contextFailed: boolean;
  assessment: ReactNode;
  mode: DataMode;
  basis: Basis;
}) {
  const [exportNote, setExportNote] = useState("");
  const [exportFailed, setExportFailed] = useState(false);
  const [exporting, setExporting] = useState(false);
  const observationId = observation?.id;
  useEffect(() => {
    setExportNote("");
    setExportFailed(false);
  }, [observationId]);
  if (!observation)
    return (
      <section className="evidence empty-selection">
        <span className="eyebrow">OBSERVATION EVIDENCE</span>
        <h2>Select a point or a row.</h2>
        <p>Inspect original measurements, timestamps and the source receipt.</p>
      </section>
    );
  const p = observation.properties;
  return (
    <section className="evidence" aria-label="Selected observation evidence">
      <div className="evidence-heading">
        <div>
          <span className="eyebrow">OBSERVATION EVIDENCE</span>
          <h2>
            {observation.geometry.coordinates[1].toFixed(5)}° N,{" "}
            {observation.geometry.coordinates[0].toFixed(5)}° E
          </h2>
        </div>
        <div className="evidence-actions">
          <span className="tag">No trained classifier · rules only</span>
          <button
            className="quiet"
            disabled={exporting}
            onClick={() => {
              setExporting(true);
              setExportFailed(false);
              downloadExport(
                `/api/v1/exports/observations/${observation.id}/evidence.geojson?${new URLSearchParams({ data_mode: mode, basis })}`,
              )
                .then((result) =>
                  setExportNote(`Saved ${result.filename} (GeoJSON, WGS84).`),
                )
                .catch((reason) => {
                  setExportFailed(true);
                  setExportNote((reason as Error).message);
                })
                .finally(() => setExporting(false));
            }}
          >
            {exporting ? "Preparing…" : "Download evidence (GeoJSON)"}
          </button>
        </div>
      </div>
      {exportNote && (
        <p
          className={`export-note ${exportFailed ? "error" : ""}`}
          role={exportFailed ? "alert" : "status"}
        >
          {exportNote}
        </p>
      )}
      <div className="evidence-grid">
        <div>
          <h3>Measurements</h3>
          <dl>
            <dt>Fire radiative power</dt>
            <dd>{measurement(p.frp_mw, "MW")}</dd>
            <dt>I4 / I5 brightness</dt>
            <dd>
              {measurement(p.brightness_i4_k, "K")} /{" "}
              {measurement(p.brightness_i5_k, "K")}
            </dd>
            <dt>Scan / track</dt>
            <dd>
              {measurement(p.scan_km, "km")} / {measurement(p.track_km, "km")}
            </dd>
            <dt>NASA confidence</dt>
            <dd>{confidence(p.source_confidence)}</dd>
            <dt>Overpass</dt>
            <dd>
              {p.daynight === "D" ? "Day" : "Night"} · {p.satellite} /{" "}
              {p.sensor}
            </dd>
          </dl>
          <p className="help">
            Brightness is not flame temperature. NASA confidence is not an AI
            class probability.
          </p>
        </div>
        <div>
          <h3>Time and provenance</h3>
          <dl>
            <dt>Satellite acquisition</dt>
            <dd>{utc(p.acquired_at)}</dd>
            <dt>Imported / received</dt>
            <dd>{utc(p.ingested_at)}</dd>
            <dt>Source publication</dt>
            <dd>Not supplied by this feed</dd>
            <dt>Availability evidence</dt>
            <dd>
              {p.first_available_at
                ? `Observed at fetch: ${utc(p.first_available_at)}`
                : "Unknown historically — retrospective replay"}
            </dd>
            <dt>Product / collection</dt>
            <dd>
              {p.product} · {p.collection_version}
            </dd>
            <dt>CSV row</dt>
            <dd>{p.raw_row_number}</dd>
          </dl>
        </div>
      </div>
      {assessment}
      <Context context={context} failed={contextFailed} />
      <details>
        <summary>Source receipt and integrity hash</summary>
        <dl className="receipt">
          <dt>Raw CSV SHA-256</dt>
          <dd>{p.raw_sha256}</dd>
          <dt>Snapshot</dt>
          <dd>{p.snapshot_id}</dd>
          <dt>Ingestion run</dt>
          <dd>{p.run_id}</dd>
          <dt>Observation identity</dt>
          <dd>{observation.id}</dd>
        </dl>
      </details>
    </section>
  );
}

const BASEMAP_KEY = "thermoscope.basemap";

function rememberBasemap(on: boolean) {
  try {
    localStorage.setItem(BASEMAP_KEY, on ? "on" : "off");
  } catch {
    /* preference not stored; the choice still applies now */
  }
}

function initialBasemap(): boolean {
  if (import.meta.env.VITE_BASEMAP === "off") return false;
  try {
    return localStorage.getItem(BASEMAP_KEY) !== "off";
  } catch {
    return true;
  }
}

function StatusStrip({ status }: { status: ServiceStatus | null }) {
  const served = status?.classifier_status?.startsWith("NOT_SERVED") ?? true;
  return (
    <section className="status-strip" aria-label="What these results are">
      <span>
        <strong>Assessments</strong>transparent rules, uncalibrated thresholds ·
        not a probability
      </span>
      <span>
        <strong>Learned model</strong>
        {served
          ? "built, not served · no reviewed labels to evaluate it"
          : status?.classifier_status}
      </span>
      <span>
        <strong>Human validation</strong>pending · deferred until reviewers are
        available
      </span>
    </section>
  );
}

function App({ status }: { status: ServiceStatus | null }) {
  const [mode, setMode] = useState<DataMode>("HISTORICAL_REPLAY");
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [regionId, setRegionId] = useState("jamnagar");
  const [query, setQuery] = useState<Query | null>(null);
  const [dates, setDates] = useState({ start: "", end: "" });
  const [page, setPage] = useState<ObservationPage | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  const [showMap, setShowMap] = useState(true);
  const [facilities, setFacilities] = useState<FacilityCollection | null>(null);
  const [context, setContext] = useState<ObservationContext | null>(null);
  const [contextFailed, setContextFailed] = useState(false);
  const [basis, setBasis] = useState<Basis>("RETROSPECTIVE");
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [timeline, setTimeline] = useState<TimelineData | null>(null);
  const [assessmentFailed, setAssessmentFailed] = useState(false);
  const [basemap, setBasemap] = useState(initialBasemap);
  const [basemapUnavailable, setBasemapUnavailable] = useState(false);
  const [withRules, setWithRules] = useState(false);
  const [exportNote, setExportNote] = useState("");
  const [exportFailed, setExportFailed] = useState(false);
  const [exporting, setExporting] = useState(false);
  const select = useCallback((id: string) => setSelectedId(id), []);
  const chooseBasemap = useCallback((on: boolean) => {
    setBasemap(on);
    if (on) setBasemapUnavailable(false);
    rememberBasemap(on);
  }, []);
  const basemapFailed = useCallback(() => {
    // Tiles could not be fetched (offline or blocked): stay map-free, and remember it so
    // later page loads make no further external requests until the user turns it back on.
    setBasemap(false);
    setBasemapUnavailable(true);
    rememberBasemap(false);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10000);
    let active = true;
    setCatalog(null);
    setPage(null);
    setQuery(null);
    setLoading(true);
    setError("");
    readApi<Catalog>(`/api/v1/catalog?data_mode=${mode}`, controller.signal)
      .then((result) => {
        if (active) setCatalog(result);
      })
      .catch((reason) => {
        if (active) {
          setError(
            reason instanceof Error ? reason.message : "Cannot load regions.",
          );
          setLoading(false);
        }
      })
      .finally(() => clearTimeout(timer));
    return () => {
      active = false;
      controller.abort();
      clearTimeout(timer);
    };
  }, [mode, reload]);

  useEffect(() => {
    const region = catalog?.regions.find((item) => item.id === regionId);
    if (!region || catalog?.data_mode !== mode) return;
    setDates({ start: region.start_date, end: region.end_date });
    setQuery({
      bbox: region.bbox,
      start_date: region.start_date,
      end_date: region.end_date,
      offset: 0,
    });
  }, [catalog, regionId, mode]);

  useEffect(() => {
    if (!query || catalog?.data_mode !== mode) return;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10000);
    let active = true;
    setLoading(true);
    setPage(null);
    setSelectedId(null);
    setError("");
    const parameters = new URLSearchParams({
      ...query,
      offset: String(query.offset),
      data_mode: mode,
      limit: "100",
    });
    readApi<ObservationPage>(
      `/api/v1/observations?${parameters}`,
      controller.signal,
    )
      .then((result) => {
        if (active) setPage(result);
      })
      .catch((reason) => {
        if (active)
          setError(
            reason instanceof Error
              ? reason.message
              : "Cannot load observations.",
          );
      })
      .finally(() => {
        clearTimeout(timer);
        if (active) setLoading(false);
      });
    return () => {
      active = false;
      controller.abort();
      clearTimeout(timer);
    };
  }, [query, mode, catalog]);

  useEffect(() => {
    if (!query) return;
    const controller = new AbortController();
    let active = true;
    setFacilities(null);
    readApi<FacilityCollection>(
      `/api/v1/map/facilities.geojson?${new URLSearchParams({ bbox: query.bbox, data_mode: mode })}`,
      controller.signal,
    )
      .then((result) => {
        if (active) setFacilities(result);
      })
      .catch(() => {
        if (active) setFacilities(null);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [query?.bbox, mode]);

  useEffect(() => {
    setContext(null);
    setContextFailed(false);
    if (!selectedId) return;
    const controller = new AbortController();
    let active = true;
    readApi<ObservationContext>(
      `/api/v1/observations/${selectedId}/context?data_mode=${mode}`,
      controller.signal,
    )
      .then((result) => {
        if (active) setContext(result);
      })
      .catch(() => {
        if (active) setContextFailed(true);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [selectedId, mode]);

  useEffect(() => {
    setAssessment(null);
    setTimeline(null);
    setAssessmentFailed(false);
    if (!selectedId) return;
    const controller = new AbortController();
    let active = true;
    const query = new URLSearchParams({ data_mode: mode, basis });
    Promise.all([
      readApi<Assessment>(
        `/api/v1/observations/${selectedId}/assessment?${query}`,
        controller.signal,
      ),
      readApi<TimelineData>(
        `/api/v1/observations/${selectedId}/timeline?${query}&days=180`,
        controller.signal,
      ),
    ])
      .then(([result, series]) => {
        if (!active) return;
        setAssessment(result);
        setTimeline(series);
      })
      .catch(() => {
        if (active) setAssessmentFailed(true);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [selectedId, mode, basis]);

  const region = catalog?.regions.find((item) => item.id === regionId);
  const latestRun = page?.meta.latest_run;
  const selected = page?.features.find((item) => item.id === selectedId);
  const total = page?.meta.total_observations ?? 0;
  const tooMany = total > EXPORT_LIMITS.observations;
  const rulesTooMany = total > EXPORT_LIMITS.withRules;

  function exportWindow(format: "csv" | "geojson") {
    if (!query) return;
    const parameters = new URLSearchParams({
      bbox: query.bbox,
      start_date: query.start_date,
      end_date: query.end_date,
      data_mode: mode,
      rule_outputs: String(withRules && !rulesTooMany),
    });
    setExporting(true);
    setExportFailed(false);
    downloadExport(`/api/v1/exports/observations.${format}?${parameters}`)
      .then((result) =>
        setExportNote(
          `Saved ${result.filename}: ${result.count} observation(s), pixel centres in WGS84 with sources and units.`,
        ),
      )
      .catch((reason) => {
        setExportFailed(true);
        setExportNote((reason as Error).message);
      })
      .finally(() => setExporting(false));
  }

  return (
    <div className="shell">
      <a
        className="skip-link"
        href="#observation-list"
        onClick={(event) => {
          event.preventDefault();
          const list = document.getElementById("observation-list");
          const first = list?.querySelector<HTMLElement>(".observation-row");
          (first ?? list)?.focus();
        }}
      >
        Skip to the observation list
      </a>
      <Rail active="observations" />
      <main>
        <header>
          <span>THERMAL INTELLIGENCE WORKBENCH</span>
          <span className="tag">Research preview</span>
        </header>
        <section className="intro">
          <div>
            <div className="eyebrow">NASA FIRMS / VIIRS NOAA-20</div>
            <h1>Satellite observations.</h1>
            <p>Inspect the measurements. Trace the evidence.</p>
          </div>
          <button
            onClick={() => setReload((value) => value + 1)}
            disabled={loading}
          >
            Reload stored data ↻
          </button>
        </section>
        <div className="mode-bar">
          <div className="mode-buttons" aria-label="Data source mode">
            <button
              aria-pressed={mode === "HISTORICAL_REPLAY"}
              onClick={() => setMode("HISTORICAL_REPLAY")}
            >
              Historical replay
            </button>
            <button
              aria-pressed={mode === "LIVE"}
              onClick={() => setMode("LIVE")}
            >
              Latest provider fetch
            </button>
          </div>
          <p>
            {mode === "HISTORICAL_REPLAY"
              ? "Saved real observations · historical availability unknown"
              : "Manually fetched NASA data · no automatic polling"}
          </p>
        </div>
        <StatusStrip status={status} />
        <form
          className="filters"
          onSubmit={(event) => {
            event.preventDefault();
            if (query)
              setQuery({
                ...query,
                start_date: dates.start,
                end_date: dates.end,
                offset: 0,
              });
          }}
        >
          <label>
            Region
            <select
              value={regionId}
              onChange={(event) => setRegionId(event.target.value)}
              disabled={!catalog}
            >
              {catalog?.regions.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              )) ?? <option value="jamnagar">Loading regions…</option>}
            </select>
          </label>
          <label>
            From · UTC
            <input
              type="date"
              value={dates.start}
              required
              onChange={(event) =>
                setDates({ ...dates, start: event.target.value })
              }
            />
          </label>
          <label>
            Through · UTC
            <input
              type="date"
              value={dates.end}
              required
              onChange={(event) =>
                setDates({ ...dates, end: event.target.value })
              }
            />
          </label>
          <button className="primary" disabled={!query || loading}>
            Apply dates
          </button>
          <span className="filter-hint">Up to 31 days</span>
        </form>
        {error && (
          <div className="notice error" role="alert">
            {error}
          </div>
        )}
        {latestRun?.status === "FAILED" && (
          <div className="notice error" role="status">
            The latest ingestion failed ({latestRun.error_code}). Previously
            stored observations remain available.
          </div>
        )}
        {latestRun?.status === "PARTIAL" && (
          <div className="notice" role="status">
            The latest import quarantined {latestRun.rejected_rows} row(s). Only
            accepted observations appear here.
          </div>
        )}
        <section className="metrics" aria-label="Observation summary">
          <div>
            <span>Observations in this window</span>
            <strong>{page?.meta.total_observations ?? "—"}</strong>
            <small>Satellite detections, not confirmed fires</small>
          </div>
          <div>
            <span>Latest acquisition</span>
            <strong className="date-metric">
              {utc(page?.meta.latest_acquisition_at)}
            </strong>
            <small>Time measured by the satellite</small>
          </div>
          <div>
            <span>
              {mode === "LIVE"
                ? "Latest fetch attempt"
                : "Latest import attempt"}
            </span>
            <strong className="date-metric">
              {utc(latestRun?.received_at ?? latestRun?.started_at)}
            </strong>
            <small>
              {latestRun?.status.toLowerCase() ?? "No run for this window"}
            </small>
          </div>
        </section>
        <section className="workspace" aria-label="Observation workbench">
          <div className="map-panel">
            <div className="panel-heading">
              <h2>{region?.name ?? "Regional"} observations</h2>
              <div className="panel-actions">
                {showMap && (
                  <button
                    className="quiet"
                    aria-pressed={basemap}
                    onClick={() => chooseBasemap(!basemap)}
                  >
                    {basemap
                      ? "Basemap on"
                      : basemapUnavailable
                        ? "Basemap unavailable · retry"
                        : "Basemap off"}
                  </button>
                )}
                <button
                  className="quiet"
                  onClick={() => setShowMap((value) => !value)}
                >
                  {showMap ? "Hide map" : "Show map"}
                </button>
              </div>
            </div>
            {loading ? (
              <div className="map-placeholder" role="status">
                Loading stored observations…
              </div>
            ) : page && showMap ? (
              <Suspense
                fallback={
                  <div className="map-placeholder">Loading map renderer…</div>
                }
              >
                <MapView
                  features={page.features}
                  bounds={page.meta.bbox}
                  selectedId={selectedId}
                  onSelect={select}
                  facilities={facilities}
                  support={
                    context?.observation_id === selectedId
                      ? context.support_region.geometry
                      : null
                  }
                  basemap={basemap}
                  onBasemapUnavailable={basemapFailed}
                />
              </Suspense>
            ) : (
              <div className="map-placeholder">
                {error
                  ? "Data could not be loaded."
                  : "Map hidden. Use the observation list to inspect every record."}
              </div>
            )}
            <div className="map-source">
              Data:{" "}
              <a
                href="https://firms.modaps.eosdis.nasa.gov/"
                target="_blank"
                rel="noreferrer"
              >
                NASA FIRMS
              </a>{" "}
              · {page?.features.length ?? 0} points on this page · Facility
              context © OpenStreetMap contributors (ODbL)
              {facilities?.meta.snapshots[0]
                ? `, as of ${utc(facilities.meta.snapshots[0].osm_base_at)}`
                : " unavailable"}{" "}
              ·{" "}
              <a
                href="https://www.openstreetmap.org/fixthemap"
                target="_blank"
                rel="noreferrer"
              >
                Report a basemap issue
              </a>
            </div>
          </div>
          <div className="list-panel">
            <div className="panel-heading">
              <h2>Observation list</h2>
              <span className="tag">UTC</span>
            </div>
            <div
              className="observations"
              id="observation-list"
              tabIndex={-1}
              aria-label="Stored observations"
            >
              {!loading && !error && page?.features.length === 0 && (
                <p className="empty-list">
                  No observations in this window. A non-detection does not prove
                  absence of fire.
                </p>
              )}
              {page?.features.map((item) => (
                <button
                  key={item.id}
                  className={`observation-row ${selectedId === item.id ? "active" : ""}`}
                  aria-pressed={selectedId === item.id}
                  onClick={() => select(item.id)}
                >
                  <span className="row-top">
                    <strong>{measurement(item.properties.frp_mw, "MW")}</strong>
                    <span>
                      {item.properties.daynight === "D" ? "Day" : "Night"}
                    </span>
                  </span>
                  <span>{utc(item.properties.acquired_at)}</span>
                  <span className="row-bottom">
                    {item.geometry.coordinates[1].toFixed(4)},{" "}
                    {item.geometry.coordinates[0].toFixed(4)}{" "}
                    <span>
                      {confidence(item.properties.source_confidence)} confidence
                    </span>
                  </span>
                </button>
              ))}
            </div>
            {page && (
              <div className="pagination">
                <button
                  disabled={page.meta.offset === 0}
                  onClick={() =>
                    query &&
                    setQuery({
                      ...query,
                      offset: Math.max(0, query.offset - 100),
                    })
                  }
                >
                  Previous
                </button>
                <span>
                  {page.features.length
                    ? `${page.meta.offset + 1}–${page.meta.offset + page.features.length}`
                    : "0"}{" "}
                  of {page.meta.total_observations}
                </span>
                <button
                  disabled={page.meta.next_offset === null}
                  onClick={() =>
                    query &&
                    page.meta.next_offset !== null &&
                    setQuery({ ...query, offset: page.meta.next_offset })
                  }
                >
                  Next
                </button>
              </div>
            )}
            {page?.meta.pagination_capped && (
              <p className="empty-list" role="status">
                Narrow the date range to inspect the remaining observations.
                This query has reached its pagination limit.
              </p>
            )}
            {page && (
              <div className="export-bar" aria-label="Export this window">
                <span>Export window</span>
                <button
                  disabled={exporting || tooMany}
                  onClick={() => exportWindow("csv")}
                >
                  CSV
                </button>
                <button
                  disabled={exporting || tooMany}
                  onClick={() => exportWindow("geojson")}
                >
                  GeoJSON
                </button>
                <label>
                  <input
                    type="checkbox"
                    checked={withRules && !rulesTooMany}
                    disabled={rulesTooMany}
                    onChange={(event) => setWithRules(event.target.checked)}
                  />
                  with rule outputs
                </label>
                <p
                  className={`export-note ${exportFailed ? "error" : ""}`}
                  role={exportFailed ? "alert" : "status"}
                >
                  {exporting
                    ? "Preparing export…"
                    : exportNote ||
                      (tooMany
                        ? `${total} observations: narrow the dates (exports are limited to ${EXPORT_LIMITS.observations}).`
                        : rulesTooMany
                          ? `Rule outputs can be added for up to ${EXPORT_LIMITS.withRules} observations.`
                          : "Pixel centres, not fire boundaries · units and sources included.")}
                </p>
              </div>
            )}
          </div>
        </section>
        <Evidence
          observation={selected}
          context={context?.observation_id === selectedId ? context : null}
          contextFailed={contextFailed}
          mode={mode}
          basis={basis}
          assessment={
            <AssessmentPanel
              assessment={
                assessment?.observation_id === selectedId ? assessment : null
              }
              timeline={
                timeline?.observation_id === selectedId ? timeline : null
              }
              failed={assessmentFailed}
              basis={basis}
              onBasis={setBasis}
            />
          }
        />
        <footer>
          <p>
            Assessments are transparent rules with uncalibrated thresholds, not
            a trained model. Mapped facilities and event grouping are context.
            No industrial-incident confirmation is available.
          </p>
          <span>ThermoScope · Git_Push_Pray</span>
        </footer>
      </main>
    </div>
  );
}

function currentPage(): "observations" | "review" {
  return window.location.hash.startsWith("#/review")
    ? "review"
    : "observations";
}

function Root() {
  const [page, setPage] = useState(currentPage);
  const [status, setStatus] = useState<ServiceStatus | null>(null);
  const reviewOnly = Boolean(status?.review_only);
  useEffect(() => {
    const update = () => setPage(currentPage());
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    readApi<ServiceStatus>("/api/v1/status", controller.signal)
      .then(setStatus)
      .catch(() => undefined);
    return () => controller.abort();
  }, []);
  // A blind-review server never shows the automated assessments.
  if (page === "observations" && !reviewOnly) return <App status={status} />;
  return (
    <div className="shell">
      <Rail active="review" reviewOnly={reviewOnly} />
      <main>
        <Suspense fallback={<p className="help">Loading review workspace…</p>}>
          <ReviewPage />
        </Suspense>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
