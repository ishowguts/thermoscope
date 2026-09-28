"""Offline demo packages (P07-SUB-001, `demo-package-v1`).

A demo package is a small, permitted subset of the saved real inputs: every NASA FIRMS file the
database recorded for a few regions (read back from the content-addressed object store, with the
provider retrieval time where a sidecar was retained), the OpenStreetMap extract for those
regions, and the ESA WorldCover chips and summaries already extracted for the observations the
workbench lists. It is built from what this project retained (never refetched), carries every
file's SHA-256, source, licence and attribution, and loads into an empty database with no network
access, so a demo can be replayed on another machine or with the network off.

Loading reuses the normal importers (historical replay mode, hash-checked), restores land-cover
summaries only after recomputing them from the packaged chip and matching the recorded values,
and rebuilds events. It does not touch labels, case sets, features, reviewer accounts or models,
and it is safe to repeat (stored rows are reused).
"""

import hashlib
import json
import re
import shutil
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import text

from thermoscope.config import DataMode, Settings
from thermoscope.context import support_radius_m
from thermoscope.context_ingestion import ingest_osm
from thermoscope.database import batch_engine
from thermoscope.events import build_event_run
from thermoscope.firms import IngestError
from thermoscope.ingestion import ingest
from thermoscope.landcover import (
    ATTRIBUTION as WORLDCOVER_ATTRIBUTION,
)
from thermoscope.landcover import (
    CONTEXT_RADIUS_M,
    DOI,
    PRODUCT,
    SUMMARY_VERSION,
    summarize_array,
)
from thermoscope.landcover import (
    LICENSE as WORLDCOVER_LICENSE,
)
from thermoscope.object_store import ObjectStore
from thermoscope.regions import NOAA20_PRODUCTS, REGIONS, Bounds, Product, Window

PACKAGE_VERSION = "demo-package-v1"
MAX_PACKAGE_BYTES = 50_000_000  # a demo subset, not a mirror
KEY_BEARING = re.compile(rb"firms\.modaps\.eosdis\.nasa\.gov/api/", re.IGNORECASE)
SOURCES = {
    "NASA_FIRMS": {
        "license": "NASA open data (no restriction on reuse); cite the source",
        "attribution": "We acknowledge the use of data from NASA's Fire Information for Resource "
        "Management System (FIRMS), part of NASA's Earth Science Data and Information System "
        "(ESDIS). https://firms.modaps.eosdis.nasa.gov/",
    },
    "OPENSTREETMAP": {
        "license": "ODbL-1.0",
        "attribution": "© OpenStreetMap contributors, available under the Open Database "
        "Licence (https://www.openstreetmap.org/copyright). Derived databases must stay ODbL.",
    },
    "ESA_WORLDCOVER": {
        "license": WORLDCOVER_LICENSE,
        "attribution": WORLDCOVER_ATTRIBUTION + f" (doi:{DOI})",
    },
}
FIXED_FILES = {"manifest.json", "README.txt"}


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def region_box(region_id: str) -> Bounds:
    for region in REGIONS:
        if region["id"] == region_id:
            return Bounds.parse(region["bbox"])
    raise IngestError("UNKNOWN_REGION")


def _sidecars(directory: Path, pattern: str):
    for meta_path in sorted(directory.glob(pattern)):
        info = json.loads(meta_path.read_text())
        data_path = meta_path.with_name(meta_path.name[: -len(".meta.json")])
        payload = data_path.read_bytes()
        if sha256(payload) != info["content_sha256"]:
            raise IngestError("FILE_HASH_MISMATCH")
        yield data_path, meta_path, info, payload


def _copy(source: Path, target: Path):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def build_package(
    settings: Settings,
    out: Path,
    name: str,
    regions: list[str],
    firms_dirs: list[Path],
    osm_dir: Path,
    landcover_product: str = Product.NOAA20.value,
) -> dict:
    """Copy the chosen regions' retained inputs into `out/name` with a hashed manifest."""
    for region in regions:
        region_box(region)
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,60}", name):
        raise ValueError("package name: lowercase letters, digits, . _ -")
    target = out / name
    if target.exists():
        raise FileExistsError(target)
    secret = settings.firms_map_key.get_secret_value().encode() if settings.firms_map_key else None
    files: list[dict] = []
    staging = out / f".{name}.partial"
    shutil.rmtree(staging, ignore_errors=True)
    try:
        # FIRMS windows come from this database's own receipts (the files the workbench
        # actually shows), read from the content-addressed object store; a retained sidecar
        # with the same hash adds the provider retrieval time.
        retrieved = {}
        for directory in firms_dirs:
            for _, _, info, _ in _sidecars(directory, "*.csv.meta.json"):
                retrieved[info["content_sha256"]] = info["received_at"]
        store_root = settings.object_store_local_path
        for run in _firms_runs(settings, regions):
            payload = (store_root / "raw" / f"{run['sha256']}.csv").read_bytes()
            if sha256(payload) != run["sha256"]:
                raise IngestError("OBJECT_HASH_MISMATCH")
            _check_clean(payload, secret)
            name_ = f"{run['region']}-{run['product']}-{run['start_date']}-{run['days']}"
            if run["duplicate_window"]:
                name_ += f"-{run['sha256'][:12]}"
            path = f"firms/{name_}.csv"
            (staging / "firms").mkdir(parents=True, exist_ok=True)
            (staging / path).write_bytes(payload)
            files.append(
                {
                    "path": path,
                    "kind": "FIRMS_CSV",
                    "source": "NASA_FIRMS",
                    "region": run["region"],
                    "product": run["product"],
                    "start_date": run["start_date"],
                    "days": run["days"],
                    "provider_received_at": retrieved.get(run["sha256"]),
                    "first_imported_at": run["first_imported_at"],
                }
            )
        for region in regions:
            snapshots = sorted(_sidecars(osm_dir, f"{region}-osm-*.json.meta.json"),
                               key=lambda item: item[2]["received_at"])  # fmt: skip
            if not snapshots:
                raise IngestError("OSM_SNAPSHOT_MISSING")
            data_path, meta_path, info, payload = snapshots[-1]
            _check_clean(payload, secret)
            _copy(data_path, staging / "osm" / data_path.name)
            _copy(meta_path, staging / "osm" / meta_path.name)
            files.append(
                {
                    "path": f"osm/{data_path.name}",
                    "kind": "OSM_OVERPASS_JSON",
                    "source": "OPENSTREETMAP",
                    "region": region,
                    "received_at": info["received_at"],
                    "endpoint": info["endpoint"],
                    "query_sha256": info["query_sha256"],
                    "sidecar": f"osm/{meta_path.name}",
                }
            )
        summaries = _landcover_rows(settings, regions, landcover_product)
        for row in summaries:
            chip = (store_root / row["chip_object"]).read_bytes()
            chip_sha = Path(row["chip_object"]).stem
            if sha256(chip) != chip_sha:
                raise IngestError("OBJECT_HASH_MISMATCH")
            target_chip = staging / "worldcover" / f"{chip_sha}.tif"
            if not target_chip.exists():
                target_chip.parent.mkdir(parents=True, exist_ok=True)
                target_chip.write_bytes(chip)
                files.append({"path": f"worldcover/{chip_sha}.tif", "kind": "WORLDCOVER_CHIP",
                              "source": "ESA_WORLDCOVER"})  # fmt: skip
        summary_bytes = (
            json.dumps(summaries, indent=1, sort_keys=True, default=str) + "\n"
        ).encode()
        (staging / "worldcover").mkdir(parents=True, exist_ok=True)
        (staging / "worldcover" / "summaries.json").write_bytes(summary_bytes)
        files.append({"path": "worldcover/summaries.json", "kind": "WORLDCOVER_SUMMARIES",
                      "source": "ESA_WORLDCOVER", "rows": len(summaries),
                      "summary_version": SUMMARY_VERSION, "product": PRODUCT})  # fmt: skip
        for entry in files:
            payload = (staging / entry["path"]).read_bytes()
            entry["sha256"], entry["bytes"] = sha256(payload), len(payload)
            if entry.get("sidecar"):
                entry["sidecar_sha256"] = sha256((staging / entry["sidecar"]).read_bytes())
        total = sum(e["bytes"] for e in files)
        if total > MAX_PACKAGE_BYTES:
            raise IngestError("PACKAGE_TOO_LARGE")
        files.sort(key=lambda e: e["path"])
        manifest = {
            "package_version": PACKAGE_VERSION,
            "name": name,
            "regions": regions,
            "data_mode": DataMode.HISTORICAL_REPLAY.value,
            "created_at": datetime.now(UTC).isoformat(),
            "purpose": "Offline demonstration replay of saved real observations. Not the frozen "
            "P05 evaluation set; contains no labels, reviews or model outputs.",
            "sources": SOURCES,
            "files": files,
            "bytes": total,
            "content_sha256": content_digest(files),
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
        (staging / "README.txt").write_text(readme(manifest))
        staging.rename(target)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return summary_of(manifest, target)


def _check_clean(payload: bytes, secret: bytes | None):
    """Refuse files that could carry a credential (never prints what matched)."""
    if KEY_BEARING.search(payload) or (secret and secret in payload):
        raise IngestError("POSSIBLE_CREDENTIAL_IN_FILE")


def _firms_runs(settings: Settings, regions: list[str]) -> list[dict]:
    runs = []
    with batch_engine(settings) as engine, engine.connect() as conn:
        for region in regions:
            rows = conn.execute(
                text("""
                SELECT r.product,r.start_date,(r.end_date-r.start_date+1) AS days,
                    s.content_sha256 AS sha256,min(r.received_at) AS first_imported_at
                FROM ingestion_runs r JOIN source_snapshots s ON s.id=r.snapshot_id
                WHERE r.data_mode='HISTORICAL_REPLAY' AND r.status IN ('SUCCEEDED','PARTIAL')
                    AND r.product = ANY(:family)
                    AND ST_Equals(r.bounds,ST_MakeEnvelope(:west,:south,:east,:north,4326))
                GROUP BY r.product,r.start_date,r.end_date,s.content_sha256
                ORDER BY r.product,r.start_date,s.content_sha256
            """),
                region_box(region).model_dump() | {"family": list(NOAA20_PRODUCTS)},
            ).mappings()
            items = [dict(r) for r in rows]
            windows: dict[tuple, int] = {}
            for item in items:
                key = (item["product"], item["start_date"])
                windows[key] = windows.get(key, 0) + 1
            for item in items:
                runs.append(
                    item
                    | {
                        "region": region,
                        "start_date": item["start_date"].isoformat(),
                        "first_imported_at": item["first_imported_at"].isoformat(),
                        "duplicate_window": windows[(item["product"], item["start_date"])] > 1,
                    }
                )
    return runs


def _landcover_rows(settings: Settings, regions: list[str], product: str) -> list[dict]:
    rows = []
    with batch_engine(settings) as engine, engine.connect() as conn:
        for region in regions:
            box = region_box(region).model_dump()
            for row in conn.execute(
                text("""
                SELECT l.observation_id,l.tile_id,l.source,l.window_sha256,l.chip_object,
                    l.tile_edge_clipped,l.support_basis,l.support,l.context,l.status,l.run_id,
                    l.extracted_at
                FROM landcover_summaries l JOIN observations o ON o.id=l.observation_id
                WHERE l.product=:lc AND l.summary_version=:version AND o.product=:product
                    AND o.geom && ST_MakeEnvelope(:west,:south,:east,:north,4326)
                    AND EXISTS (SELECT 1 FROM observation_receipts x
                        JOIN ingestion_runs r ON r.id=x.run_id WHERE x.observation_id=o.id
                        AND r.data_mode='HISTORICAL_REPLAY' AND r.status IN ('SUCCEEDED','PARTIAL'))
                ORDER BY l.observation_id
            """),
                box | {"lc": PRODUCT, "version": SUMMARY_VERSION, "product": product},
            ).mappings():
                rows.append(
                    dict(row)
                    | {
                        "run_id": str(row["run_id"]),
                        "extracted_at": row["extracted_at"].isoformat(),
                        "region": region,
                    }
                )
    return rows


def content_digest(files: list[dict]) -> str:
    """Identifies the package content independently of when or where it was built."""
    lines = "".join(f"{e['path']} {e['sha256']}\n" for e in sorted(files, key=lambda e: e["path"]))
    return sha256(lines.encode())


def readme(manifest: dict) -> str:
    lines = [
        f"ThermoScope demo package {manifest['name']} ({manifest['package_version']})",
        "",
        manifest["purpose"],
        f"Regions: {', '.join(manifest['regions'])}. Mode: {manifest['data_mode']}.",
        f"Files: {len(manifest['files'])}, {manifest['bytes']} bytes, content SHA-256 "
        f"{manifest['content_sha256']}.",
        "",
        "Sources and licences:",
    ]
    for key, source in manifest["sources"].items():
        lines += [f"- {key}: {source['license']}", f"  {source['attribution']}"]
    lines += [
        "",
        "Load (offline): python scripts/demo_package.py load --package <this folder> "
        "--database thermoscope_demo --create --offline",
        "Every file is checked against manifest.json before anything is stored.",
    ]
    return "\n".join(lines) + "\n"


def summary_of(manifest: dict, where: Path) -> dict:
    kinds: dict[str, int] = {}
    for entry in manifest["files"]:
        kinds[entry["kind"]] = kinds.get(entry["kind"], 0) + 1
    return {
        "package": str(where),
        "name": manifest["name"],
        "regions": manifest["regions"],
        "files": kinds,
        "bytes": manifest["bytes"],
        "content_sha256": manifest["content_sha256"],
    }


def verify_package(directory: Path) -> dict:
    """Every listed file present with its hash and size; nothing unlisted."""
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest.get("package_version") != PACKAGE_VERSION:
        raise IngestError("UNSUPPORTED_PACKAGE_VERSION")
    problems = []
    listed = set(FIXED_FILES)
    for entry in manifest["files"]:
        for path, digest in ((entry["path"], entry["sha256"]),
                             (entry.get("sidecar"), entry.get("sidecar_sha256"))):  # fmt: skip
            if path is None:
                continue
            listed.add(path)
            file = directory / path
            if not file.is_file():
                problems.append({"path": path, "problem": "MISSING"})
            elif sha256(file.read_bytes()) != digest:
                problems.append({"path": path, "problem": "HASH_MISMATCH"})
    for file in directory.rglob("*"):
        if file.is_file() and file.relative_to(directory).as_posix() not in listed:
            problems.append({"path": file.relative_to(directory).as_posix(),
                             "problem": "NOT_IN_MANIFEST"})  # fmt: skip
    if content_digest(manifest["files"]) != manifest["content_sha256"]:
        problems.append({"path": "manifest.json", "problem": "CONTENT_DIGEST_MISMATCH"})
    return {"ok": not problems, "problems": problems} | summary_of(manifest, directory)


def load_package(settings: Settings, directory: Path, *, build_events: bool = True) -> dict:
    """Import a verified package as historical replay; safe to repeat."""
    check = verify_package(directory)
    if not check["ok"]:
        raise IngestError("PACKAGE_VERIFICATION_FAILED")
    manifest = json.loads((directory / "manifest.json").read_text())
    report = {"firms": {}, "inserted_rows": 0, "osm": {}, "landcover": {}, "events": {}}
    for entry in manifest["files"]:
        if entry["kind"] != "FIRMS_CSV":
            continue
        payload = (directory / entry["path"]).read_bytes()
        window = Window(
            product=Product(entry["product"]),
            bounds=region_box(entry["region"]),
            start_date=date.fromisoformat(entry["start_date"]),
            days=entry["days"],
        )
        result = ingest(settings, window, DataMode.HISTORICAL_REPLAY, payload=payload,
                        expected_sha256=entry["sha256"])  # fmt: skip
        report["firms"][result["status"]] = report["firms"].get(result["status"], 0) + 1
        report["inserted_rows"] += result.get("inserted_rows", 0)
    for entry in manifest["files"]:
        if entry["kind"] != "OSM_OVERPASS_JSON":
            continue
        result = ingest_osm(
            settings,
            entry["region"],
            payload=(directory / entry["path"]).read_bytes(),
            expected_sha256=entry["sha256"],
            retrieved_at=datetime.fromisoformat(entry["received_at"].replace("Z", "+00:00")),
            endpoint=entry["endpoint"],
        )
        report["osm"][entry["region"]] = result.get("status")
    report["landcover"] = restore_landcover(settings, directory)
    if build_events:
        for region in manifest["regions"]:
            result = build_event_run(settings, region, DataMode.HISTORICAL_REPLAY)
            report["events"][region] = {
                k: result.get(k) for k in ("status", "input_count", "event_count", "site_count")
            }
    return report | {"package": manifest["name"], "content_sha256": manifest["content_sha256"]}


def restore_landcover(settings: Settings, directory: Path) -> dict:
    """Insert packaged land-cover summaries only when the chip reproduces them exactly."""
    import rasterio
    from rasterio.io import MemoryFile

    rows = json.loads((directory / "worldcover" / "summaries.json").read_text())
    store = ObjectStore(settings.object_store_local_path)
    restored = existing = 0
    with batch_engine(settings) as engine, engine.begin() as conn:
        for row in rows:
            obs = conn.execute(
                text("""SELECT ST_X(geom) AS lon,ST_Y(geom) AS lat,
                    (payload->>'scan_km')::double precision AS scan,
                    (payload->>'track_km')::double precision AS track
                    FROM observations WHERE id=:id"""),
                {"id": row["observation_id"]},
            ).mappings().first()  # fmt: skip
            if obs is None:
                raise IngestError("LANDCOVER_OBSERVATION_MISSING")
            chip = (directory / "worldcover" / f"{Path(row['chip_object']).stem}.tif").read_bytes()
            with rasterio.Env(), MemoryFile(chip) as memory, memory.open() as dataset:
                array, transform = dataset.read(1), dataset.transform
            window_sha = sha256(
                json.dumps([array.shape, list(transform)[:6]]).encode() + array.tobytes()
            )
            radius, basis = support_radius_m(obs["scan"], obs["track"])
            support = summarize_array(array, transform, obs["lon"], obs["lat"], radius)
            context = summarize_array(array, transform, obs["lon"], obs["lat"], CONTEXT_RADIUS_M)
            if (
                window_sha != row["window_sha256"]
                or basis != row["support_basis"]
                or support != row["support"]
                or context != row["context"]
            ):
                raise IngestError("LANDCOVER_SUMMARY_NOT_REPRODUCED")
            if store.save_raw(chip, suffix="tif") != Path(row["chip_object"]).stem:
                raise IngestError("OBJECT_HASH_MISMATCH")
            inserted = conn.execute(
                text("""
                INSERT INTO landcover_summaries (observation_id,product,summary_version,run_id,
                    tile_id,source,window_sha256,chip_object,tile_edge_clipped,support_basis,
                    support,context,status,extracted_at)
                VALUES (:observation_id,:product,:version,CAST(:run_id AS uuid),:tile_id,:source,
                    :window_sha256,:chip_object,:tile_edge_clipped,:support_basis,
                    CAST(:support AS jsonb),CAST(:context AS jsonb),:status,:extracted_at)
                ON CONFLICT (observation_id,product,summary_version) DO NOTHING
            """),
                row
                | {
                    "product": PRODUCT,
                    "version": SUMMARY_VERSION,
                    "support": json.dumps(row["support"]),
                    "context": json.dumps(row["context"]),
                    "extracted_at": datetime.fromisoformat(row["extracted_at"]),
                },
            ).rowcount
            restored += inserted
            existing += 1 - inserted
    return {"summaries": len(rows), "restored": restored, "already_present": existing,
            "summary_version": SUMMARY_VERSION}  # fmt: skip
