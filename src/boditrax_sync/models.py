"""Data model for a Boditrax scan."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Reading:
    """One body-composition scan with its metric values."""

    reading_id: str
    recorded_at: datetime
    metrics: dict[str, float] = field(default_factory=dict)
    kiosk_id: str | None = None
    device_type_id: int | None = None
    reading_type_id: int | None = None
