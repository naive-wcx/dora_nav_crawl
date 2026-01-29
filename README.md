# dora_nav_crawl

本仓库包含两条主线：**导航**（`keda/`、`slam/`）与 **抓取**（`dora_ws/`、`robot_camera_sender/`）。两个体系依赖、构建方式与运行入口不同，请按模块阅读。

## 模块与分工

- **导航**
  - `keda/`：基于 Dora 的导航数据流与车辆控制（激光雷达、定位、路径规划、纵横向控制、底盘通讯、可视化）
  - `slam/`：ROS/catkin 形式的 SLAM 工作区（`hdl_graph_slam`、`fast_gicp` 等），用于建图/定位基线
- **抓取**
  - `dora_ws/dora_robot_single/`：Dora-rs 抓取主数据流（语音、视觉、机械臂）
  - `robot_camera_sender/`：工控机端 RealSense TCP 发送端（与 `dora-camera-net` 端对应）
  - `dora_ws/hand_eye_calibration-main/`：手眼标定脚本与数据
- 其他
  - `小车导航操作.pdf`：导航操作文档
  - `dataflow-graph-工控机.html`：数据流可视化产物（供快速浏览）

## 导航逻辑（keda + slam）

### keda：Dora 数据流（主运行入口：`keda/run.yml`）
核心流程（与 `keda/run.yml` 一致）：

1. **激光雷达采集**（Livox）  
   `keda/livox/src/livox_dora_driver2.cpp` 驱动 MID360，发布 `pointcloud`。
2. **点云定位**（hdl_localization）  
   `keda/dora-hdl_localization/src/dora_hdl_node.cpp` 读取地图 `MAP_PCD`，下采样后做 NDT/配准定位，输出 `cur_pose`，并可写出轨迹到 `way_points` 文件。
3. **道路/参考线发布**  
   `keda/map/pub_road/src/pubroad.cpp` 从 `Waypoints.txt` 读取参考线，输出 `road_lane`。
4. **位姿转 Frenet**  
   `keda/map/road_line_publisher/road_lane.cpp` 结合 `road_lane` 与 `cur_pose` 计算 `s/d`，输出 `cur_pose_all`。
5. **任务/道路属性**  
   `keda/planning/mission_planning/task_pub/main.cpp` 从 `road_msg.txt` 读取道路属性并输出 `road_attri_msg`  
   （另有 `pub_main.cpp` 版本从数据库读取任务/道路属性）。
6. **路径规划**  
   `keda/planning/routing_planning/node_routing_core.cpp` 将 `road_lane + cur_pose_all + road_attri_msg` 组合成 `raw_path`，并输出 `Request`（速度/刹车/倒车/AEB）。  
   规划核心在 `pathplanning.cpp`，通过 Frenet 采样与样条拟合生成 30 个路径点。
7. **纵横向控制**  
   - 横向：`control/vehicle_control/lat_controller` 使用纯跟踪生成 `SteeringCmd`  
   - 纵向：`control/vehicle_control/lon_controller` 根据 `Request` 生成 `TrqBreCmd`
8. **底盘通讯**  
   `control/vehicle_control/mick/adora_chassis_a2pro_dora_node.cc` 通过串口或 UDP 向底盘下发控制（由环境变量选择模式）。
9. **可视化**  
   `keda/rerun` 将 `pointcloud/raw_path/cur_pose` 输出到 Rerun。

### slam：ROS SLAM 工作区（建图/定位基线）
`slam/` 为 catkin 工作区，内含 `hdl_graph_slam`、`fast_gicp`、`ndt_omp` 等。  
示例入口：

```bash
cd slam
./launch.sh
```

> `slam/devel/` 为已编译产物，`slam/src/hdl_graph_slam/README.md` 为原始上游说明。

## 抓取逻辑（dora_ws + robot_camera_sender）

### dora_robot_single：语音 + 视觉 + 机械臂抓取
主数据流：`dora_ws/dora_robot_single/dataflow.yml`

- 语音链路：`dora-microphone -> dora-vad -> dora-distil-whisper -> state_machine`
- 视觉链路：`dora-camera-net -> dora-qwen2-5-vl -> parse_bbox -> dora-object-to-pose -> state_machine -> dora-rm65`
- 可视化：`visualization_node` 订阅相机/识别/语音结果

### 相机与标定
- `robot_camera_sender/realsense_tcp_sender.py` 在工控机端推送彩色/深度帧（TCP）  
- `dora_ws/hand_eye_calibration-main/` 提供 eye-in-hand / eye-to-hand 标定脚本

## 关键配置（常用）

**导航（keda）**
- `MAP_PCD`：地图点云路径（默认 `keda/data/map.pcd`）
- `map_downsample_resolution` / `point_downsample_resolution`：定位下采样参数  
- `use_imu`：是否启用 IMU 融合（`1`/`0`）
- `way_points`：轨迹输出路径（默认 `keda/data/path/trajectory.txt`）
- 底盘通讯：`COMMUNICATION_MODE`（0 串口 / 1 UDP），`UDP_TARGET_IP/PORT` 等

**抓取（dora_ws）**
- `TCP_LISTEN_PORT`：相机 TCP 监听端口（`dora-camera-net`）
- `MODEL_NAME_OR_PATH`：Qwen2.5-VL 模型路径
- `ACTIVATION_WORDS`：语音触发词

## 推荐阅读

- 导航：`keda/run.yml`、`keda/Waypoints.txt`、`keda/road_msg.txt`
- SLAM：`slam/src/hdl_graph_slam/README.md`
- 抓取：`dora_ws/dora_robot_single/README.md` 与 `README_ROBOT.md`
- 相机发送端：`robot_camera_sender/README.md`
