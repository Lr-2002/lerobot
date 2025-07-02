#!/usr/bin/env python3
"""
实际使用示例 - 展示如何轻松集成你的系统
"""

from simple_data_collector import DataCollector, CameraSource, JointSensor, TactileSensor, TeleopController
import cv2
import numpy as np

# 你的实际系统类（替换为你的实际实现）
class YourCameraSystem:
    """你的相机系统"""
    def __init__(self, camera_ids: list):
        self.camera_ids = camera_ids
        self.cameras = {}
        for cam_id in camera_ids:
            # TODO: 初始化你的相机
            self.cameras[cam_id] = None  # 替换为实际相机对象
    
    def get_camera_frame(self, camera_id: int):
        """获取指定相机的帧"""
        # TODO: 替换为你的相机读取代码
        # return self.cameras[camera_id].read()
        return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

class YourRobotSystem:
    """你的机器人系统"""
    def __init__(self):
        # TODO: 初始化你的机器人连接
        pass
    
    def get_joint_positions(self):
        """获取关节位置"""
        # TODO: 替换为你的关节读取代码
        return np.random.uniform(-3.14, 3.14, 26).tolist()
    
    def get_end_effector_pose(self):
        """获取末端执行器位姿"""
        # TODO: 替换为你的位姿读取代码
        return {
            'position': [0.5, 0.2, 0.8],
            'orientation': [0, 0, 0, 1]  # 四元数
        }

class YourTactileSystem:
    """你的触觉系统"""
    def __init__(self, can_interface="can0"):
        self.can_interface = can_interface
        # TODO: 初始化CAN接口
    
    def read_tactile_sensors(self):
        """读取触觉传感器数据"""
        # TODO: 替换为你的CAN触觉读取代码
        return np.random.uniform(0, 1000, (1100, 1))

class YourTeleopSystem:
    """你的遥操作系统"""
    def __init__(self):
        # TODO: 初始化遥操作设备
        pass
    
    def get_teleop_commands(self):
        """获取遥操作命令"""
        # TODO: 替换为你的遥操作读取代码
        return {
            'arm_commands': np.random.uniform(-1, 1, 26).tolist(),
            'gripper_command': 0.5,
            'body_velocity': [0.1, 0.0, 0.0]
        }

def main():
    """主函数 - 超简单的数据收集设置"""
    
    print("🚀 初始化机器人数据收集系统...")
    
    # 1. 创建数据收集器
    collector = DataCollector(
        fps=30,  # 主频率
        dataset_name="humanoid_robot_data"
    )
    
    # 2. 初始化你的系统
    camera_system = YourCameraSystem([0, 1, 2, 3, 4])  # 5个相机
    robot_system = YourRobotSystem()
    tactile_system = YourTactileSystem()
    teleop_system = YourTeleopSystem()
    
    # 3. 注册数据源 - 超级简单！
    
    # 相机数据（不同频率）
    for i in range(5):
        collector.add_sensor(
            f"camera_{i}_rgb",
            lambda cam_id=i: camera_system.get_camera_frame(cam_id),
            frequency=30  # 30fps
        )
    
    # 机器人状态数据（高频率）
    collector.add_sensor(
        "joint_positions",
        robot_system.get_joint_positions,
        frequency=100  # 100Hz
    )
    
    collector.add_sensor(
        "end_effector_pose",
        robot_system.get_end_effector_pose,
        frequency=100
    )
    
    # 触觉数据（中等频率）
    collector.add_sensor(
        "tactile_data",
        tactile_system.read_tactile_sensors,
        frequency=50  # 50Hz
    )
    
    # 遥操作命令（标准频率）
    collector.add_controller(
        "teleop_commands",
        teleop_system.get_teleop_commands,
        frequency=30  # 30Hz
    )
    
    print("✅ 所有数据源已注册")
    print("📊 数据源概览:")
    print(f"   - 传感器: {len(collector.sensors)} 个")
    print(f"   - 控制器: {len(collector.controllers)} 个")
    print()
    print("🎯 使用方法:")
    print("   - 程序会自动开始收集数据")
    print("   - 按 Ctrl+C 停止并保存数据")
    print("   - 数据会保存到 ./data/ 目录")
    print()
    
    # 4. 开始收集 - 就这么简单！
    collector.run_forever()

if __name__ == "__main__":
    main()
