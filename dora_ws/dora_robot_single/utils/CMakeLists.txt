#===========================================================
#  Dora-rs 多语言节点示例项目 - 工具CMake配置
#  Dora-rs Multi-language Nodes Example Project - Utils CMake Configuration
#===========================================================
#
#  作者/Author: wyongcheng with Claude
#  日期/Date: 2025-08-20
#  版本/Version: 1.0.0
#
#  说明/Description:
#  这个文件包含dora仓库的克隆和构建逻辑，供C和C++节点共享使用
#  This file contains the cloning and building logic for the dora repository,
#  shared by C and C++ nodes
#
#===========================================================

# 输出工具模块信息 / Output utils module information
message(STATUS "========================================================")
message(STATUS "  加载Dora-rs工具模块")
message(STATUS "  Loading Dora-rs Utils Module")
message(STATUS "========================================================")

cmake_minimum_required(VERSION 3.21)
project(dora-utils)

# 设置dora根目录路径 / Set dora root directory path
# 一定设置dora根目录路径!!!
set(DORA_ROOT_DIR "/home/ccdora-rs/dora-rs_ws/conversation_c/build/dora/src/Dora" CACHE FILEPATH "Path to the root of dora")


# 设置C和C++的包含目录和库目录 / Set include and library directories for C and C++
set(dora_c_include_dir "${CMAKE_CURRENT_BINARY_DIR}/include/c")
set(dora_cxx_include_dir "${CMAKE_CURRENT_BINARY_DIR}/include/cxx")
set(node_bridge "${CMAKE_CURRENT_BINARY_DIR}/node_bridge.cc")

if(DORA_ROOT_DIR)
    # 如果提供了dora根目录，使用本地dora / If dora root directory is provided, use local dora
    message(STATUS "使用本地Dora仓库 / Using local Dora repository: ${DORA_ROOT_DIR}")
    include(ExternalProject)
    ExternalProject_Add(Dora
        SOURCE_DIR ${DORA_ROOT_DIR}
        BUILD_IN_SOURCE True
        CONFIGURE_COMMAND ""
        BUILD_COMMAND
            cargo build
            --package dora-node-api-c
            --package dora-node-api-cxx
        INSTALL_COMMAND ""
    )

    # 为C API创建包含目录和复制头文件 / Create include directory and copy headers for C API
    add_custom_command(OUTPUT ${dora_c_include_dir}
        WORKING_DIRECTORY ${DORA_ROOT_DIR}
        DEPENDS Dora
        COMMAND
            mkdir ${dora_c_include_dir} -p
            &&
            cp apis/c/node ${dora_c_include_dir} -r
    )

    # 为C++ API创建包含目录和复制头文件 / Create include directory and copy headers for C++ API
    add_custom_command(OUTPUT ${node_bridge} ${dora_cxx_include_dir}
        WORKING_DIRECTORY ${DORA_ROOT_DIR}
        DEPENDS Dora
        COMMAND
            mkdir ${dora_cxx_include_dir} -p
            &&
            cp target/cxxbridge/dora-node-api-cxx/src/lib.rs.cc ${node_bridge}
            &&
            cp target/cxxbridge/dora-node-api-cxx/src/lib.rs.h ${dora_cxx_include_dir}/dora-node-api.h
    )
    
    # 设置库目录 / Set library directory
    set(dora_link_dirs ${DORA_ROOT_DIR}/target/debug)
else()
    # 如果没有提供dora根目录，从GitHub克隆dora / If dora root directory is not provided, clone dora from GitHub
    message(STATUS "从GitHub克隆Dora仓库 / Cloning Dora repository from GitHub")
    include(ExternalProject)
    ExternalProject_Add(Dora
        PREFIX ${CMAKE_CURRENT_BINARY_DIR}/dora
        GIT_REPOSITORY https://github.com/dora-rs/dora.git
        GIT_TAG v0.3.12 # main
        BUILD_IN_SOURCE True
        CONFIGURE_COMMAND ""
        BUILD_COMMAND
            cargo build
            --package dora-node-api-c
            --package dora-node-api-cxx
            --target-dir ${CMAKE_CURRENT_BINARY_DIR}/dora/src/Dora/target
        INSTALL_COMMAND ""
    )

    # 为C API创建包含目录和复制头文件 / Create include directory and copy headers for C API
    add_custom_command(OUTPUT ${dora_c_include_dir}
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/dora/src/Dora/target
        DEPENDS Dora
        COMMAND
            mkdir ${dora_c_include_dir} -p
            &&
            cp ../apis/c/node ${dora_c_include_dir} -r
    )

    # 为C++ API创建包含目录和复制头文件 / Create include directory and copy headers for C++ API
    add_custom_command(OUTPUT ${node_bridge} ${dora_cxx_include_dir}
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/dora/src/Dora/target
        DEPENDS Dora
        COMMAND
            mkdir ${dora_cxx_include_dir} -p
            &&
            cp cxxbridge/dora-node-api-cxx/src/lib.rs.cc ${node_bridge}
            &&
            cp cxxbridge/dora-node-api-cxx/src/lib.rs.h ${dora_cxx_include_dir}/dora-node-api.h
    )

    # 设置库目录 / Set library directory
    set(dora_link_dirs ${CMAKE_CURRENT_BINARY_DIR}/dora/src/Dora/target/debug)
endif()

# 创建C和C++ API的自定义目标 / Create custom targets for C and C++ APIs
add_custom_target(Dora_c ALL DEPENDS ${dora_c_include_dir})
add_custom_target(Dora_cxx ALL DEPENDS ${node_bridge} ${dora_cxx_include_dir})

# 导出变量，供其他CMakeLists.txt使用 / Export variables for use by other CMakeLists.txt files
set(DORA_C_INCLUDE_DIR ${dora_c_include_dir} CACHE PATH "Path to dora C API include directory")
set(DORA_CXX_INCLUDE_DIR ${dora_cxx_include_dir} CACHE PATH "Path to dora C++ API include directory")
set(DORA_NODE_BRIDGE ${node_bridge} CACHE FILEPATH "Path to dora C++ node bridge file")
set(DORA_LINK_DIRS ${dora_link_dirs} CACHE PATH "Path to dora library directory")

include_directories(
  ${DORA_C_INCLUDE_DIR}/node
  ${DORA_CXX_INCLUDE_DIR}
)

message(STATUS "========================================================")
message(STATUS "Dora C API包含目录 / Dora C API include directory: ${DORA_C_INCLUDE_DIR}")
message(STATUS "Dora C++ API包含目录 / Dora C++ API include directory: ${DORA_CXX_INCLUDE_DIR}")
message(STATUS "Dora库目录 / Dora library directory: ${DORA_LINK_DIRS}")
message(STATUS "========================================================")