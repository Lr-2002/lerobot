# 🤖 简化数据收集器使用指南

## 🎯 核心理念

这个系统的设计理念是**极简易用**：
- **3步开始**: 创建收集器 → 注册数据源 → 开始收集
- **实时多线程**: 不同数据源可以有不同的采样频率
- **一键停止**: Ctrl+C 自动停止并保存数据
- **LeRobot兼容**: 自动转换为标准格式

## 🚀 快速开始

### 方法1: 使用快速启动工具

```bash
# 1. 创建配置模板
python quick_start.py template

# 2. 编辑 my_data_config.py (替换TODO部分)
# 3. 运行你的配置
python my_data_config.py
```

### 方法2: 直接编写代码

```python
from simple_data_collector import DataCollector

# 创建收集器
collector = DataCollector(fps=30, dataset_name="my_robot_data")

# 注册你的数据源
collector.add_sensor("camera_rgb", your_camera.get_frame, frequency=30)
collector.add_sensor("joint_pos", your_robot.get_joints, frequency=100)
collector.add_controller("teleop", your_teleop.get_action, frequency=30)

# 开始收集 (Ctrl+C停止)
collector.run_forever()
```

## 📊 数据源类型详解

### 传感器数据 (add_sensor)

```python
# 相机数据
collector.add_sensor("camera_0_rgb", lambda: camera.read(), frequency=30)

# 关节位置
collector.add_sensor("joint_positions", robot.get_joint_positions, frequency=100)

# 触觉数据
collector.add_sensor("tactile", tactile_system.read_sensors, frequency=50)

# IMU数据
collector.add_sensor("imu", imu.get_data, frequency=200)
```

### 控制器数据 (add_controller)

```python
# 遥操作命令
collector.add_controller("teleop_action", teleop.get_commands, frequency=30)

# 自动控制输出
collector.add_controller("auto_control", controller.compute_action, frequency=50)
```

## 🔧 实际系统集成示例

### 相机系统集成

```python
import cv2

class MyCameraSystem:
    def __init__(self):
        self.cameras = {}
        for i in range(3):  # 3个相机
            self.cameras[i] = cv2.VideoCapture(i)
    
    def get_frame(self, camera_id):
        ret, frame = self.cameras[camera_id].read()
        return frame if ret else None

# 使用
camera_system = MyCameraSystem()
for i in range(3):
    collector.add_sensor(
        f"camera_{i}_rgb",
        lambda cam_id=i: camera_system.get_frame(cam_id),
        frequency=30
    )
```

### 机器人系统集成

```python
class MyRobotSystem:
    def __init__(self):
        # 初始化你的机器人连接
        self.robot = your_robot_library.connect()
    
    def get_joint_positions(self):
        return self.robot.get_joint_angles()
    
    def get_end_effector_pose(self):
        return self.robot.get_ee_pose()

# 使用
robot = MyRobotSystem()
collector.add_sensor("joint_pos", robot.get_joint_positions, frequency=100)
collector.add_sensor("ee_pose", robot.get_end_effector_pose, frequency=100)
```

### CAN总线触觉系统

```python
import can

class CANTactileSystem:
    def __init__(self, interface='can0'):
        self.bus = can.interface.Bus(channel=interface, bustype='socketcan')
    
    def read_tactile_data(self):
        # 读取CAN消息并解析触觉数据
        msg = self.bus.recv(timeout=0.01)
        if msg:
            return self.parse_tactile_message(msg)
        return np.zeros(1100)  # 默认值

# 使用
tactile = CANTactileSystem()
collector.add_sensor("tactile_data", tactile.read_tactile_data, frequency=50)
```

## 📁 数据格式说明

### 原始HDF5格式
```
data/
└── my_robot_data_20240702_161152.h5
    ├── camera_0_rgb/
    │   ├── data          # 图像数据数组
    │   └── timestamps    # 时间戳
    ├── joint_positions/
    │   ├── data          # 关节位置数组
    │   └── timestamps    # 时间戳
    └── ...
```

### LeRobot标准格式
```python
# 转换为LeRobot格式
from lerobot_format_converter import convert_simple_data_to_lerobot

dataset = convert_simple_data_to_lerobot(
    h5_file="./data/my_robot_data_20240702_161152.h5",
    output_dir="./lerobot_dataset",
    task_name="pick_and_place"
)
```

## ⚙️ 高级配置

### 不同采样频率策略

```python
# 高频率: 控制相关数据
collector.add_sensor("joint_pos", robot.get_joints, frequency=200)
collector.add_sensor("joint_vel", robot.get_velocities, frequency=200)

# 中频率: 视觉数据
collector.add_sensor("camera_rgb", camera.get_frame, frequency=30)

# 低频率: 慢变化数据
collector.add_sensor("temperature", sensors.get_temp, frequency=1)
```

### 错误处理和恢复

```python
def robust_camera_read():
    try:
        return camera.read()
    except Exception as e:
        print(f"相机读取错误: {e}")
        return None  # 返回None，系统会自动处理

collector.add_sensor("camera_rgb", robust_camera_read, frequency=30)
```

### 数据预处理

```python
def preprocessed_image():
    raw_image = camera.read()
    # 预处理: 调整大小、格式转换等
    processed = cv2.resize(raw_image, (640, 480))
    return processed

collector.add_sensor("camera_processed", preprocessed_image, frequency=30)
```

## 🔍 调试和监控

### 实时监控数据收集

```python
import threading
import time

def monitor_collection(collector):
    while collector.running:
        total_samples = sum(len(data) for data in collector.collected_data.values())
        print(f"已收集样本: {total_samples}")
        time.sleep(1)

# 启动监控线程
monitor_thread = threading.Thread(target=monitor_collection, args=(collector,), daemon=True)
monitor_thread.start()

collector.run_forever()
```

### 数据质量检查

```python
def check_data_quality():
    for name, data_list in collector.collected_data.items():
        if len(data_list) == 0:
            print(f"⚠️ {name}: 无数据")
        elif len(data_list) < expected_samples * 0.8:
            print(f"⚠️ {name}: 数据量不足 ({len(data_list)} < {expected_samples})")
        else:
            print(f"✅ {name}: 数据正常 ({len(data_list)} 样本)")

# 在停止收集后检查
collector.stop_collection()
check_data_quality()
collector.save_data()
```

## 🎯 最佳实践

### 1. 系统设计
- **模块化**: 每个数据源独立实现
- **容错性**: 单个数据源错误不影响整体
- **可扩展**: 轻松添加新的数据源

### 2. 性能优化
- **合理频率**: 根据实际需求设置采样频率
- **内存管理**: 大数据量时定期保存
- **CPU负载**: 避免数据源回调函数过于复杂

### 3. 数据管理
- **命名规范**: 使用描述性的数据源名称
- **版本控制**: 记录数据收集的配置和版本
- **备份策略**: 重要数据及时备份

## 🚨 常见问题解决

### Q: 数据收集频率不稳定？
**A**: 检查数据源回调函数的执行时间，优化或降低频率

### Q: 某些数据源经常出错？
**A**: 添加异常处理，返回默认值或None

### Q: 内存占用过高？
**A**: 定期保存数据并清空缓存，或降低图像分辨率

### Q: 数据同步问题？
**A**: 系统自动处理时间戳，确保数据源回调函数快速返回

## 🎉 完整工作流程

1. **系统准备**
   ```bash
   python quick_start.py template  # 创建模板
   ```

2. **配置编辑**
   - 编辑 `my_data_config.py`
   - 替换TODO部分为实际系统代码

3. **数据收集**
   ```bash
   python my_data_config.py  # 开始收集
   # Ctrl+C 停止
   ```

4. **格式转换**
   ```bash
   python quick_start.py convert --h5-file ./data/xxx.h5
   ```

5. **训练使用**
   ```python
   from datasets import load_from_disk
   dataset = load_from_disk("./lerobot_dataset")
   ```

---

**开始你的机器人数据收集之旅！** 🚀

有问题？查看 `test_simple_collector.py` 了解更多使用示例。
