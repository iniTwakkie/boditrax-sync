"""API client tests against synthetic gRPC-web responses (no network)."""

from __future__ import annotations

import struct

import pytest

from boditrax_sync import api
from boditrax_sync.api import BoditraxClient, BoditraxError
from boditrax_sync.proto import enc_varint, frame


def _field_int(field: int, value: int) -> bytes:
    return bytes([field << 3]) + enc_varint(value)


def _field_bytes(field: int, value: bytes) -> bytes:
    return bytes([field << 3 | 2]) + enc_varint(len(value)) + value


def _field_float(field: int, value: float) -> bytes:
    return bytes([field << 3 | 5]) + struct.pack("<f", value)


def _field_double(field: int, value: float) -> bytes:
    return bytes([field << 3 | 1]) + struct.pack("<d", value)


AUTH_INNER = _field_bytes(1, b"token-123") + _field_bytes(2, b"2026-01-01T00:00:00Z")

READING_ONE = (
    _field_bytes(1, b"rid-1")
    + _field_bytes(2, b"kiosk-9")
    + _field_int(3, 7)
    + _field_bytes(4, b"07-08-2025 17:30:00")
    + _field_int(5, 1)
    + _field_bytes(6, _field_int(1, 1) + _field_float(2, 100.3))
    + _field_bytes(6, _field_int(1, 12) + _field_float(2, 7.0))
)

READING_TWO = (
    _field_bytes(1, b"rid-2")
    + _field_int(3, 7)
    + _field_bytes(4, b"10-01-2026 09:15:00")
    + _field_int(5, 1)
    + _field_bytes(6, _field_int(1, 1) + _field_double(2, 101.0))
)

SYNC_INNER = _field_bytes(5, READING_ONE) + _field_bytes(5, READING_TWO)


class _FakeResponse:
    def __init__(self, payload: bytes, status_code: int = 200) -> None:
        self.status_code = status_code
        self.content = frame(payload)


def _ok(inner: bytes) -> _FakeResponse:
    return _FakeResponse(_field_bytes(1, inner) + _field_int(2, 1))


def _fake_post(url, data=None, headers=None, timeout=None):
    if url.endswith("IdentityService/Authenticate"):
        return _ok(AUTH_INNER)
    if url.endswith("SyncLoginService/Get"):
        assert "Bearer token-123" in (headers or {}).get("authorization", "")
        return _ok(SYNC_INNER)
    raise AssertionError(f"unexpected call: {url}")


def _client() -> BoditraxClient:
    return BoditraxClient("user@example.com", "pw", client_secret="test-secret")


def test_fetch_readings(monkeypatch) -> None:
    monkeypatch.setattr(api.requests, "post", _fake_post)
    readings = _client().fetch_readings()

    assert [reading.reading_id for reading in readings] == ["rid-1", "rid-2"]
    assert readings[0].metrics["BodyWeight"] == 100.3
    assert readings[0].metrics["VisceralFatRating"] == 7.0
    # second reading uses the double wire type; both must decode
    assert readings[1].metrics["BodyWeight"] == 101.0
    assert readings[0].kiosk_id == "kiosk-9"
    assert readings[1].kiosk_id is None
    assert readings[1].device_type_id == 7
    assert readings[1].recorded_at.utcoffset() is not None


def test_request_failure_raises(monkeypatch) -> None:
    failure = _field_bytes(1, AUTH_INNER) + _field_int(2, 0)
    monkeypatch.setattr(api.requests, "post", lambda *a, **k: _FakeResponse(failure))
    with pytest.raises(BoditraxError, match="request failed"):
        _client().authenticate()


def test_http_error_raises(monkeypatch) -> None:
    monkeypatch.setattr(api.requests, "post", lambda *a, **k: _FakeResponse(b"", status_code=500))
    with pytest.raises(BoditraxError, match="HTTP 500"):
        _client().authenticate()


def test_missing_client_secret(monkeypatch) -> None:
    monkeypatch.delenv("BODITRAX_CLIENT_SECRET", raising=False)
    monkeypatch.setattr(api, "DEFAULT_CLIENT_SECRET", "")
    client = BoditraxClient("user@example.com", "pw")
    with pytest.raises(BoditraxError, match="client secret missing"):
        client.authenticate()
