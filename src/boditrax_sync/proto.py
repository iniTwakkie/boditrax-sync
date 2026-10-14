"""Minimal gRPC-web + protobuf wire codec with no protobuf dependency.

The Boditrax mobile API speaks gRPC-web with protobuf payloads. Only a handful
of message shapes are needed, so this module implements just enough of the wire
format: length-prefixed gRPC-web frames (with gzip support) and the protobuf
wire types used by the API (varint, 64-bit, length-delimited, 32-bit).
"""

from __future__ import annotations

import gzip
import struct


def frame(payload: bytes) -> bytes:
    """Wrap a protobuf message in a gRPC-web data frame."""
    return b"\x00" + struct.pack(">I", len(payload)) + payload


def parse_frames(body: bytes) -> list[bytes]:
    """Split a gRPC-web response body into its protobuf messages."""
    out: list[bytes] = []
    i = 0
    while i + 5 <= len(body):
        flag = body[i]
        length = struct.unpack(">I", body[i + 1 : i + 5])[0]
        data = body[i + 5 : i + 5 + length]
        if flag & 0x01:
            data = gzip.decompress(data)
        out.append(data)
        i += 5 + length
    return out


def read_varint(data: bytes, i: int) -> tuple[int, int]:
    """Read a base-128 varint at offset ``i``; returns (value, new_offset)."""
    shift = 0
    value = 0
    while True:
        if i >= len(data):
            raise ValueError("truncated varint")
        byte = data[i]
        i += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, i
        shift += 7


def pb_decode(data: bytes) -> dict[int, list[tuple[int, object]]]:
    """Decode a protobuf message into ``{field: [(wire_type, value), ...]}``.

    Values are ints for varint fields and bytes for all other wire types.
    """
    out: dict[int, list[tuple[int, object]]] = {}
    i = 0
    while i < len(data):
        key, i = read_varint(data, i)
        field, wire = key >> 3, key & 7
        if wire == 0:
            value, i = read_varint(data, i)
        elif wire == 1:
            if i + 8 > len(data):
                raise ValueError(f"truncated 64-bit field {field}")
            value = data[i : i + 8]
            i += 8
        elif wire == 2:
            length, i = read_varint(data, i)
            if i + length > len(data):
                raise ValueError(f"truncated length-delimited field {field}")
            value = data[i : i + length]
            i += length
        elif wire == 5:
            if i + 4 > len(data):
                raise ValueError(f"truncated 32-bit field {field}")
            value = data[i : i + 4]
            i += 4
        else:
            raise ValueError(f"unsupported protobuf wire type {wire} (field {field})")
        out.setdefault(field, []).append((wire, value))
    return out


def enc_varint(n: int) -> bytes:
    """Encode a base-128 varint."""
    out = b""
    while True:
        byte = n & 0x7F
        n >>= 7
        out += bytes([byte | 0x80]) if n else bytes([byte])
        if not n:
            return out


def enc_str(field: int, value: str) -> bytes:
    """Encode a length-delimited string field."""
    raw = value.encode()
    return bytes([field << 3 | 2]) + enc_varint(len(raw)) + raw


def enc_bool(field: int, value: bool) -> bytes:
    """Encode a varint boolean field."""
    return bytes([field << 3]) + (b"\x01" if value else b"\x00")
