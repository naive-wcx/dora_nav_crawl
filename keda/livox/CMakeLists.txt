
#---------------------------------------------------------------------------------------
# include file
#---------------------------------------------------------------------------------------
include_directories(
  ${APR_INCLUDE_DIRS}
  ${YAMLCPP_INCLUDE_DIRS}
  ${DORA_INCLUDE_DIR}
  ./3rdparty/Livox-SDK/include
  ./3rdparty
  src
)


set(LIVOX_SDK_LIB "${CMAKE_CURRENT_SOURCE_DIR}/3rdparty/Livox-SDK/lib/liblivox_lidar_sdk_static.a")


# if(NOT EXISTS ${LIVOX_SDK_LIB})
#   message(FATAL_ERROR "Livox SDK静态库文件不存在: ${LIVOX_SDK_LIB}")
# endif()

add_executable(livox_dora_driver_node
  src/lds.cpp
  src/lds_lidar.cpp
  src/lddc_dora.cpp
  src/livox_dora_driver2.cpp

  src/comm/comm.cpp
  src/comm/ldq.cpp
  src/comm/semaphore.cpp
  src/comm/lidar_imu_data_queue.cpp
  src/comm/cache_index.cpp
  src/comm/pub_handler.cpp

  src/parse_cfg_file/parse_cfg_file.cpp
  src/parse_cfg_file/parse_livox_lidar_cfg.cpp

  src/call_back/lidar_common_callback.cpp
  src/call_back/livox_lidar_callback.cpp
)


#---------------------------------------------------------------------------------------
# link libraries
#---------------------------------------------------------------------------------------
target_link_libraries(livox_dora_driver_node
  ${DORA_NODE_API_LIB}
  # ${LIVOX_LIDAR_SDK_LIBRARY}
  # ${Boost_LIBRARY}
  ${LIVOX_SDK_LIB}
  m
  rt
  dl
  pthread
)

install(TARGETS livox_dora_driver_node)
