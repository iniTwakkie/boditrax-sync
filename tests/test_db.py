"""Database sync tests (SQLite always, PostgreSQL when a test URL is configured)."""

from __future__ import annotations

import os
import sqlite3

import pytest

from boditrax_sync.db import SyncResult, connect
from boditrax_sync.models import Reading

PG_URL = os.environ.get("BODITRAX_TEST_POSTGRES_URL")


def _total_metrics(readings: list[Reading]) -> int:
    return sum(len(reading.metrics) for reading in readings)


def test_unsupported_url() -> None:
    with pytest.raises(ValueError):
        connect("mysql://nope")


def test_sqlite_sync_roundtrip(tmp_path, sample_readings: list[Reading]) -> None:
    db_file = tmp_path / "boditrax.db"
    db = connect(f"sqlite://{db_file}")
    try:
        first = db.upsert_readings(sample_readings)
        second = db.upsert_readings(sample_readings)
    finally:
        db.close()

    assert first == SyncResult(
        readings_fetched=2, new_readings=2, metrics_written=_total_metrics(sample_readings)
    )
    assert second == SyncResult(
        readings_fetched=2, new_readings=0, metrics_written=_total_metrics(sample_readings)
    )

    conn = sqlite3.connect(db_file)
    try:
        assert conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM metrics").fetchone()[0] == _total_metrics(
            sample_readings
        )
        weight, unit = conn.execute(
            "SELECT value, unit FROM metrics"
            " WHERE reading_id = 'reading-2' AND metric = 'BodyWeight'"
        ).fetchone()
        assert weight == 101.0
        assert unit == "kg"
        recorded_at = conn.execute(
            "SELECT recorded_at FROM readings WHERE reading_id = 'reading-2'"
        ).fetchone()[0]
        assert recorded_at.startswith("2026-01-10")
    finally:
        conn.close()


def test_sqlite_detects_new_readings(tmp_path, sample_readings: list[Reading]) -> None:
    db = connect(f"sqlite://{tmp_path}/boditrax.db")
    try:
        db.upsert_readings(sample_readings)
        extra = Reading(
            reading_id="reading-3",
            recorded_at=sample_readings[-1].recorded_at,
            metrics={"BodyWeight": 99.9},
        )
        result = db.upsert_readings([*sample_readings, extra])
        assert result.new_readings == 1
        assert result.metrics_written == _total_metrics(sample_readings) + 1
    finally:
        db.close()


@pytest.mark.skipif(not PG_URL, reason="BODITRAX_TEST_POSTGRES_URL not set")
def test_postgres_sync_roundtrip(sample_readings: list[Reading]) -> None:
    import psycopg

    with psycopg.connect(PG_URL) as conn:
        conn.execute("DROP SCHEMA IF EXISTS boditrax CASCADE")
        conn.commit()

    try:
        db = connect(PG_URL)
        try:
            first = db.upsert_readings(sample_readings)
            second = db.upsert_readings(sample_readings)
        finally:
            db.close()

        assert first.new_readings == 2
        assert second.new_readings == 0

        with psycopg.connect(PG_URL) as conn:
            count = conn.execute("SELECT COUNT(*) FROM boditrax.metrics").fetchone()[0]
            assert count == _total_metrics(sample_readings)
            value = conn.execute(
                "SELECT value FROM boditrax.metrics"
                " WHERE reading_id = 'reading-2' AND metric = 'BodyWeight'"
            ).fetchone()[0]
            assert value == 101.0
    finally:
        with psycopg.connect(PG_URL) as conn:
            conn.execute("DROP SCHEMA IF EXISTS boditrax CASCADE")
            conn.commit()
