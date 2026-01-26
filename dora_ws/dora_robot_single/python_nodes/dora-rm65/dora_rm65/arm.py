import os
import time
import sys
import logging
import numpy as np
import pyarrow as pa
from dora import Node

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from Robotic_Arm.rm_robot_interface import *

# RIGHT_ROBOT_IP = os.getenv("ROBOT_IP", "192.168.1.18")
# LEFT_ROBOT_IP = os.getenv("ROBOT_IP", "192.168.1.19")


class robot_rm65:
    def __init__(self):
        #---------------------------------connect
        self.right_arm = RoboticArm(rm_thread_mode_e.RM_TRIPLE_MODE_E)
        right_connect=self.right_arm.rm_create_robot_arm("192.168.1.19", 8080)
        #---------------------------------right_arm init
        self.right_arm.rm_set_arm_run_mode(2)
        self.right_arm.rm_set_tool_voltage(3) 
        self.right_arm.rm_set_modbus_mode(1,115200,2)   
        self.right_write_params = rm_peripheral_read_write_params_t(1, 40000, 1)
        self.right_arm.rm_write_single_register(self.right_write_params,100)
        error_code, curr_state = self.right_arm.rm_get_current_arm_state()
        if error_code == 0:            
            curr_arm_pose = curr_state['pose']
            curr_joint = curr_state['joint']
            print(f"arm pose {curr_arm_pose}, arm joints {curr_joint}")
        else:
            print(f"获取机械臂状态失败，错误码: {error_code}") 
        # self.right_arm.rm_change_tool_frame("lebai2")


def main():
    print("初始化节点")
    node = Node()
    print("初始化机械臂")
    rm65=robot_rm65()
    print("初始化完成，等待指令...")
    for event in node:
        print(f"收到事件: {event['type']} - {event.get('id', 'unknown')}")
        if event["type"] == "INPUT" and (event["id"] == "pose_r" or event["id"]=="pose_l"):  # 修正缩进：统一使用4个空格
            print(f"处理{event['id']}事件")
            values: np.array = event["value"].to_numpy(zero_copy_only=False)
            encoding = event["metadata"]["encoding"]
            print(f"编码类型: {encoding}")
            wait = event["metadata"].get("wait", True)
            duration = float(event["metadata"].get("duration", 1))
            grasp = event["metadata"].get("grasp", True)
            arm_p = event["metadata"].get("arm","right")
            print(f"机械臂: {arm_p}, 持续时间: {duration}")
            if encoding == "xyzrpy":
                # 确保正确解析xyzrpy数据：前6个值是位置和姿态，第7个是夹爪值
                values = values.reshape((-1, 7))
                for i, value in enumerate(values):
                    print(f"Processing row {i+1}/{len(values)}")
                    obj_pose_workframe = [
                        float(value[0]),  # x
                        float(value[1]),  # y
                        float(value[2]),  # z
                        float(value[3]),  # rx
                        float(value[4]),  # ry
                        float(value[5]),  # rz
                     ]
                    print(f"收到目标物体位姿（workframe）：{obj_pose_workframe}")
                    gripper = float(value[6])  # 夹爪值
                    if arm_p=="right":
                        # 初始化移动结果变量
                        move_p = 1  # 默认为错误状态
                        
                        # 获取当前机械臂状态
                        error_code, curr_state = rm65.right_arm.rm_get_current_arm_state()
                        if error_code != 0:
                            print(f"获取机械臂状态失败，错误码: {error_code}")
                            node.send_output("response_r_arm", pa.array([False]), metadata={"error": "Failed to get arm state"})
                            continue
                            
                        curr_arm_pose = curr_state['pose']
                        curr_joint = curr_state['joint']
                        print(f"arm pose {curr_arm_pose}, arm joints {curr_joint}")
                        # 获取当前关节角度
                        curr_joint_list = curr_joint
                        
                        # # 创建算法接口实例
                        algo_handle = Algo(rm_robot_arm_model_e.RM_MODEL_RM_65_E, rm_force_type_e.RM_MODEL_RM_B_E)

                        # 创建工具坐标系下的目标位姿                        
                        # 夹爪长度  == 0.3m
                        target_pose_baseframe = algo_handle.rm_algo_cartesian_tool(curr_joint_list, obj_pose_workframe[0], obj_pose_workframe[1], obj_pose_workframe[2]-0.2)

                        # 创建上方位置
                        target_pose_baseframe[1] -= 0.03
                        target_pose_baseframe[0] += 0.05

                        above_obj_pose_baseframe = target_pose_baseframe.copy()
                        above_obj_pose_baseframe[0] -= 0.05  # 上方位置增加10cm
                        #ADora max旋转角度
                        # above_obj_pose_baseframe[3:] = [-0.08,-1.425,-1.927]
                        #Single_desktop旋转角度
                        above_obj_pose_baseframe[3:] = [-1.547, -0.006, -1.593]
                        # time.sleep(10)
                        # [-1.547, -0.006, -1.593]
                        # [-0.455,-1.396,-0.265]
                        print("目标物体上方位置:", above_obj_pose_baseframe)

                        # 先移动到目标物体上方位置
                        print("移动到目标物体上方...")
                        approach_pose_result = rm65.right_arm.rm_movej_p(above_obj_pose_baseframe, 20, 0, 0, 1)
                        print("移动到目标物体上方结果:", approach_pose_result)
                        
                        if approach_pose_result == 0:
                            # 移动到目标位置
                            print("移动到目标位置...")
                            move_p = rm65.right_arm.rm_movej_p(target_pose_baseframe, 20, 0, 0, 1)
                            print("目标位置移动结果:", move_p)
                            
                            # 设置夹爪状态（0表示关闭夹爪，用于抓取）
                            try:
                                print("关闭夹爪进行抓取...")
                                gripper_result = rm65.right_arm.rm_write_single_register(rm65.right_write_params, 0)
                                print("夹爪关闭结果:", gripper_result)
                                if gripper_result != 0:
                                    print(f"夹爪控制失败，错误码: {gripper_result}")
                            except Exception as e:
                                print("夹爪控制错误:", e)
                                
                            # 等待夹爪动作完成
                            time.sleep(0.5)
                        else:
                            move_p = approach_pose_result  # 如果上方位置失败，使用其结果
                            print(f"移动到接近位置失败，错误码: {move_p}")
                    # 发送操作结果
                    if move_p != 0:
                        print(f"抓取操作失败，错误码: {move_p}")
                        node.send_output("response_r_arm", pa.array([False]), metadata={"error": f"Failed to grasp, error code: {move_p}"})
                        continue  # 使用continue而不是break，以便处理后续事件
                    else:
                        print("抓取操作成功完成")
                        node.send_output("response_r_arm", pa.array([True]), metadata={"message": "Grasp operation completed successfully"})
      
            elif encoding == "jointstate":
                # 修正数据结构：r_init_pose中有7个元素，前6个是关节角度，最后1个是夹爪值
                values = values.reshape((-1, 7))
                arm_j=event["metadata"].get("arm","right")
                print(f"关节状态数据: {values}")
                for value in values:
                    # 确保使用正确的关节数据：六轴机械臂需要6个关节角度
                    joints = value[:6].tolist()
                    gripper = value[6]
                    print(f"关节角度: {joints}")
                    print(f"夹爪值: {gripper}")
                    if arm_p=="right":
                        try:
                            print("执行关节运动...")
                            move_j=rm65.right_arm.rm_movej(joints, 40, 0, 0, 1)
                            print(f"关节运动结果: {move_j}")
                            logging.info("初始位置调用")
                            try:
                                print("设置夹爪...")
                                response_gripper = rm65.right_arm.rm_write_single_register(rm65.right_write_params,int(gripper))
                                print(f"夹爪设置结果: {response_gripper}")
                            except Exception as e:
                                print(f"夹爪设置错误: {e}")
                            time.sleep(0.2)
                        except Exception as e:
                            print(f"关节运动错误: {e}")
                            move_j = 1  # 设置为错误状态
                
                # 无论成功与否，都发送响应，确保状态机不会一直等待
                if arm_p=="right":
                    success = move_j==0
                    print(f"发送响应: {success}")
                    node.send_output("response_r_arm", pa.array([success]))