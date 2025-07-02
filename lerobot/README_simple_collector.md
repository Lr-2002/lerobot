# 简化版通用数据收集器

## 🎯 设计目标

这个简化版数据收集器专为你的需求设计：

- ✅ **轻松引入** - 一行代码添加一个数据源
- ✅ **实时性** - 多线程并行收集，各数据源独立运行
- ✅ **操作性** - Ctrl+C直接优雅退出并保存数据
- ✅ **丰富性** - 支持相机、传感器、控制器等多种数据源

## 🚀 快速开始

### 基本使用（3步搞定）

```python
from simple_data_collector import SimpleDataCollector

# 1. 创建收集器
collector = SimpleDataCollector("./my_data")

# 2. 添加数据源（一行一个！）
collector.add_sensor("arm_joints", your_arm.get_joints, frequency=100)
collector.add_sensor("camera", your_camera.get_image, frequency=30)
collector.add_control("teleop", your_teleop.get_command, frequency=50)

# 3. 开始收集
collector.run_forever()  # Ctrl+C停止并自动保存
```

## 📋 支持的数据源类型

### 1. 传感器数据
```python
# IMU传感器
collector.add_sensor("imu", imu_system.get_data, frequency=200)

# 力传感器
collector.add_sensor("force", force_sensor.read, frequency=100)

# 关节位置
collector.add_sensor("joints", robot.get_joint_pos, frequency=100)
```

### 2. 相机数据
```python
# 多个相机
collector.add_camera("front_cam", camera_id=0, frequency=30)
collector.add_camera("side_cam", camera_id=1, frequency=30)

# 或者自定义相机回调
collector.add_sensor("custom_cam", lambda: your_camera.capture(), frequency=30)
```

### 3. 控制数据
```python
# 遥操作命令
collector.add_control("teleop", teleop_system.get_command, frequency=50)

# 键盘输入
collector.add_control("keyboard", keyboard_handler.get_input, frequency=30)
```

## 🔧 高级功能

### 手动控制收集过程
```python
collector = SimpleDataCollector("./data")

# 添加数据源...
collector.add_sensor("sensor1", callback1, frequency=100)

# 手动开始/停止
collector.start_collection()
time.sleep(10)  # 收集10秒
collector.stop_collection()
collector.save_data("my_experiment")
```

### 自定义数据源配置
```python
from simple_data_collector import DataSourceConfig

config = DataSourceConfig(
    name="high_freq_sensor",
    data_type="sensor", 
    frequency=1000.0,  # 1kHz
    enabled=True,
    params={"buffer_size": 1024}
)

collector.add_data_source(config, your_callback)
```

## 📊 数据格式

收集的数据保存为JSON格式，包含：

```json
{
  "metadata": {
    "total_samples": 1000,
    "duration": 10.5,
    "data_sources": {
      "arm_joints": {"type": "sensor", "frequency": 100, "samples": 950},
      "camera": {"type": "image", "frequency": 30, "samples": 315}
    }
  },
  "timestamps": [1234567890.1, 1234567890.2, ...],
  "data": {
    "arm_joints": [[1.2, 3.4, ...], [1.3, 3.5, ...], ...],
    "camera": [<image_data>, <image_data>, ...]
  }
}
```

## 🛠️ 与你现有系统集成

### 集成你的机械臂系统
```python
# 假设你有一个RealmanArm类
realman_arm = RealmanArm()

collector.add_sensor("arm_pos", realman_arm.get_joint_positions, frequency=100)
collector.add_sensor("arm_vel", realman_arm.get_joint_velocities, frequency=100)
```

### 集成你的相机系统
```python
# 假设你有多个相机
for i, camera in enumerate(your_cameras):
    collector.add_sensor(f"camera_{i}", 
                        lambda cam=camera: cam.capture(), 
                        frequency=30)
```

### 集成你的遥操作系统
```python
# 假设你有遥操作系统
teleop = YourTeleopSystem()

collector.add_control("teleop_arm", 
                     lambda: teleop.get_arm_command(), 
                     frequency=50)
collector.add_control("teleop_base", 
                     lambda: teleop.get_base_command(), 
                     frequency=30)
```

## 🔍 实时监控

运行时会显示实时状态：
```
🚀 简化数据收集器已初始化
✅ 已添加数据源: arm_joints (sensor, 100.0Hz)
✅ 已添加数据源: camera (image, 30.0Hz)
🔄 启动数据收集线程: arm_joints
🔄 启动数据收集线程: camera
🎯 开始收集数据，共 2 个数据源
💡 按 Ctrl+C 停止收集并保存数据
📈 已收集 1523 个样本
```

## ⚡ 性能特点

- **多线程并行** - 每个数据源独立线程，互不影响
- **频率控制** - 每个数据源可设置不同采样频率
- **数据同步** - 自动同步不同频率的数据源
- **内存优化** - 使用队列缓冲，避免内存爆炸
- **优雅退出** - Ctrl+C安全停止并保存所有数据

## 🐛 故障处理

- 单个数据源出错不影响其他数据源
- 自动重试机制
- 详细错误日志
- 数据完整性检查

这个设计比原来的复杂适配器简单多了，你觉得怎么样？
