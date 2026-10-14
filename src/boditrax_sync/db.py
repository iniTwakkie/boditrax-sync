"""Optional database sync targets: PostgreSQL and SQLite.

Both backends create a self-contained schema (a ``readings`` table and a
``metrics`` table) and idempotently upsert scans: each reading is rewritten
metric by metric inside a transaction, so repeat runs are safe and edits made
in the Boditrax app are reflected on the next sync.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from .metrics import METRIC_UNITS
from .models import Reading

SCHEMA_POSTGRES = """
CREATE SCHEMA IF NOT EXISTS boditrax;

CREATE TABLE IF NOT EXISTS boditrax.readings (
    reading_id      text PRIMARY KEY,
    recorded_at     timestamptz NOT NULL,
    kiosk_id        text,
    device_type_id  integer,
    reading_type_id integer,
    fetched_at      timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS boditrax.metrics (
    reading_id text NOT NULL REFERENCES boditrax.readings(reading_id) ON DELETE CASCADE,
    metric     text NOT NULL,
    value      double precision NOT NULL,
    unit       text NOT NULL DEFAULT '',
    PRIMARY KEY (reading_id, metric)
);
"""

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS readings (
    reading_id      text PRIMARY KEY,
    recorded_at     text NOT NULL,
    kiosk_id        text,
    device_type_id  integer,
    reading_type_id integer,
    fetched_at      text NOT NULL
);

CREATE TABLE IF NOT EXISTS metrics (
    reading_id text NOT NULL REFERENCES readings(reading_id) ON DELETE CASCADE,
    metric     text NOT NULL,
    value      real NOT NULL,
    unit       text NOT NULL DEFAULT '',
    PRIMARY KEY (reading_id, metric)
);
"""


@dataclass
class SyncResult:
    readings_fetched: int
    new_readings: int
    metrics_written: int


class Database(Protocol):
    def upsert_readings(self, readings: list[Reading]) -> SyncResult: ...

    def close(self) -> None: ...


def connect(db_url: str) -> Database:
    """Open a sync target. Accepts ``postgresql://...`` or ``sqlite://<path>``."""
    if db_url.startswith(("postgresql://", "postgres://")):
        return PostgresDatabase(db_url)
    if db_url.startswith("sqlite://"):
        path = db_url[len("sqlite://") :]
        while path.startswith("//"):
            path = path[1:]
        if not path:
            raise ValueError("sqlite:// database URL needs a path, e.g. sqlite:///data/boditrax.db")
        return SqliteDatabase(path)
    raise ValueError(f"unsupported database URL {db_url!r} (use postgresql:// or sqlite://)")


class SqliteDatabase:
    def __init__(self, path: str) -> None:
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA_SQLITE)
        self.conn.commit()

    def upsert_readings(self, readings: list[Reading]) -> SyncResult:
        fetched_at = datetime.now(timezone.utc).isoformat()
        with self.conn:
            existing = {row[0] for row in self.conn.execute("SELECT reading_id FROM readings")}
            metrics_written = 0
            for reading in readings:
                self.conn.execute(
                    """
                    INSERT INTO readings
                        (reading_id, recorded_at, kiosk_id,
                         device_type_id, reading_type_id, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT (reading_id) DO UPDATE SET
                        recorded_at = excluded.recorded_at,
                        kiosk_id = excluded.kiosk_id,
                        device_type_id = excluded.device_type_id,
                        reading_type_id = excluded.reading_type_id,
                        fetched_at = excluded.fetched_at
                    """,
                    (
                        reading.reading_id,
                        reading.recorded_at.isoformat(),
                        reading.kiosk_id,
                        reading.device_type_id,
                        reading.reading_type_id,
                        fetched_at,
                    ),
                )
                self.conn.execute("DELETE FROM metrics WHERE reading_id = ?", (reading.reading_id,))
                rows = [
                    (reading.reading_id, name, value, METRIC_UNITS.get(name, ""))
                    for name, value in reading.metrics.items()
                ]
                self.conn.executemany(
                    "INSERT INTO metrics (reading_id, metric, value, unit) VALUES (?, ?, ?, ?)",
                    rows,
                )
                metrics_written += len(rows)
        return SyncResult(
            readings_fetched=len(readings),
            new_readings=sum(1 for reading in readings if reading.reading_id not in existing),
            metrics_written=metrics_written,
        )

    def close(self) -> None:
        self.conn.close()


class PostgresDatabase:
    def __init__(self, url: str) -> None:
        try:
            import psycopg
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise RuntimeError(
                "PostgreSQL support requires the 'postgres' extra: "
                "pip install 'boditrax-sync[postgres]'"
            ) from exc

        self.conn = psycopg.connect(url)
        with self.conn.cursor() as cur:
            cur.execute(SCHEMA_POSTGRES)
        self.conn.commit()

    def upsert_readings(self, readings: list[Reading]) -> SyncResult:
        fetched_at = datetime.now(timezone.utc)
        with self.conn.cursor() as cur:
            cur.execute("SELECT reading_id FROM boditrax.readings")
            existing = {row[0] for row in cur.fetchall()}
            metrics_written = 0
            for reading in readings:
                cur.execute(
                    """
                    INSERT INTO boditrax.readings
                        (reading_id, recorded_at, kiosk_id,
                         device_type_id, reading_type_id, fetched_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (reading_id) DO UPDATE SET
                        recorded_at = EXCLUDED.recorded_at,
                        kiosk_id = EXCLUDED.kiosk_id,
                        device_type_id = EXCLUDED.device_type_id,
                        reading_type_id = EXCLUDED.reading_type_id,
                        fetched_at = EXCLUDED.fetched_at
                    """,
                    (
                        reading.reading_id,
                        reading.recorded_at,
                        reading.kiosk_id,
                        reading.device_type_id,
                        reading.reading_type_id,
                        fetched_at,
                    ),
                )
                cur.execute(
                    "DELETE FROM boditrax.metrics WHERE reading_id = %s", (reading.reading_id,)
                )
                rows = [
                    (reading.reading_id, name, value, METRIC_UNITS.get(name, ""))
                    for name, value in reading.metrics.items()
                ]
                cur.executemany(
                    "INSERT INTO boditrax.metrics (reading_id, metric, value, unit)"
                    " VALUES (%s, %s, %s, %s)",
                    rows,
                )
                metrics_written += len(rows)
        self.conn.commit()
        return SyncResult(
            readings_fetched=len(readings),
            new_readings=sum(1 for reading in readings if reading.reading_id not in existing),
            metrics_written=metrics_written,
        )

    def close(self) -> None:
        self.conn.close()
