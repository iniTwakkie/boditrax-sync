"""Shared test fixtures."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from boditrax_sync.models import Reading

TZ = ZoneInfo("Europe/London")


@pytest.fixture
def sample_readings() -> list[Reading]:
    return [
        Reading(
            reading_id="reading-1",
            recorded_at=datetime(2025, 8, 7, 17, 30, tzinfo=TZ),
            kiosk_id="kiosk-1",
            device_type_id=7,
            reading_type_id=1,
            metrics={
                "BodyWeight": 100.3,
                "MuscleMass": 75.1,
                "FatMass": 21.3,
                "VisceralFatRating": 7.0,
                "BodyMassIndex": 26.7,
                "MetabolicAge": 35.0,
                "BoditraxScore": 731.0,
            },
        ),
        Reading(
            reading_id="reading-2",
            recorded_at=datetime(2026, 1, 10, 9, 15, tzinfo=TZ),
            kiosk_id="kiosk-1",
            device_type_id=7,
            reading_type_id=1,
            metrics={
                "BodyWeight": 101.0,
                "MuscleMass": 74.9,
                "FatMass": 22.2,
                "VisceralFatRating": 8.0,
                "BodyMassIndex": 26.8,
                "MetabolicAge": 37.0,
                "BoditraxScore": 722.0,
            },
        ),
    ]
