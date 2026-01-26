"""
CC Dora-rs事件循环框架包安装脚本
CC Dora-rs Event Loop Framework Package Installation Script

作者/Author: Claude
日期/Date: 2025-08-21
版本/Version: 1.0.0
"""

from setuptools import setup, find_packages

with open("README.md", "w") as f:
    f.write("""# CC Dora-rs Event Loop Framework

A Python event loop framework for Dora-rs, simplifying node event handling.

## Features

- Event system for registering and triggering event handlers
- Input handler mapping for different input IDs
- Timer support with periodic and one-time timers
- Event loop encapsulation

## Installation

```bash
pip install -e .
```

## Usage

```python
from cc_dora_event_loop import EventLoop, InputEvent

# Create event loop
event_loop = EventLoop("my_node")

# Register input handler
event_loop.register_input_handler("some_input", lambda event: print(f"Received: {event.data}"))

# Register timer
event_loop.register_timer("heartbeat", 5.0, lambda: print("Heartbeat"))

# Run event loop
event_loop.run()
```
""")

setup(
    name="cc_dora_event_loop",
    version="1.0.0",
    description="CC Dora-rs Event Loop Framework",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Claude",
    author_email="claude@example.com",
    url="https://github.com/example/cc_dora_event_loop",
    packages=find_packages(),
    install_requires=[
        "dora-rs",
        "pyarrow",
    ],
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)