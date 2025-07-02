# 视频数据收集器 (Video Data Collector)

## 概述

这是一个专门为LeRobot设计的支持视频存储的数据收集器，解决了图像数据存储空间占用过大的问题。

## 主要特性

### 🎥 视频存储支持
- **自动视频编码**: 图像序列自动编码为MP4视频文件
- **多种编码器**: 支持 `libx264`, `libx265`, `libsvtav1`
- **可调质量**: CRF参数控制压缩质量 (0=无损, 51=最差)
- **显著节省空间**: 典型压缩比 2-10x

### 📊 LeRobot兼容性
- **标准格式**: 兼容LeRobot数据集格式
- **元数据记录**: 完整的视频编码参数记录
- **时间戳同步**: 精确的时间戳记录
- **HDF5存储**: 非图像数据使用HDF5格式

### 🚀 易用性
- **简单注册**: 一行代码注册数据源
- **多线程**: 每个数据源独立线程，不同采样频率
- **优雅停止**: Ctrl+C自动保存并编码视频
- **实时反馈**: 详细的进度和统计信息

## 快速开始

```python
from video_data_collector import VideoDataCollector, VideoConfig

# 创建收集器
video_config = VideoConfig(
    enabled=True,
    codec="libx264",  # 或 "libx265", "libsvtav1"
    crf=23,          # 质量: 18-28推荐
    fps=30
)

collector = VideoDataCollector(
    output_dir="./robot_data",
    video_config=video_config
)

# 注册数据源
def get_camera_frame():
    # 返回 numpy array (H, W, 3)
    return camera.capture()

def get_joint_positions():
    # 返回关节位置数据
    return robot.get_joint_positions()

# 注册图像数据源 (将被编码为视频)
collector.register_data_source(
    "camera_main", 
    get_camera_frame, 
    frequency=30, 
    is_image=True
)

# 注册普通数据源 (保存为HDF5)
collector.register_data_source(
    "joint_positions", 
    get_joint_positions, 
    frequency=100
)

# 开始收集
collector.run_forever()  # 按Ctrl+C停止
```

## 视频编码配置

### 编码器选择

| 编码器 | 特点 | 推荐场景 |
|--------|------|----------|
| `libx264` | 兼容性好，速度快 | 通用场景 |
| `libx265` | 压缩率高，质量好 | 存储空间敏感 |
| `libsvtav1` | 最新标准，效率高 | 现代系统 |

### 质量参数 (CRF)

| CRF值 | 质量 | 用途 |
|-------|------|------|
| 18-23 | 高质量 | 精细操作，重要数据 |
| 23-28 | 平衡 | 一般机器人任务 |
| 28-35 | 低质量 | 预览，快速原型 |

## 存储空间对比

### 示例数据 (640x480, 30fps, 5分钟)

| 存储方式 | 文件大小 | 压缩比 |
|----------|----------|--------|
| PNG图片 | ~2.7GB | 1x |
| H.264 (CRF=23) | ~270MB | 10x |
| H.265 (CRF=23) | ~135MB | 20x |

## 与LeRobot集成

生成的数据可以直接用于LeRobot训练：

```python
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset

# 加载视频数据集
dataset = LeRobotDataset(
    repo_id="your_dataset",
    video_backend="pyav"  # 或 "torchcodec"
)

# 正常使用
for episode in dataset:
    images = episode["observation.images.camera_main"]
    actions = episode["action"]
```

## 最佳实践

### 1. 视频质量设置
```python
# 高质量 (用于重要数据)
video_config = VideoConfig(crf=18, codec="libx265")

# 平衡 (推荐)
video_config = VideoConfig(crf=23, codec="libx264")

# 节省空间 (用于大量数据)
video_config = VideoConfig(crf=28, codec="libx265")
```

### 2. 多相机设置
```python
# 不同相机可以使用不同频率
collector.register_data_source("camera_main", cam1.get_frame, 
                              frequency=30, is_image=True)
collector.register_data_source("camera_wrist", cam2.get_frame, 
                              frequency=15, is_image=True)
```

### 3. 内存优化
- 图像数据直接写入临时文件，不占用内存
- 非图像数据才保存在内存中
- 适合长时间数据收集

## 故障排除

### 1. ffmpeg未安装
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### 2. 编码器不支持
```python
# 检查可用编码器
import subprocess
result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True)
print(result.stdout)
```

### 3. 视频质量问题
- 降低CRF值提高质量
- 使用libx265获得更好压缩
- 检查原始图像质量

## 技术细节

### 数据流程
1. **图像采集** → 临时JPEG文件
2. **数据采集** → 内存缓存
3. **停止信号** → 触发保存流程
4. **视频编码** → ffmpeg处理图像序列
5. **数据保存** → HDF5 + JSON元数据
6. **清理** → 删除临时文件

### 文件结构
```
output_dir/
├── camera_main.mp4          # 主相机视频
├── camera_wrist.mp4         # 手腕相机视频
├── data_timestamp.h5        # 非图像数据
└── metadata_timestamp.json  # 元数据
```

### 元数据格式
```json
{
  "collection_time": 1234567890,
  "video_config": {
    "enabled": true,
    "codec": "libx264",
    "crf": 23,
    "fps": 30
  },
  "data_sources": {
    "camera_main": {
      "frequency": 30,
      "is_image": true,
      "sample_count": 900
    }
  }
}
```

## 性能优化

### 1. 编码速度
- 使用libx264获得最快编码
- 降低关键帧间隔 (g参数)
- 使用硬件编码器 (如果可用)

### 2. 存储优化
- SSD存储提高I/O性能
- 分离临时目录和输出目录
- 定期清理旧数据

### 3. 内存使用
- 图像数据不占用内存
- 只有非图像数据保存在内存
- 适合长时间收集

---

**开始你的高效机器人数据收集之旅！** 🎥🤖

有问题？查看 `video_data_collector.py` 了解更多实现细节。
