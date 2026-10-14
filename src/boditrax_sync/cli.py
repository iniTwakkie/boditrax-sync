"""Command line interface for boditrax-sync."""

from __future__ import annotations

import argparse
import getpass
import logging
import os
import sys
from pathlib import Path

from . import __version__
from .api import DEFAULT_TIMEZONE, BoditraxClient
from .config import CredentialsError, load_credentials, save_credentials
from .db import connect
from .export import to_csv, to_json, to_table

logger = logging.getLogger("boditrax_sync")


def _add_credentials_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--credentials",
        type=Path,
        metavar="PATH",
        help="credentials file (default: ~/.config/boditrax-sync/credentials.json)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="boditrax-sync",
        description=(
            "Unofficial tool to download Boditrax 2.0 body-composition scans: "
            "export as JSON/CSV or sync into PostgreSQL/SQLite."
        ),
        epilog="Documentation: https://github.com/iniTwakkie/boditrax-sync",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    parser.add_argument(
        "--timezone",
        default=DEFAULT_TIMEZONE,
        help="timezone the scan timestamps belong to (default: %(default)s)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    login = subparsers.add_parser("login", help="verify and store account credentials")
    login.add_argument("--username", help="Boditrax account email (prompted if omitted)")
    _add_credentials_arg(login)

    fetch = subparsers.add_parser("fetch", help="fetch scans and print or save them")
    fetch.add_argument(
        "--format",
        choices=["table", "json", "csv"],
        help="output format (default: table, or inferred from --output suffix)",
    )
    fetch.add_argument("-o", "--output", type=Path, metavar="FILE", help="write to FILE")
    _add_credentials_arg(fetch)

    sync = subparsers.add_parser("sync", help="sync scans into PostgreSQL or SQLite")
    sync.add_argument(
        "--db-url",
        default=os.environ.get("BODITRAX_DB_URL"),
        help="postgresql://... or sqlite://<path> (or set BODITRAX_DB_URL)",
    )
    sync.add_argument("--dry-run", action="store_true", help="fetch and report, write nothing")
    _add_credentials_arg(sync)

    return parser


def _fetch_readings(args: argparse.Namespace) -> list:
    username, password = load_credentials(args.credentials)
    client = BoditraxClient(username, password, timezone=args.timezone)
    readings = client.fetch_readings()
    if readings:
        logger.info(
            "fetched %d readings (%s to %s)",
            len(readings),
            readings[0].recorded_at.date(),
            readings[-1].recorded_at.date(),
        )
    else:
        logger.info("no readings returned for this account")
    return readings


def _resolve_format(args: argparse.Namespace) -> str:
    if args.format:
        return args.format
    if args.output:
        suffix = args.output.suffix.lower()
        if suffix == ".json":
            return "json"
        if suffix == ".csv":
            return "csv"
    return "table"


def cmd_login(args: argparse.Namespace) -> int:
    username = args.username or input("Boditrax account email: ").strip()
    if not username:
        raise CredentialsError("a username is required")
    password = getpass.getpass("Boditrax password: ")
    if not password:
        raise CredentialsError("a password is required")

    client = BoditraxClient(username, password)
    client.authenticate()
    path = save_credentials(username, password, args.credentials)
    print(f"Credentials verified and saved to {path}")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    readings = _fetch_readings(args)
    fmt = _resolve_format(args)
    renderers = {"json": to_json, "csv": to_csv, "table": to_table}
    text = renderers[fmt](readings)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        logger.info("wrote %d readings to %s", len(readings), args.output)
    else:
        sys.stdout.write(text)
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    if not args.db_url:
        logger.error("sync needs --db-url (or BODITRAX_DB_URL), e.g. sqlite:///boditrax.db")
        return 2
    readings = _fetch_readings(args)
    if args.dry_run:
        metric_values = sum(len(reading.metrics) for reading in readings)
        logger.info(
            "dry run: would sync %d readings (%d metric values) to %s",
            len(readings),
            metric_values,
            args.db_url,
        )
        return 0

    database = connect(args.db_url)
    try:
        result = database.upsert_readings(readings)
    finally:
        database.close()
    logger.info(
        "synced %d readings (%d new, %d metric values written) to %s",
        result.readings_fetched,
        result.new_readings,
        result.metrics_written,
        args.db_url,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
        stream=sys.stderr,
    )
    handlers = {"login": cmd_login, "fetch": cmd_fetch, "sync": cmd_sync}
    try:
        return handlers[args.command](args)
    except KeyboardInterrupt:
        logger.error("interrupted")
        return 130
    except Exception as exc:
        logger.error("error: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
