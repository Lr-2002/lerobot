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
from dataclasses import dataclass
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

class SimpleDataCollector:
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
    
    def _signal_handler(self, signum, frame):
        """处理Ctrl+C信号"""
        print("\n🛑 收到停止信号，正在优雅关闭...")
        self.stop()
    
    def register_data_source(self, name: str, callback: Callable[[], Any], 
                           frequency: float = None, is_image: bool = False):
        """注册数据源"""
        if frequency is None:
            frequency = self.default_frequency
            
        config = DataSourceConfig(
            name=name,
            callback=callback,
            frequency=frequency,
            is_image=is_image
        )
        
        self.data_sources[name] = config
        self.collected_data[name] = []
        self.timestamps[name] = []
        
        if is_image and self.video_config.enabled:
            # Create temporary directory for image frames
            temp_dir = Path(tempfile.mkdtemp(prefix=f"images_{name}_"))
            self.temp_image_dirs[name] = temp_dir
            self.image_counters[name] = 0
            print(f"📷 注册图像数据源 '{name}' @ {frequency} Hz (视频编码)")
        else:
            print(f"📊 注册数据源 '{name}' @ {frequency} Hz")
    
    def _collect_data_thread(self, source_name: str):
        """数据收集线程"""
        config = self.data_sources[source_name]
        interval = 1.0 / config.frequency
        
        print(f"🔄 开始收集 '{source_name}' @ {config.frequency} Hz")
        
        while not self.stop_event.is_set():
            start_time = time.time()
            
            try:
                # Get data from callback
                data = config.callback()
                timestamp = time.time()
                
                if config.is_image and self.video_config.enabled:
                    # Save image to temporary file
                    self._save_image_frame(source_name, data, timestamp)
                else:
                    # Store data in memory
                    with self.data_lock:
                        self.collected_data[source_name].append(data)
                        self.timestamps[source_name].append(timestamp)
                
            except Exception as e:
                print(f"❌ 数据源 '{source_name}' 错误: {e}")
            
            # Sleep for the remaining time
            elapsed = time.time() - start_time
            sleep_time = max(0, interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        print(f"✅ '{source_name}' 线程已停止")
    
    def _save_image_frame(self, source_name: str, image_data: np.ndarray, timestamp: float):
        """保存图像帧到临时文件"""
        try:
            # Convert numpy array to PIL Image
            if isinstance(image_data, np.ndarray):
                if image_data.dtype != np.uint8:
                    image_data = (image_data * 255).astype(np.uint8)
                
                if len(image_data.shape) == 3:
                    image = Image.fromarray(image_data)
                else:
                    image = Image.fromarray(image_data, mode='L')
            else:
                image = image_data
            
            # Save to temporary directory
            frame_idx = self.image_counters[source_name]
            temp_dir = self.temp_image_dirs[source_name]
            image_path = temp_dir / f"frame_{frame_idx:06d}.jpg"
            
            image.save(image_path, "JPEG", quality=95)
            
            # Store timestamp
            with self.data_lock:
                self.timestamps[source_name].append(timestamp)
            
            self.image_counters[source_name] += 1
            
        except Exception as e:
            print(f"❌ 保存图像帧失败 '{source_name}': {e}")
    
    def start(self):
        """开始数据收集"""
        if self.is_collecting:
            print("⚠️ 数据收集已在进行中")
            return
        
        self.is_collecting = True
        self.stop_event.clear()
        
        print("🚀 开始数据收集...")
        
        # Start collection threads
        for source_name in self.data_sources:
            thread = threading.Thread(
                target=self._collect_data_thread,
                args=(source_name,),
                daemon=False  # Changed to False to ensure proper cleanup
            )
            thread.start()
            self.threads[source_name] = thread
        
        print(f"✅ 启动了 {len(self.threads)} 个数据收集线程")
    
    def stop(self):
        """停止数据收集"""
        if not self.is_collecting:
            print("⚠️ 数据收集未在进行")
            return
        
        print("🛑 停止数据收集...")
        self.stop_event.set()
        
        # Wait for all threads to finish
        for source_name, thread in self.threads.items():
            if thread.is_alive():
                thread.join(timeout=3.0)
                if thread.is_alive():
                    print(f"⚠️ 线程 '{source_name}' 未能正常停止")
        
        self.is_collecting = False
        
        # Process and save data
        self._save_data()
        
        print("✅ 数据收集已停止")
    
    def _save_data(self):
        """保存收集的数据"""
        timestamp = int(time.time())
        
        # Encode videos for image sources
        if self.video_config.enabled:
            self._encode_videos()
        
        # Save non-image data to HDF5
        h5_path = self.output_dir / f"data_{timestamp}.h5"
        self._save_hdf5_data(h5_path)
        
        # Save metadata
        metadata_path = self.output_dir / f"metadata_{timestamp}.json"
        self._save_metadata(metadata_path)
        
        # Cleanup temporary directories
        self._cleanup_temp_dirs()
        
        print(f"💾 数据已保存到 {self.output_dir}")
    
    def _encode_videos(self):
        """编码视频文件"""
        print("🎬 开始视频编码...")
        
        for source_name, temp_dir in self.temp_image_dirs.items():
            if not temp_dir.exists():
                continue
                
            # Count frames
            frame_files = list(temp_dir.glob("frame_*.jpg"))
            if len(frame_files) == 0:
                continue
            
            print(f"🎥 编码 '{source_name}' -> {source_name}.mp4")
            
            # Calculate original size
            original_size = sum(f.stat().st_size for f in frame_files)
            
            # Encode video using ffmpeg
            video_path = self.output_dir / f"{source_name}.mp4"
            self._run_ffmpeg_encoding(temp_dir, video_path)
            
            # Calculate compression ratio
            if video_path.exists():
                compressed_size = video_path.stat().st_size
                ratio = original_size / compressed_size if compressed_size > 0 else 1
                print(f"✅ '{source_name}' 视频编码完成")
                print(f"   压缩比: {ratio:.1f}x ({original_size/1024/1024:.1f}MB -> {compressed_size/1024/1024:.1f}MB)")
    
    def _run_ffmpeg_encoding(self, input_dir: Path, output_path: Path):
        """运行ffmpeg编码"""
        try:
            cmd = [
                "ffmpeg", "-y",  # Overwrite output
                "-framerate", str(self.video_config.fps),
                "-i", str(input_dir / "frame_%06d.jpg"),
                "-c:v", self.video_config.codec,
                "-crf", str(self.video_config.crf),
                "-pix_fmt", self.video_config.pixel_format,
                "-g", str(self.video_config.keyframe_interval),
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ ffmpeg编码失败: {result.stderr}")
                
        except Exception as e:
            print(f"❌ 视频编码错误: {e}")
    
    def _save_hdf5_data(self, h5_path: Path):
        """保存非图像数据到HDF5"""
        try:
            with h5py.File(h5_path, 'w') as f:
                for source_name, data_list in self.collected_data.items():
                    config = self.data_sources[source_name]
                    
                    # Skip image sources (they are saved as videos)
                    if config.is_image and self.video_config.enabled:
                        continue
                    
                    if len(data_list) == 0:
                        continue
                    
                    # Convert to numpy array
                    try:
                        data_array = np.array(data_list)
                        timestamps_array = np.array(self.timestamps[source_name])
                        
                        # Create group for this data source
                        group = f.create_group(source_name)
                        group.create_dataset('data', data=data_array)
                        group.create_dataset('timestamps', data=timestamps_array)
                        
                    except Exception as e:
                        print(f"⚠️ 无法保存数据源 '{source_name}': {e}")
                        
        except Exception as e:
            print(f"❌ 保存HDF5文件失败: {e}")
    
    def _save_metadata(self, metadata_path: Path):
        """保存元数据"""
        metadata = {
            "collection_time": int(time.time()),
            "dataset_name": self.dataset_name,
            "video_config": {
                "enabled": self.video_config.enabled,
                "codec": self.video_config.codec,
                "crf": self.video_config.crf,
                "fps": self.video_config.fps
            } if self.video_config.enabled else None,
            "data_sources": {}
        }
        
        for source_name, config in self.data_sources.items():
            if config.is_image and self.video_config.enabled:
                sample_count = self.image_counters.get(source_name, 0)
            else:
                sample_count = len(self.collected_data.get(source_name, []))
            
            metadata["data_sources"][source_name] = {
                "frequency": config.frequency,
                "is_image": config.is_image,
                "sample_count": sample_count
            }
        
        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            print(f"❌ 保存元数据失败: {e}")
    
    def _cleanup_temp_dirs(self):
        """清理临时目录"""
        for source_name, temp_dir in self.temp_image_dirs.items():
            if temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                    print(f"🧹 清理临时目录: {temp_dir}")
                except Exception as e:
                    print(f"⚠️ 清理临时目录失败 {temp_dir}: {e}")
    
    def run_for_duration(self, duration: float):
        """运行指定时间"""
        self.start()
        print(f"💤 收集数据 {duration} 秒...")
        
        # Wait for the specified duration
        start_time = time.time()
        while time.time() - start_time < duration and self.is_collecting:
            time.sleep(0.1)
        
        self.stop()
    
    def run_forever(self):
        """持续运行直到Ctrl+C"""
        self.start()
        print("💡 按 Ctrl+C 停止收集")
        try:
            while self.is_collecting:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n🛑 收到停止信号...")
        finally:
            if self.is_collecting:
                self.stop()
    
    def get_stats(self):
        """获取收集统计"""
        stats = {}
        total_samples = 0
        
        for source_name, config in self.data_sources.items():
            if config.is_image and self.video_config.enabled:
                count = self.image_counters.get(source_name, 0)
            else:
                count = len(self.collected_data.get(source_name, []))
            
            stats[source_name] = count
            total_samples += count
        
        return stats, total_samples


# 示例使用
if __name__ == "__main__":
    # 模拟数据源
    def get_mock_image():
        """模拟相机数据"""
        return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    def get_mock_sensor():
        """模拟传感器数据"""
        return np.random.randn(6).tolist()
    
    # 创建收集器
    video_config = VideoConfig(
        enabled=True,
        codec="libx264",
        crf=23,
        fps=30
    )
    
    collector = SimpleDataCollector(
        fps=30,
        dataset_name="test_data",
        output_dir="./simple_data",
        video_config=video_config
    )
    
    # 注册数据源
    collector.register_data_source("camera", get_mock_image, frequency=30, is_image=True)
    collector.register_data_source("sensors", get_mock_sensor, frequency=100, is_image=False)
    
    print("\n🎬 简化数据收集器演示")
    print("💡 将收集3秒数据，然后自动停止")
    
    # 运行3秒
    collector.run_for_duration(3.0)
    
    # 显示统计
    stats, total = collector.get_stats()
    print(f"\n📊 收集统计:")
    for name, count in stats.items():
        print(f"  {name}: {count} 个样本")
    print(f"  总计: {total} 个样本")
