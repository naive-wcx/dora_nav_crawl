#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
读取RealSense D435相机内参的脚本
此脚本连接到RealSense D435相机，获取其内参，并将其打印出来和保存到文件中
"""

import pyrealsense2 as rs
import numpy as np
import json
import os
import argparse

def get_camera_intrinsics(save_to_file=True, output_file="camera_intrinsics.json"):
    """
    获取RealSense D435相机的内参
    
    Args:
        save_to_file: 是否将内参保存到文件
        output_file: 输出文件名
        
    Returns:
        内参字典
    """
    print("正在连接RealSense D435相机...")
    
    # 创建RealSense管道
    pipeline = rs.pipeline()
    config = rs.config()
    
    # 启用彩色和深度流
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    
    try:
        # 启动管道
        profile = pipeline.start(config)
        
        # 等待几帧以确保相机稳定
        for i in range(5):
            pipeline.wait_for_frames()
        
        # 获取深度流配置文件
        depth_profile = profile.get_stream(rs.stream.depth)
        depth_intrinsics = depth_profile.as_video_stream_profile().get_intrinsics()
        
        # 获取彩色流配置文件
        color_profile = profile.get_stream(rs.stream.color)
        color_intrinsics = color_profile.as_video_stream_profile().get_intrinsics()
        
        # 获取深度到彩色的外参
        depth_to_color_extrinsics = depth_profile.get_extrinsics_to(color_profile)
        
        # 创建内参字典
        intrinsics_data = {
            "depth": {
                "width": depth_intrinsics.width,
                "height": depth_intrinsics.height,
                "fx": depth_intrinsics.fx,
                "fy": depth_intrinsics.fy,
                "ppx": depth_intrinsics.ppx,
                "ppy": depth_intrinsics.ppy,
                "model": str(depth_intrinsics.model),
                "coeffs": depth_intrinsics.coeffs
            },
            "color": {
                "width": color_intrinsics.width,
                "height": color_intrinsics.height,
                "fx": color_intrinsics.fx,
                "fy": color_intrinsics.fy,
                "ppx": color_intrinsics.ppx,
                "ppy": color_intrinsics.ppy,
                "model": str(color_intrinsics.model),
                "coeffs": color_intrinsics.coeffs
            },
            "depth_to_color_extrinsics": {
                "rotation": depth_to_color_extrinsics.rotation,
                "translation": depth_to_color_extrinsics.translation
            }
        }
        
        # 打印内参信息
        print("\n相机内参信息:")
        print("深度相机:")
        print(f"  分辨率: {depth_intrinsics.width}x{depth_intrinsics.height}")
        print(f"  焦距: fx={depth_intrinsics.fx}, fy={depth_intrinsics.fy}")
        print(f"  主点: cx={depth_intrinsics.ppx}, cy={depth_intrinsics.ppy}")
        print(f"  畸变模型: {depth_intrinsics.model}")
        print(f"  畸变系数: {depth_intrinsics.coeffs}")
        
        print("\n彩色相机:")
        print(f"  分辨率: {color_intrinsics.width}x{color_intrinsics.height}")
        print(f"  焦距: fx={color_intrinsics.fx}, fy={color_intrinsics.fy}")
        print(f"  主点: cx={color_intrinsics.ppx}, cy={color_intrinsics.ppy}")
        print(f"  畸变模型: {color_intrinsics.model}")
        print(f"  畸变系数: {color_intrinsics.coeffs}")
        
        print("\n深度到彩色的外参:")
        print(f"  旋转矩阵: {depth_to_color_extrinsics.rotation}")
        print(f"  平移向量: {depth_to_color_extrinsics.translation}")
        
        # 保存到文件
        if save_to_file:
            # 将numpy数组转换为列表以便JSON序列化
            intrinsics_data["depth"]["coeffs"] = list(intrinsics_data["depth"]["coeffs"])
            intrinsics_data["color"]["coeffs"] = list(intrinsics_data["color"]["coeffs"])
            intrinsics_data["depth_to_color_extrinsics"]["rotation"] = list(intrinsics_data["depth_to_color_extrinsics"]["rotation"])
            intrinsics_data["depth_to_color_extrinsics"]["translation"] = list(intrinsics_data["depth_to_color_extrinsics"]["translation"])
            
            with open(output_file, 'w') as f:
                json.dump(intrinsics_data, f, indent=4)
            print(f"\n内参已保存到文件: {os.path.abspath(output_file)}")
        
        return intrinsics_data
        
    except Exception as e:
        print(f"错误: {e}")
        return None
    finally:
        # 停止管道
        pipeline.stop()

def format_for_dora(intrinsics_data):
    """
    将内参格式化为Dora节点可用的格式
    
    Args:
        intrinsics_data: 内参字典
        
    Returns:
        Dora格式的内参
    """
    if not intrinsics_data:
        return None
    
    # 为Dora节点准备内参数据
    dora_intrinsics = {
        "depth": {
            "width": intrinsics_data["depth"]["width"],
            "height": intrinsics_data["depth"]["height"],
            "focal": [int(intrinsics_data["depth"]["fx"]), int(intrinsics_data["depth"]["fy"])],
            "resolution": [int(intrinsics_data["depth"]["ppx"]), int(intrinsics_data["depth"]["ppy"])]
        },
        "color": {
            "width": intrinsics_data["color"]["width"],
            "height": intrinsics_data["color"]["height"],
            "focal": [int(intrinsics_data["color"]["fx"]), int(intrinsics_data["color"]["fy"])],
            "resolution": [int(intrinsics_data["color"]["ppx"]), int(intrinsics_data["color"]["ppy"])]
        }
    }
    
    print("\nDora节点格式的内参:")
    print(f"深度相机: width={dora_intrinsics['depth']['width']}, height={dora_intrinsics['depth']['height']}")
    print(f"深度相机: focal={dora_intrinsics['depth']['focal']}, resolution={dora_intrinsics['depth']['resolution']}")
    print(f"彩色相机: width={dora_intrinsics['color']['width']}, height={dora_intrinsics['color']['height']}")
    print(f"彩色相机: focal={dora_intrinsics['color']['focal']}, resolution={dora_intrinsics['color']['resolution']}")
    
    # 保存Dora格式的内参
    with open("dora_camera_intrinsics.json", 'w') as f:
        json.dump(dora_intrinsics, f, indent=4)
    print(f"Dora格式的内参已保存到文件: {os.path.abspath('dora_camera_intrinsics.json')}")
    
    return dora_intrinsics

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='读取RealSense D435相机内参')
    parser.add_argument('--save', action='store_true', help='保存内参到文件')
    parser.add_argument('--output', type=str, default='camera_intrinsics.json', help='输出文件名')
    args = parser.parse_args()
    
    # 获取相机内参
    intrinsics_data = get_camera_intrinsics(save_to_file=args.save, output_file=args.output)
    
    # 格式化为Dora节点可用的格式
    if intrinsics_data:
        format_for_dora(intrinsics_data)