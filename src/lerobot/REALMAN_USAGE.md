# Realman Robot Data Collection with Teleoperation

## 概述

这个脚本集成了 ButtonTele 遥操作系统和 SimpleDataCollector，用于收集 Realman 机器人的完整数据集，包括：
- 双臂相机图像（自动编码为MP4视频）
- 机器人关节状态和末端执行器位姿
- 遥操作命令数据
- 可选的触觉传感器数据

## 快速开始

### 1. 确保依赖已安装

```bash
# 确保 ffmpeg 已安装（用于视频编码）
sudo apt install ffmpeg

# 确保 Python 依赖已安装
pip install numpy pillow h5py rospy cv_bridge
```

### 2. 检查硬件连接

默认配置：
- 左臂IP: `192.168.1.18`
- 右臂IP: `192.168.1.19`  
- 左手串口: `/dev/ttyUSB0`
- 右手串口: `/dev/ttyUSB1`
- ESP32设备: `ESP32_Left`, `ESP32_Right`

### 3. 运行数据收集

```bash
cd /home/lr-2002/project/lr_gist/lerobot/src/lerobot
python realman_data_collection.py
```

### 4. 操作说明

- 程序启动后会自动初始化所有系统
- 如果遥操作系统初始化失败，会继续收集其他数据
- 按 `Ctrl+C` 停止收集并保存数据
- 数据保存到 `./realman_data/` 目录

## 输出数据格式

### 目录结构
```
./realman_data/
├── realman_teleop_data_YYYYMMDD_HHMMSS/
│   ├── videos/
│   │   ├── camera_left_color.mp4
│   │   ├── camera_left_depth.mp4
│   │   ├── camera_right_color.mp4
│   │   └── camera_right_depth.mp4
│   ├── data.hdf5
│   └── metadata.json
```

### 数据内容

**视频数据 (MP4格式):**
- `camera_left_color`: 左臂彩色相机
- `camera_left_depth`: 左臂深度相机  
- `camera_right_color`: 右臂彩色相机
- `camera_right_depth`: 右臂深度相机

**传感器数据 (HDF5格式):**
- `robot_joints`: 机器人关节角度 (30Hz)
- `end_effector_pose`: 末端执行器位姿 (30Hz)
- `teleop_commands`: 遥操作命令 (30Hz)
  - `left_arm_joints`: 左臂关节目标
  - `right_arm_joints`: 右臂关节目标
  - `left_gripper`: 左手爪位置
  - `right_gripper`: 右手爪位置
  - `timestamp`: 时间戳

## 自定义配置

如需修改默认配置，编辑 `realman_data_collection.py` 中的以下部分：

```python
# 遥操作系统配置
teleop_system = RealmanTeleopSystem(
    left_arm_ip='192.168.1.18',      # 修改左臂IP
    right_arm_ip='192.168.1.19',     # 修改右臂IP
    left_hand_port='/dev/ttyUSB0',   # 修改左手串口
    right_hand_port='/dev/ttyUSB1',  # 修改右手串口
    left_esp32_name='ESP32_Left',    # 修改ESP32名称
    right_esp32_name='ESP32_Right'
)

# 数据收集配置
collector = SimpleDataCollector(
    fps=30,                          # 修改采样频率
    dataset_name="realman_teleop_data",  # 修改数据集名称
    output_dir="./realman_data",     # 修改输出目录
    video_config=video_config
)
```

## 故障排除

### 遥操作系统初始化失败
- 检查机械臂IP地址是否正确
- 确认串口设备是否存在且有权限访问
- 检查ESP32设备连接状态

### 视频编码失败
- 确保 `ffmpeg` 已正确安装
- 检查磁盘空间是否充足

### ROS话题连接失败
- 确认ROS master正在运行
- 检查相机话题是否发布数据
- 验证话题名称是否正确

## 注意事项

1. **安全第一**: 确保机器人在安全的工作空间内操作
2. **数据存储**: 视频文件可能很大，确保有足够的存储空间
3. **网络延迟**: 遥操作可能受网络延迟影响，建议使用有线连接
4. **系统资源**: 多线程数据收集会消耗较多CPU和内存资源

## TODO 项目

- [ ] 添加触觉传感器数据收集
- [ ] 实现数据回放和可视化工具
- [ ] 添加数据质量检查功能
- [ ] 支持配置文件加载
