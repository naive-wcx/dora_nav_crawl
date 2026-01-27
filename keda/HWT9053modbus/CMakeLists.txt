include_directories(
  ${DORA_INCLUDE_DIR}
  ${COMMON_INCLUDE_DIR}
  ${CMAKE_CURRENT_SOURCE_DIR}/include
)
# aux_source_directory(${CMAKE_SOURCE_DIR}/src  SRC_LIST)

add_executable(imu_driver_node src/main.cpp src/serial.cpp src/wit_c_sdk.cpp)

target_link_libraries(imu_driver_node
  ${DORA_NODE_API_LIB}
  m
  rt
  dl 
)




