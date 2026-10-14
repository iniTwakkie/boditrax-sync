"""Wire-codec round-trip tests."""

from __future__ import annotations

import gzip
import struct

from boditrax_sync.proto import (
    enc_bool,
    enc_str,
    enc_varint,
    frame,
    parse_frames,
    pb_decode,
    read_varint,
)


def test_varint_roundtrip() -> None:
    for number in [0, 1, 127, 128, 300, 16384, 2**35]:
        encoded = enc_varint(number)
        assert read_varint(encoded, 0) == (number, len(encoded))


def test_frame_roundtrip() -> None:
    payload = b"hello boditrax"
    assert parse_frames(frame(payload)) == [payload]


def test_gzip_frame() -> None:
    payload = b"compressed"
    compressed = gzip.compress(payload)
    body = b"\x01" + struct.pack(">I", len(compressed)) + compressed
    assert parse_frames(body) == [payload]


def test_parse_frames_ignores_trailing_garbage() -> None:
    assert parse_frames(b"\x00\x00") == []


def test_pb_decode_strings_and_varints() -> None:
    data = enc_str(1, "abc") + enc_bool(2, True) + enc_str(3, "x" * 200)
    decoded = pb_decode(data)
    assert decoded[1][0][1] == b"abc"
    assert decoded[2][0][1] == 1
    assert len(decoded[3][0][1]) == 200


def test_pb_decode_float32_and_double() -> None:
    data = bytes([2 << 3 | 5]) + struct.pack("<f", 75.5)
    data += bytes([3 << 3 | 1]) + struct.pack("<d", 101.3)
    decoded = pb_decode(data)
    wire_f, raw_f = decoded[2][0]
    wire_d, raw_d = decoded[3][0]
    assert wire_f == 5 and wire_d == 1
    assert struct.unpack("<f", raw_f)[0] == 75.5
    assert struct.unpack("<d", raw_d)[0] == 101.3
