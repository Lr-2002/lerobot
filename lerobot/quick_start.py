#!/usr/bin/env python3
"""
快速启动脚本 - 一键开始数据收集
"""

import argparse
import sys
from pathlib import Path

def create_template_config():
    """创建配置模板"""
    template = '''#!/usr/bin/env python3
"""
你的数据收集配置文件
根据你的实际系统修改这个文件
"""

from simple_data_collector import DataCollector
import numpy as np

# =============================================================================
# 🔧 在这里定义你的实际系统类
# =============================================================================

class MyCameraSystem:
    """你的相机系统 - 替换为实际实现"""
    def __init__(self, camera_ids):
        self.camera_ids = camera_ids
        print(f"📷 初始化相机系统: {camera_ids}")
        # TODO: 初始化你的相机
    
    def get_frame(self, camera_id):
        """获取相机帧"""
        # TODO: 替换为你的实际相机读取代码
        # 示例：return cv2.imread(f"camera_{camera_id}.jpg")
        return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

class MyRobotSystem:
    """你的机器人系统 - 替换为实际实现"""
    def __init__(self):
        print("🤖 初始化机器人系统")
        # TODO: 初始化你的机器人连接
    
    def get_joint_positions(self):
        """获取关节位置"""
        # TODO: 替换为你的实际关节读取代码
        return np.random.uniform(-3.14, 3.14, 26).tolist()
    
    def get_end_effector_pose(self):
        """获取末端执行器位姿"""
        # TODO: 替换为你的实际位姿读取代码
        return {
            'position': [0.5, 0.2, 0.8],
            'orientation': [0, 0, 0, 1]
        }

class MyTactileSystem:
    """你的触觉系统 - 替换为实际实现"""
    def __init__(self):
        print("👋 初始化触觉系统")
        # TODO: 初始化你的CAN接口或其他触觉接口
    
    def get_tactile_data(self):
        """获取触觉数据"""
        # TODO: 替换为你的实际触觉读取代码
        return np.random.uniform(0, 1000, (1100, 1))

class MyTeleopSystem:
    """你的遥操作系统 - 替换为实际实现"""
    def __init__(self):
        print("🎮 初始化遥操作系统")
        # TODO: 初始化你的遥操作设备
    
    def get_teleop_action(self):
        """获取遥操作动作"""
        # TODO: 替换为你的实际遥操作读取代码
        return {
            'arm_joints': np.random.uniform(-1, 1, 26).tolist(),
            'gripper': 0.5,
            'body_velocity': [0.1, 0.0, 0.0]
        }

# =============================================================================
# 🚀 数据收集配置
# =============================================================================

def setup_data_collection():
    """设置数据收集"""
    
    # 创建数据收集器
    collector = DataCollector(
        fps=30,  # 主频率
        dataset_name="my_robot_dataset"  # 数据集名称
    )
    
    # 初始化你的系统
    camera_system = MyCameraSystem([0, 1, 2])  # 3个相机
    robot_system = MyRobotSystem()
    tactile_system = MyTactileSystem()
    teleop_system = MyTeleopSystem()
    
    # 注册数据源
    print("📝 注册数据源...")
    
    # 相机数据
    for i in range(3):
        collector.add_sensor(
            f"camera_{i}_rgb",
            lambda cam_id=i: camera_system.get_frame(cam_id),
            frequency=30
        )
    
    # 机器人状态
    collector.add_sensor(
        "joint_positions",
        robot_system.get_joint_positions,
        frequency=100  # 高频率
    )
    
    collector.add_sensor(
        "end_effector_pose",
        robot_system.get_end_effector_pose,
        frequency=100
    )
    
    # 触觉数据
    collector.add_sensor(
        "tactile_data",
        tactile_system.get_tactile_data,
        frequency=50
    )
    
    # 遥操作命令
    collector.add_controller(
        "teleop_action",
        teleop_system.get_teleop_action,
        frequency=30
    )
    
    return collector

if __name__ == "__main__":
    print("🚀 启动数据收集...")
    
    # 设置数据收集
    collector = setup_data_collection()
    
    print("✅ 配置完成！")
    print("💡 按 Ctrl+C 停止收集并保存数据")
    print()
    
    # 开始收集
    collector.run_forever()
'''
    
    with open("my_data_config.py", "w") as f:
        f.write(template)
    
    print("✅ 已创建配置模板: my_data_config.py")
    print("📝 请编辑这个文件，替换TODO部分为你的实际系统代码")

def run_demo():
    """运行演示"""
    print("🎬 运行演示模式...")
    
    from simple_data_collector import DataCollector, CameraSource, JointSensor, TactileSensor, TeleopController
    
    # 创建演示数据收集器
    collector = DataCollector(fps=10, dataset_name="demo_data")  # 低频率演示
    
    # 创建演示数据源
    camera = CameraSource(0)
    joints = JointSensor(26)
    tactile = TactileSensor()
    teleop = TeleopController()
    
    # 注册数据源
    collector.add_sensor("demo_camera", camera.get_frame, frequency=10)
    collector.add_sensor("demo_joints", joints.get_positions, frequency=20)
    collector.add_sensor("demo_tactile", tactile.get_tactile_data, frequency=15)
    collector.add_controller("demo_teleop", teleop.get_action, frequency=10)
    
    print("🎯 演示模式启动！")
    print("⏱️ 将运行10秒后自动停止...")
    
    import threading
    import time
    
    # 启动收集
    collector.start_collection()
    
    # 10秒后停止
    def stop_after_delay():
        time.sleep(10)
        collector.stop_collection()
        collector.save_data()
        print("🎉 演示完成！查看 ./data/ 目录")
    
    threading.Thread(target=stop_after_delay, daemon=True).start()
    
    try:
        while collector.running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        collector.stop_collection()
        collector.save_data()

def convert_data(h5_file, output_dir):
    """转换数据格式"""
    print(f"🔄 转换数据: {h5_file} -> {output_dir}")
    
    try:
        from lerobot_format_converter import convert_simple_data_to_lerobot
        
        dataset = convert_simple_data_to_lerobot(
            h5_file=h5_file,
            output_dir=output_dir,
            task_name="robot_manipulation"
        )
        
        print("✅ 转换完成！")
        return True
        
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="机器人数据收集快速启动工具")
    parser.add_argument("command", choices=["template", "demo", "convert"], 
                       help="命令: template(创建模板), demo(运行演示), convert(转换数据)")
    parser.add_argument("--h5-file", help="要转换的H5文件路径 (convert命令)")
    parser.add_argument("--output-dir", default="./lerobot_dataset", 
                       help="输出目录 (convert命令)")
    
    args = parser.parse_args()
    
    if args.command == "template":
        create_template_config()
        
    elif args.command == "demo":
        run_demo()
        
    elif args.command == "convert":
        if not args.h5_file:
            print("❌ 请指定H5文件路径: --h5-file <path>")
            sys.exit(1)
        
        if not Path(args.h5_file).exists():
            print(f"❌ 文件不存在: {args.h5_file}")
            sys.exit(1)
        
        success = convert_data(args.h5_file, args.output_dir)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    print("🤖 机器人数据收集快速启动工具")
    print("=" * 50)
    
    if len(sys.argv) == 1:
        print("使用方法:")
        print("  python quick_start.py template  # 创建配置模板")
        print("  python quick_start.py demo     # 运行演示")
        print("  python quick_start.py convert --h5-file <file>  # 转换数据")
        print()
        print("快速开始:")
        print("  1. python quick_start.py template")
        print("  2. 编辑 my_data_config.py")
        print("  3. python my_data_config.py")
        sys.exit(0)
    
    main()
