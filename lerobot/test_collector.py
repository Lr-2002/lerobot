#!/usr/bin/env python3
"""
测试简化数据收集器（不依赖摄像头）
"""

from simple_data_collector import SimpleDataCollector
import numpy as np
import time

def test_basic_collection():
    """测试基本数据收集功能"""
    print("🧪 开始测试基本数据收集...")
    
    # 创建收集器
    collector = SimpleDataCollector("./test_data")
    
    # 添加模拟传感器
    collector.add_sensor("imu", 
                        lambda: np.random.randn(6).tolist(), 
                        frequency=100)
    
    collector.add_sensor("force_sensor", 
                        lambda: np.random.randn(3).tolist(), 
                        frequency=50)
    
    collector.add_control("arm_command", 
                         lambda: np.random.randn(7).tolist(), 
                         frequency=30)
    
    # 开始收集
    collector.start_collection()
    
    # 收集5秒数据
    print("📊 收集5秒数据...")
    for i in range(5):
        time.sleep(1)
        status = collector.get_status()
        print(f"  第{i+1}秒: 已收集 {status['samples_collected']} 个样本")
    
    # 停止并保存
    collector.stop_collection()
    output_file = collector.save_data("test_run")
    
    print(f"✅ 测试完成，数据保存到: {output_file}")
    return output_file

def test_high_frequency():
    """测试高频数据收集"""
    print("\n🚀 测试高频数据收集...")
    
    collector = SimpleDataCollector("./test_data")
    
    # 添加高频传感器
    collector.add_sensor("high_freq_sensor", 
                        lambda: np.random.randn(10).tolist(), 
                        frequency=500)  # 500Hz
    
    collector.add_sensor("medium_freq_sensor", 
                        lambda: np.random.randn(5).tolist(), 
                        frequency=100)  # 100Hz
    
    collector.add_sensor("low_freq_sensor", 
                        lambda: {"data": np.random.randn(3).tolist(), "timestamp": time.time()}, 
                        frequency=10)   # 10Hz
    
    # 收集3秒
    collector.start_collection()
    time.sleep(3)
    collector.stop_collection()
    
    output_file = collector.save_data("high_freq_test")
    print(f"✅ 高频测试完成: {output_file}")

if __name__ == "__main__":
    # 运行测试
    test_basic_collection()
    test_high_frequency()
    
    print("\n🎉 所有测试完成！")
    print("💡 你可以查看 ./test_data/ 目录下的数据文件")
