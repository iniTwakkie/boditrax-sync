"""Boditrax mobile API client (gRPC-web + protobuf).

The Boditrax 2.0 app talks gRPC-web to ``mobile.api.boditrax.cloud``. The
client authenticates with the app's OAuth password grant (client id
``boditrax.mobile.app``) and pulls every reading via ``SyncLoginService/Get``.

Protocol reverse-engineered from Boditrax 2.0 v3.1.1 and verified against the
app's own CSV export (340/340 values identical, 2026-10-14).
"""

from __future__ import annotations

import base64
import logging
import os
import struct
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from .metrics import METRICS
from .models import Reading
from .proto import enc_bool, enc_str, frame, parse_frames, pb_decode

logger = logging.getLogger(__name__)

API_BASE = "https://mobile.api.boditrax.cloud"
PATH_AUTH = "/boditrax.shared.api.contract.service.MobileApi.IdentityService/Authenticate"
PATH_SYNC = "/boditrax.shared.api.contract.service.MobileApi.SyncLoginService/Get"

CLIENT_ID = "boditrax.mobile.app"
# Client secret shipped inside the Boditrax 2.0 mobile app (extractable from the
# public app binary). Not a user secret; override with BODITRAX_CLIENT_SECRET if
# Boditrax ever rotates it.
DEFAULT_CLIENT_SECRET = "YYDjpolvHrv2wmZkSwPRwsPFHgIa6q"

# Fetch every reading from the account: from the year 2000 until now.
SYNC_REQUEST = (
    enc_str(1, "a20b7e6e-f439-4f4c-a915-b026a1ee9911")
    + enc_bool(2, True)
    + enc_str(3, "01-01-2000 00:00:00")
    + enc_bool(5, True)
)

DEFAULT_TIMEZONE = "Europe/London"


class BoditraxError(RuntimeError):
    """Raised for API-level failures (HTTP errors, rejected requests)."""


class BoditraxClient:
    """Minimal client for the Boditrax mobile API."""

    def __init__(
        self,
        username: str,
        password: str,
        client_secret: str | None = None,
        timezone: str = DEFAULT_TIMEZONE,
        timeout: float = 30,
    ) -> None:
        self.username = username
        self.password = password
        self.client_secret = (
            client_secret or os.environ.get("BODITRAX_CLIENT_SECRET") or DEFAULT_CLIENT_SECRET
        )
        self.timezone = ZoneInfo(timezone)
        self.timeout = timeout

    # ------------------------------------------------------------ protocol

    def _call(self, path: str, payload: bytes, metadata: dict[str, str]) -> dict:
        headers = {"content-type": "application/grpc-web+proto", "x-grpc-web": "1"}
        headers.update(metadata)
        try:
            resp = requests.post(
                API_BASE + path, data=frame(payload), headers=headers, timeout=self.timeout
            )
        except requests.RequestException as exc:
            raise BoditraxError(f"{path}: {exc}") from exc
        if resp.status_code != 200:
            raise BoditraxError(f"{path}: HTTP {resp.status_code}")
        frames = parse_frames(resp.content)
        if not frames:
            raise BoditraxError(f"{path}: empty gRPC response")
        message = pb_decode(frames[0])
        if message.get(2, [(0, 0)])[0][1] != 1:
            raise BoditraxError(f"{path}: request failed (error={message.get(4)})")
        return message

    # ------------------------------------------------------------ public API

    def authenticate(self) -> str:
        """Log in and return a bearer token."""
        if not self.client_secret:
            raise BoditraxError(
                "Boditrax client secret missing: set BODITRAX_CLIENT_SECRET to the "
                "secret bundled with the Boditrax 2.0 mobile app"
            )
        message = self._call(
            PATH_AUTH,
            b"",
            {
                "client_id": CLIENT_ID,
                "client_secret": self.client_secret,
                "grant_type": "password",
                "username": self.username,
                "password": base64.b64encode(self.password.encode()).decode(),
                "encoded": "1",
            },
        )
        auth = pb_decode(message[1][0][1])
        token = auth[1][0][1].decode()
        expires = auth[2][0][1].decode() if 2 in auth else "unknown"
        logger.info("authenticated as %s (token expires %s)", self.username, expires)
        return token

    def fetch_readings(self) -> list[Reading]:
        """Fetch every reading on the account, oldest first, with named metrics."""
        token = self.authenticate()
        message = self._call(PATH_SYNC, SYNC_REQUEST, {"authorization": "Bearer " + token})
        inner = pb_decode(message[1][0][1])

        readings: list[Reading] = []
        for _, raw_reading in inner.get(5, []):
            r = pb_decode(raw_reading)
            metrics: dict[str, float] = {}
            for _, raw_metric in r.get(6, []):
                m = pb_decode(raw_metric)
                metric_id = m[1][0][1] if 1 in m else 0
                value = _metric_value(m)
                name = METRICS.get(metric_id, (f"Unknown_{metric_id}", ""))[0]
                metrics[name] = round(value, 2)
            readings.append(
                Reading(
                    reading_id=r[1][0][1].decode(),
                    kiosk_id=r[2][0][1].decode() if 2 in r else None,
                    device_type_id=r[3][0][1] if 3 in r else None,
                    recorded_at=datetime.strptime(
                        r[4][0][1].decode(), "%d-%m-%Y %H:%M:%S"
                    ).replace(tzinfo=self.timezone),
                    reading_type_id=r[5][0][1] if 5 in r else None,
                    metrics=metrics,
                )
            )
        readings.sort(key=lambda reading: reading.recorded_at)
        return readings


def _metric_value(metric: dict) -> float:
    """Decode metric field 2, which may be protobuf float (4-byte) or double (8-byte)."""
    if 2 not in metric:
        return 0.0
    wire, raw = metric[2][0]
    if wire == 5:
        return struct.unpack("<f", raw)[0]
    if wire == 1:
        return struct.unpack("<d", raw)[0]
    raise BoditraxError(f"unexpected wire type {wire} for metric value")
