"""TODO: Add docstring."""

import os
from pathlib import Path

import cv2
import numpy as np
import pyarrow as pa
from dora import Node
from PIL import Image
from qwen_vl_utils import process_vision_info
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

"""
离线使用Qwen2.5-VL模型的详细步骤:

1. 下载模型的方法:

   方法一：使用ModelScope下载（推荐中国大陆用户使用）:
   ```python
   # 安装modelscope
   pip install modelscope
   
   # 下载模型
   from modelscope import snapshot_download
   model_dir = snapshot_download('qwen/Qwen2.5-VL-7B-Instruct', cache_dir='/home/dora/models')
   print(f"模型已下载到: {model_dir}")
   ```

   方法二：使用HuggingFace下载（使用清华源加速）:
   ```bash
   # 设置HuggingFace镜像
   export HF_ENDPOINT=https://hf-mirror.com/
   # 或者使用上海交大镜像
   # export HF_ENDPOINT=https://mirror.sjtu.edu.cn/hugging-face/
   
   # 下载模型
   huggingface-cli download Qwen/Qwen2.5-VL-7B-Instruct --local-dir /home/dora/models/qwen2.5-vl --local-dir-use-symlinks False
   ```

2. 配置模型路径:
   - 在dataflow.yml中设置环境变量:
     ```yaml
     env:
       MODEL_NAME_OR_PATH: /home/dora/models/qwen2.5-vl
     ```
   - 或者直接修改本文件中的MODEL_PATH变量
"""

# 设置默认模型路径 - 修改为您下载的模型实际位置
MODEL_PATH = "/home/dora/dora_ws/dora_robot_single/models/qwen/Qwen2.5-VL-7B-Instruct"

# 修复路径中的特殊字符
if "___" in MODEL_PATH:
    MODEL_PATH = MODEL_PATH.replace("___", ".")
    print(f"修复后的模型路径: {MODEL_PATH}")


# 允许通过环境变量覆盖模型路径
MODEL_NAME_OR_PATH = os.getenv("MODEL_NAME_OR_PATH", MODEL_PATH)
print(f"使用模型路径: {MODEL_NAME_OR_PATH}")

# # 检查模型路径是否存在
# if os.path.exists(MODEL_NAME_OR_PATH):
#     print(f"模型路径存在: {MODEL_NAME_OR_PATH}")
#     if os.path.isdir(MODEL_NAME_OR_PATH):
#         files = os.listdir(MODEL_NAME_OR_PATH)
#         print(f"目录内容: {files}")
#         if "config.json" in files:
#             print("找到config.json文件，模型路径有效")
#         else:
#             print("警告: 目录中没有找到config.json文件，可能不是有效的模型目录")
# else:
#     print(f"警告: 模型路径不存在: {MODEL_NAME_OR_PATH}")
#     # 尝试在常见位置查找模型
#     print("尝试在常见位置查找模型...")
#     possible_paths = [
#         "/home/dora/models/qwen2.5-vl",
#         "/home/dora/models/Qwen2.5-VL-7B-Instruct",
#         "/home/dora/dora_ws/dora_robot_single/models/qwen/Qwen2.5-VL-7B-Instruct",
#         "/home/dora/dora_ws/dora_robot_single/models/Qwen2.5-VL-7B-Instruct"
#     ]
#     for path in possible_paths:
#         if os.path.exists(path):
#             print(f"找到可用的模型路径: {path}")
#             MODEL_NAME_OR_PATH = path
#             break

SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    """You're an AI assistant that helps identify objects in images.
    When asked to find an object, ONLY output a JSON array wrapped in markdown code block (```json).
    Each object in the array MUST contain 'label' and 'bbox_2d' fields.
    The bbox_2d MUST be [x1, y1, x2, y2] coordinates representing the bounding box.
    
    IMPORTANT: Your entire response must be ONLY the JSON code block, nothing else.
    
    Example output format:
    ```json
    [{"label": "mouse", "bbox_2d": [100, 200, 150, 250]}]
    ```""",
)
ACTIVATION_WORDS = os.getenv("ACTIVATION_WORDS", "").split()

DEFAULT_QUESTION = os.getenv(
    "DEFAULT_QUESTION",
    "Describe this image",
)
IMAGE_RESIZE_RATIO = float(os.getenv("IMAGE_RESIZE_RATIO", "1.0"))
print(IMAGE_RESIZE_RATIO)
HISTORY = os.getenv("HISTORY", "False") in ["True", "true"]
ADAPTER_PATH = os.getenv("ADAPTER_PATH", "")


# Check if flash_attn is installed
try:
    import flash_attn as _  # noqa
    print(f"尝试使用flash_attention加载模型...")
    
    # 检查是否是本地路径
    local_files_only = os.path.exists(MODEL_NAME_OR_PATH) and os.path.isdir(MODEL_NAME_OR_PATH)
    
    try:
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            MODEL_NAME_OR_PATH,
            torch_dtype="auto",
            device_map="auto",
            attn_implementation="flash_attention_2",
            local_files_only=local_files_only,  # 仅当是本地路径时才强制使用本地文件
            trust_remote_code=True  # 信任远程代码
        )
        print("模型加载成功(使用flash_attention)")
    except Exception as e:
        print(f"使用flash_attention加载失败: {e}")
        print("尝试在线加载模型...")
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            "Qwen/Qwen2.5-VL-3B-Instruct",
            torch_dtype="auto",
            device_map="auto",
            attn_implementation="flash_attention_2",
            trust_remote_code=True
        )
        print("在线模型加载成功(使用flash_attention)")
except (ImportError, ModuleNotFoundError) as e:
    print(f"flash_attention导入失败: {e}")
    print(f"使用标准方式加载模型: {MODEL_NAME_OR_PATH}")
    
    # 检查是否是本地路径
    local_files_only = os.path.exists(MODEL_NAME_OR_PATH) and os.path.isdir(MODEL_NAME_OR_PATH)
    
    try:
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            MODEL_NAME_OR_PATH,
            torch_dtype="auto",
            device_map="auto",
            local_files_only=local_files_only,  # 仅当是本地路径时才强制使用本地文件
            trust_remote_code=True  # 信任远程代码
        )
        print("模型加载成功(使用标准方式)")
    except Exception as e:
        print(f"使用本地文件加载失败: {e}")
        print("尝试在线加载模型...")
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            "Qwen/Qwen2.5-VL-3B-Instruct",
            torch_dtype="auto",
            device_map="auto",
            trust_remote_code=True
        )
        print("在线模型加载成功(使用标准方式)")


if ADAPTER_PATH != "":
    model.load_adapter(ADAPTER_PATH, "dora")


# default processor
print(f"加载处理器: {MODEL_NAME_OR_PATH}")
# 检查是否是本地路径
local_files_only = os.path.exists(MODEL_NAME_OR_PATH) and os.path.isdir(MODEL_NAME_OR_PATH)

try:
    processor = AutoProcessor.from_pretrained(
        MODEL_NAME_OR_PATH,
        local_files_only=local_files_only,  # 仅当是本地路径时才强制使用本地文件
        trust_remote_code=True  # 信任远程代码
    )
    print("处理器加载成功")
except Exception as e:
    print(f"使用本地文件加载处理器失败: {e}")
    print("尝试在线加载处理器...")
    try:
        processor = AutoProcessor.from_pretrained(
            "Qwen/Qwen2.5-VL-3B-Instruct",
            trust_remote_code=True
        )
        print("在线处理器加载成功")
    except Exception as e:
        print(f"在线加载处理器失败: {e}")
        raise RuntimeError("无法加载处理器，请确保模型文件完整或网络连接正常")


def generate(frames: dict, question, history, past_key_values=None, image_id=None):
    """Generate the response to the question given the image using Qwen2 model."""
    if image_id is not None:
        images = [frames[image_id]]
    else:
        images = list(frames.values())
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "image": image,
                    "resized_height": image.size[1] * IMAGE_RESIZE_RATIO,
                    "resized_width": image.size[0] * IMAGE_RESIZE_RATIO,
                }
                for image in images
            ]
            + [
                {"type": "text", "text": question},
            ],
        },
    ]
    tmp_history = history + messages
    # Preparation for inference
    text = processor.apply_chat_template(
        tmp_history,
        tokenize=False,
        add_generation_prompt=True,
    )
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )

    inputs = inputs.to(model.device)

    # Inference: Generation of the output
    ## TODO: Add past_key_values to the inputs when https://github.com/huggingface/transformers/issues/34678 is fixed.
    outputs = model.generate(
        **inputs,
        max_new_tokens=128,  # past_key_values=past_key_values
    )
    # past_key_values = outputs.past_key_values

    generated_ids_trimmed = [
        out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, outputs)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )
    if HISTORY:
        history += [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                ],
            },
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": output_text[0]},
                ],
            },
        ]
    print(f"{output_text[0]}, {history}, {past_key_values}")

    return output_text[0], history, past_key_values


def main():
    # 初始化PyArrow数组并创建Dora节点
    pa.array([])  # initialize pyarrow array
    
    try:
        node = Node()
    except Exception as e:
        print(f"创建Dora节点失败: {e}")
        raise

    # 初始化图像帧存储字典
    frames = {}
    # 根据系统提示初始化对话历史
    if SYSTEM_PROMPT:
        history = [
            {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
        ]
    else:
        history = []

    # 初始化缓存文本、图像ID和注意力机制参数
    cached_text = DEFAULT_QUESTION
    image_id = None
    past_key_values = None

    # 主事件循环
    for event in node:
        event_type = event["type"]

        if event_type == "INPUT":
            event_id = event["id"]

            if "image" in event_id:
                # 图像数据处理流程
                storage = event["value"]
                metadata = event["metadata"]
                encoding = metadata["encoding"]
                width = metadata["width"]
                height = metadata["height"]

                # 根据编码格式处理不同图像类型
                if encoding in ["bgr8", "rgb8"] + ["jpeg", "jpg", "jpe", "bmp", "webp", "png"]:
                    channels = 3
                    storage_type = np.uint8

                # 处理BGR格式图像（OpenCV默认格式）
                if encoding == "bgr8":
                    frame = storage.to_numpy().astype(storage_type).reshape((height, width, channels))
                    frame = frame[:, :, ::-1]  # BGR转RGB
                # 处理RGB格式图像
                elif encoding == "rgb8":
                    frame = storage.to_numpy().astype(storage_type).reshape((height, width, channels))
                # 处理压缩格式图像
                elif encoding in ["jpeg", "jpg", "jpe", "bmp", "webp", "png"]:
                    storage = storage.to_numpy()
                    frame = cv2.imdecode(storage, cv2.IMREAD_COLOR)
                    frame = frame[:, :, ::-1]  # BGR转RGB
                
                # 将处理后的图像存入帧缓存
                image = Image.fromarray(frame)
                frames[event_id] = image

            elif "text" in event_id:
                # 文本输入处理流程
                if len(event["value"]) > 0:
                    text = event["value"][0].as_py()
                    image_id = event["metadata"].get("image_id", None)

                    words = text.split()
                    if len(ACTIVATION_WORDS) > 0 and all(word not in ACTIVATION_WORDS for word in words):
                        continue

                    cached_text = text  # 更新缓存文本

                    # 图像帧检查：若无可用图像帧则跳过
                    if len(frames.keys()) == 0:
                        continue
                    
                    # 调用生成函数获取模型响应
                    response, history, past_key_values = generate(
                        frames, text, history, past_key_values, image_id,
                    )
                    # 发送文本响应输出
                    node.send_output(
                        "text",
                        pa.array([response]),
                        {"image_id": image_id if image_id is not None else "all"},
                    )
                # else:
                #     text = cached_text  # 使用缓存的默认问题
                
                # 激活词检查：如果设置激活词且当前文本不含任何激活词，跳过处理 

        elif event_type == "ERROR":
            print("Event Error:" + event["error"])


if __name__ == "__main__":
    main()
