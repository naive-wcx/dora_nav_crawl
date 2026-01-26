"""TODO: Add docstring."""

import json
import os

import numpy as np
import pyarrow as pa
from dora import Node

node = Node()

IMAGE_RESIZE_RATIO = float(os.getenv("IMAGE_RESIZE_RATIO", "1.0"))


def extract_bboxes(json_text):
    """Extract bounding boxes from a JSON string with markdown markers and return them as a NumPy array.

    Parameters
    ----------
    json_text : str
        JSON string containing bounding box data, including ```json markers.

    Returns
    -------
    np.ndarray: NumPy array of bounding boxes.

    """
    # Ensure all lines are stripped of whitespace and markers
    lines = json_text.strip().splitlines()

    # Filter out lines that are markdown markers
    clean_lines = [line for line in lines if not line.strip().startswith("```")]

    # Join the lines back into a single string
    clean_text = "\n".join(clean_lines)
    # Parse the cleaned JSON text
    try:
        data = json.loads(clean_text)

        # Extract bounding boxes
        bboxes = [item["bbox_2d"] for item in data]
        labels = [item["label"] for item in data]

        return np.array(bboxes), np.array(labels)
    except Exception as _e:  # noqa
        pass
    return None, None


for event in node:
    if event["type"] == "INPUT":
        text = event["value"][0].as_py()
        image_id = event["metadata"]["image_id"]
        
        print("===== parse_bbox 接收到的文本 =====")
        print(text)
        print("=================================")

        bboxes, labels = extract_bboxes(text)
        if bboxes is not None and len(bboxes) > 0:
            print(f"成功提取边界框: {bboxes}")
            print(f"标签: {labels}")
            bboxes = bboxes * int(1 / IMAGE_RESIZE_RATIO)
            if "human" in labels[0] or "head" in labels[0]:
                print(f"发送人脸边界框: {bboxes}")
                node.send_output(
                    "bbox_face",
                    pa.array(bboxes.ravel()),
                    metadata={"encoding": "xyxy", "image_id": image_id},
                )
            else:
                print(f"发送物体边界框: {bboxes}")
                print(f"边界框标签: {labels}")
                node.send_output(
                    "bbox",
                    pa.array(bboxes.ravel()),
                    metadata={"encoding": "xyxy", "image_id": image_id},
                )
        else:
            print("未能提取到边界框，可能原因：")
            print("1. 文本不包含有效的JSON数据")
            print("2. JSON数据格式不正确")
            print("3. 未识别到物体")
