"""
ZMQ Codec — DataEnvelope ↔ ZMQ multipart dönüşümü.

Format:
    Frame 0: topic (bytes)        → "iq" | "fft" | "waterfall" | "detections"
    Frame 1: header_json (bytes)  → JSON metadata
    Frame 2: payload (bytes)      → numpy tobytes()

Bu modül PySide6-bağımsızdır; saf Python + numpy + json.
"""

from __future__ import annotations

import json

import numpy as np

from ehcore.contracts import DataEnvelope

# data_type → ZMQ topic eşlemesi
_TYPE_TO_TOPIC = {
    "iq_block": b"iq",
    "fft_frame": b"fft",
    "waterfall_row": b"waterfall",
    "detections": b"detections",
}

_TOPIC_TO_TYPE = {v: k for k, v in _TYPE_TO_TOPIC.items()}


def zmq_encode(envelope: DataEnvelope) -> list[bytes]:
    """
    DataEnvelope'u ZMQ multipart mesajına dönüştür.

    Returns:
        [topic, header_json, payload_bytes]
    """
    topic = _TYPE_TO_TOPIC.get(envelope.data_type, envelope.data_type.encode())
    header = json.dumps(envelope.to_dict(), ensure_ascii=False).encode("utf-8")
    payload = envelope.payload.tobytes()

    return [topic, header, payload]


def zmq_decode(frames: list[bytes]) -> DataEnvelope:
    """
    ZMQ multipart mesajını DataEnvelope'a dönüştür.

    Args:
        frames: [topic, header_json, payload_bytes]

    Returns:
        DataEnvelope

    Raises:
        ValueError: Geçersiz frame sayısı veya format.
    """
    if len(frames) != 3:
        raise ValueError(f"ZMQ mesajı 3 parça olmalı, {len(frames)} alındı.")

    topic, header_bytes, payload_bytes = frames

    # Header parse
    header = json.loads(header_bytes.decode("utf-8"))

    # data_type belirle
    data_type = _TOPIC_TO_TYPE.get(topic, header.get("data_type", "iq_block"))

    # Payload → numpy array
    dtype_str = header.get("dtype", "complex64")
    shape = tuple(header.get("shape", [len(payload_bytes) // np.dtype(dtype_str).itemsize]))
    payload = np.frombuffer(payload_bytes, dtype=dtype_str).reshape(shape)

    return DataEnvelope(
        data_type=data_type,
        payload=payload.copy(),  # Kendi belleğine sahip olsun
        timestamp=header.get("timestamp", 0.0),
        source_id=header.get("source_id", ""),
        center_freq=header.get("center_freq", 0.0),
        sample_rate=header.get("sample_rate", 0.0),
        dtype=dtype_str,
        shape=shape,
        metadata=header.get("metadata", {}),
    )
