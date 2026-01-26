"""TODO: Add docstring."""

# State Machine
import json
import os
import time

import numpy as np
import pyarrow as pa
from dora import Node

IMAGE_RESIZE_RATIO = float(os.getenv("IMAGE_RESIZE_RATIO", "1.0"))
node = Node()

ACTIVATION_WORDS = os.getenv("ACTIVATION_WORDS", "").split()
TABLE_HEIGHT = float(os.getenv("TABLE_HEIGHT", "-0.41"))

# ADora max视角
# r_init_pose = [157.47799682617188, -73.1780014038086, 66.6729965209961, 57.86199951171875, 94.26499938964844, -171.822998046875,100]
r_init_pose = [-3.947999954223633, 87.58499908447266, -64.58899688720703, 3.7909998893737793, -108.41699981689453, 88.95899963378906, 100]
#Single_desktop视角
# r_init_pose = [71.001, 70.028, 99.441, -69.270, 102.877, -5.533, 100]


# ADora max视角
# r_init_middle = [
#     156.772,
#     -24.730,
#     -62.480,
#     80.768,
#     125.439,
#     -91.649,
#     0,
# ]
r_init_middle = [-3.947999954223633, 87.58499908447266, -64.58899688720703, 3.7909998893737793, -108.41699981689453, 88.95899963378906, 0]

#Single_desktop视角
# r_init_middle = [
#     25.125,
#     66.461,
#     114.657,
#     -127.163,
#     11.354,
#     -27.100,
#     0,
# ]

# ADora max视角
# r_init_end = [
#     156.772,
#     -24.730,
#     -62.480,
#     80.768,
#     125.439,
#     -91.649,
#     100,
# ]
r_init_end = [-3.947999954223633, 87.58499908447266, -64.58899688720703, 3.7909998893737793, -108.41699981689453, 88.95899963378906, 100]

#Single_desktop视角
# r_init_end = [
#     24.998,
#     59.106,
#     119.570,
#     -76.121,
#     20.816,
#     -27.091,
#     100,
# ]


right_R=np.array([[ 0.99626541 , -0.00189474 , -0.08632295],
               [ 0.00235725 , 0.99998341 , 0.00525635],
               [ 0.08631156 , -0.0054402  , 0.99625334]])

right_t= np.array([[-0.06137702],
               [-0.065354842],
               [ 0.11946556]])

stop = True
not_init=True


def camera_to_base(point_camera,R,t):
    point_camera = np.array(point_camera).reshape(3,1)
    point_base = np.dot(R, point_camera) + t
    return point_base.flatten()

def extract_bboxes(json_text) -> (np.ndarray, np.ndarray):
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

def handle_speech(last_text):
    global stop, cache
    word_list=list(last_text.lower())
    words = last_text.lower().split()
    print("words: ", words)
    if len(ACTIVATION_WORDS) > 0 and any(word in ACTIVATION_WORDS for word in word_list):
        # 更新cache中的text为实际输入的文本
        cache["text"] = last_text
        
        # 提取物体名称，去掉"帮我拿"等前缀
        object_name = last_text
        for prefix in ["帮我拿", "给我拿", "帮我", "给我", "拿"]:
            object_name = object_name.replace(prefix, "")
        object_name = object_name.strip()
        
        node.send_output(
            "text_vlm",
            pa.array(
                [
                    f"给定提示：{last_text}。请识别图像中的{object_name}并输出其边界框",
                ],
            ),
            metadata={"image_id": "image_depth"},
        )
        node.send_output(
            "prompt",
            pa.array([last_text]),
            metadata={"image_id": "image_depth"},
        )
        print(f"sending: {last_text}")
        stop = False


def wait_for_event(id, timeout=None, cache={}):
    """TODO: Add docstring."""
    while True:
        event = node.next(timeout=timeout)
        if event is None:
            cache["finished"] = True
            return None, cache
        if event["type"] == "INPUT":
            cache[event["id"]] = event["value"]
            if event["id"] == "text":
                cache[event["id"]] = event["value"][0].as_py()
                handle_speech(event["value"][0].as_py())
            elif event["id"] == id:
                return event["value"], cache

        elif event["type"] == "ERROR":
            return None, cache


def wait_for_events(ids: list[str], timeout=None, cache={}):
    """TODO: Add docstring."""
    response = {}
    while True:
        event = node.next(timeout=timeout)
        if event is None:
            cache["finished"] = True
            return None, cache
        if event["type"] == "INPUT":
            cache[event["id"]] = event["value"]
            if event["id"] == "text":
                cache[event["id"]] = event["value"][0].as_py()
                handle_speech(event["value"][0].as_py())
            elif event["id"] in ids:
                response[event["id"]] = event["value"]
                if len(response) == len(ids):
                    return response, cache
        elif event["type"] == "ERROR":
            return None, cache

def get_prompt():
    """TODO: Add docstring."""
    text = wait_for_event(id="text", timeout=0.3)
    if text is None:
        return None
    text = text[0].as_py()

    words = text.lower().split()
    if len(ACTIVATION_WORDS) > 0 and all(
        word not in ACTIVATION_WORDS for word in words
    ):
        return None
    return text

last_text = ""
cache = {"text": "Put the orange in the metal box"}

while True:
    ### === IDLE ===
    if not_init:
        node.send_output(
            "action_r_arm",
            pa.array(r_init_pose),
            metadata={"encoding": "jointstate", "duration": 1,"arm":"right"},
        )
        time.sleep(0.5)
        _, cache = wait_for_events(
            ids=["response_r_arm"], timeout=3, cache=cache,
        )
        arm_holding_object = None
        not_init=False
    # Try pose and until one is successful
    text, cache = wait_for_event(id="text", timeout=0.3, cache=cache)

    if stop:
        continue
    

    while True:
        values, cache = wait_for_event(id="pose", cache=cache)
        if values is None:
            continue
        values = values.to_numpy().reshape((-1, 6))
        if len(values) > 1:
            continue
        x = values[0][0]
        y = values[0][1]
        z = values[0][2]

        x_new,y_new,z_new = camera_to_base([x,y,z],right_R,right_t) 
        trajectory = np.array([     
            [x_new, y_new, z_new, 0, 0, 0, 100],
            # [x_new, y_new, z_new, 0, 0, 0, 0],
        ]).ravel() 
        node.send_output(
            "action_r_arm",
            pa.array(trajectory),
            metadata={"encoding": "xyzrpy", "duration": "0.5","arm":"right"},
        )
        event, cache = wait_for_event(id="response_r_arm", timeout=15, cache=cache)

        if event is not None and event[0].as_py():
            print("Success")
            arm_holding_object = "right"
            break
        else:
            print("Failed: x: ", x_new, " y: ", y_new, " z: ", z_new)
            node.send_output(
                "action_r_arm",
                pa.array(r_init_pose),
                metadata={"encoding": "jointstate", "duration": "0.75","arm":"right"},
            )
            event, cache = wait_for_event(id="response_r_arm",  timeout=5,cache=cache)
            break
    print("已经退出！！！！！！！！！！")
    time.sleep(1)

    if arm_holding_object == "right":
        node.send_output(
                "action_r_arm",
                pa.array(r_init_middle),
                metadata={"encoding": "jointstate", "duration": "0.75","arm":"right"},
            )
        event, cache = wait_for_event(id="response_r_arm",  timeout=5,cache=cache)

    if arm_holding_object == "right":
        node.send_output(
            "action_r_arm",
            pa.array(r_init_end),
            metadata={"encoding": "jointstate", "duration": "0.75","arm":"right"},
            )
    event, cache = wait_for_event(id="response_r_arm",  timeout=5,cache=cache)
        
    # if arm_holding_object == "right":
    #     print("进入if!!!!!!!!!!!")
    #     node.send_output(
    #             "action_r_arm",
    #             pa.array(r_init_pose),
    #             metadata={"encoding": "jointstate", "duration": "1","arm":"right"},
    #         )
    #     event, cache = wait_for_event(id="response_r_arm", timeout=4, cache=cache)
    #     time.sleep(0.5)
        
    # if arm_holding_object == "right":
    #     node.send_output(
    #             "action_r_arm",
    #             pa.array(r_init_pose),
    #             metadata={"encoding": "jointstate", "duration": "1","arm":"right"},
    #         )
    #     event, cache = wait_for_event(id="response_r_arm", timeout=4, cache=cache)
    #     time.sleep(0.5)
    stop = True
    not_init=True
    if cache.get("finished", False):
        break

