"""
Rerun可视化节点 - 用于接收和可视化多个数据源
Rerun Visualization Node - For receiving and visualizing multiple data sources

作者/Author: Claude
日期/Date: 2025-08-31
版本/Version: 1.0.0
"""

import os
import sys
from pathlib import Path
import time
import json
import logging
import threading
import cv2
import numpy as np
import pyarrow as pa
from PIL import Image
from typing import Dict, Any, Optional, List
from queue import Queue
import rerun as rr

EVENT_LOOP_DIR = Path(__file__).resolve().parents[3] / "utils" / "event_loop" / "python"
if EVENT_LOOP_DIR.is_dir():
    sys.path.insert(0, str(EVENT_LOOP_DIR))

from cc_dora_event_loop import EventLoop, InputEvent, cc_get_logger

# 配置日志
logger = cc_get_logger()

LOG_WITH_TIMESTAMP = False


class VisualizationNode:
    """Rerun可视化节点类，用于接收和可视化多个数据源"""

    def __init__(self):
        """初始化节点"""
        self.event_loop = EventLoop("Visualization Node")
        self.logger = logger
        self.logger.setLevel(logging.INFO)

        # 可视化数据
        self.camera_image = Queue()
        self.state_machine_graph = Queue()
        self.llm_text = "wait LLM text..."
        self.object_name = ""
        self.object_coordinates = []
        self.arm_status = "idle"
        
        # 边界框数据
        self.boxes2d = None
        self.box_labels = []

        # 线程控制
        self.running = True
        self.rerun_thread = None

        self.rec: rr.RecordingStream = None

    def setup(self):
        """设置事件处理器和Rerun可视化"""
        # 初始化Rerun
        # rr.init("dora-rs-visualization", spawn=True) #本地 rerun
        config = rr.ChunkBatcherConfig(
            flush_num_bytes=2**8,
            flush_num_rows=10,
        )

        self.rec = rr.RecordingStream(
            "dora-rs-visualization", batcher_config=config)
        # self.rec.set_sinks(rr.GrpcSink())
        self.rec.spawn()

        # rr.init("dora-rs-visualization")
        # rr.set_sinks(rr.GrpcSink("rerun+http://192.168.41.1:9876/proxy"))

        # 注册输入处理器
        self.event_loop.register_input_handler(
            "vision_result",
            self.handle_vision_result
        )

        self.event_loop.register_input_handler(
            "text_whisper",
            self.handle_text_whisper
        )

        self.event_loop.register_input_handler(
            "camera_image",
            self.handle_image
        )

        # self.event_loop.register_input_handler(
        #     "camera_image",
        #     self.handle_image
        # )

        self.event_loop.register_input_handler(
            "camera_torso/boxes2d",
            self.handle_boxes2d
        )

        self.event_loop.register_input_handler(
            "state_machine_graph",
            self.handle_image
        )

        self.event_loop.register_input_handler(
            "arm_status",
            self.handle_arm_status
        )

        self.event_loop.register_input_handler(
            "tick",
            self.handle_tick
        )
        
        # 注册边界框处理器
        self.event_loop.register_input_handler(
            "boxes2d",
            self.handle_boxes2d
        )

        # 启动Rerun更新线程
        self.rerun_thread = threading.Thread(target=self._rerun_update_thread)
        self.rerun_thread.daemon = True


    def handle_boxes2d(self, event: InputEvent):
        """
        处理边界框数据

        Args:
            event: 输入事件
        """
        try:
            # 获取边界框数据
            boxes_data = event.data.to_numpy()
            metadata = event.metadata
            encoding = metadata.get("encoding", "")
            image_id = metadata.get("image_id", "")
            
            self.logger.info(f"[边界框] 接收到边界框数据: shape={boxes_data.shape}, encoding={encoding}, image_id={image_id}")
            print(f"[边界框] 接收到边界框数据: {boxes_data}")
            
            if encoding == "xyxy" and len(boxes_data) > 0:
                # 重塑为[x1, y1, x2, y2]格式
                if len(boxes_data) == 4:  # 单个边界框
                    self.boxes2d = boxes_data.reshape(1, 4)
                    self.box_labels = ["object"]
                else:  # 多个边界框
                    num_boxes = len(boxes_data) // 4
                    self.boxes2d = boxes_data.reshape(num_boxes, 4)
                    self.box_labels = ["object"] * num_boxes
                
                self.logger.info(f"[边界框] 处理后的边界框: {self.boxes2d}")
                print(f"[边界框] 处理后的边界框: {self.boxes2d}")
            else:
                self.logger.error(f"[边界框] 不支持的编码或空数据: {encoding}")
                
        except Exception as e:
            self.logger.error(f"[错误] 处理边界框数据失败: {e}")
            print(f"[错误] 处理边界框数据失败: {e}")

    def handle_vision_result(self, event: InputEvent):
        """
        处理视觉节点的结果

        Args:
            event: 输入事件
        """
        try:
            # 解析视觉节点发送的数据
            data_bytes = bytes(event.data.to_pylist()).decode('utf-8')
            vision_data = json.loads(data_bytes)

            # 更新本地数据
            if "description" in vision_data:
                self.llm_text = vision_data["description"]
                self.logger.info(f"[视觉] 收到LLM描述: {self.llm_text}")

            if "object" in vision_data:
                self.object_name = vision_data["object"]

            if "coordinates" in vision_data:
                self.object_coordinates = vision_data["coordinates"]

        except Exception as e:
            self.logger.error(f"[错误] 解析视觉数据失败: {e}")

    def handle_text_whisper(self, event: InputEvent):
        """
        处理视觉节点的结果

        Args:
            event: 输入事件
        """
        try:
            # 解析视觉节点发送的数据
            text = event.data[0].as_py()
            self.llm_text = text
            self.logger.info(f"[收到whisper描述: {text}")

        except Exception as e:
            self.logger.error(f"[错误] 解析whisper数据失败: {e}")


    def handle_arm_status(self, event: InputEvent):
        """
        处理机械臂状态事件

        Args:
            event: 输入事件
        """
        try:
            data_bytes = bytes(event.data.to_pylist()).decode('utf-8')
            arm_data = json.loads(data_bytes)
            status = arm_data.get("status", "")

            # 更新状态机状态
            self.arm_status = status
            self.logger.info(f"[状态机] 收到状态: {status}")

            # 将数据放入队列
            # if self.state_machine_queue.full():
            #     self.state_machine_queue.get_nowait()  # 移除旧数据
            # self.state_machine_queue.put_nowait(arm_data)

        except Exception as e:
            self.logger.error(f"[错误] 解析状态机数据失败: {e}")

    def handle_image(self, event: InputEvent):
        """
        处理摄像头图像数据 - 使用Dora标准方式接收图像

        Args:
            event: 输入事件
        """
        # self.logger.error(f"收到图像")
        try:
            # 获取图像数据和元数据
            storage = event.data
            metadata = event.metadata
            encoding = metadata["encoding"]
            width = metadata["width"]
            height = metadata["height"]
            frame = None

            # 根据编码类型解析图像数据
            if encoding == "bgr8" or encoding == "rgb8":
                channels = 3
                storage_type = np.uint8

                # 解析为numpy数组并重塑为图像
                frame = storage.to_numpy().astype(storage_type).reshape((height, width, channels))

                # 如果是BGR格式，无需转换（OpenCV默认使用BGR）
                # 如果是RGB格式，需要转换为BGR（用于OpenCV处理）
                if encoding == "rgb8":
                    frame = frame[:, :, ::-1]  # RGB to BGR

            elif encoding in ["jpeg", "jpg", "jpe", "bmp", "webp", "png"]:
                # 处理压缩图像
                storage_numpy = storage.to_numpy()
                frame = cv2.imdecode(storage_numpy, cv2.IMREAD_COLOR)

            else:
                self.logger.error(f"[错误] 不支持的图像编码: {encoding}")

            # 更新摄像头图像
            if frame is not None:
                if event.id == "camera_image":
                    self.camera_image.put(frame)
                    # self.logger.info(
                    #     f"[摄像头] 接收到图像: {width}x{height}, 编码: {encoding}")
                if event.id == "state_machine_graph":
                    self.state_machine_graph.put(frame)
                   

        except Exception as e:
            self.logger.error(f"[错误] 处理摄像头图像失败: {e}")

    def handle_tick(self, event: InputEvent):
        """
        处理定时器事件

        Args:
            event: 输入事件
        """
        pass
        # 定时检查状态机图片是否存在并加载
        # self._check_and_load_state_machine_image()

    def _rerun_update_thread(self):
        """Rerun更新线程，定期将数据发送到Rerun进行可视化"""
        self.logger.info("[Rerun] 可视化线程已启动")

        while self.running:
            try:
                # rr.set_time("sensor_time", timestamp=time.time())

                self.rec.log(
                    "sys.info",
                    rr.TextDocument(
                        f'''
# System Information
vision/llm_text: {self.llm_text}

arm/status: {self.arm_status}

'''.strip(),
                        media_type=rr.MediaType.MARKDOWN,
                    ),
                    static=not LOG_WITH_TIMESTAMP
                )

                if not self.camera_image.empty():
                    img = self.camera_image.get_nowait()
                    self.rec.log("vision/camera_image",
                                 rr.Image(img,
                                          color_model=rr.ColorModel.BGR),
                                 static=not LOG_WITH_TIMESTAMP
                                 )
                # 添加边界框 - 优先使用从parse_bbox接收的边界框数据
                if self.boxes2d is not None and len(self.boxes2d) > 0:
                    h, w = img.shape[:2]
                    
                    # 确保所有坐标在图像范围内
                    boxes_array = []
                    for box in self.boxes2d:
                        x1, y1, x2, y2 = box
                        x1 = max(0, min(x1, w-1))
                        y1 = max(0, min(y1, h-1))
                        x2 = max(0, min(x2, w-1))
                        y2 = max(0, min(y2, h-1))
                        boxes_array.extend([x1, y1, x2, y2])
                    
                    # print(f"[Rerun] 显示边界框: {boxes_array}")
                    self.rec.log("vision/camera_image",
                                 rr.Boxes2D(array=boxes_array,
                                           array_format=rr.Box2DFormat.XYXY,
                                           labels=self.box_labels,
                                           colors=[0, 255, 0]),
                                 static=not LOG_WITH_TIMESTAMP
                                 )
                # 备用方案：使用从vision_result提取的坐标
                elif self.object_coordinates and len(self.object_coordinates) == 4:
                    x1, y1, x2, y2 = self.object_coordinates
                    # 确保坐标在图像范围内
                    h, w = img.shape[:2]
                    x1 = max(0, min(x1, w-1))
                    y1 = max(0, min(y1, h-1))
                    x2 = max(0, min(x2, w-1))
                    y2 = max(0, min(y2, h-1))

                    # 记录带边界框的图像
                    print(f"[Rerun] 显示备用边界框: [{x1}, {y1}, {x2}, {y2}]")
                    self.rec.log("vision/camera_image",
                                 rr.Boxes2D(array=[x1, y1, x2, y2],
                                            array_format=rr.Box2DFormat.XYXY,
                                            labels=[self.object_name or "object"],
                                            colors=[0, 255, 0]),
                                 static=not LOG_WITH_TIMESTAMP
                                 )

                # 如果有状态机图像，记录到 Rerun
                if not self.state_machine_graph.empty():
                   # cv2.imread(f'robot_state_machine.png')
                    img = self.state_machine_graph.get_nowait()
                    self.rec.log("state_machine/graph",
                                 rr.Image(img,
                                          color_model=rr.ColorModel.BGR),
                                 static=not LOG_WITH_TIMESTAMP
                                 )

                time.sleep(0.01)

            except Exception as e:
                self.logger.error(f"[Rerun] 更新线程错误: {e}")
                time.sleep(0.01)

        self.logger.info("[Rerun] 可视化线程已结束")

    def run(self):
        """运行节点"""
        self.logger.info("Rerun可视化节点启动")

        # 设置事件处理器和Rerun可视化
        self.setup()

        # 启动Rerun更新线程
        self.rerun_thread.start()

        # 运行事件循环
        self.event_loop.run()

        # 停止线程
        self.running = False
        if self.rerun_thread is not None:
            self.rerun_thread.join(timeout=1.0)

        self.logger.info("Rerun可视化节点已关闭")


def main():
    """主函数"""
    node = VisualizationNode()
    node.run()


if __name__ == "__main__":
    main()
