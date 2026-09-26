import {
  StrictMode,
  Suspense,
  lazy,
  useCallback,
  useEffect,
  useState,
} from "react";
import { createRoot } from "react-dom/client";
import { confidence, measurement, readApi, utc } from "./api";
import type { Catalog, DataMode, Observation, ObservationPage } from "./api";
const MapView = lazy(() =>
  import("./MapView").then((module) => ({ default: module.MapView })),
);
import "./style.css";

type Query = {
  bbox: string;
  start_date: string;
  end_date: string;
  offset: number;
};

function Evidence({ observation }: { observation: Observation | undefined }) {
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
        <span className="tag">Unclassified observation</span>
      </div>
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

function App() {
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
  const select = useCallback((id: string) => setSelectedId(id), []);

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

  const region = catalog?.regions.find((item) => item.id === regionId);
  const latestRun = page?.meta.latest_run;
  const selected = page?.features.find((item) => item.id === selectedId);

  return (
    <div className="shell">
      <aside className="rail" aria-label="Project identity">
        <a className="brand" href="/" aria-label="ThermoScope home">
          <span className="mark">T</span> ThermoScope
        </a>
        <div className="rail-section">WORKSPACE</div>
        <div className="selected">
          ◉ <span>Observations</span>
        </div>
        <p className="rail-note">
          A traceable view of
          <br />
          satellite-detected heat.
        </p>
        <div className="rail-bottom">
          <span className="dot" /> Regional pilot
          <small>Git_Push_Pray · SIH 2026</small>
        </div>
      </aside>
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
              <button
                className="quiet"
                onClick={() => setShowMap((value) => !value)}
              >
                {showMap ? "Hide map" : "Show map"}
              </button>
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
              · {page?.features.length ?? 0} points on this page ·{" "}
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
            <div className="observations" aria-label="Stored observations">
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
          </div>
        </section>
        <Evidence observation={selected} />
        <footer>
          <p>
            Observations are unclassified. No trained model or
            industrial-incident confirmation is available.
          </p>
          <span>ThermoScope · Git_Push_Pray</span>
        </footer>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
