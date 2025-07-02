#!/usr/bin/env python3
"""
测试简单数据收集器
"""

from simple_data_collector import DataCollector
import numpy as np
import time
import threading

def test_basic_collection():
    """测试基本数据收集功能"""
    print("🧪 测试基本数据收集功能...")
    
    # 创建收集器
    collector = DataCollector(fps=5, dataset_name="test_data")
    
    # 简单的测试数据源
    def get_test_sensor_data():
        return np.random.rand(10)
    
    def get_test_controller_data():
        return {"action": np.random.rand(5).tolist()}
    
    # 注册数据源
    collector.add_sensor("test_sensor", get_test_sensor_data, frequency=10)
    collector.add_controller("test_controller", get_test_controller_data, frequency=5)
    
    # 开始收集
    collector.start_collection()
    
    # 收集3秒
    time.sleep(3)
    
    # 停止收集
    collector.stop_collection()
    
    # 保存数据
    collector.save_data("./test_output")
    
    # 检查结果
    if collector.collected_data:
        print("✅ 数据收集成功！")
        for name, data in collector.collected_data.items():
            print(f"   {name}: {len(data)} 个样本")
        return True
    else:
        print("❌ 数据收集失败！")
        return False

def test_multi_frequency():
    """测试多频率数据收集"""
    print("\n🧪 测试多频率数据收集...")
    
    collector = DataCollector(fps=10, dataset_name="multi_freq_test")
    
    # 不同频率的数据源
    def high_freq_data():
        return time.time()
    
    def low_freq_data():
        return np.random.rand(3, 3)
    
    collector.add_sensor("high_freq", high_freq_data, frequency=20)
    collector.add_sensor("low_freq", low_freq_data, frequency=2)
    
    collector.start_collection()
    time.sleep(2)
    collector.stop_collection()
    
    # 检查频率
    high_count = len(collector.collected_data.get("high_freq", []))
    low_count = len(collector.collected_data.get("low_freq", []))
    
    print(f"   高频数据: {high_count} 个样本 (期望约40)")
    print(f"   低频数据: {low_count} 个样本 (期望约4)")
    
    if high_count > low_count * 5:  # 高频应该明显多于低频
        print("✅ 多频率测试成功！")
        return True
    else:
        print("❌ 多频率测试失败！")
        return False

def test_error_handling():
    """测试错误处理"""
    print("\n🧪 测试错误处理...")
    
    collector = DataCollector(fps=5, dataset_name="error_test")
    
    # 正常数据源
    def normal_data():
        return [1, 2, 3]
    
    # 会出错的数据源
    def error_data():
        if np.random.rand() > 0.5:
            raise Exception("模拟错误")
        return [4, 5, 6]
    
    collector.add_sensor("normal", normal_data, frequency=10)
    collector.add_sensor("error_prone", error_data, frequency=10)
    
    collector.start_collection()
    time.sleep(2)
    collector.stop_collection()
    
    # 检查是否有正常数据
    normal_count = len(collector.collected_data.get("normal", []))
    error_count = len(collector.collected_data.get("error_prone", []))
    
    print(f"   正常数据: {normal_count} 个样本")
    print(f"   错误数据: {error_count} 个样本")
    
    if normal_count > 0:
        print("✅ 错误处理测试成功！")
        return True
    else:
        print("❌ 错误处理测试失败！")
        return False

def main():
    """运行所有测试"""
    print("🚀 开始测试简单数据收集器...")
    print("=" * 50)
    
    tests = [
        test_basic_collection,
        test_multi_frequency,
        test_error_handling
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 测试异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"🎯 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统工作正常")
    else:
        print("⚠️ 部分测试失败，请检查系统")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
