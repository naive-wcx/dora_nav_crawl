"""RealSense Dora node that publishes color + depth frames."""

import atexit
import os

import numpy as np
import pyarrow as pa
import pyrealsense2 as rs
from dora import Node


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def main() -> None:
    width = _env_int("COLOR_WIDTH", 640)
    height = _env_int("COLOR_HEIGHT", 480)
    fps = _env_int("FPS", 15)
    warmup_frames = _env_int("WARMUP_FRAMES", 15)
    timeout_ms = _env_int("FRAME_TIMEOUT_MS", 1000)

    node = Node()
    pipeline = rs.pipeline()
    config = rs.config()

    config.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)
    config.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)

    try:
        profile = pipeline.start(config)
    except Exception as exc:
        raise RuntimeError(f"Failed to start RealSense pipeline: {exc}") from exc

    atexit.register(pipeline.stop)

    align = rs.align(rs.stream.color)
    depth_sensor = profile.get_device().first_depth_sensor()
    depth_scale = depth_sensor.get_depth_scale()

    color_profile = profile.get_stream(rs.stream.color).as_video_stream_profile()
    color_intrinsics = color_profile.get_intrinsics()
    focal = [int(round(color_intrinsics.fx)), int(round(color_intrinsics.fy))]
    resolution = [int(round(color_intrinsics.ppx)), int(round(color_intrinsics.ppy))]

    for _ in range(warmup_frames):
        try:
            pipeline.wait_for_frames(timeout_ms)
        except Exception:
            return

    for event in node:
        if event["type"] != "INPUT" or event["id"] != "tick":
            continue

        try:
            frames = pipeline.wait_for_frames(timeout_ms)
            frames = align.process(frames)
        except Exception:
            continue

        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()
        if color_frame is None or depth_frame is None:
            continue

        color_image = np.asanyarray(color_frame.get_data())
        color_image = np.ascontiguousarray(color_image)
        node.send_output(
            "image_depth",
            pa.array(color_image.ravel()),
            metadata={
                "encoding": "bgr8",
                "width": color_frame.get_width(),
                "height": color_frame.get_height(),
            },
        )

        depth_raw = np.asanyarray(depth_frame.get_data())
        depth_meters = depth_raw.astype(np.float64) * depth_scale
        depth_meters = np.ascontiguousarray(depth_meters)
        node.send_output(
            "depth",
            pa.array(depth_meters.ravel()),
            metadata={
                "width": depth_frame.get_width(),
                "height": depth_frame.get_height(),
                "focal": focal,
                "resolution": resolution,
            },
        )


if __name__ == "__main__":
    main()
