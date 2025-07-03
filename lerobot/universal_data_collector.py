from lerobot.common.robots import Robot, RobotConfig
from lerobot.common.teleoperators import Teleoperator, TeleoperatorConfig
from dataclasses import dataclass, field
import numpy as np
from typing import Dict, Any, Callable

@dataclass
class DataProviderConfig:
    """数据提供者的配置"""
    name: str
    # 自定义参数，可以为空
    params: Dict[str, Any] = field(default_factory=dict)

class ExternalDataProvider:
    """外部数据提供接口类"""
    
    def __init__(self):
        self.data_callbacks = {}
    
    def register_data_callback(self, name, callback_fn):
        """注册一个数据提供回调函数"""
        self.data_callbacks[name] = callback_fn
    
    def get_data(self, name):
        """获取指定名称的数据"""
        if name in self.data_callbacks:
            try:
                return self.data_callbacks[name]()
            except Exception as e:
                print(f"Error getting data for {name}: {e}")
                return None
        return None

# 全局数据提供者
data_provider = ExternalDataProvider()

@dataclass
class AdapterRobotConfig(RobotConfig):
    """适配器机器人配置"""
    # 添加任何需要的配置参数
    external_data_configs: Dict[str, Any] = field(default_factory=dict)

class AdapterRobot(Robot):
    """适配外部数据源的机器人类"""
    
    def __init__(self, config: AdapterRobotConfig):
        super().__init__(config)
        self.config = config
        
        # 定义动作和观测特征
        self.action_features = [
            # 26维上肢动作
            *[f"arm_{i}" for i in range(26)],
            # 3D本体运动
            "body_x", "body_y", "body_z"
        ]
        
        self.observation_features = [
            # 相机图像 - 这些名称应与您提供的数据键名一致
            *[f"camera_{i}_rgb" for i in range(5)],  # 假设5个相机
            *[f"camera_{i}_depth" for i in range(3)],  # 假设3个是深度相机
            
            # 状态量
            *[f"joint_pos_{i}" for i in range(26)],
            "position_x", "position_y", "position_z"
        ]
        
        # 如果有触觉数据
        if config.external_data_configs.get("has_tactile", False):
            self.observation_features.append("tactile")
    
    def connect(self):
        """不需要实际连接，只是保持API一致"""
        print("AdapterRobot ready for data")
    
    def disconnect(self):
        """不需要实际断开连接，只是保持API一致"""
        print("AdapterRobot disconnected")
    
    def get_observation(self):
        """从外部数据提供者获取观测数据"""
        observation = {}
        
        # 获取相机数据
        for i in range(5):
            rgb_data = data_provider.get_data(f"camera_{i}_rgb")
            if rgb_data is not None:
                observation[f"camera_{i}_rgb"] = rgb_data
        
        for i in range(3):
            depth_data = data_provider.get_data(f"camera_{i}_depth")
            if depth_data is not None:
                observation[f"camera_{i}_depth"] = depth_data
        
        # 获取状态数据
        for i in range(26):
            joint_data = data_provider.get_data(f"joint_pos_{i}")
            if joint_data is not None:
                observation[f"joint_pos_{i}"] = joint_data
        
        # 获取位置数据
        for pos in ["position_x", "position_y", "position_z"]:
            pos_data = data_provider.get_data(pos)
            if pos_data is not None:
                observation[pos] = pos_data
        
        # 获取触觉数据
        tactile_data = data_provider.get_data("tactile")
        if tactile_data is not None:
            observation["tactile"] = tactile_data
        
        return observation
    
    def send_action(self, action):
        """这个方法只记录动作，不实际执行"""
        # 可以选择性地将动作发送回您的系统
        # 例如通过某个回调函数
        action_callback = data_provider.get_data("action_callback")
        if action_callback and callable(action_callback):
            action_callback(action)
        
        return action  # 返回原始动作


@dataclass
class AdapterTeleoperatorConfig(TeleoperatorConfig):
    """适配器远程操作配置"""
    # 添加任何需要的配置参数
    pass

class AdapterTeleoperator(Teleoperator):
    """适配外部远程操作数据的适配器类"""
    
    def __init__(self, config: AdapterTeleoperatorConfig):
        super().__init__(config)
        self.config = config
    
    def connect(self):
        """不需要实际连接，只是保持API一致"""
        pass
    
    def disconnect(self):
        """不需要实际断开连接，只是保持API一致"""
        pass
    
    def get_action(self):
        """从外部数据提供者获取动作数据"""
        action = {}
        
        # 获取上肢动作
        for i in range(26):
            arm_data = data_provider.get_data(f"teleop_arm_{i}")
            if arm_data is not None:
                action[f"arm_{i}"] = arm_data
            else:
                action[f"arm_{i}"] = 0.0  # 默认值
        
        # 获取本体运动
        for dir_name in ["body_x", "body_y", "body_z"]:
            body_data = data_provider.get_data(f"teleop_{dir_name}")
            if body_data is not None:
                action[dir_name] = body_data
            else:
                action[dir_name] = 0.0  # 默认值
        
        return action

from lerobot.common.robots import register_robot_type
from lerobot.common.teleoperators import register_teleoperator_type

# 注册适配器类型
register_robot_type("adapter_robot", AdapterRobot, AdapterRobotConfig)
register_teleoperator_type("adapter_teleop", AdapterTeleoperator, AdapterTeleoperatorConfig)

# 您已有的遥操作系统
class YourTeleopSystem:
    def get_joint_values(self):
        # 您自己的获取关节值逻辑
        return [0.1] * 26
    
    def get_body_movement(self):
        # 您自己的获取本体运动逻辑
        return [0.05, 0.0, 0.02]

# 您已有的CAN触觉系统
class YourCANTactileSystem:
    def read_tactile_data(self):
        # 您自己的CAN读取逻辑
        return np.zeros((1100, 1))

# 初始化您的系统
your_teleop = YourTeleopSystem()
your_tactile = YourCANTactileSystem()

# 注册数据回调
# for i in range(26):
#     # 注册闭包函数来获取特定关节值
#     joint_idx = i  # 创建闭包
#     data_provider.register_data_callback(
#         f"teleop_arm_{i}", 
#         lambda: your_teleop.get_joint_values()[joint_idx]
#     )
# 注册数据回调
for i in range(26):
    # 创建一个函数工厂来避免闭包问题
    def create_callback(idx):
        return lambda: your_teleop.get_joint_values()[idx]
    
    data_provider.register_data_callback(
        f"teleop_arm_{i}", 
        create_callback(i)
    )
# 注册本体运动回调
data_provider.register_data_callback(
    "teleop_body_x", 
    lambda: your_teleop.get_body_movement()[0]
)
data_provider.register_data_callback(
    "teleop_body_y", 
    lambda: your_teleop.get_body_movement()[1]
)
data_provider.register_data_callback(
    "teleop_body_z", 
    lambda: your_teleop.get_body_movement()[2]
)

# 注册触觉数据回调
data_provider.register_data_callback(
    "tactile", 
    lambda: your_tactile.read_tactile_data()
)

# 创建配置
from lerobot.record import record, DatasetRecordConfig, RecordConfig

robot_config = AdapterRobotConfig(
    type="adapter_robot",
    external_data_configs={"has_tactile": True}
)

teleop_config = AdapterTeleoperatorConfig(
    type="adapter_teleop"
)

dataset_config = DatasetRecordConfig(
    repo_id="your_username/robot_dataset",
    single_task="Pick and place task",
    fps=30
)

record_config = RecordConfig(
    robot=robot_config,
    dataset=dataset_config,
    teleop=teleop_config,
    display_data=True
)

# 执行记录
dataset = record(record_config)

