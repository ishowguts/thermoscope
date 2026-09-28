"""Build, verify, load and serve an offline ThermoScope demo package (P07-SUB-001).

Run from the repository root through the project runtime (docs/tasks/P07-DEMO-RUNBOOK.md):

    PYTHONPATH=backend bash scripts/run.sh uv run --frozen python scripts/demo_package.py \\
        build --name thermoscope-demo-v1 --regions jamnagar,punjab
    PYTHONPATH=backend bash scripts/run.sh uv run --frozen python scripts/demo_package.py \\
        load --package local/demo-package/thermoscope-demo-v1 --database thermoscope_demo \\
        --create --offline
    PYTHONPATH=backend bash scripts/run.sh uv run --frozen python scripts/demo_package.py \\
        serve --database thermoscope_demo --offline

`build` reads the database and object store configured in .env (`--source-objects` overrides the
store). `load` and `serve` need `--database NAME`: the server, user and password of DATABASE_URL
in .env with another database name, never the configured one, on a loopback server only; their
objects go to `--objects` (default local/demo-objects). Nothing secret is printed. `--create`
creates the database and applies the migrations.

`--offline` is a guard for this process, not a firewall: Python-level connections and name
lookups to anything but the local machine are refused, HTTP clients in C libraries (curl, GDAL)
are pointed at a dead local proxy, and the database must be on a loopback server. Physically
disconnecting the machine remains the acceptance check. Every command prints one JSON report.
"""

import argparse
import ipaddress
import json
import os
import socket
import sys
import time
from pathlib import Path

DEFAULT_FIRMS_DIRS = ["local/history-fetch", "local/p05-fetch/raw", "local/p05-backfill/raw"]
DEFAULT_OSM_DIR = "local/context-fetch"
DEFAULT_OUT = "local/demo-package"
DEFAULT_OBJECTS = "local/demo-objects"
DEAD_PROXY = "http://127.0.0.1:9"
LOOPBACK = {"localhost", "127.0.0.1", "::1"}


def _loopback_host(host) -> bool:
    if host is None or host in LOOPBACK:
        return True
    if isinstance(host, bytes):
        host = host.decode(errors="replace")
    try:
        return ipaddress.ip_address(str(host).split("%")[0]).is_loopback
    except ValueError:
        return False


def forbid_network():
    """Refuse Python-level connections, datagrams and name lookups except to the local machine,
    and point C-library HTTP clients at a dead local proxy. A guard, not a firewall."""
    original = {
        "connect": socket.socket.connect,
        "connect_ex": socket.socket.connect_ex,
        "sendto": socket.socket.sendto,
        "sendmsg": socket.socket.sendmsg,
        "getaddrinfo": socket.getaddrinfo,
        "gethostbyname": socket.gethostbyname,
        "gethostbyname_ex": socket.gethostbyname_ex,
        "gethostbyaddr": socket.gethostbyaddr,
        "getnameinfo": socket.getnameinfo,
    }

    def local(address) -> bool:
        if isinstance(address, (str, bytes)):  # AF_UNIX path
            return True
        return _loopback_host(address[0])

    def refuse(what, host):
        raise OSError(f"offline mode: refused {what} {host}")

    def connect(self, address):
        if not local(address):
            refuse("connection to", address[0])
        return original["connect"](self, address)

    def connect_ex(self, address):
        if not local(address):
            refuse("connection to", address[0])
        return original["connect_ex"](self, address)

    def sendto(self, data, *args):
        address = args[-1]
        if not local(address):
            refuse("datagram to", address[0])
        return original["sendto"](self, data, *args)

    def sendmsg(self, buffers, ancdata=(), flags=0, address=None):
        if address is not None and not local(address):
            refuse("datagram to", address[0])
        if address is None:
            return original["sendmsg"](self, buffers, ancdata, flags)
        return original["sendmsg"](self, buffers, ancdata, flags, address)

    def lookup(name):
        def guarded(host, *args, **kwargs):
            if not _loopback_host(host):
                refuse("name lookup for", host)
            return original[name](host, *args, **kwargs)

        return guarded

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
    socket.socket.sendto = sendto
    socket.socket.sendmsg = sendmsg
    socket.getaddrinfo = lookup("getaddrinfo")
    socket.gethostbyname = lookup("gethostbyname")
    socket.gethostbyname_ex = lookup("gethostbyname_ex")
    socket.gethostbyaddr = lookup("gethostbyaddr")

    def getnameinfo(address, flags):
        if not local(address):
            refuse("name lookup for", address[0])
        return original["getnameinfo"](address, flags)

    socket.getnameinfo = getnameinfo
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy",
                 "all_proxy", "GDAL_HTTP_PROXY"):  # fmt: skip
        os.environ[name] = DEAD_PROXY
    os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost,::1"


def loopback_database(url) -> bool:
    """The server and any libpq host/hostaddr override in the URL are on this machine (a
    missing host means a local socket)."""
    hosts = [url.host]
    for key in ("host", "hostaddr"):
        value = url.query.get(key)
        for item in value if isinstance(value, tuple) else [value] if value else []:
            hosts += str(item).split(",")
    return all(h is None or str(h).startswith("/") or _loopback_host(h) for h in hosts)


def configured_database():
    from sqlalchemy.engine import make_url
    from thermoscope.config import Settings

    base = Settings().database_url
    if base is None:
        raise SystemExit("DATABASE_URL is not configured in .env")
    return make_url(base.get_secret_value())


def use_database(name: str, create: bool) -> None:
    """Point DATABASE_URL at another database on the configured loopback server."""
    if not name.replace("_", "").isalnum() or not name.startswith("thermoscope_"):
        raise SystemExit("--database must look like thermoscope_<name>")
    url = configured_database()
    if not loopback_database(url):
        raise SystemExit("demo databases are only created and used on a loopback server")
    if name == url.database:
        raise SystemExit("--database must not be the database configured in .env")
    target = url.set(database=name)
    if create:
        import psycopg
        from psycopg import sql

        admin = url.set(drivername="postgresql", database="postgres")
        with psycopg.connect(admin.render_as_string(hide_password=False), autocommit=True) as c:
            exists = c.execute("SELECT 1 FROM pg_database WHERE datname=%s", (name,)).fetchone()
            if not exists:
                c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    os.environ["DATABASE_URL"] = target.render_as_string(hide_password=False)
    if create:
        from alembic import command
        from alembic.config import Config

        command.upgrade(Config("alembic.ini"), "head")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["build", "verify", "load", "serve"])
    parser.add_argument("--name", default="thermoscope-demo-v1")
    parser.add_argument("--regions", default="jamnagar,punjab")
    parser.add_argument(
        "--firms-dir", action="append", help="sidecar folders that add provider retrieval times"
    )
    parser.add_argument("--osm-dir", default=DEFAULT_OSM_DIR)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--package", help="package folder for verify/load")
    parser.add_argument("--expect-sha256", help="content hash received separately (verify/load)")
    parser.add_argument("--database", help="demo database name (required for load/serve)")
    parser.add_argument("--objects", default=DEFAULT_OBJECTS, help="object folder (load/serve)")
    parser.add_argument("--source-objects", help="object store to read from (build)")
    parser.add_argument("--create", action="store_true", help="create and migrate --database")
    parser.add_argument("--offline", action="store_true", help="refuse non-loopback network")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    if args.command in {"load", "serve"}:
        if not args.database:
            parser.error(f"{args.command} needs --database thermoscope_<name> (a demo database)")
        from thermoscope.config import Settings

        main_store = Path(Settings().object_store_local_path).resolve()
        objects = Path(args.objects).resolve()
        if objects == main_store or main_store in objects.parents or objects in main_store.parents:
            parser.error("--objects must not be, contain or lie inside the object store in .env")
        os.environ["OBJECT_STORE_LOCAL_PATH"] = args.objects
    if args.command == "serve":
        os.environ["APP_DATA_MODE"] = "HISTORICAL_REPLAY"  # a demo package is always replay
    if args.command == "build" and args.source_objects:
        os.environ["OBJECT_STORE_LOCAL_PATH"] = args.source_objects
    if args.offline:
        if args.command != "verify" and not loopback_database(configured_database()):
            raise SystemExit("--offline needs the database on a loopback server")
        forbid_network()
    if args.database:
        use_database(args.database, args.create)

    from thermoscope.config import Settings
    from thermoscope.firms import IngestError
    from thermoscope.replay import build_package, load_package, verify_package

    started = time.monotonic()
    try:
        if args.command == "build":
            report = build_package(
                Settings(),
                Path(args.out),
                args.name,
                [r.strip() for r in args.regions.split(",") if r.strip()],
                [Path(d) for d in (args.firms_dir or DEFAULT_FIRMS_DIRS) if Path(d).is_dir()],
                Path(args.osm_dir),
            )
        elif args.command == "verify":
            report = verify_package(Path(_need(parser, args.package)), args.expect_sha256)
        elif args.command == "load":
            report = load_package(Settings(), Path(_need(parser, args.package)),
                                  expect_sha256=args.expect_sha256)  # fmt: skip
        else:
            import uvicorn
            from thermoscope.main import create_app

            print(json.dumps({"serving": f"http://127.0.0.1:{args.port}",
                              "database": args.database or "from .env",
                              "offline": args.offline}), flush=True)  # fmt: skip
            uvicorn.run(create_app(Settings()), host="127.0.0.1", port=args.port,
                        log_level="warning")  # fmt: skip
            return 0
    except (IngestError, ValueError, FileExistsError, OSError) as error:
        code = error.code if isinstance(error, IngestError) else type(error).__name__
        print(json.dumps({"status": "FAILED", "error": code, "detail": str(error)[:200]}))
        return 1
    report["seconds"] = round(time.monotonic() - started, 2)
    report["offline"] = args.offline
    print(json.dumps(report, indent=2, default=str))
    return 0 if report.get("ok", True) else 1


def _need(parser, value):
    if not value:
        parser.error("this command needs --package")
    return value


def cli() -> int:
    """Report an unreachable database as one JSON line instead of a driver traceback."""
    try:
        return main()
    except Exception as error:  # noqa: BLE001 - classified below, never echoed
        from psycopg import OperationalError as DriverError
        from sqlalchemy.exc import OperationalError

        if not isinstance(error, (OperationalError, DriverError)):
            raise
        hint = "Check that PostGIS is running and DATABASE_URL in .env."
        print(json.dumps({"status": "FAILED", "error": "DATABASE_UNAVAILABLE", "detail": hint}))
        return 1


if __name__ == "__main__":
    sys.exit(cli())
