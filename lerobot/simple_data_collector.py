#!/usr/bin/env python3
"""
简化版通用数据收集器
支持多线程实时数据收集，统一存储为LeRobot格式
"""

import threading
import time
import signal
import sys
from dataclasses import dataclass, field
from typing import Dict, Any, Callable, Optional, List
import numpy as np
from queue import Queue, Empty
import json
from pathlib import Path
import cv2

@dataclass
class DataSourceConfig:
    """数据源配置"""
    name: str                    # 数据源名称
    data_type: str              # 数据类型: 'image', 'sensor', 'control'
    frequency: float = 30.0     # 采样频率 Hz
    enabled: bool = True        # 是否启用
    params: Dict[str, Any] = field(default_factory=dict)  # 自定义参数

class SimpleDataCollector:
    """简化版数据收集器"""
    
    def __init__(self, output_dir: str = "./data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 数据源管理
        self.data_sources: Dict[str, DataSourceConfig] = {}
        self.data_callbacks: Dict[str, Callable] = {}
        
        # 多线程管理
        self.threads: List[threading.Thread] = []
        self.data_queues: Dict[str, Queue] = {}
        self.running = False
        
        # 数据存储
        self.collected_data: Dict[str, List] = {}
        self.timestamps: List[float] = []
        
        # 设置信号处理（Ctrl+C优雅退出）
        signal.signal(signal.SIGINT, self._signal_handler)
        
        print("🚀 简化数据收集器已初始化")
    
    def add_data_source(self, config: DataSourceConfig, callback: Callable):
        """添加数据源"""
        self.data_sources[config.name] = config
        self.data_callbacks[config.name] = callback
        self.data_queues[config.name] = Queue()
        self.collected_data[config.name] = []
        
        print(f"✅ 已添加数据源: {config.name} ({config.data_type}, {config.frequency}Hz)")
    
    def add_camera(self, name: str, camera_id: int = 0, frequency: float = 30.0):
        """快速添加相机数据源"""
        def camera_callback():
            cap = cv2.VideoCapture(camera_id)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret:
                    return frame
            return None
        
        config = DataSourceConfig(
            name=name,
            data_type="image",
            frequency=frequency,
            params={"camera_id": camera_id}
        )
        self.add_data_source(config, camera_callback)
    
    def add_sensor(self, name: str, callback: Callable, frequency: float = 100.0):
        """快速添加传感器数据源"""
        config = DataSourceConfig(
            name=name,
            data_type="sensor", 
            frequency=frequency
        )
        self.add_data_source(config, callback)
    
    def add_control(self, name: str, callback: Callable, frequency: float = 50.0):
        """快速添加控制数据源"""
        config = DataSourceConfig(
            name=name,
            data_type="control",
            frequency=frequency
        )
        self.add_data_source(config, callback)
    
    def _data_collection_thread(self, source_name: str):
        """单个数据源的收集线程"""
        config = self.data_sources[source_name]
        callback = self.data_callbacks[source_name]
        queue = self.data_queues[source_name]
        
        interval = 1.0 / config.frequency
        
        print(f"🔄 启动数据收集线程: {source_name}")
        
        while self.running:
            try:
                start_time = time.time()
                
                # 获取数据
                data = callback()
                if data is not None:
                    timestamp = time.time()
                    queue.put((timestamp, data))
                
                # 控制频率
                elapsed = time.time() - start_time
                sleep_time = max(0, interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                print(f"❌ 数据源 {source_name} 出错: {e}")
                time.sleep(0.1)
    
    def _data_sync_thread(self):
        """数据同步线程 - 将所有数据源的数据同步到主存储"""
        print("🔄 启动数据同步线程")
        
        while self.running:
            try:
                current_time = time.time()
                synced_data = {}
                
                # 从各个队列获取最新数据
                for source_name, queue in self.data_queues.items():
                    latest_data = None
                    latest_timestamp = 0
                    
                    # 获取队列中最新的数据
                    while True:
                        try:
                            timestamp, data = queue.get_nowait()
                            if timestamp > latest_timestamp:
                                latest_timestamp = timestamp
                                latest_data = data
                        except Empty:
                            break
                    
                    if latest_data is not None:
                        synced_data[source_name] = latest_data
                
                # 如果有数据，保存到主存储
                if synced_data:
                    self.timestamps.append(current_time)
                    for source_name, data in synced_data.items():
                        self.collected_data[source_name].append(data)
                    
                    # 为没有数据的源填充None
                    for source_name in self.data_sources.keys():
                        if source_name not in synced_data:
                            self.collected_data[source_name].append(None)
                
                time.sleep(1.0 / 30.0)  # 30Hz同步频率
                
            except Exception as e:
                print(f"❌ 数据同步出错: {e}")
                time.sleep(0.1)
    
    def start_collection(self):
        """开始数据收集"""
        if self.running:
            print("⚠️  数据收集已在运行中")
            return
        
        if not self.data_sources:
            print("❌ 没有配置数据源，请先添加数据源")
            return
        
        self.running = True
        
        # 启动各个数据源的收集线程
        for source_name in self.data_sources.keys():
            if self.data_sources[source_name].enabled:
                thread = threading.Thread(
                    target=self._data_collection_thread,
                    args=(source_name,),
                    daemon=True
                )
                thread.start()
                self.threads.append(thread)
        
        # 启动数据同步线程
        sync_thread = threading.Thread(
            target=self._data_sync_thread,
            daemon=True
        )
        sync_thread.start()
        self.threads.append(sync_thread)
        
        print(f"🎯 开始收集数据，共 {len(self.data_sources)} 个数据源")
        print("💡 按 Ctrl+C 停止收集并保存数据")
    
    def stop_collection(self):
        """停止数据收集"""
        if not self.running:
            return
        
        print("\n🛑 正在停止数据收集...")
        self.running = False
        
        # 等待所有线程结束
        for thread in self.threads:
            thread.join(timeout=2.0)
        
        self.threads.clear()
        print("✅ 所有收集线程已停止")
    
    def save_data(self, filename: Optional[str] = None):
        """保存数据为LeRobot兼容格式"""
        if not self.timestamps:
            print("⚠️  没有收集到数据")
            return
        
        if filename is None:
            timestamp = int(time.time())
            filename = f"collected_data_{timestamp}"
        
        # 保存元数据
        metadata = {
            "total_samples": len(self.timestamps),
            "duration": self.timestamps[-1] - self.timestamps[0] if self.timestamps else 0,
            "data_sources": {
                name: {
                    "type": config.data_type,
                    "frequency": config.frequency,
                    "samples": len([x for x in self.collected_data[name] if x is not None])
                }
                for name, config in self.data_sources.items()
            },
            "collection_time": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 保存到JSON文件
        output_file = self.output_dir / f"{filename}.json"
        with open(output_file, 'w') as f:
            json.dump({
                "metadata": metadata,
                "timestamps": self.timestamps,
                "data": {name: data for name, data in self.collected_data.items()}
            }, f, indent=2, default=str)
        
        print(f"💾 数据已保存到: {output_file}")
        print(f"📊 收集了 {len(self.timestamps)} 个样本，时长 {metadata['duration']:.2f} 秒")
        
        return output_file
    
    def _signal_handler(self, signum, frame):
        """信号处理器 - 处理Ctrl+C"""
        print(f"\n🔔 收到信号 {signum}，正在优雅退出...")
        self.stop_collection()
        self.save_data()
        print("👋 数据收集器已退出")
        sys.exit(0)
    
    def run_forever(self):
        """运行数据收集器直到手动停止"""
        self.start_collection()
        
        try:
            while self.running:
                time.sleep(1)
                # 显示实时状态
                if len(self.timestamps) > 0:
                    print(f"\r📈 已收集 {len(self.timestamps)} 个样本", end="", flush=True)
        except KeyboardInterrupt:
            pass  # 信号处理器会处理
    
    def get_status(self):
        """获取收集器状态"""
        return {
            "running": self.running,
            "data_sources": len(self.data_sources),
            "samples_collected": len(self.timestamps),
            "active_threads": len(self.threads)
        }


# 使用示例和工具函数
def create_dummy_sensor_callback(sensor_name: str, dim: int = 1):
    """创建虚拟传感器回调函数"""
    def callback():
        return np.random.randn(dim).tolist()
    return callback

def create_dummy_control_callback(control_name: str, dim: int = 6):
    """创建虚拟控制回调函数"""
    def callback():
        return np.random.randn(dim).tolist()
    return callback

if __name__ == "__main__":
    # 使用示例
    collector = SimpleDataCollector("./collected_data")
    
    # 添加各种数据源
    collector.add_camera("front_camera", camera_id=0, frequency=30)
    collector.add_sensor("imu", create_dummy_sensor_callback("imu", 6), frequency=100)
    collector.add_sensor("force_sensor", create_dummy_sensor_callback("force", 3), frequency=50)
    collector.add_control("arm_joints", create_dummy_control_callback("arm", 7), frequency=50)
    
    # 开始收集
    collector.run_forever()
