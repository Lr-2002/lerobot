#!/usr/bin/env python3
"""
简化测试版本 - 不依赖ROS，展示如何使用SimpleDataCollector
"""

from simple_data_collector_clean import SimpleDataCollector, VideoConfig
import cv2
import numpy as np
import time

# 模拟相机系统（不依赖ROS）
class MockCamera:
    def __init__(self, camera_id):
        self.camera_id = camera_id
        self.frame_count = 0
    
    def get_image(self):
        """生成模拟图像"""
        # 创建一个彩色图像，显示相机ID和帧数
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 设置背景颜色（每个相机不同颜色）
        colors = [(100, 50, 200), (50, 200, 100), (200, 100, 50), (150, 150, 50), (50, 150, 150)]
        color = colors[self.camera_id % len(colors)]
        img[:] = color
        
        # 添加文字信息
        text = f"Camera {self.camera_id} - Frame {self.frame_count}"
        cv2.putText(img, text, (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # 添加时间戳
        timestamp = f"Time: {time.time():.2f}"
        cv2.putText(img, timestamp, (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        self.frame_count += 1
        return img

# 模拟机器人系统
class MockRobotSystem:
    def __init__(self):
        self.joint_count = 0
        self.pose_count = 0
    
    def get_joint_positions(self):
        """获取模拟关节位置"""
        # 生成26个关节的正弦波位置
        t = time.time()
        positions = []
        for i in range(26):
            pos = np.sin(t + i * 0.1) * (i + 1) * 0.1
            positions.append(float(pos))
        
        self.joint_count += 1
        return positions
    
    def get_end_effector_pose(self):
        """获取模拟末端执行器位姿"""
        t = time.time()
        pose = {
            'position': [
                0.5 + 0.1 * np.sin(t),
                0.2 + 0.1 * np.cos(t),
                0.8 + 0.05 * np.sin(t * 2)
            ],
            'orientation': [
                np.sin(t * 0.5) * 0.1,
                np.cos(t * 0.5) * 0.1,
                0.0,
                1.0
            ],
            'timestamp': t
        }
        
        self.pose_count += 1
        return pose

def main():
    """主函数 - 简化测试版本"""
    
    print("🚀 初始化简化数据收集测试...")
    
    # 1. 创建视频配置
    video_config = VideoConfig(
        enabled=True,
        codec="libx264",
        crf=23,  # 高质量
        fps=30
    )
    
    # 2. 创建数据收集器
    collector = SimpleDataCollector(
        fps=30,  # 主频率
        dataset_name="mock_robot_data",
        output_dir="./test_data",
        video_config=video_config
    )
    
    # 3. 初始化模拟系统
    print("📷 初始化模拟相机系统...")
    cameras = []
    for i in range(3):  # 3个模拟相机
        cam = MockCamera(i)
        cameras.append(cam)
        print(f"✅ 模拟相机 {i} 初始化完成")
    
    print("🤖 初始化模拟机器人系统...")
    robot_system = MockRobotSystem()
    
    # 4. 注册数据源
    print("📝 注册数据源...")
    
    # 注册相机数据源（图像数据）
    for i, cam in enumerate(cameras):
        collector.register_data_source(
            f"mock_camera_{i}",
            cam.get_image,
            frequency=30,
            is_image=True  # 标记为图像数据
        )
        print(f"✅ 注册模拟相机 {i}")
    
    # 注册机器人数据源（非图像数据）
    collector.register_data_source(
        "joint_positions",
        robot_system.get_joint_positions,
        frequency=100  # 100Hz
    )
    print("✅ 注册关节位置传感器")
    
    collector.register_data_source(
        "end_effector_pose",
        robot_system.get_end_effector_pose,
        frequency=50  # 50Hz
    )
    print("✅ 注册末端执行器位姿传感器")
    
    print(f"✅ 所有数据源已注册 ({len(collector.data_sources)} 个)")
    print()
    print("🎯 测试说明:")
    print("   - 将收集5秒的模拟数据")
    print("   - 3个模拟相机 @ 30fps")
    print("   - 关节位置 @ 100Hz")
    print("   - 末端位姿 @ 50Hz")
    print("   - 图像会自动编码为视频文件")
    print()
    
    # 5. 开始收集测试
    try:
        print("🎬 开始5秒数据收集测试...")
        collector.run_for_duration(5.0)  # 收集5秒
        
        # 显示统计信息
        stats = collector.get_stats()
        print("\n📊 收集统计:")
        for source_name, count in stats.items():
            print(f"   {source_name}: {count} 个样本")
        
    except Exception as e:
        print(f"\n❌ 数据收集错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("💾 测试完成")

if __name__ == "__main__":
    main()
