# dora_nav_crawl

本仓库整合了抓取与移动相关的多个子工程：Dora-rs 语音/视觉抓取流水线、RealSense 相机发送端、以及导航/SLAM 相关工程。不同模块依赖和运行方式不同，请优先阅读对应子目录的说明。

## 主要模块

- `dora_ws/`
  - `dora_robot_single`: 语音/视觉/机械臂抓取主数据流（`dataflow.yml`）
  - `hand_eye_calibration-main`: 手眼标定脚本与配置
- `robot_camera_sender/`: 工控机端 RealSense TCP 发送脚本（与 `dora-camera-net` 配套）
- `keda/`: 车辆控制/规划/地图与传感器相关工程（control/planning/map 等）
- `slam/`: ROS/catkin 形式的 SLAM 工程，含 `hdl_graph_slam`、`fast_gicp` 等
- `小车导航操作.pdf`: 导航/使用说明文档

## 功能概览

- 基于 Dora 数据流的语音交互、视觉识别与目标位姿计算，驱动机械臂抓取
- 相机与机械臂手眼标定（eye-in-hand / eye-to-hand）
- 机器人导航与 SLAM 相关组件（独立工作区）

## 快速入口

- 抓取系统：`dora_ws/dora_robot_single/README.md` 与 `dora_ws/dora_robot_single/README_ROBOT.md`
- 手眼标定：`dora_ws/hand_eye_calibration-main/README.md`
- 相机发送端：`robot_camera_sender/README.md`
