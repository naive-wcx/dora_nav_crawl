#!/bin/bash

#===========================================================
#  Dora-rs 多语言节点示例项目构建脚本
#  Dora-rs Multi-language Nodes Example Project Build Script
#===========================================================
#
#  作者/Author: wyongcheng with Claude
#  日期/Date: 2025-08-20
#  版本/Version: 1.0.0
#
#  环境要求/Environment Requirements:
#  - CMake >= 3.21
#  - GCC/Clang with C++17 support
#  - Dora-rs == 0.3.12
#
#===========================================================

echo "=========================================================="
echo "  Dora-rs 多语言节点示例项目"
echo "  Dora-rs Multi-language Nodes Example Project"
echo "=========================================================="
echo "构建时间/Build Time: $(date)"
echo "构建系统/Build System: $(uname -s) $(uname -r)"
echo "构建目录/Build Directory: $(pwd)"
echo "=========================================================="

set -e

# 创建构建目录 / Create build directory
echo "创建构建目录 / Creating build directory..."
mkdir -p build
cd build

# 配置项目 / Configure project
echo "配置项目 / Configuring project..."
cmake ..

# 构建项目 / Build project
echo "构建项目 / Building project..."
make

# 安装构建产物 / Install build artifacts
echo "安装构建产物 / Installing build artifacts..."
make install

# 构建 dora-rs python / Building dora-rs python
echo "构建 dora-rs python / Building dora-rs python..."
cd ..  # 返回项目根目录 / Return to project root directory
# dora build $(pwd)/dataflow.yml --uv

echo "=========================================================="
echo "  构建完成 / Build completed successfully!"
echo "=========================================================="