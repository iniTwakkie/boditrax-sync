"""JSON, CSV and terminal-table renderers for fetched readings."""

from __future__ import annotations

import csv
import io
import json

from .metrics import METRIC_COLUMNS
from .models import Reading

IDENTITY_COLUMNS = ["reading_id", "recorded_at", "kiosk_id", "device_type_id", "reading_type_id"]

# Compact column set for the terminal table view.
TABLE_METRICS = [
    ("BodyWeight", "Weight kg"),
    ("MuscleMass", "Muscle kg"),
    ("FatMass", "Fat kg"),
    ("VisceralFatRating", "Visceral"),
    ("BodyMassIndex", "BMI"),
    ("MetabolicAge", "Meta age"),
    ("BoditraxScore", "Score"),
]


def reading_to_dict(reading: Reading) -> dict:
    return {
        "reading_id": reading.reading_id,
        "recorded_at": reading.recorded_at.isoformat(),
        "kiosk_id": reading.kiosk_id,
        "device_type_id": reading.device_type_id,
        "reading_type_id": reading.reading_type_id,
        "metrics": reading.metrics,
    }


def to_json(readings: list[Reading]) -> str:
    return json.dumps([reading_to_dict(reading) for reading in readings], indent=2) + "\n"


def to_csv(readings: list[Reading]) -> str:
    """Wide CSV: one row per reading, one column per metric (BodyMetricTypeId order)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([*IDENTITY_COLUMNS, *METRIC_COLUMNS])
    for reading in readings:
        writer.writerow(
            [
                reading.reading_id,
                reading.recorded_at.isoformat(),
                reading.kiosk_id,
                reading.device_type_id,
                reading.reading_type_id,
                *[_format_value(reading.metrics.get(name), missing="") for name in METRIC_COLUMNS],
            ]
        )
    return buf.getvalue()


def to_table(readings: list[Reading]) -> str:
    if not readings:
        return "No readings found.\n"
    headers = ["Date", *[label for _, label in TABLE_METRICS]]
    rows = [
        [
            reading.recorded_at.date().isoformat(),
            *[_format_value(reading.metrics.get(name)) for name, _ in TABLE_METRICS],
        ]
        for reading in readings
    ]
    widths = [
        max(len(headers[column]), *(len(row[column]) for row in rows))
        for column in range(len(headers))
    ]
    lines = [
        "  ".join(header.ljust(width) for header, width in zip(headers, widths, strict=True))
    ]
    lines += [
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True))
        for row in rows
    ]
    return "\n".join(lines) + "\n"


def _format_value(value: float | None, missing: str = "-") -> str:
    if value is None:
        return missing
    return f"{value:g}"
