# Dora Robot Single

基于 Dora-rs 的语音 + 视觉 + 机械臂抓取示例。通过语音指令触发视觉识别（Qwen2.5-VL），结合深度图估计目标三维位姿，驱动 RM65 机械臂执行抓取。

## 核心流程
- 语音链路: dora-microphone -> dora-vad -> dora-distil-whisper -> state_machine
- 视觉链路: dora-camera-net -> dora-qwenvl -> parse_bbox -> dora-object-to-pose -> state_machine -> dora-rm65
- 可视化: visualization_node 订阅相机、VLM 结果与语音文本

## 目录结构
- `dataflow.yml`: 主数据流配置，连接语音、视觉、机械臂等节点
- `example_dataflow.yml`: 参考数据流
- `python_nodes/`: Dora Python 节点
  - `dora-camera-net`: TCP 接收 RealSense 彩色/深度帧
  - `dora-qwen2-5-vl`: Qwen2.5-VL 视觉语言模型
  - `parse_bbox.py`: 解析 VLM 输出的 bbox
  - `dora-object-to-pose`: 2D bbox + 深度 -> 3D 位姿 (Rust)
  - `dora-rm65`: RM65 机械臂控制
  - `dora-microphone`/`dora-vad`/`dora-distil-whisper`: 语音采集、VAD、ASR
  - `visualization_node`: Rerun 可视化
- `read_realsense_intrinsics.py`/`dora_camera_intrinsics.json`: 相机内参工具与示例
- `utils/`: C/C++/Python 事件循环与共享构建
- `out/`: 运行输出（日志/会话文件，已忽略）
- `.cargo/`: Rust 镜像与网络配置
- `README_ROBOT.md`: 详细部署与标定说明

## 快速开始
1. 安装依赖并构建节点:
   `dora build dataflow.yml`
2. 启动 Dora:
   `dora up`
   `dora start ./dataflow.yml`
3. 启动相机发送端:
   - `dora-camera-net` 监听 TCP `TCP_LISTEN_PORT` (默认 5002)，需要外部 RealSense 发送脚本推送彩色/深度帧。

## 关键配置
- `dataflow.yml`:
  - `MODEL_NAME_OR_PATH`: Qwen2.5-VL 本地模型路径
  - `TCP_LISTEN_PORT`: 相机 TCP 端口
  - `TARGET_LANGUAGE`: Whisper 识别语言
  - `ACTIVATION_WORDS`: 语音触发词
- `python_nodes/pick-place-rm65.py`:
  - `right_R`/`right_t`: 手眼标定矩阵
  - 机械臂初始位姿与抓取参数
- `python_nodes/dora-object-to-pose/src/lib.rs`:
  - 相机内参与深度解析参数

## 测试
在对应节点目录运行 `pytest`（如 `python_nodes/dora-vad/tests`）。
