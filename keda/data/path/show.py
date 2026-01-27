import matplotlib.pyplot as plt
import os

def read_coordinate_file(file_path):
    """
    读取txt坐标文件，每行格式为 x y
    :param file_path: txt文件路径
    :return: 包含x坐标列表和y坐标列表的元组
    """
    x_coords = []
    y_coords = []
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误：文件 {file_path} 不存在！")
        return None, None
    
    # 读取文件
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                # 去除空白字符并分割
                line = line.strip()
                if not line:  # 跳过空行
                    continue
                
                # 分割坐标（支持空格/制表符分隔）
                parts = line.split()
                if len(parts) != 2:
                    print(f"警告：第 {line_num} 行格式错误，跳过该行 -> {line}")
                    continue
                
                # 转换为浮点数
                try:
                    x = float(parts[0])
                    y = float(parts[1])
                    x_coords.append(x)
                    y_coords.append(y)
                except ValueError:
                    print(f"警告：第 {line_num} 行不是有效数字，跳过该行 -> {line}")
    
    except Exception as e:
        print(f"读取文件出错：{e}")
        return None, None
    
    if not x_coords or not y_coords:
        print("错误：文件中未读取到有效坐标数据！")
        return None, None
    
    return x_coords, y_coords

def plot_trajectory(x_coords, y_coords, file_name="轨迹图"):
    """
    绘制轨迹图
    :param x_coords: x坐标列表
    :param y_coords: y坐标列表
    :param file_name: 图表标题
    """
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 支持中文显示
    plt.rcParams['axes.unicode_minus'] = False    # 支持负号显示
    
    # 创建画布
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 绘制轨迹线（蓝色）
    ax.plot(x_coords, y_coords, color='blue', linewidth=1.5, label='轨迹', alpha=0.8)
    # 标记起点（绿色圆点）
    ax.scatter(x_coords[0], y_coords[0], color='green', s=80, label='起点', zorder=5)
    # 标记终点（红色圆点）
    ax.scatter(x_coords[-1], y_coords[-1], color='red', s=80, label='终点', zorder=5)
    
    # 设置图表样式
    ax.set_title(f'{file_name}', fontsize=14, fontweight='bold')
    ax.set_xlabel('X 坐标', fontsize=12)
    ax.set_ylabel('Y 坐标', fontsize=12)
    ax.grid(True, alpha=0.3, linestyle='--')  # 显示网格
    ax.legend(loc='best', fontsize=10)        # 显示图例
    ax.axis('equal')                          # 等比例显示X/Y轴，避免轨迹变形
    
    # 显示图表
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # ===================== 配置项 =====================
    # 替换为你的txt文件路径（绝对路径/相对路径都可以）
    COORD_FILE_PATH = "trajectory.txt"
    # ==================================================
    
    # 读取坐标
    x, y = read_coordinate_file(COORD_FILE_PATH)
    
    # 绘制轨迹
    if x and y:
        print(f"成功读取 {len(x)} 个坐标点")
        plot_trajectory(x, y, file_name=f"{os.path.basename(COORD_FILE_PATH)} - 轨迹图")

