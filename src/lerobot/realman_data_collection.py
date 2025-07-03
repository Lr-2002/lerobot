#!/usr/bin/env python3
"""
实际使用示例 - 展示如何轻松集成你的系统
"""

from simple_data_collector_clean import SimpleDataCollector, VideoConfig
import cv2
import numpy as np
import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import time

from realman_tele import ButtonTele
import signal

# 你的实际系统类（替换为你的实际实现）
class BasicCamera:
	def __init__(self, prefix) -> None:

		self.prefix = prefix
		self.topic_name = f'{self.prefix}/image_raw'
		self.bridge = CvBridge()
		self.image = None 
		
		rospy.loginfo(f"订阅主题：{self.topic_name}")
		self.sub = rospy.Subscriber(self.topic_name, Image, self.image_callback)
		# 不要在这里调用rospy.spin()，会阻塞

	def image_callback(self, data):
		try:
			cv_image = self.bridge.imgmsg_to_cv2(data, "bgr8")
			self.image = cv_image
		except Exception as e:
			rospy.logerr(f"图像转换失败: {e}")

	def get_image(self):		
		if self.image is None:
			rospy.logwarn_once(f"Camera {self.prefix} image is None, waiting...")
			start = rospy.Time.now()
			while self.image is None and (rospy.Time.now() - start).to_sec() < 1.0:
				rospy.sleep(0.01)
			if self.image is None:
				raise RuntimeError(f"Camera {self.prefix} image is None after waiting 1 second")
		return self.image


class RealSenseCamera(BasicCamera):
	"""你的相机系统"""
	def __init__(self, camera_id):
		self.camera_id = camera_id
		self.prefix = f'/camera_d435_{camera_id}/color/'
		BasicCamera.__init__(self, self.prefix)
		

class USBCamera(BasicCamera):
	"""你的相机系统"""
	def __init__(self, camera_id):
		self.camera_id = camera_id
		self.prefix = f'/camera{camera_id}/'
		BasicCamera.__init__(self, self.prefix)
		

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

class RealmanTeleopSystem:
	"""基于ButtonTele的遥操作系统"""
	def __init__(self, 
			left_arm_ip='192.168.1.18',
			right_arm_ip='192.168.1.19',
			left_hand_port='/dev/ttyUSB0',
			right_hand_port='/dev/ttyUSB1',
			left_esp32_name='ESP32_Left',
			right_esp32_name='ESP32_Right'):
		self.teleop = ButtonTele(
			left_arm_ip=left_arm_ip,
			right_arm_ip=right_arm_ip,
			left_hand_port=left_hand_port,
			right_hand_port=right_hand_port,
			left_esp32_device_name=left_esp32_name,
			right_esp32_device_name=right_esp32_name
		)
		self.teleop.start()
		print("✅ 遥操作系统已启动")
	
	def get_teleop_commands(self):
		"""获取遥操作命令"""
		try:
			# 从 ButtonTele 获取当前状态
			# 这里需要根据 ButtonTele 的实际 API 调整
			commands = {
				'left_arm_joints': getattr(self.teleop, 'left_arm_joints', [0]*7),
				'right_arm_joints': getattr(self.teleop, 'right_arm_joints', [0]*7),
				'left_hand': getattr(self.teleop, 'left_hand', [0] * 6 ),
				'right_hand': getattr(self.teleop, 'right_hand', [0] * 6 ),
				'timestamp': time.time()
			}
			return commands
		except Exception as e:
			rospy.logwarn(f"获取遥操作命令失败: {e}")
			return {
				'left_arm_joints': [0]*7,
				'right_arm_joints': [0]*7,
				'left_hand': [0]*6,
				'right_hand': [0]*6,
				'timestamp': time.time()
			}
	
	def stop(self):
		"""停止遥操作系统"""
		if hasattr(self, 'teleop'):
			self.teleop.stop()
			print("🛑 遥操作系统已停止")

def signal_handler(sig, frame):
	"""信号处理器"""
	print("\n🛑 收到停止信号...")
	# 这里会由 KeyboardInterrupt 处理

def main():
	"""主函数 - 集成遥操作的数据收集系统"""
	
	print("🚀 初始化Realman机器人数据收集系统...")
	print("🎯 输出目录: ./realman_data")
	print("📊 数据集名称: realman_teleop_data")
	
	# 设置信号处理器
	signal.signal(signal.SIGINT, signal_handler)
	
	# 初始化ROS节点
	rospy.init_node('realman_data_collector', anonymous=True)
	
	# 1. 创建视频配置
	video_config = VideoConfig(
		enabled=True,
		codec="libx264",
		crf=23,  # 高质量
		fps=30
	)
	
	# 2. 创建数据收集器
	collector = SimpleDataCollector(
		fps=30,  # 默认频率
		dataset_name="realman_teleop_data",
		output_dir="./realman_data",
		video_config=video_config
	)
	
	# 3. 初始化你的系统
	print("📷 初始化相机系统...")
	realsense_cameras = []
	usb_cameras = []
	
	# 创建相机实例（但不要在构造函数中调用rospy.spin())
	try:
		for i in range(3):
			cam = RealSenseCamera(i)
			realsense_cameras.append(cam)
			print(f"✅ RealSense相机 {i} 初始化完成")
	except Exception as e:
		print(f"⚠️ RealSense相机初始化失败: {e}")
	
	try:
		for i in range(2):
			cam = USBCamera(i)
			usb_cameras.append(cam)
			print(f"✅ USB相机 {i} 初始化完成")
	except Exception as e:
		print(f"⚠️ USB相机初始化失败: {e}")
	
	print("🤖 初始化机器人系统...")
	robot_system = YourRobotSystem()
	
	print("🎮 初始化遥操作系统...")
	teleop_system = None
	try:
		teleop_system = RealmanTeleopSystem(
			left_arm_ip='192.168.1.18',
			right_arm_ip='192.168.1.19',
			left_hand_port='/dev/ttyUSB0',
			right_hand_port='/dev/ttyUSB1',
			left_esp32_name='ESP32_Left',
			right_esp32_name='ESP32_Right'
		)
	except Exception as e:
		print(f"⚠️ 遥操作系统初始化失败: {e}")
		print("📝 将继续进行数据收集，但不包含遥操作数据")
	
	# 4. 注册数据源 - 使用正确的API
	print("📝 注册数据源...")
	
	# 注册相机数据源（图像数据）
	for i, cam in enumerate(realsense_cameras):
		collector.register_data_source(
			f"realsense_{i}_rgb",
			cam.get_image,  # 直接传递方法引用
			frequency=30,
			is_image=True  # 标记为图像数据
		)
		print(f"✅ 注册 RealSense {i} 相机")
	
	for i, cam in enumerate(usb_cameras):
		collector.register_data_source(
			f"usb_{i}_rgb",
			cam.get_image,
			frequency=30,
			is_image=True
		)
		print(f"✅ 注册 USB {i} 相机")
	
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
	
	# 注册遥操作数据源
	if teleop_system is not None:
		collector.register_data_source(
			"teleop_commands",
			teleop_system.get_teleop_commands,
			frequency=30  # 30Hz
		)
		print("✅ 注册遥操作命令")
	
	# 可选：注册触觉数据
	# tactile_system = YourTactileSystem()
	# collector.register_data_source(
	#     "tactile_data",
	#     tactile_system.read_tactile_sensors,
	#     frequency=50
	# )
	
	print(f"✅ 所有数据源已注册 ({len(collector.data_sources)} 个)")
	print()
	print("🎯 使用说明:")
	print("   - 程序将自动开始收集数据")
	print("   - 按 Ctrl+C 停止并保存数据")
	print("   - 数据会保存到 ./realman_data/ 目录")
	print("   - 图像数据会自动编码为视频文件")
	if teleop_system is not None:
		print("   - 包含遥操作数据收集")
	print()
	
	# 5. 开始收集 - 集成遥操作系统！
	try:
		print("🎆 开始 Realman 机器人数据收集...")
		collector.run_forever()
	except KeyboardInterrupt:
		print("\n🛑 用户中断收集")
	except Exception as e:
		print(f"\n❌ 数据收集错误: {e}")
		import traceback
		traceback.print_exc()
	finally:
		# 清理遥操作系统
		if teleop_system is not None:
			try:
				teleop_system.stop()
			except Exception as e:
				print(f"⚠️ 停止遥操作系统时出错: {e}")
		print("💾 Realman 数据收集完成")

if __name__ == "__main__":
	main()
