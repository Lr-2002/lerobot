# 简化数据收集器 🤖

一个超级简单易用的机器人数据收集系统，专为LeRobot设计。

## ✨ 特性

- **🚀 超简单** - 几行代码就能开始收集数据
- **⚡ 实时性** - 多线程并行收集，支持不同频率
- **🛑 操作性** - Ctrl+C即可停止并自动保存
- **🔌 丰富性** - 支持相机、传感器、控制器等多种数据源
- **💾 兼容性** - 自动转换为LeRobot标准格式

## 🚀 快速开始

### 1. 基础使用

```python
from simple_data_collector import DataCollector

# 创建收集器
collector = DataCollector(fps=30, dataset_name="my_robot_data")

# 添加数据源（超简单！）
collector.add_sensor("camera_rgb", your_camera.get_frame, frequency=30)
collector.add_sensor("joint_pos", your_robot.get_joints, frequency=100)
collector.add_controller("teleop", your_teleop.get_action, frequency=30)

# 开始收集（Ctrl+C停止）
collector.run_forever()
```

### 2. 完整示例

```python
# 参考 my_data_collection_example.py
python my_data_collection_example.py
```

### 3. 转换为LeRobot格式

```python
from lerobot_format_converter import convert_simple_data_to_lerobot

# 转换数据
dataset = convert_simple_data_to_lerobot(
    h5_file="./data/my_robot_data_20240702_161152.h5",
    output_dir="./lerobot_dataset",
    task_name="pick_and_place"
)
```

## 📊 数据源类型

### 传感器数据 (add_sensor)
- **相机**: RGB图像、深度图像
- **关节**: 位置、速度、力矩
- **触觉**: 压力、温度
- **IMU**: 加速度、角速度
- **其他**: 任何传感器数据

### 控制器数据 (add_controller)
- **遥操作**: 人工控制命令
- **自动控制**: 算法输出
- **混合控制**: 人机协作

## 🔧 自定义你的系统

只需要替换示例中的TODO部分：

```python
class YourCameraSystem:
    def get_camera_frame(self, camera_id):
        # TODO: 替换为你的相机读取代码
        return your_actual_camera_read(camera_id)

class YourRobotSystem:
    def get_joint_positions(self):
        # TODO: 替换为你的关节读取代码
        return your_actual_joint_read()
```

## 📁 输出格式

### 原始数据 (HDF5)
```
data/
├── my_robot_data_20240702_161152.h5      # 原始数据
└── my_robot_data_20240702_161152_metadata.json  # 元数据
```

### LeRobot格式
```
lerobot_dataset/
├── dataset_info.json
├── data-00000-of-00001.arrow
└── metadata.json
```

## 🎯 使用场景

1. **快速原型** - 几分钟内开始收集数据
2. **多模态数据** - 同时收集视觉、触觉、运动数据
3. **实时系统** - 支持高频率数据收集
4. **研究实验** - 轻松切换不同配置

## 🔄 工作流程

1. **初始化** → 创建DataCollector
2. **注册** → 添加你的数据源
3. **收集** → 自动多线程收集
4. **停止** → Ctrl+C自动保存
5. **转换** → 转为LeRobot格式
6. **训练** → 用于机器人学习

## 💡 最佳实践

### 频率设置
- **相机**: 30Hz (标准视频)
- **关节**: 100Hz (高精度控制)
- **触觉**: 50Hz (触觉反馈)
- **遥操作**: 30Hz (人类反应)

### 数据同步
- 系统自动处理时间戳
- 支持不同频率的数据源
- 自动对齐到最短序列

### 错误处理
- 单个数据源错误不影响其他
- 自动重试机制
- 详细错误日志

## 🚨 注意事项

1. **内存使用**: 大量图像数据会占用内存，建议定期保存
2. **磁盘空间**: 确保有足够空间存储数据
3. **权限**: 某些传感器可能需要特殊权限
4. **网络**: 上传到HuggingFace需要网络连接

## 🛠️ 故障排除

### 常见问题

**Q: 数据收集很慢？**
A: 检查数据源的处理时间，考虑降低频率或优化代码

**Q: 某个传感器数据缺失？**
A: 检查传感器连接和权限，查看错误日志

**Q: 转换LeRobot格式失败？**
A: 确保数据格式正确，检查numpy数组维度

**Q: Ctrl+C不能停止？**
A: 可能有线程阻塞，检查数据源回调函数

## 📞 支持

遇到问题？
1. 查看错误日志
2. 检查数据源实现
3. 参考示例代码
4. 提交Issue

---

**开始你的机器人数据收集之旅吧！** 🚀
