"""Send RealSense color + depth frames to a TCP server."""

import argparse
import os
import pickle
import socket
import struct
import sys
import time

import numpy as np
import pyrealsense2 as rs

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


def _env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value else default


def _connect(host: str, port: int) -> socket.socket:
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.connect((host, port))
            print(f"[sender] Connected to {host}:{port}")
            return sock
        except Exception as exc:
            print(f"[sender] اتصال失败: {exc}, 2 秒后重试")
            time.sleep(2)


def _send_packet(sock: socket.socket, metadata: dict, data: bytes) -> None:
    meta_bytes = pickle.dumps(metadata)
    header = struct.pack(HEADER_FORMAT, MAGIC, len(meta_bytes), len(data))
    sock.sendall(header + meta_bytes + data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send RealSense frames over TCP")
    parser.add_argument("--host", default=_env_str("TCP_SERVER_IP", "192.168.1.122"))
    parser.add_argument("--port", type=int, default=_env_int("TCP_SERVER_PORT", 5002))
    parser.add_argument("--width", type=int, default=_env_int("COLOR_WIDTH", 640))
    parser.add_argument("--height", type=int, default=_env_int("COLOR_HEIGHT", 480))
    parser.add_argument("--fps", type=int, default=_env_int("FPS", 15))
    parser.add_argument("--warmup", type=int, default=_env_int("WARMUP_FRAMES", 15))
    parser.add_argument("--timeout", type=int, default=_env_int("FRAME_TIMEOUT_MS", 1000))
    args = parser.parse_args()

    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, args.width, args.height, rs.format.bgr8, args.fps)
    config.enable_stream(rs.stream.depth, args.width, args.height, rs.format.z16, args.fps)

    try:
        profile = pipeline.start(config)
    except Exception as exc:
        print(f"[sender] 启动 RealSense 失败: {exc}")
        return 1

    align = rs.align(rs.stream.color)
    depth_sensor = profile.get_device().first_depth_sensor()
    depth_scale = depth_sensor.get_depth_scale()

    color_profile = profile.get_stream(rs.stream.color).as_video_stream_profile()
    color_intrinsics = color_profile.get_intrinsics()
    focal = [int(round(color_intrinsics.fx)), int(round(color_intrinsics.fy))]
    resolution = [int(round(color_intrinsics.ppx)), int(round(color_intrinsics.ppy))]

    for _ in range(args.warmup):
        try:
            pipeline.wait_for_frames(args.timeout)
        except Exception:
            break

    sock = _connect(args.host, args.port)

    try:
        while True:
            try:
                frames = pipeline.wait_for_frames(args.timeout)
                frames = align.process(frames)
            except Exception:
                continue

            color_frame = frames.get_color_frame()
            depth_frame = frames.get_depth_frame()
            if color_frame is None or depth_frame is None:
                continue

            color_image = np.asanyarray(color_frame.get_data())
            color_image = np.ascontiguousarray(color_image)
            color_meta = {
                "encoding": "bgr8",
                "width": color_frame.get_width(),
                "height": color_frame.get_height(),
            }
            _send_packet(sock, color_meta, color_image.tobytes())

            depth_raw = np.asanyarray(depth_frame.get_data())
            depth_meters = depth_raw.astype(np.float64) * depth_scale
            depth_meters = np.ascontiguousarray(depth_meters)
            depth_meta = {
                "width": depth_frame.get_width(),
                "height": depth_frame.get_height(),
                "focal": focal,
                "resolution": resolution,
            }
            _send_packet(sock, depth_meta, depth_meters.tobytes())

    except KeyboardInterrupt:
        print("[sender] 退出")
    except Exception as exc:
        print(f"[sender] 发送失败: {exc}")
    finally:
        try:
            sock.close()
        except Exception:
            pass
        pipeline.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
