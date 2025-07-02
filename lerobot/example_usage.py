#!/usr/bin/env python3
"""
简化数据收集器使用示例
展示如何轻松集成各种传感器和控制器
"""

from simple_data_collector import SimpleDataCollector, DataSourceConfig
import numpy as np
import time

# 模拟你的各种系统
class YourRobotArm:
    """你的机械臂系统"""
    def get_joint_positions(self):
        # 返回26个关节位置
        return np.random.randn(26).tolist()
    
    def get_joint_velocities(self):
        return np.random.randn(26).tolist()

class YourCameraSystem:
    """你的相机系统"""
    def get_camera_image(self, camera_id):
        # 模拟返回图像数据
        return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

class YourIMUSystem:
    """你的IMU系统"""
    def get_imu_data(self):
        # 返回加速度计和陀螺仪数据
        return {
            "accel": np.random.randn(3).tolist(),
            "gyro": np.random.randn(3).tolist(),
            "orientation": np.random.randn(4).tolist()  # 四元数
        }

class YourForceSystem:
    """你的力传感器系统"""
    def get_force_data(self):
        return np.random.randn(6).tolist()  # 3D力 + 3D力矩

class YourTeleopSystem:
    """你的遥操作系统"""
    def get_teleop_command(self):
        return {
            "arm_command": np.random.randn(26).tolist(),
            "base_command": np.random.randn(3).tolist()
        }

def main():
    """主函数 - 展示超简单的使用方式"""
    
    # 1. 创建数据收集器
    collector = SimpleDataCollector("./robot_data")
    
    # 2. 初始化你的各种系统
    robot_arm = YourRobotArm()
    camera_system = YourCameraSystem()
    imu_system = YourIMUSystem()
    force_system = YourForceSystem()
    teleop_system = YourTeleopSystem()
    
    # 3. 超简单地添加数据源 - 一行代码一个传感器！
    
    # 添加机械臂数据
    collector.add_sensor("arm_positions", robot_arm.get_joint_positions, frequency=100)
    collector.add_sensor("arm_velocities", robot_arm.get_joint_velocities, frequency=100)
    
    # 添加相机数据
    collector.add_sensor("front_camera", lambda: camera_system.get_camera_image(0), frequency=30)
    collector.add_sensor("side_camera", lambda: camera_system.get_camera_image(1), frequency=30)
    collector.add_sensor("wrist_camera", lambda: camera_system.get_camera_image(2), frequency=30)
    
    # 添加IMU数据
    collector.add_sensor("imu", imu_system.get_imu_data, frequency=200)
    
    # 添加力传感器数据
    collector.add_sensor("wrist_force", force_system.get_force_data, frequency=100)
    
    # 添加遥操作控制数据
    collector.add_control("teleop_commands", teleop_system.get_teleop_command, frequency=50)
    
    # 4. 开始收集 - 就这么简单！
    print("🚀 开始数据收集...")
    print("💡 按 Ctrl+C 停止并保存数据")
    
    collector.run_forever()

def advanced_example():
    """高级使用示例 - 更多控制"""
    
    collector = SimpleDataCollector("./advanced_data")
    
    # 你可以手动控制每个数据源的配置
    config = DataSourceConfig(
        name="high_freq_sensor",
        data_type="sensor",
        frequency=1000.0,  # 1kHz高频传感器
        enabled=True,
        params={"buffer_size": 1024}
    )
    
    def high_freq_callback():
        return np.random.randn(10).tolist()
    
    collector.add_data_source(config, high_freq_callback)
    
    # 手动控制收集过程
    collector.start_collection()
    
    # 收集10秒数据
    time.sleep(10)
    
    collector.stop_collection()
    collector.save_data("advanced_test")
    
    # 查看状态
    status = collector.get_status()
    print(f"收集状态: {status}")

if __name__ == "__main__":
    # 运行基本示例
    main()
    
    # 或者运行高级示例
    # advanced_example()
