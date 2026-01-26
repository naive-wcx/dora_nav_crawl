#===========================================================
#  Dora-rs 多语言节点示例项目 - 顶层CMake配置
#  Dora-rs Multi-language Nodes Example Project - Top-level CMake Configuration
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

cmake_minimum_required(VERSION 3.21)
project(dora-example-project 
        VERSION 1.0.0
        DESCRIPTION "Dora-rs Multi-language Nodes Example Project"
        LANGUAGES C CXX)

# 输出项目信息 / Output project information
message(STATUS "========================================================")
message(STATUS "  Dora-rs 多语言节点示例项目")
message(STATUS "  Dora-rs Multi-language Nodes Example Project")
message(STATUS "========================================================")
message(STATUS "项目版本/Project Version: ${PROJECT_VERSION}")
message(STATUS "CMake版本/CMake Version: ${CMAKE_VERSION}")
message(STATUS "构建类型/Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C编译器/C Compiler: ${CMAKE_C_COMPILER_ID} ${CMAKE_C_COMPILER_VERSION}")
message(STATUS "C++编译器/C++ Compiler: ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "构建目录/Build Directory: ${CMAKE_BINARY_DIR}")
message(STATUS "========================================================")

# 包含utils目录中的CMakeLists.txt / Include CMakeLists.txt from utils directory
include(${CMAKE_CURRENT_SOURCE_DIR}/utils/CMakeLists.txt)

# 添加C和C++节点的子目录 / Add subdirectories for C and C++ nodes
add_subdirectory(c_nodes)
add_subdirectory(cpp_nodes)

# 创建安装目标 / Create installation target
install(DIRECTORY DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/../bin)

message(STATUS "========================================================")
message(STATUS "  配置完成 / Configuration completed")
message(STATUS "========================================================")