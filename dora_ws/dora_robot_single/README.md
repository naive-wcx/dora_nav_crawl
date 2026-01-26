# Dora-rs 多语言节点例程

本仓库使用Dora-rs创建C、C++和Python三种语言的节点，并让它们互相通信。  

本仓库是大型项目的模板工程，基于 Dora-rs 0.3.12。

## 项目结构

```
dora-rs_example_project/
├── c_nodes/                # C语言节点
│   ├── talker/             # C语言talker节点
│   │   └── node.c
│   ├── listener/           # C语言listener节点
│   │   └── node.c
│   └── CMakeLists.txt      # C语言节点的子构建文件
├── cpp_nodes/              # C++语言节点
│   ├── talker/             # C++语言talker节点
│   │   └── node.cc
│   ├── listener/           # C++语言listener节点
│   │   └── node.cc
│   ├── text_output/        # C++文本输出节点
│   │   └── node.cc
│   └── CMakeLists.txt      # C++语言节点的子构建文件
├── python_nodes/           # Python语言节点
│   ├── talker/             # Python语言talker节点
│   │   ├── talker/
│   │   │   └── main.py
│   │   └── setup.py
│   ├── listener/           # Python语言listener节点
│   │   ├── listener/
│   │   │   └── main.py
│   │   └── setup.py
│   └── vision_node/        # Python摄像头视觉识别节点
│       ├── vision_node/
│       │   └── main.py
│       └── setup.py
├── utils/                  # 工具目录
│   └── CMakeLists.txt      # 共享的CMake构建逻辑
├── bin/                    # 构建输出目录
├── CMakeLists.txt          # 顶层CMake构建文件
└── dataflow.yml            # 主配置文件，用于连接所有节点
```

## 构建系统

分层 CMake 构建：

1. **顶层CMakeLists.txt**：控制整个C/C++部分的构建，包含子目录
2. **utils/CMakeLists.txt**：所有C/C++共享dora目录
3. **c_nodes/CMakeLists.txt**：C节点例程
4. **cpp_nodes/CMakeLists.txt**：C++节点例程

## 运行

注意， pip 安装的 `dora_rs_cli` 和全局运行时 `dora-cli` 版本需一致。本仓库构建系统在`dora-rs_example_project/CMakeLists.txt:82`和接下来的安装指令中，都指定了 dora-rs 版本，可根据实际情况修改。

1. 安装 Dora-rs：
   ```bash
   # dora runtime
   curl --proto '=https' --tlsv1.2 -LsSf https://github.com/dora-rs/dora/releases/v0.3.12/download/dora-cli-installer.sh | sh
   # virtual environment
   conda create -n dora-rs python=3.11
   pip install dora-rs-cli==0.3.12 -i https://pypi.tuna.tsinghua.edu.cn/simple
   pip install dora-rs==0.3.12 -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

2. 安装 Rust 构建系统
   ```bash
   curl https://sh.rustup.rs -sSf | sh
   ```

3. 安装自定义的一些 python 依赖
   ```bash
   # 进入包目录
   cd dora-rs_example_project/utils/event_loop/python
   # 安装包（开发模式）
   pip install -e .
   # 或者 进入包目录
   # cd dora-rs_example_project/utils/event_loop/python
   # 安装包
   # pip install .
   ```

4. 构建并运行项目：

   ```bash
   cd dora-rs_example_project
   ./build.sh
   dora up
   dora start ./dataflow.yml
   ```

## 节点间通信

在这个示例中，所有的talker节点都会发送消息，所有的listener节点都会接收这些消息。这展示了不同语言编写的节点互相通信。

- C语言talker节点每500毫秒发送一次消息
- C++语言talker节点每700毫秒发送一次消息
- Python语言talker节点每1000毫秒发送一次消息

所有的listener节点都会接收并打印这些消息，展示了跨语言通信的能力。
情况
注意 dora-rs 没有在C/C++支持其他类型，需要自己手动序列化为UInt8字节流，然后解码。否则出现以下错误
> dora C++ Node does not yet support higher level type of arrow. Only UInt8.

## 事件循环

## 日志系统

## 数据类型
由于dora-rs 在C/C++仅支持 Arrow UInt8 字节流，因此本示例工程没有使用如下的 dora-rs 的示范项目方法:

```python
node.send_output(
   "speech", 
   pa.array(["Hello World"])
   )
```

该方法把所有的数据都打包成只有一个元素的 list ，在接收时取第一个元素：

```python
message = event["value"][0].as_py()
```

本工程手动序列化成 uint8 并传输 Arrow uint list 类型:
(ps: 期待 dora 以后拓展一下事件循环等功能, 添加更多类型支持)
```python
self.event_loop.node.send_output(
   "vision_result", 
   pa.array(
      list(message_bytes), 
      type=pa.uint8()
      )
   
   )
```

接收:

```python
# event loop Event code
cls(
      id = event["id"],
      data = pa.array([]) if event["id"] == 'tick' else event["value"]
   )
# node code
data_bytes = bytes(event.data.to_pylist()).decode('utf-8')
response = json.loads(data_bytes)
```

## 可视化界面

可视化界面使用 Rerun 实现, 安装 python 依赖。
```bash
pip3 install rerun-sdk -i https://pypi.tuna.tsinghua.edu.cn/simple
rerun # 直接能打开才对
```

如果不想保存时间线，在记录时添加参数 `static=True`

```python
rr.log("vision/llm_text",
         rr.TextLog(self.llm_text),
         static=True
         )
```

使用 conda 管理 C++ 依赖 

```bash
conda install -c conda-forge librerun-sdk rerun-sdk
```

然后在 `Cmakelists.txt`里添加
```cmake
find_package(rerun_sdk REQUIRED)
 
# …
 
target_link_libraries(<yourtarget> PRIVATE rerun_sdk)
```


## 扩展

你可以通过以下方式扩展这个项目：

1. 添加更多的节点
2. 修改现有节点的功能
3. 添加更复杂的数据处理逻辑
4. 尝试使用其他Dora-rs支持的语言

