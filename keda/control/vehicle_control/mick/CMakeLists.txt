#========================
#  serial
#========================
set(SRC_SERIAL
    ./thirdparty/serial/src/serial.cc
    ./thirdparty/serial/src/impl/unix.cc
    ./thirdparty/serial/src/impl/list_ports/list_ports_linux.cc
)
set(SERIAL_INCLUDE_DIR ./thirdparty/serial/include)
add_library(serial ${SRC_SERIAL})
target_include_directories(serial PRIVATE ${SERIAL_INCLUDE_DIR})
target_link_libraries(serial rt pthread)
install(TARGETS serial)

include_directories(
    include
    ${COMMON_INCLUDE_DIR}
    ${EIGEN3_INCLUDE_DIRS}
    ${DORA_INCLUDE_DIR}
    ${SERIAL_INCLUDE_DIR}
)


add_executable(mickx4_bringup_v3_node
    ./mickx4_bringup_v3_node.cc
)
target_link_libraries(mickx4_bringup_v3_node
    ${DORA_NODE_API_LIB}
    serial
    rt
    dl
)

add_executable(adora_chassis_a2pro_dora_node
    ./adora_chassis_a2pro_dora_node.cc
)
target_link_libraries(adora_chassis_a2pro_dora_node
    ${DORA_NODE_API_LIB}
    serial
    rt
    dl
)

# install(TARGETS
#     mickx4_bringup_v3_node
# )