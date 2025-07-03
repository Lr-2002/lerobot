#!/usr/bin/env python3
"""
支持视频存储的简化数据收集器
基于LeRobot格式，支持图像数据的视频编码存储
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

class VideoDataCollector:
    """支持视频存储的数据收集器"""
    
    def __init__(self, output_dir: str = "./data", default_frequency: float = 30.0, 
                 video_config: Optional[VideoConfig] = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.default_frequency = default_frequency
        self.video_config = video_config or VideoConfig()
        
        # 数据源管理
        self.data_sources: Dict[str, DataSourceConfig] = {}
        self.collected_data: Dict[str, List] = {}
        self.timestamps: Dict[str, List] = {}
        
        # 线程管理
        self.threads: Dict[str, threading.Thread] = {}
        self.stop_event = threading.Event()
        self.data_lock = threading.Lock()
        self.is_collecting = False
        
        # 视频存储相关
        self.temp_image_dirs: Dict[str, Path] = {}  # 临时图像目录
        self.image_counters: Dict[str, int] = {}  # 图像帧计数器
        
        # 信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        
        print(f"🎥 视频数据收集器初始化完成")
        print(f"📁 输出目录: {self.output_dir}")
        print(f"🎬 视频编码: {'启用' if self.video_config.enabled else '禁用'}")
        if self.video_config.enabled:
            print(f"   编码器: {self.video_config.codec}")
            print(f"   质量: CRF={self.video_config.crf}")
    
    def register_data_source(self, name: str, callback: Callable[[], Any], 
                           frequency: Optional[float] = None, enabled: bool = True,
                           is_image: bool = False):
        """注册数据源
        
        Args:
            name: 数据源名称
            callback: 数据获取回调函数
            frequency: 采样频率 (Hz)
            enabled: 是否启用
            is_image: 是否为图像数据源
        """
        config = DataSourceConfig(
            name=name,
            callback=callback,
            frequency=frequency or self.default_frequency,
            enabled=enabled,
            is_image=is_image
        )
        
        self.data_sources[name] = config
        self.collected_data[name] = []
        self.timestamps[name] = []
        
        # 为图像数据源设置临时目录
        if is_image and self.video_config.enabled:
            temp_dir = Path(tempfile.mkdtemp(prefix=f"images_{name}_"))
            self.temp_image_dirs[name] = temp_dir
            self.image_counters[name] = 0
            print(f"📷 注册图像数据源 '{name}' @ {config.frequency} Hz (视频编码)")
        else:
            print(f"📊 注册数据源 '{name}' @ {config.frequency} Hz")
    
    def _collect_data(self, source_name: str):
        """数据收集线程函数"""
        config = self.data_sources[source_name]
        interval = 1.0 / config.frequency
        
        print(f"🔄 开始收集 '{source_name}' @ {config.frequency} Hz")
        
        while not self.stop_event.is_set():
            start_time = time.time()
            
            try:
                # 获取数据
                data = config.callback()
                timestamp = time.time()
                
                # 图像数据特殊处理
                if config.is_image and self.video_config.enabled:
                    self._save_image_frame(source_name, data, timestamp)
                else:
                    # 常规数据存储
                    with self.data_lock:
                        self.collected_data[source_name].append(data)
                        self.timestamps[source_name].append(timestamp)
                        
            except Exception as e:
                print(f"❌ '{source_name}' 数据收集错误: {e}")
                continue
            
            # 控制采样频率
            elapsed = time.time() - start_time
            sleep_time = max(0, interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _save_image_frame(self, source_name: str, frame: np.ndarray, timestamp: float):
        """保存图像帧到临时目录"""
        temp_dir = self.temp_image_dirs[source_name]
        frame_counter = self.image_counters[source_name]
        filename = f"{frame_counter:06d}.jpg"
        filepath = temp_dir / filename
        
        # 保存图像
        if isinstance(frame, np.ndarray):
            # 确保是RGB格式
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                Image.fromarray(frame.astype(np.uint8)).save(filepath, quality=95)
            else:
                print(f"⚠️ 不支持的图像格式: {frame.shape}")
        
        # 同时记录时间戳
        with self.data_lock:
            self.timestamps[source_name].append(timestamp)
        
        # 更新计数器
        self.image_counters[source_name] += 1
    
    def _encode_videos(self):
        """将图像序列编码为视频"""
        if not self.video_config.enabled:
            return
        
        print("🎬 开始视频编码...")
        
        for source_name, temp_dir in self.temp_image_dirs.items():
            if not temp_dir.exists():
                continue
                
            # 检查是否有图像文件
            image_files = list(temp_dir.glob("*.jpg"))
            if not image_files:
                print(f"⚠️ '{source_name}' 没有图像文件")
                continue
            
            # 输出视频路径
            video_path = self.output_dir / f"{source_name}.mp4"
            
            try:
                # 使用ffmpeg编码视频
                cmd = [
                    "ffmpeg", "-y",  # 覆盖输出文件
                    "-framerate", str(self.video_config.fps),
                    "-i", str(temp_dir / "%06d.jpg"),
                    "-c:v", self.video_config.codec,
                    "-crf", str(self.video_config.crf),
                    "-pix_fmt", self.video_config.pixel_format,
                    "-g", str(self.video_config.keyframe_interval),
                    str(video_path)
                ]
                
                print(f"🎥 编码 '{source_name}' -> {video_path}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"✅ '{source_name}' 视频编码完成")
                    # 计算压缩比
                    original_size = sum(f.stat().st_size for f in image_files)
                    video_size = video_path.stat().st_size
                    ratio = original_size / video_size if video_size > 0 else 0
                    print(f"   压缩比: {ratio:.1f}x ({original_size/1024/1024:.1f}MB -> {video_size/1024/1024:.1f}MB)")
                else:
                    print(f"❌ '{source_name}' 视频编码失败: {result.stderr}")
                    
            except Exception as e:
                print(f"❌ '{source_name}' 视频编码异常: {e}")
    
    def start_collection(self):
        """开始数据收集"""
        if self.is_collecting:
            print("⚠️ 数据收集已在运行中")
            return
        
        self.is_collecting = True
        print("🚀 开始数据收集...")
        print("💡 按 Ctrl+C 停止收集")
        
        # 启动所有数据源线程
        for name, config in self.data_sources.items():
            if config.enabled:
                thread = threading.Thread(
                    target=self._collect_data,
                    args=(name,),
                    daemon=True
                )
                thread.start()
                self.threads[name] = thread
        
        print(f"✅ 启动了 {len(self.threads)} 个数据收集线程")
    
    def stop_collection(self):
        """停止数据收集"""
        if not self.is_collecting:
            print("⚠️ 数据收集未在运行")
            return
        
        print("🛑 停止数据收集...")
        self.stop_event.set()
        self.is_collecting = False
        
        # 等待所有线程结束
        for name, thread in self.threads.items():
            thread.join(timeout=2.0)
            print(f"✅ '{name}' 线程已停止")
        
        # 编码视频
        self._encode_videos()
        
        # 保存数据
        self._save_data()
        
        # 清理临时目录
        self._cleanup_temp_dirs()
        
        # 打印统计信息
        self._print_statistics()
    
    def _save_data(self):
        """保存收集的数据"""
        timestamp = int(time.time())
        data_file = self.output_dir / f"data_{timestamp}.h5"
        metadata_file = self.output_dir / f"metadata_{timestamp}.json"
        
        print(f"💾 保存数据到 {data_file}")
        
        # 保存HDF5数据
        with h5py.File(data_file, 'w') as f:
            for source_name, data_list in self.collected_data.items():
                if data_list:  # 只保存非空数据
                    try:
                        # 转换为numpy数组
                        if isinstance(data_list[0], (int, float)):
                            data_array = np.array(data_list)
                        elif isinstance(data_list[0], np.ndarray):
                            data_array = np.stack(data_list)
                        else:
                            # 对于其他类型，尝试转换
                            data_array = np.array(data_list, dtype=object)
                        
                        f.create_dataset(source_name, data=data_array)
                        
                        # 保存时间戳
                        if source_name in self.timestamps:
                            timestamps = np.array(self.timestamps[source_name])
                            f.create_dataset(f"{source_name}_timestamps", data=timestamps)
                            
                    except Exception as e:
                        print(f"⚠️ 保存 '{source_name}' 数据时出错: {e}")
        
        # 保存元数据
        metadata = {
            "collection_time": timestamp,
            "video_config": {
                "enabled": self.video_config.enabled,
                "codec": self.video_config.codec,
                "crf": self.video_config.crf,
                "fps": self.video_config.fps
            },
            "data_sources": {
                name: {
                    "frequency": config.frequency,
                    "is_image": config.is_image,
                    "sample_count": len(self.collected_data.get(name, []))
                }
                for name, config in self.data_sources.items()
            }
        }
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"📋 元数据保存到 {metadata_file}")
    
    def _cleanup_temp_dirs(self):
        """清理临时目录"""
        for source_name, temp_dir in self.temp_image_dirs.items():
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                print(f"🧹 清理临时目录: {temp_dir}")
    
    def _print_statistics(self):
        """打印收集统计信息"""
        print("\n📊 数据收集统计:")
        total_samples = 0
        for name, data_list in self.collected_data.items():
            count = len(data_list)
            total_samples += count
            config = self.data_sources[name]
            data_type = "图像" if config.is_image else "数据"
            print(f"  {name}: {count} 个{data_type}样本")
        
        print(f"  总计: {total_samples} 个样本")
        
        # 视频文件统计
        if self.video_config.enabled:
            video_files = list(self.output_dir.glob("*.mp4"))
            if video_files:
                total_video_size = sum(f.stat().st_size for f in video_files)
                print(f"  视频文件: {len(video_files)} 个 ({total_video_size/1024/1024:.1f}MB)")
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\n🛑 收到信号 {signum}，正在停止...")
        self.stop_collection()
        print("👋 再见！")
        exit(0)
    
    def run_forever(self):
        """运行数据收集直到手动停止"""
        self.start_collection()
        
        try:
            while self.is_collecting:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_collection()

# 示例数据源类
class MockCamera:
    """模拟相机"""
    def __init__(self, width=640, height=480):
        self.width = width
        self.height = height
        print(f"📷 模拟相机初始化 ({width}x{height})")
    
    def get_frame(self):
        """获取模拟图像帧"""
        # 生成彩色噪声图像
        frame = np.random.randint(0, 256, (self.height, self.width, 3), dtype=np.uint8)
        return frame

class MockSensor:
    """模拟传感器"""
    def __init__(self, dim=6):
        self.dim = dim
        print(f"📊 模拟传感器初始化 ({dim}维)")
    
    def get_data(self):
        """获取模拟传感器数据"""
        return np.random.randn(self.dim).astype(np.float32)

# 使用示例
if __name__ == "__main__":
    # 创建视频数据收集器
    video_config = VideoConfig(
        enabled=True,
        codec="libx264",
        crf=23,
        fps=30
    )
    
    collector = VideoDataCollector(
        output_dir="./video_data",
        default_frequency=30.0,
        video_config=video_config
    )
    
    # 注册数据源
    camera1 = MockCamera(640, 480)
    camera2 = MockCamera(320, 240)
    joint_sensor = MockSensor(7)
    
    collector.register_data_source("camera_main", camera1.get_frame, 
                                 frequency=30, is_image=True)
    collector.register_data_source("camera_wrist", camera2.get_frame, 
                                 frequency=15, is_image=True)
    collector.register_data_source("joint_positions", joint_sensor.get_data, 
                                 frequency=100)
    
    # 开始收集
    print("🎬 视频数据收集器演示")
    print("💡 将收集5秒数据，然后自动停止并编码视频")
    
    collector.start_collection()
    time.sleep(5)  # 收集5秒
    collector.stop_collection()
