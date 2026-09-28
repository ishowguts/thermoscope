"""Build, verify, load and serve an offline ThermoScope demo package (P07-SUB-001).

Run from the repository root through the project runtime, for example:

    PYTHONPATH=backend bash scripts/run.sh uv run --frozen python scripts/demo_package.py \\
        build --name thermoscope-demo-v1 --regions jamnagar,punjab
    PYTHONPATH=backend bash scripts/run.sh uv run --frozen python scripts/demo_package.py \\
        load --package local/demo-package/thermoscope-demo-v1 --database thermoscope_demo \\
        --create --offline
    PYTHONPATH=backend bash scripts/run.sh uv run --frozen python scripts/demo_package.py \\
        serve --database thermoscope_demo --offline

`--database NAME` reuses the server, user and password of DATABASE_URL in .env with another
database name; nothing secret is printed. `--create` creates that database on a loopback server
and applies the migrations. `--offline` makes this process refuse every network connection
except to the local machine, so a successful run shows that nothing was fetched.
Every command prints one JSON report.
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


def forbid_network():
    """Allow loopback and local sockets only; anything else raises before a packet is sent."""
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_getaddrinfo = socket.getaddrinfo

    def local(address) -> bool:
        if isinstance(address, (str, bytes)):  # AF_UNIX path
            return True
        host = address[0]
        if host in {"localhost", "127.0.0.1", "::1"}:
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    def connect(self, address):
        if not local(address):
            raise OSError(f"offline mode: refused connection to {address[0]}")
        return original_connect(self, address)

    def connect_ex(self, address):
        if not local(address):
            raise OSError(f"offline mode: refused connection to {address[0]}")
        return original_connect_ex(self, address)

    def getaddrinfo(host, *args, **kwargs):
        if host not in {None, "localhost", "127.0.0.1", "::1"}:
            try:
                if not ipaddress.ip_address(host).is_loopback:
                    raise OSError(f"offline mode: refused name lookup for {host}")
            except ValueError:
                raise OSError(f"offline mode: refused name lookup for {host}") from None
        return original_getaddrinfo(host, *args, **kwargs)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
    socket.getaddrinfo = getaddrinfo


def use_database(name: str, create: bool) -> None:
    """Point DATABASE_URL at another database on the configured loopback server."""
    from sqlalchemy.engine import make_url
    from thermoscope.config import Settings

    if not name.replace("_", "").isalnum() or not name.startswith("thermoscope_"):
        raise SystemExit("--database must look like thermoscope_<name>")
    base = Settings().database_url
    if base is None:
        raise SystemExit("DATABASE_URL is not configured in .env")
    url = make_url(base.get_secret_value())
    if url.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("demo databases are only created and used on a loopback server")
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
    parser.add_argument("--database", help="database name on the configured server")
    parser.add_argument("--create", action="store_true", help="create and migrate --database")
    parser.add_argument("--offline", action="store_true", help="refuse non-loopback network")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    if args.offline:
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
            report = verify_package(Path(_need(parser, args.package)))
        elif args.command == "load":
            report = load_package(Settings(), Path(_need(parser, args.package)))
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


if __name__ == "__main__":
    sys.exit(main())
