# 基于本机RealSense与机械臂的智能抓取系统

本项目实现了一个基于语音指令的智能物品抓取系统，全部在本机完成语音、视觉与机械臂控制，通过 Dora-rs 数据流完成节点协同。

## 系统架构

整个项目位于`dora-ws`文件夹中，包含以下主要组件：

- **dora_robot_single**：机器人运行代码，负责处理语音指令、视觉识别和机械臂控制
- **hand_eye_calibration-main**：负责摄像头与机械臂的手眼标定

## 环境准备与项目构建

### 激活虚拟环境

在开始任何操作之前，请先激活项目所需的Conda虚拟环境：

```bash
conda activate dora
```

所有后续命令都需要在此虚拟环境中执行，以确保使用正确的依赖版本。

### 项目构建

项目中包含多个节点，每个节点都有自己的依赖项。使用以下命令构建整个项目：

```bash
cd dora-ws/dora_robot_single
dora build dataflow.yml
```

这个命令会根据dataflow.yml文件中定义的build指令，安装每个节点中pyproject.toml文件中声明的环境依赖。

#### 重要说明

- **依赖管理**：在构建新的dora工程时，请确认每个节点需要的依赖，保持所使用的工具版本一致，避免版本冲突。
- **配置更新**：如果修改了任何节点的pyproject.toml文件，需要重新运行`dora build dataflow.yml`命令以更新依赖。

### Rust节点编译

本项目包含Rust编写的节点（如dora-object-to-pose），这些节点使用Cargo.toml进行依赖管理和编译：

1. Rust节点的编译过程会自动处理Cargo.toml中定义的依赖
2. 编译会生成二进制文件或库文件，然后通过Python绑定暴露给Dora-rs

如果需要单独编译Rust节点，可以使用以下命令：

```bash
pip install -e python_nodes/dora-object-to-pose -i https://pypi.tuna.tsinghua.edu.cn/simple
```

这个命令会触发Rust代码的编译过程，并将编译后的库安装为Python包。

## 快速开始

### 本机设置

1. 进入项目根目录：
   ```bash
   cd dora-ws/dora_robot_single
   ```

2. 安装/更新依赖：
   ```bash
   dora build dataflow.yml
   ```

3. 启动 Dora 运行时与数据流：
   ```bash
   dora up
   dora start ./dataflow.yml
   ```

4. 在**工控机（相机端）**启动发送脚本：
   ```bash
   cd dora-ws/robot_camera_sender
   python realsense_tcp_sender.py --host <本机IP> --port 5002
   ```

如需调整相机分辨率/帧率，可在工控机上设置：
```bash
export COLOR_WIDTH=640 COLOR_HEIGHT=480 FPS=15
```
## 使用方法

系统启动后，您可以通过麦克风发出语音指令，例如：

- "帮我拿一瓶水"
- "帮我拿个鼠标"

系统会通过以下步骤处理您的请求：

1. 语音识别将您的指令转换为文本
2. 视觉系统识别目标物品
3. 在rerun界面中显示目标物品的框图
4. 机械臂移动并抓取目标物品

## 系统组件详解

### PC端组件

PC端运行的是主要的控制逻辑，包括：

- 语音识别处理
- 大语言模型理解
- 机械臂控制算法
- 视觉处理与目标识别
- 数据流协调

主要通过`dataflow.yml`配置文件定义各个节点之间的数据流关系。

## 手眼标定

系统使用`hand_eye_calibration-main`文件夹中的工具进行摄像头与机械臂的手眼标定，确保机械臂能够准确定位和抓取目标物品。


## 故障排除

### 常见问题

- 如果系统无法识别语音指令，请检查麦克风连接和音量设置
- 如果rerun中没有显示目标物品框图，请检查摄像头连接与相机节点是否在运行
- 如果机械臂不移动，请检查机械臂连接和控制参数

## 进阶配置

系统可以通过修改配置文件进行进一步定制，主要配置文件包括：

- `dataflow.yml`：定义PC端数据流

## 参数调整

为了适应不同的硬件设置和使用环境，您可能需要调整系统中的各种参数。以下是主要参数调整的位置和方法：

### 机械臂节点坐标调整

在`python_nodes/dora-rm65/dora_rm65/arm.py`文件中：

```python
# 夹爪长度调整（基于工具坐标系）
target_pose_baseframe = algo_handle.rm_algo_cartesian_tool(curr_joint_list, obj_pose_workframe[0], obj_pose_workframe[1], obj_pose_workframe[2]-0.2)

# 上方位置调整（基于基坐标系，因此需要进入睿尔曼官方示教器中确认当前安装角度的基坐标系朝向，代码中安装角度为侧装，垂直向上为x负轴）
above_obj_pose_baseframe = target_pose_baseframe.copy()
above_obj_pose_baseframe[0] -= 0.1  # 上方位置增加10cm

# 旋转角度调整（第108-111行）
#ADora max旋转角度
above_obj_pose_baseframe[3:] = [-0.08,-1.425,-1.927]
```

这些参数控制机械臂的抓取位置和姿态，您可以根据实际机械臂和工作环境进行调整：
- 夹爪长度：`obj_pose_workframe[2]-0.2`中的`0.2`表示夹爪长度，单位为米
- 上方位置：`above_obj_pose_baseframe[0] -= 0.1`中的`0.1`表示抓取前在目标上方的高度，单位为米
- 旋转角度：`above_obj_pose_baseframe[3:] = [-0.455,-1.396,-0.265]`定义了机械臂末端的姿态角度（rx, ry, rz）

### 坐标转换节点相机内参调整

在`python_nodes/dora-object-to-pose/src/lib.rs`文件中：

```rust
let mut focal_length = vec![6604.9804077148438, 604.8917236328125];
let mut resolution = vec![310.1200866699219, 235.96502685546875]; // 默认主点坐标
```

这些参数定义了深度相机的内参，用于将2D图像坐标转换为3D空间坐标：
- `focal_length`：相机的焦距参数 [fx, fy]
- `resolution`：相机的主点坐标 [cx, cy]

您可以使用`read_realsense_intrinsics.py`脚本读取实际相机的内参，然后更新这些值：

```bash
python read_realsense_intrinsics.py
```

脚本会输出深度相机的内参，您应该使用相机的参数来更新代码中的值。

### 状态机节点机械臂角度和标定矩阵调整

在`python_nodes/pick-place-rm65.py`文件中：

```python
# 机械臂初始位姿（最后一位为夹爪开合度，100为张开，0为关闭）
# ADora max视角
r_init_pose = [157.47799682617188, -73.1780014038086, 66.6729965209961, 57.86199951171875, 94.26499938964844, -171.822998046875,100]

# 机械臂中间位姿
# ADora max视角
r_init_middle = [
    156.772,
    -24.730,
    -62.480,
    80.768,
    125.439,
    -91.649,
    0,
]

# 机械臂结束位姿
# ADora max视角
r_init_end = [
    156.772,
    -24.730,
    -62.480,
    80.768,
    125.439,
    -91.649,
    100,
]
read_realsense_intrinsics
# 手眼标定矩阵
right_R=np.array([[ 0.99626541 , -0.00189474 , -0.08632295],
               [ 0.00235725 , 0.99998341 , 0.00525635],
               [ 0.08631156 , -0.0054402  , 0.99625334]])

right_t= np.array([[-0.06137702],
               [-0.065354842],
               [ 0.11946556]])
```

这些参数控制机械臂的运动轨迹和坐标转换：
- `r_init_pose`、`r_init_middle`、`r_init_end`：定义了机械臂的初始位姿、中间位姿和结束位姿，前6个值是关节角度（单位：度），最后一个值是夹爪状态（0-100）
- `right_R`和`right_t`：手眼标定矩阵，用于将相机坐标系中的点转换到机械臂基座坐标系中

如果您更换了机械臂或相机的位置，需要重新进行手眼标定，并更新这些矩阵值。

### 参数调整建议

1. **相机内参调整**：每次更换相机后，都应该运行`read_realsense_intrinsics.py`获取最新的相机内参，并更新到代码中。

2. **手眼标定**：如果调整了相机或机械臂的位置，需要重新进行手眼标定，更新标定矩阵。

3. **机械臂位姿**：根据实际工作环境和任务需求，调整机械臂的初始位姿、中间位姿和结束位姿。

4. **抓取参数**：根据目标物体的大小和形状，调整夹爪长度和抓取高度。
