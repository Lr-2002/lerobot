#!/usr/bin/env python3
"""
简化的通用数据收集器
支持多线程、实时数据收集，Ctrl+C停止
"""

import threading
import time
import signal
import sys
#!/usr/bin/env python3
"""
简化的数据收集器
支持基本的多线程数据收集和视频存储
"""

import threading
import time
import signal
import json
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, Callable, Optional, List
import h5py
import tempfile
import shutil
from PIL import Image
import subprocess
import os
from collections import defaultdict
from datetime import datetime

@dataclass
class DataSourceConfig:
    """数据源配置"""
    name: str
    callback: Callable[[], Any]
    frequency: float = 30.0  # Hz
    enabled: bool = True
    is_image: bool = False  # 是否为图像数据源

@dataclass
class VideoConfig:
    """视频编码配置"""
    enabled: bool = True  # 启用视频编码
    codec: str = "libx264"  # 视频编码器: libx264, libx265, libsvtav1
    pixel_format: str = "yuv420p"  # 像素格式
    crf: int = 23  # 恒定质量因子 (0=无损, 51=最差质量)
    fps: int = 30  # 视频帧率
    keyframe_interval: int = 2  # 关键帧间隔

class DataCollector:
    """简化的数据收集器"""
    
    def __init__(self, fps: int = 30, dataset_name: str = "robot_data", output_dir: str = "./data", 
                 video_config: Optional[VideoConfig] = None):
        self.fps = fps
        self.dataset_name = dataset_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.default_frequency = fps
        self.video_config = video_config or VideoConfig()
        self.data_sources: Dict[str, DataSourceConfig] = {}
        self.collected_data: Dict[str, List] = {}
        self.timestamps: Dict[str, List] = {}
        self.threads: Dict[str, threading.Thread] = {}
        self.stop_event = threading.Event()
        self.data_lock = threading.Lock()
        self.is_collecting = False
        
        # For video storage
        self.temp_image_dirs: Dict[str, Path] = {}  # Temporary directories for images
        self.image_counters: Dict[str, int] = {}  # Frame counters for each image source
        
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        
        print(f"🤖 数据收集器初始化完成 - FPS: {fps}, 数据集: {dataset_name}")
        if self.video_config.enabled:
            print(f"🎥 视频编码: 启用 ({self.video_config.codec}, CRF={self.video_config.crf})")
        name: str
        callback: Callable[[], Any]
        frequency: float = 30.0  # Hz
        enabled: bool = True
        is_image: bool = False  # Whether this data source produces images

    @dataclass
    class VideoConfig:
        """Configuration for video encoding"""
        enabled: bool = True  # Use video encoding for images
        codec: str = "libsvtav1"  # Video codec: libsvtav1, libx264, libx265
        pixel_format: str = "yuv420p"  # Pixel format
        crf: int = 30  # Constant Rate Factor (quality: 0=lossless, 51=worst)
        fps: int = 30  # Video frame rate
        keyframe_interval: int = 2  # GOP size (frames between keyframes)

    def add_sensor(self, name: str, callback: Callable, frequency: Optional[int] = None, enabled: bool = True, is_image: bool = False):
        """添加传感器数据源
        
        Args:
            name: 传感器名称
            callback: 获取数据的回调函数
            frequency: 采样频率，None表示使用默认FPS
            enabled: 是否启用该数据源
            is_image: 是否为图像数据源
        """
        config = self.DataSourceConfig(
            name=name,
            callback=callback,
            frequency=frequency or self.default_frequency,
            enabled=enabled,
            is_image=is_image
        )
        self.data_sources[name] = config
        self.collected_data[name] = []
        self.timestamps[name] = []
        
        # Setup temporary directory for image data sources if video encoding is enabled
        if is_image and self.video_config.enabled:
            temp_dir = Path(tempfile.mkdtemp(prefix=f"images_{name}_"))
            self.temp_image_dirs[name] = temp_dir
            self.image_counters[name] = 0
            print(f"Registered image data source '{name}' at {config.frequency} Hz (video encoding enabled)")
        else:
            print(f"Registered data source '{name}' at {config.frequency} Hz")
    
    def add_controller(self, name: str, callback: Callable, frequency: Optional[int] = None, enabled: bool = True, is_image: bool = False):
        """添加控制器数据源
        
        Args:
            name: 控制器名称
            callback: 获取数据的回调函数
            frequency: 采样频率，None表示使用默认FPS
            enabled: 是否启用该数据源
            is_image: 是否为图像数据源
        """
        config = self.DataSourceConfig(
            name=name,
            callback=callback,
            frequency=frequency or self.default_frequency,
            enabled=enabled,
            is_image=is_image
        )
        self.data_sources[name] = config
        self.collected_data[name] = []
        self.timestamps[name] = []
        
        # Setup temporary directory for image data sources if video encoding is enabled
        if is_image and self.video_config.enabled:
            temp_dir = Path(tempfile.mkdtemp(prefix=f"images_{name}_"))
            self.temp_image_dirs[name] = temp_dir
            self.image_counters[name] = 0
            print(f"Registered image data source '{name}' at {config.frequency} Hz (video encoding enabled)")
        else:
            print(f"Registered data source '{name}' at {config.frequency} Hz")
    
    def _collect_data(self, source_name: str):
        """Data collection thread function"""
        config = self.data_sources[source_name]
        interval = 1.0 / config.frequency
        
        print(f"Started collecting data from '{source_name}' at {config.frequency} Hz")
        
        while not self.stop_event.is_set():
            start_time = time.time()
            
            try:
                # Get data from callback
                data = config.callback()
                timestamp = time.time()
                
                # Handle image data differently if video encoding is enabled
                if config.is_image and self.video_config.enabled:
                    self._save_image_frame(source_name, data, timestamp)
                else:
                    # Store data thread-safely
                    with self.data_lock:
                        self.collected_data[source_name].append(data)
                        self.timestamps[source_name].append(timestamp)
                    
            except Exception as e:
                print(f"Error collecting data from '{source_name}': {e}")
                continue
            
            # Sleep for the remaining time to maintain frequency
            elapsed = time.time() - start_time
            sleep_time = max(0, interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _save_image_frame(self, source_name: str, frame: np.ndarray, timestamp: float):
        """Save an image frame to a temporary directory"""
        temp_dir = self.temp_image_dirs[source_name]
        frame_counter = self.image_counters[source_name]
        filename = f"{frame_counter:06d}.jpg"
        filepath = temp_dir / filename
        
        # Save image frame
        Image.fromarray(frame).save(filepath)
        
        # Update frame counter
        self.image_counters[source_name] += 1
    
    def start_collection(self):
        """开始数据收集"""
        if self.is_collecting:
            print("⚠️ 数据收集已在运行中")
            return
        
        self.is_collecting = True
        
        print("🚀 开始数据收集...")
        
        # 启动传感器线程
        for name, config in self.data_sources.items():
            if config.enabled:
                thread = threading.Thread(
                    target=self._collect_data,
                    args=(name,),
                    daemon=True
                )
                thread.start()
                self.threads[name] = thread
                daemon=True
            
            thread.start()
            self.threads.append(thread)
        
        # 启动控制器线程
        for name, info in self.controllers.items():
            thread = threading.Thread(
                target=self._collect_data_thread,
                args=(name, info, 'controller'),
                daemon=True
            )
            thread.start()
            self.threads.append(thread)
        
        print(f"✅ 已启动 {len(self.threads)} 个数据收集线程")
        print("💡 按 Ctrl+C 停止收集")
    
    def stop_collection(self):
        """停止数据收集"""
        if not self.running:
            return
        
        print("\n🛑 停止数据收集...")
        self.running = False
        
        # 等待所有线程结束
        for thread in self.threads:
            thread.join(timeout=1.0)
        
        self.threads.clear()
        print("✅ 所有线程已停止")
        
        # 显示收集到的数据统计
        total_samples = sum(len(data) for data in self.collected_data.values())
        print(f"📊 收集统计: {total_samples} 个样本")
    
    def save_data(self, output_dir: str = "./data"):
        """保存收集的数据"""
        if not self.collected_data:
            print("⚠️ 没有数据可保存")
            return
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存为HDF5格式（LeRobot兼容）
        h5_file = output_path / f"{self.dataset_name}_{timestamp}.h5"
        
        with h5py.File(h5_file, 'w') as f:
            for source_name, data_list in self.collected_data.items():
                if not data_list:
                    continue
                
                group = f.create_group(source_name)
                
                # 提取数据和时间戳
                timestamps = [item['timestamp'] for item in data_list]
                data_values = [item['data'] for item in data_list]
                
                # 保存时间戳
                group.create_dataset('timestamps', data=np.array(timestamps))
                
                # 保存数据（处理不同数据类型）
                try:
                    if isinstance(data_values[0], np.ndarray):
                        # 图像或数组数据
                        stacked_data = np.stack(data_values)
                        group.create_dataset('data', data=stacked_data)
                    elif isinstance(data_values[0], (list, tuple)):
                        # 列表数据
                        group.create_dataset('data', data=np.array(data_values))
                    else:
                        # 标量数据
                        group.create_dataset('data', data=np.array(data_values))
                except Exception as e:
                    print(f"⚠️ 保存 {source_name} 数据时出错: {e}")
        
        # 保存元数据
        metadata = {
            'dataset_name': self.dataset_name,
            'fps': self.fps,
            'collection_time': timestamp,
            'sensors': list(self.sensors.keys()),
            'controllers': list(self.controllers.keys()),
            'total_samples': {name: len(data) for name, data in self.collected_data.items()}
        }
        
        json_file = output_path / f"{self.dataset_name}_{timestamp}_metadata.json"
        with open(json_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"💾 数据已保存:")
        print(f"   HDF5: {h5_file}")
        print(f"   元数据: {json_file}")
        print(f"   总样本数: {sum(len(data) for data in self.collected_data.values())}")
    
    def _signal_handler(self, signum, frame):
        """处理Ctrl+C信号"""
        print(f"\n🔔 收到停止信号 (信号: {signum})")
        self.stop_collection()
        self.save_data()
        print("👋 数据收集完成，再见！")
        sys.exit(0)
    
    def run_forever(self):
        """运行数据收集直到手动停止"""
        self.start_collection()
        
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_collection()
            self.save_data()

# 便捷的数据源示例类
class CameraSource:
    """相机数据源示例"""
    def __init__(self, camera_id: int = 0, resolution: tuple = (640, 480)):
        self.camera_id = camera_id
        self.resolution = resolution
        print(f"📷 初始化相机 {camera_id}")
    
    def get_frame(self):
        """获取相机帧（示例：返回随机数据）"""
        # TODO: 替换为实际的相机读取代码
        return np.random.randint(0, 255, (*self.resolution, 3), dtype=np.uint8)

class JointSensor:
    """关节传感器示例"""
    def __init__(self, joint_count: int = 26):
        self.joint_count = joint_count
        print(f"🦾 初始化关节传感器 ({joint_count}个关节)")
    
    def get_positions(self):
        """获取关节位置"""
        # TODO: 替换为实际的关节读取代码
        return np.random.uniform(-1, 1, self.joint_count).tolist()

class TactileSensor:
    """触觉传感器示例"""
    def __init__(self, sensor_count: int = 1100):
        self.sensor_count = sensor_count
        print(f"👋 初始化触觉传感器 ({sensor_count}个触点)")
    
    def get_tactile_data(self):
        """获取触觉数据"""
        # TODO: 替换为实际的CAN触觉读取代码
        return np.random.uniform(0, 1, (self.sensor_count, 1))

class TeleopController:
    """遥操作控制器示例"""
    def __init__(self):
        print("🎮 初始化遥操作控制器")
    
    def get_action(self):
        """获取遥操作动作"""
        # TODO: 替换为实际的遥操作读取代码
        return {
            'arm_joints': np.random.uniform(-1, 1, 26).tolist(),
            'body_movement': np.random.uniform(-0.1, 0.1, 3).tolist()
        }

# 使用示例
if __name__ == "__main__":
    # 创建数据收集器
    collector = DataCollector(fps=30, dataset_name="my_robot_data")
    
    # 创建数据源
    camera1 = CameraSource(camera_id=0)
    camera2 = CameraSource(camera_id=1)
    joints = JointSensor(joint_count=26)
    tactile = TactileSensor()
    teleop = TeleopController()
    
    # 注册数据源
    collector.add_sensor("camera_0_rgb", camera1.get_frame, frequency=30)
    collector.add_sensor("camera_1_rgb", camera2.get_frame, frequency=30)
    collector.add_sensor("joint_positions", joints.get_positions, frequency=100)
    collector.add_sensor("tactile_data", tactile.get_tactile_data, frequency=50)
    collector.add_controller("teleop_action", teleop.get_action, frequency=30)
    
    # 开始收集（会一直运行直到Ctrl+C）
    collector.run_forever()
