# RealSense TCP Sender

此脚本运行在**机器人工控机**上，用于读取机械臂末端的 RealSense 相机，并通过局域网 TCP 将彩色/深度数据发送到本机。

## 环境配置

建议使用 Python 3.8+，并安装 Intel RealSense 驱动与 Python 依赖。

1. 安装 RealSense SDK（示例为 Ubuntu）：
   ```bash
   sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-key F6B0FC61
   sudo add-apt-repository "deb http://realsense-hw-public.s3.amazonaws.com/Debian/apt-repo $(lsb_release -cs) main" -u
   sudo apt-get update
   sudo apt-get install -y librealsense2-utils librealsense2-dev
   ```

2. 创建虚拟环境并安装依赖：
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install pyrealsense2 numpy
   ```

3. 确认相机可用：
   ```bash
   realsense-viewer
   ```

## 使用方式

1. 在**本机**启动 Dora 数据流（接收端监听 `TCP_LISTEN_PORT`）：
   ```bash
   cd dora-ws/dora_robot_single
   dora up
   dora start ./dataflow.yml
   ```

2. 在**工控机**运行发送脚本：
   ```bash
   python realsense_tcp_sender.py --host <本机IP> --port 5002
   ```

## 可选参数

- `--host`: 本机 IP（默认读取 `TCP_SERVER_IP`，否则 `192.168.1.100`）
- `--port`: 监听端口（默认 `5002`）
- `--width`, `--height`: 分辨率（默认 `640x480`）
- `--fps`: 帧率（默认 `15`）

示例：
```bash
export TCP_SERVER_IP=192.168.1.122
export TCP_SERVER_PORT=5002
python realsense_tcp_sender.py --width 640 --height 480 --fps 15
```

## 网络要求

- 机器人与本机处于同一局域网，且本机防火墙允许 `TCP_LISTEN_PORT` 入站。
- 若传输不稳定，可降低分辨率或帧率。
