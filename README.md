# dora_nav_crawl

本仓库用于基于 Dora-rs 的机器人语音/视觉抓取与手眼标定实验。核心工作区位于 `dora_ws/`，
包含单机 RealSense + RM65 等机械臂的数据流编排与标定工具。

## 功能概览

- 基于 Dora 数据流的语音交互、视觉识别与目标位姿计算，驱动机械臂抓取
- 相机与机械臂的手眼标定（eye-in-hand / eye-to-hand）脚本与示例数据

## 目录结构

- `dora_ws/dora_robot_single`: 语音/视觉/机械臂节点与 `dataflow.yml`
- `dora_ws/hand_eye_calibration-main`: 手眼标定流程、脚本、配置与说明
- `dora_ws/dora_robot_single/README_ROBOT.md`: 运行环境与参数调整参考

## 使用提示

具体的依赖、构建与运行步骤请先阅读 `dora_ws/dora_robot_single/README.md` 与
`dora_ws/dora_robot_single/README_ROBOT.md`。
