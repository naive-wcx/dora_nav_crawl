import matplotlib.pyplot as plt

def plot_waypoints(file_path, step=20, save_path='trajectory_sparse.txt'):
    x_coords = []
    y_coords = []
    
    with open(file_path, 'r') as f:
        for i, line in enumerate(f):
            if i % step != 0:
                continue
            x, y = map(float, line.strip().split())
            x_coords.append(x)
            y_coords.append(y)
    
    # 新增保存稀疏点的代码
    with open(save_path, 'w') as f:
        for x, y in zip(x_coords, y_coords):
            f.write(f"{x:.3f} {y:.3f}\n")  # 保留3位小数
    
    plt.figure(figsize=(10, 6))
    plt.plot(x_coords, y_coords, 'b-', linewidth=2)  # 蓝色实线连接路径点
    plt.plot(x_coords, y_coords, 'ro')  # 红色圆点标记路径点
    plt.xlabel('X Coordinate (m)')
    plt.ylabel('Y Coordinate (m)')
    plt.title('Waypoints Visualization')
    plt.grid(True)
    plt.axis('equal')  # 保持坐标轴等比例
    plt.show()

if __name__ == "__main__":
    plot_waypoints('data/path/trajectory.txt', 
              step=20,
              save_path='sparse_points.txt')
