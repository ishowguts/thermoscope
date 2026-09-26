import { useEffect, useRef, useState } from "react";
import {
  Map,
  NavigationControl,
  ScaleControl,
  setWorkerUrl,
} from "maplibre-gl";
import type { GeoJSONSource } from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Observation } from "./api";

setWorkerUrl(workerUrl);

type Props = {
  features: Observation[];
  bounds: [number, number, number, number];
  selectedId: string | null;
  onSelect: (id: string) => void;
};

export function MapView({ features, bounds, selectedId, onSelect }: Props) {
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
        <span /> Satellite pixel centre · not a fire boundary
      </div>
    </div>
  );
}
