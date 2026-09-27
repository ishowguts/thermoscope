import { useEffect, useRef, useState } from "react";
import {
  Map,
  NavigationControl,
  ScaleControl,
  setWorkerUrl,
} from "maplibre-gl";
import type { GeoJSONSource } from "maplibre-gl";
import type { FeatureCollection, Polygon } from "geojson";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import "maplibre-gl/dist/maplibre-gl.css";
import type { FacilityCollection, Observation } from "./api";

setWorkerUrl(workerUrl);

type Props = {
  features: Observation[];
  bounds: [number, number, number, number];
  selectedId: string | null;
  onSelect: (id: string) => void;
  facilities: FacilityCollection | null;
  support: Polygon | null;
};

const EMPTY: FeatureCollection = {
  type: "FeatureCollection",
  features: [],
};

export function MapView({
  features,
  bounds,
  selectedId,
  onSelect,
  facilities,
  support,
}: Props) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<Map | null>(null);
  const select = useRef(onSelect);
  select.current = onSelect;
  const [ready, setReady] = useState(false);
  const [unavailable, setUnavailable] = useState(false);
  const [tileError, setTileError] = useState(false);

  useEffect(() => {
    if (!container.current) return;
    let instance: Map | null = null;
    try {
      instance = new Map({
        container: container.current,
        bounds: [
          [bounds[0], bounds[1]],
          [bounds[2], bounds[3]],
        ],
        fitBoundsOptions: { padding: 45, maxZoom: 11 },
        maxZoom: 15,
        minZoom: 3,
        renderWorldCopies: false,
        style: {
          version: 8,
          sources: {
            osm: {
              type: "raster",
              tileSize: 256,
              tiles: [
                import.meta.env.VITE_TILE_URL ??
                  "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
              ],
              attribution:
                import.meta.env.VITE_TILE_ATTRIBUTION ??
                '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
              maxzoom: 19,
            },
            observations: {
              type: "geojson",
              data: { type: "FeatureCollection", features: [] },
            },
            facilities: { type: "geojson", data: EMPTY },
            support: { type: "geojson", data: EMPTY },
          },
          layers: [
            {
              id: "background",
              type: "background",
              paint: { "background-color": "#e4eae3" },
            },
            {
              id: "basemap",
              type: "raster",
              source: "osm",
              paint: { "raster-saturation": -0.45, "raster-opacity": 0.86 },
            },
            {
              id: "facility-areas",
              type: "fill",
              source: "facilities",
              filter: ["!=", ["geometry-type"], "Point"],
              paint: { "fill-color": "#5b4b8a", "fill-opacity": 0.16 },
            },
            {
              id: "facility-outlines",
              type: "line",
              source: "facilities",
              filter: ["!=", ["geometry-type"], "Point"],
              paint: { "line-color": "#5b4b8a", "line-width": 1.2 },
            },
            {
              id: "facility-points",
              type: "circle",
              source: "facilities",
              filter: ["==", ["geometry-type"], "Point"],
              paint: {
                "circle-radius": 3,
                "circle-color": "#5b4b8a",
                "circle-stroke-color": "#fff",
                "circle-stroke-width": 1,
              },
            },
            {
              id: "support-fill",
              type: "fill",
              source: "support",
              paint: { "fill-color": "#143e39", "fill-opacity": 0.08 },
            },
            {
              id: "support-line",
              type: "line",
              source: "support",
              paint: {
                "line-color": "#143e39",
                "line-width": 2,
                "line-dasharray": [2, 2],
              },
            },
            {
              id: "observations",
              type: "circle",
              source: "observations",
              paint: {
                "circle-radius": 7,
                "circle-color": "#d75623",
                "circle-stroke-width": 2,
                "circle-stroke-color": "#fff",
                "circle-opacity": 0.9,
              },
            },
            {
              id: "selected",
              type: "circle",
              source: "observations",
              filter: ["==", ["get", "observation_id"], ""],
              paint: {
                "circle-radius": 12,
                "circle-color": "transparent",
                "circle-stroke-color": "#143e39",
                "circle-stroke-width": 3,
              },
            },
          ],
        },
        attributionControl: { compact: false },
      });
      map.current = instance;
      instance.addControl(
        new NavigationControl({ showCompass: false }),
        "top-right",
      );
      instance.addControl(new ScaleControl({ unit: "metric" }), "bottom-left");
      instance.on("load", () => setReady(true));
      instance.on("error", () => setTileError(true));
      instance.on("webglcontextlost", () => setUnavailable(true));
      instance.on("click", "observations", (event) => {
        const id = event.features?.[0]?.properties?.observation_id;
        if (id !== undefined) select.current(String(id));
      });
      instance.on("mouseenter", "observations", () => {
        if (instance) instance.getCanvas().style.cursor = "pointer";
      });
      instance.on("mouseleave", "observations", () => {
        if (instance) instance.getCanvas().style.cursor = "";
      });
    } catch {
      setUnavailable(true);
    }
    return () => {
      instance?.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    if (!ready || !map.current) return;
    (map.current.getSource("observations") as GeoJSONSource).setData({
      type: "FeatureCollection",
      features: features.map((feature) => ({
        ...feature,
        properties: { ...feature.properties, observation_id: feature.id },
      })),
    });
    map.current.fitBounds(
      [
        [bounds[0], bounds[1]],
        [bounds[2], bounds[3]],
      ],
      {
        padding: 45,
        duration: 0,
        maxZoom: 11,
      },
    );
  }, [ready, features, bounds]);

  useEffect(() => {
    if (!ready || !map.current) return;
    (map.current.getSource("facilities") as GeoJSONSource).setData(
      facilities ?? EMPTY,
    );
  }, [ready, facilities]);

  useEffect(() => {
    if (!ready || !map.current) return;
    (map.current.getSource("support") as GeoJSONSource).setData(
      support
        ? {
            type: "FeatureCollection",
            features: [{ type: "Feature", geometry: support, properties: {} }],
          }
        : EMPTY,
    );
    if (support) {
      const ring = support.coordinates[0];
      const lons = ring.map((point) => point[0]);
      const lats = ring.map((point) => point[1]);
      // Zoom to the selected pixel area so its facilities can be inspected.
      map.current.fitBounds(
        [
          [Math.min(...lons), Math.min(...lats)],
          [Math.max(...lons), Math.max(...lats)],
        ],
        { padding: 70, maxZoom: 14, duration: 400 },
      );
    }
  }, [ready, support]);

  useEffect(() => {
    if (ready)
      map.current?.setFilter("selected", [
        "==",
        ["get", "observation_id"],
        selectedId ?? "",
      ]);
  }, [ready, selectedId]);

  return (
    <div className="map-shell">
      <div
        ref={container}
        className="map-canvas"
        aria-label="Thermal observation map"
      />
      {unavailable && (
        <div className="map-fallback" role="status">
          <strong>Map rendering is unavailable.</strong>
          <p>Use the observation list to inspect every record.</p>
        </div>
      )}
      {tileError && !unavailable && (
        <div className="map-notice" role="status">
          Some map resources could not load. The observation list remains
          available.
        </div>
      )}
      {!ready && !unavailable && <div className="map-notice">Loading map…</div>}
      <div className="map-legend">
        <div>
          <span /> Satellite pixel centre · not a fire boundary
        </div>
        <div>
          <i className="legend-support" /> Approximate pixel area (selected)
        </div>
        <div>
          <i className="legend-facility" /> Mapped OSM industrial feature · not
          a confirmed source
        </div>
      </div>
    </div>
  );
}
