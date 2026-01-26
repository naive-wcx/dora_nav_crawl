# Repository Guidelines

## 项目结构与模块组织
- `dora_robot_single/`: Dora-rs 运行与多语言节点。核心配置 `dataflow.yml`/`example_dataflow.yml`，Python 节点在 `python_nodes/<node>/`，共享构建逻辑在 `utils/`，运行输出在 `out/`（生成文件）。
- `dora_robot_single/python_nodes/dora-camera-net/`: TCP 相机接收节点，输出 `image_depth` 与 `depth` 供视觉与位姿计算使用。
- `robot_camera_sender/`: 运行在工控机上的 RealSense 发送脚本与使用说明。
- `hand_eye_calibration-main/`: 手眼标定脚本与数据，入口脚本如 `collect_data.py`、`compute_in_hand.py`，依赖在 `requirements.txt`。
- 设备参数与标定文件示例：`dora_robot_single/dora_camera_intrinsics.json`、`hand_eye_calibration-main/config.yaml`。

## 架构概览
- PC 侧以 Dora-rs 数据流为主干，`dataflow.yml` 连接语音、视觉、机械臂控制等节点，节点间通过 Arrow UInt8 字节流传递结构化信息。
- 工控机端 RealSense 通过 TCP 发送彩色/深度帧，PC 侧接收节点转为 Dora 输出。
- 手眼标定模块负责生成相机到机械臂坐标变换，标定结果需要与运行时配置保持一致。

## 环境要求
- 主要依赖: Python >= 3.8, CMake >= 3.21, Dora-rs 0.3.12；工控机侧需 RealSense 驱动与 `pyrealsense2`。

## 构建、测试与开发命令
- `cd dora_robot_single && ./build.sh`: CMake 构建（会创建 `build/` 并 `make install`）。
- `cd dora_robot_single && dora build dataflow.yml`: 按 `dataflow.yml` 安装/构建节点依赖。
- `dora up` / `dora start ./dataflow.yml`: 启动 Dora 运行时和数据流。
- 工控机发送：`python robot_camera_sender/realsense_tcp_sender.py --host <PC_IP> --port 5002`。
- Rust 节点（如 `dora-object-to-pose`）：`pip install -e python_nodes/dora-object-to-pose` 触发编译。
- 手眼标定：`cd hand_eye_calibration-main && pip install -r requirements.txt`，运行 `python compute_in_hand.py` 或 `python compute_to_hand.py`。

## 编码风格与命名规范
- Python 统一 4 空格缩进，函数/变量用 `snake_case`，类用 `PascalCase`。
- 每个节点的 `pyproject.toml` 配置 Ruff；在节点目录执行 `ruff check .`。
- 保持现有目录命名 `dora-<node>` 与模块名 `dora_<node>` 的对应关系。

## 测试指南
- 现有测试集中在 `dora_robot_single/python_nodes/<node>/tests/`，使用 `pytest`。
- 在节点目录运行 `pytest`；目前无统一覆盖率门槛。

## 提交与 PR 规范
- 仓库未包含 `.git` 历史，暂无既定提交规范；建议使用简短祈使句主题，必要时加模块前缀（如 `dora: 修复语音节点`）。
- PR 需说明变更范围、运行/测试结果（如 `dora start` 输出）、涉及硬件或数据流修改时附上配置变更说明与必要截图/日志。

## 配置与数据提示
- 设备 IP、标定结果、运行输出属于环境数据，避免误提交 `out/`、标定图片或大体积数据；必要时用 `.gitignore` 维护。
- RealSense 设备需本机可见，必要时为 USB 设备配置权限规则。
