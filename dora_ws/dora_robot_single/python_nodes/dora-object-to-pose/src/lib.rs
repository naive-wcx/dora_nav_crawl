use core::f32;
use dora_node_api::{
    arrow::{
        array::{AsArray, Float64Array, UInt8Array},
        datatypes::{Float32Type, Int64Type},
    },
    dora_core::config::DataId,
    DoraNode, Event, IntoArrow, Parameter,
};
use eyre::Result;
use std::collections::HashMap;

fn points_to_pose(points: &[(f32, f32, f32)]) -> Vec<f32> {
    let (_x, _y, _z, sum_xy, sum_x2, sum_y2, n, x_min, x_max, y_min, y_max, z_min, z_max) =
        points.iter().fold(
            (
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 10.0, -10.0, 10.0, -10.0, 10., -10.0,
            ),
            |(
                acc_x,
                acc_y,
                acc_z,
                acc_xy,
                acc_x2,
                acc_y2,
                acc_n,
                acc_x_min,
                acc_x_max,
                acc_y_min,
                acc_y_max,
                acc_z_min,
                acc_z_max,
            ),
             (x, y, z)| {
                (
                    acc_x + x,
                    acc_y + y,
                    acc_z + z,
                    acc_xy + x * y,
                    acc_x2 + x * x,
                    acc_y2 + y * y,
                    acc_n + 1.,
                    f32::min(acc_x_min, *x),
                    f32::max(acc_x_max, *x),
                    f32::min(acc_y_min, *y),
                    f32::max(acc_y_max, *y),
                    f32::min(acc_z_min, *z),
                    f32::max(acc_z_max, *z),
                )
            },
        );
    let (mean_x, mean_y, mean_z) = (
        (x_max + x_min) / 2.,
        (y_max + y_min) / 2.,
        (z_max + z_min) / 2.,
    );

    // Compute covariance and standard deviations
    let cov = sum_xy / n - mean_x * mean_y;
    let std_x = (sum_x2 / n - mean_x * mean_x).sqrt();
    let std_y = (sum_y2 / n - mean_y * mean_y).sqrt();
    let corr = cov / (std_x * std_y);

    vec![mean_x, mean_y, mean_z, 0., 0., corr * f32::consts::PI / 2.]
}

pub fn lib_main() -> Result<()> {
    let (mut node, mut events) = DoraNode::init_from_env()?;
    let mut image_cache = HashMap::new();

    let mut depth_frame = None;
    let mut width = 640;
    let mut height = 480; // 修正为RealSense D435的默认高度
    let mut focal_length = vec![604.9804077148438, 604.8917236328125];
    let mut resolution = vec![310.1200866699219, 235.96502685546875]; // 默认主点坐标
    let mut depth_values_stats = Vec::new(); // 用于收集深度值统计信息
    
    // 相机参数
    let camera_pitch = std::env::var("CAMERA_PITCH")
        .unwrap_or("2.47".to_string())
        .parse::<f32>()
        .unwrap();
    let cos_theta = camera_pitch.cos();
    let sin_theta = camera_pitch.sin();
    
    // println!("初始化object-to-pose节点，默认参数：");
    // println!("  分辨率: {}x{}", width, height);
    // println!("  焦距: {:?}", focal_length);
    // println!("  主点: {:?}", resolution);
    // println!("  相机俯仰角: {}", camera_pitch);

    while let Some(event) = events.recv() {
        if let Event::Input { id, metadata, data } = event {
            match id.as_str() {
                "image" => {
                    let buffer: &UInt8Array = data.as_any().downcast_ref().unwrap();
                    image_cache.insert(id.clone(), buffer.values().to_vec());
                }
                "depth" => {
                    // println!("接收到深度图像数据");
                    
                    // 提取元数据
                    if let Some(Parameter::Integer(h)) = metadata.parameters.get("height") {
                        height = *h;
                        // println!("  深度图像高度: {}", height);
                    }
                    
                    if let Some(Parameter::Integer(w)) = metadata.parameters.get("width") {
                        width = *w;
                        // println!("  深度图像宽度: {}", width);
                    }
                    
                    if let Some(Parameter::ListInt(focals)) = metadata.parameters.get("focal") {
                        // 将整数向量转换为浮点数向量
                        focal_length = focals.iter().map(|&x| x as f32).collect();
                        // println!("  相机焦距: fx={}, fy={}", focal_length[0], focal_length[1]);
                    }
                    
                    if let Some(Parameter::ListInt(res)) = metadata.parameters.get("resolution") {
                        // 将整数向量转换为浮点数向量
                        resolution = res.iter().map(|&x| x as f32).collect();
                        // println!("  相机主点: cx={}, cy={}", resolution[0], resolution[1]);
                    }
                    
                    // 处理深度数据
                    let buffer: &Float64Array = data.as_any().downcast_ref().unwrap();
                    // println!("  深度数据长度: {}", buffer.len());
                    
                    // 收集深度值统计信息
                    depth_values_stats.clear();
                    let mut min_depth = f64::MAX;
                    let mut max_depth: f64 = 0.0;
                    let mut sum_depth = 0.0;
                    let mut valid_count = 0;
                    
                    for i in 0..std::cmp::min(buffer.len(), 100) {
                        let depth = buffer.value(i);
                        if depth > 0.0 {
                            min_depth = min_depth.min(depth);
                            max_depth = max_depth.max(depth);
                            sum_depth += depth;
                            valid_count += 1;
                            
                            if depth_values_stats.len() < 10 {
                                depth_values_stats.push(depth);
                            }
                        }
                    }
                    
                    if valid_count > 0 {
                        let avg_depth = sum_depth / valid_count as f64;
                        // println!("  深度值范围: {:.4} - {:.4} 米, 平均: {:.4} 米",
                        //         min_depth, max_depth, avg_depth);
                        // println!("  深度值样本: {:?}", depth_values_stats);
                    } else {
                        // println!("  警告: 未找到有效深度值!");
                    }
                    
                    depth_frame = Some(buffer.clone());
                }
                "masks" => {
                    let masks = if let Some(data) = data.as_primitive_opt::<Float32Type>() {
                        let data = data
                            .iter()
                            .map(|x| if let Some(x) = x { x > 0. } else { false })
                            .collect::<Vec<_>>();
                        data
                    } else if let Some(data) = data.as_boolean_opt() {
                        let data = data
                            .iter()
                            .map(|x| x.unwrap_or_default())
                            .collect::<Vec<_>>();
                        data
                    } else {
                        println!("Got unexpected data type: {}", data.data_type());
                        continue;
                    };
                    println!("width: {}, height: {}", width, height);
                    let outputs: Vec<Vec<f32>> = masks
                        .chunks(height as usize * width as usize)
                        .filter_map(|data| {
                            let mut points = vec![];
                            let mut z_total = 0.;
                            let mut n = 0.;

                            if let Some(depth_frame) = &depth_frame {
                                depth_frame.iter().enumerate().for_each(|(i, z)| {
                                    let u = i as f32 % width as f32; // Calculate x-coordinate (u)
                                    let v = i as f32 / width as f32; // Calculate y-coordinate (v)

                                    if let Some(z) = z {
                                        let z = z as f32;
                                        // 跳过无效深度值，但放宽距离限制
                                        if z == 0. {
                                            return;
                                        }
                                        
                                        // 放宽深度限制，允许更远的物体
                                        if z > 2.0 {
                                            return;
                                        }
                                        
                                        if data[i] {
                                            // let x = (u - resolution[0] as f32) * z
                                            //     / focal_length[0] as f32;
                                            // let y = (v - resolution[1] as f32) * z
                                            //     / focal_length[1] as f32;
                                            // 使用从相机获取的实际内参
                                            let x = (u - resolution[0] as f32) * z / focal_length[0] as f32;
                                            let y = (v - resolution[1] as f32) * z / focal_length[1] as f32;
                                            let new_x = x;
                                            let new_y = y;
                                            let new_z = z;

                                            points.push((new_x, new_y, new_z));
                                            z_total += new_z;
                                            n += 1.;
                                        }
                                    }
                                });
                            } else {
                                println!("No depth frame found");
                                return None;
                            }
                            if points.is_empty() {
                                println!("No points in mask found");
                                return None;
                            }
                            Some(points_to_pose(&points))
                        })
                        .collect();
                    let flatten_data = outputs.into_iter().flatten().collect::<Vec<_>>();
                    let mut metadata = metadata.parameters.clone();
                    metadata.insert(
                        "encoding".to_string(),
                        Parameter::String("xyzrpy".to_string()),
                    );
                    println!("Got data: {:?}", flatten_data);

                    node.send_output(
                        DataId::from("pose".to_string()),
                        metadata,
                        flatten_data.into_arrow(),
                    )?;
                }
                "boxes2d" => {
                    println!("接收到边界框数据");
                    if let Some(data) = data.as_primitive_opt::<Int64Type>() {
                        let rgb_width = 640;
                        let rgb_height = 480;
                        let scale_x = width as f32 / rgb_width as f32;
                        let scale_y = height as f32 / rgb_height as f32;
                        
                        println!("  边界框缩放比例: scale_x={}, scale_y={}", scale_x, scale_y);
                        println!("  深度图像尺寸: {}x{}", width, height);
                        println!("  RGB图像尺寸: {}x{}", rgb_width, rgb_height);
                        
                        let values = data.values();
                        println!("  边界框数据: {:?}", values);
                        
                        let mut pose_data = vec![];
                        let outputs: Vec<Vec<f32>> = values
                            .chunks(4)
                            .filter_map(|data| {
                                // 原始边界坐标
                                let mut is_active: bool = true;
                                let x_min_orig = (data[0] as f32) * scale_x;
                                let y_min_orig = (data[1] as f32) * scale_y;
                                let x_max_orig = (data[2] as f32) * scale_x;
                                let y_max_orig = (data[3] as f32) * scale_y;
                                
                                // 计算中心点和缩小后的尺寸
                                let center_x = ((x_min_orig + x_max_orig) / 2.0 ) as usize;
                                let center_y = ((y_min_orig + y_max_orig) / 2.0 ) as usize;
                                let center_x = center_x as f32;
                                let center_y = center_y as f32;
                                // 不再缩小边界框，使用完整尺寸
                                let new_width = x_max_orig - x_min_orig;
                                let new_height = y_max_orig - y_min_orig;
                                
                                println!("  原始边界框: x=[{}, {}], y=[{}, {}]",
                                         x_min_orig, x_max_orig, y_min_orig, y_max_orig);
                                println!("  边界框中心点: ({}, {})", center_x, center_y);
                                println!("  边界框尺寸: {}x{}", new_width, new_height);
                                let x_min = center_x - new_width / 2.0;
                                let x_max = center_x + new_width / 2.0;
                                let y_min = center_y - new_height / 2.0;
                                let y_max = center_y + new_height / 2.0;

                                let mut points = vec![];
                                let mut z_min = 100.;
                                let mut z_total = 0.;
                                let mut n = 0.;
                                println!("  相机参数: 主点=({}, {}), 焦距=({}, {})",
                                         resolution[0], resolution[1], focal_length[0], focal_length[1]);
                                if let Some(depth_frame) = &depth_frame {
                                    
                                    depth_frame.iter().enumerate().for_each(|(i, z)| {
                                        
                                        if i >= (width as usize * height as usize) {
                                            return;
                                        }
                                        let u =(i % width as usize) as f32; 
                                        let v =(i / width as usize) as f32;
                                        

                                        if let Some(z) = z {
                                            let z = z as f32;

                                            // 检查是否在边界框中心点附近（使用更大的范围）
                                            if (u>=center_x-3.0 && u<=center_x+3.0) && (v>=center_y-3.0 && v<=center_y+3.0) && is_active
                                            {
                                                println!("  找到中心点附近的像素: u={}, v={}", u, v);
                                                if z>0.0
                                                {
                                                    // 使用从相机获取的实际内参
                                                    let x_test = (u - resolution[0] as f32) * z / focal_length[0] as f32;
                                                    let y_test = (v - resolution[1] as f32) * z / focal_length[1] as f32;
                                                    
                                                    println!("  中心点3D坐标: x={:.4}, y={:.4}, z={:.4}", x_test, y_test, z);
                                                    is_active = false;
                                                    
                                                    // 记录位姿数据
                                                    pose_data.extend(vec![
                                                        x_test,
                                                        y_test,
                                                        z,
                                                        0.0,
                                                        0.0,
                                                        0.0
                                                    ]);
                                                } else {
                                                    println!("  警告: 中心点深度值无效!");
                                                }
                                            }

                                            
                                            // 放宽深度过滤条件
                                            if z == 0. {
                                                return; // 仍然跳过无效深度值
                                            }
                                            
                                            // 放宽距离限制
                                            if z > 2.0 {
                                                return;
                                            }
                                            if u > x_min && u < x_max && v > y_min && v < y_max {
                                                // 使用从相机获取的实际内参
                                                let x = (u - resolution[0] as f32) * z / focal_length[0] as f32;
                                                let y = (v - resolution[1] as f32) * z / focal_length[1] as f32;

                                                let new_x = x;
                                                let new_y = y;
                                                let new_z = z;
                                                if  new_z < z_min 
                                                {
                                                    z_min = new_z;
                                                }
                                                points.push((new_x, new_y, new_z));
                                                z_total += new_z;
                                                n += 1.;
                                            }
                                        }
                                    });
                                } else {
                                    println!("No depth frame found");
                                    return None;
                                }
                                // 检查是否有足够的点
                                if points.is_empty() {
                                    println!("  警告: 边界框内没有有效的深度点!");
                                    
                                    // 如果已经有中心点位姿数据，仍然返回结果
                                    if !pose_data.is_empty() {
                                        println!("  使用中心点位姿数据作为备选方案");
                                        return Some(vec![
                                            pose_data[0], pose_data[1], pose_data[2],
                                            pose_data[3], pose_data[4], pose_data[5]
                                        ]);
                                    }
                                    
                                    return None;
                                }
                                
                                println!("  边界框内有效点数量: {}", points.len());
                                let raw_mean_z = z_total / n as f32;
                                let threshold = (raw_mean_z + z_min) / 2.;
                                let points = points
                                    .into_iter()
                                    .filter(|(_x, _y, z)| z > &threshold)
                                    .collect::<Vec<_>>();
                                Some(points_to_pose(&points))
                            })
                            .collect();
                        let flatten_data = pose_data.clone();
                        // let flatten_data = outputs.into_iter().flatten().collect::<Vec<_>>();
                        // let flatten_data = pose_data.into_iter().flatten().collect::<Vec<_>>();
                        println!("  计算得到的位姿数据: {:?}", flatten_data);
                        let mut metadata = metadata.parameters.clone();
                        metadata.insert(
                            "encoding".to_string(),
                            Parameter::String("xyzrpy".to_string()),
                        );

                        // 检查位姿数据是否有效
                        if flatten_data.is_empty() {
                            println!("  错误: 位姿数据为空，不发送输出");
                        } else {
                            println!("  发送位姿数据到状态机");
                            node.send_output(
                                DataId::from("pose".to_string()),
                                metadata,
                                flatten_data.into_arrow(),
                            )?;
                            println!("  位姿数据发送成功");
                        }
                    }
                }
                other => println!("接收到未处理的输入: `{other}`"),
            }
        }
    }

    Ok(())
}

#[cfg(feature = "python")]
use pyo3::{
    pyfunction, pymodule,
    types::{PyModule, PyModuleMethods},
    wrap_pyfunction, Bound, PyResult, Python,
};

#[cfg(feature = "python")]
#[pyfunction]
fn py_main(_py: Python) -> eyre::Result<()> {
    lib_main()
}

/// A Python module implemented in Rust.
#[cfg(feature = "python")]
#[pymodule]
fn dora_object_to_pose(_py: Python, m: Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(py_main, &m)?)?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}