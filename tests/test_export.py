"""Export renderer tests."""

from __future__ import annotations

import csv
import io
import json

from boditrax_sync.export import to_csv, to_json, to_table
from boditrax_sync.models import Reading


def test_csv_is_wide_and_ordered(sample_readings: list[Reading]) -> None:
    rows = list(csv.reader(io.StringIO(to_csv(sample_readings))))
    header, body = rows[0], rows[1:]
    assert header[:5] == [
        "reading_id",
        "recorded_at",
        "kiosk_id",
        "device_type_id",
        "reading_type_id",
    ]
    assert "BodyWeight" in header
    assert "BoditraxScore" in header
    assert len(body) == 2

    weight_column = header.index("BodyWeight")
    assert body[1][weight_column] == "101"
    # a metric absent from a reading is left blank
    assert body[1][header.index("HDLLevel")] == ""


def test_json_structure(sample_readings: list[Reading]) -> None:
    data = json.loads(to_json(sample_readings))
    assert [item["reading_id"] for item in data] == ["reading-1", "reading-2"]
    assert data[1]["metrics"]["BodyWeight"] == 101.0
    assert data[0]["recorded_at"].startswith("2025-08-07")
    assert data[0]["kiosk_id"] == "kiosk-1"


def test_table_contains_key_values(sample_readings: list[Reading]) -> None:
    text = to_table(sample_readings)
    assert "Date" in text
    assert "2026-01-10" in text
    assert "101" in text


def test_table_empty() -> None:
    assert to_table([]) == "No readings found.\n"
