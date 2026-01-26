"""Receive RealSense frames over TCP and publish to Dora."""

import os
import pickle
import socket
import struct
import sys
import time

import numpy as np
import pyarrow as pa
from dora import Node

MAGIC = 0xABCD1234
HEADER_FORMAT = "!IIQ"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _recv_exact(conn: socket.socket, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        chunk = conn.recv(size - len(data))
        if not chunk:
            raise ConnectionError("Connection closed")
        data.extend(chunk)
    return bytes(data)


def _accept_connection(server: socket.socket) -> socket.socket:
    conn, addr = server.accept()
    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    print(f"[camera-net] Connected by {addr}")
    return conn


def _decode_payload(metadata: dict, data_bytes: bytes) -> tuple[str, np.ndarray]:
    if "encoding" in metadata:
        width = int(metadata["width"])
        height = int(metadata["height"])
        expected = width * height * 3
        buffer = np.frombuffer(data_bytes, dtype=np.uint8)
        if buffer.size < expected:
            raise ValueError("image payload too small")
        frame = buffer[:expected]
        return "image_depth", frame

    width = int(metadata["width"])
    height = int(metadata["height"])
    expected = width * height
    buffer = np.frombuffer(data_bytes, dtype=np.float64)
    if buffer.size < expected:
        raise ValueError("depth payload too small")
    frame = buffer[:expected]
    return "depth", frame


def main() -> None:
    host = os.getenv("TCP_LISTEN_HOST", "0.0.0.0")
    port = _env_int("TCP_LISTEN_PORT", 5002)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(1)
    print(f"[camera-net] Listening on {host}:{port}")

    node = Node()

    while True:
        conn = None
        try:
            conn = _accept_connection(server)
            while True:
                header = _recv_exact(conn, HEADER_SIZE)
                magic, meta_len, data_len = struct.unpack(HEADER_FORMAT, header)
                if magic != MAGIC:
                    raise ValueError(f"Invalid magic: {hex(magic)}")

                metadata_bytes = _recv_exact(conn, meta_len)
                metadata = pickle.loads(metadata_bytes)

                payload = _recv_exact(conn, data_len)
                event_id, frame = _decode_payload(metadata, payload)

                # print(f"[camera-net] Received {event_id} frame\n\n\n")

                node.send_output(
                    event_id,
                    pa.array(frame),
                    metadata=metadata,
                )
        except KeyboardInterrupt:
            print("[camera-net] Shutting down")
            break
        except Exception as exc:
            print(f"[camera-net] Connection error: {exc}")
            time.sleep(1.0)
        finally:
            if conn is not None:
                try:
                    conn.close()
                except OSError:
                    pass


if __name__ == "__main__":
    sys.exit(main())
