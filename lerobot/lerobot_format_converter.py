#!/usr/bin/env python3
"""
LeRobot格式转换器
将简单数据收集器的数据转换为LeRobot标准格式
"""

import h5py
import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, List
import torch
from datasets import Dataset, Features, Value, Array3D, Array2D, Sequence
from huggingface_hub import HfApi
import tempfile
import shutil

class LeRobotFormatConverter:
    """LeRobot格式转换器"""
    
    def __init__(self):
        self.episode_data = []
        self.features = {}
    
    def convert_h5_to_lerobot(self, h5_file_path: str, output_dir: str, 
                             repo_id: str = None, task_name: str = "robot_task"):
        """将H5文件转换为LeRobot格式
        
        Args:
            h5_file_path: 输入的H5文件路径
            output_dir: 输出目录
            repo_id: HuggingFace仓库ID（可选）
            task_name: 任务名称
        """
        
        print(f"🔄 开始转换: {h5_file_path}")
        
        # 读取H5数据
        data_dict = self._load_h5_data(h5_file_path)
        
        # 转换为LeRobot格式
        lerobot_data = self._convert_to_lerobot_format(data_dict, task_name)
        
        # 保存数据集
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 创建HuggingFace数据集
        dataset = Dataset.from_list(lerobot_data, features=self.features)
        
        # 保存到本地
        dataset.save_to_disk(str(output_path))
        
        # 保存元数据
        self._save_metadata(output_path, h5_file_path, task_name)
        
        print(f"✅ 转换完成: {output_path}")
        print(f"📊 数据集信息:")
        print(f"   - 总帧数: {len(lerobot_data)}")
        print(f"   - 特征数: {len(self.features)}")
        
        # 可选：上传到HuggingFace Hub
        if repo_id:
            self._upload_to_hub(dataset, repo_id)
        
        return dataset
    
    def _load_h5_data(self, h5_file_path: str) -> Dict[str, Any]:
        """加载H5数据"""
        data_dict = {}
        
        with h5py.File(h5_file_path, 'r') as f:
            for source_name in f.keys():
                group = f[source_name]
                data_dict[source_name] = {
                    'data': np.array(group['data']),
                    'timestamps': np.array(group['timestamps'])
                }
        
        return data_dict
    
    def _convert_to_lerobot_format(self, data_dict: Dict, task_name: str) -> List[Dict]:
        """转换为LeRobot格式"""
        
        # 找到最短的时间序列长度
        min_length = min(len(data['data']) for data in data_dict.values())
        
        print(f"📏 对齐数据长度: {min_length} 帧")
        
        lerobot_data = []
        
        for frame_idx in range(min_length):
            frame_data = {
                'frame_index': frame_idx,
                'episode_index': 0,  # 单个episode
                'task': task_name,
                'timestamp': 0.0  # 将在下面设置
            }
            
            # 处理每个数据源
            for source_name, source_data in data_dict.items():
                data_array = source_data['data'][frame_idx]
                timestamp = source_data['timestamps'][frame_idx]
                
                # 设置时间戳（使用第一个数据源的时间戳）
                if frame_idx == 0 or 'timestamp' not in frame_data:
                    frame_data['timestamp'] = float(timestamp)
                
                # 根据数据类型处理
                if 'camera' in source_name and 'rgb' in source_name:
                    # 图像数据
                    frame_data[f'observation.images.{source_name}'] = data_array
                    self._update_features(f'observation.images.{source_name}', data_array)
                
                elif 'joint' in source_name or 'position' in source_name:
                    # 关节/位置数据
                    if isinstance(data_array, (list, np.ndarray)):
                        frame_data[f'observation.state.{source_name}'] = np.array(data_array, dtype=np.float32)
                        self._update_features(f'observation.state.{source_name}', data_array)
                    else:
                        frame_data[f'observation.state.{source_name}'] = float(data_array)
                        self._update_features(f'observation.state.{source_name}', data_array)
                
                elif 'tactile' in source_name:
                    # 触觉数据
                    frame_data[f'observation.state.{source_name}'] = np.array(data_array, dtype=np.float32)
                    self._update_features(f'observation.state.{source_name}', data_array)
                
                elif 'teleop' in source_name or 'action' in source_name:
                    # 动作数据
                    if isinstance(data_array, dict):
                        for key, value in data_array.items():
                            frame_data[f'action.{key}'] = np.array(value, dtype=np.float32) if isinstance(value, (list, np.ndarray)) else float(value)
                            self._update_features(f'action.{key}', value)
                    else:
                        frame_data[f'action.{source_name}'] = np.array(data_array, dtype=np.float32) if isinstance(data_array, (list, np.ndarray)) else float(data_array)
                        self._update_features(f'action.{source_name}', data_array)
                
                else:
                    # 其他数据
                    frame_data[f'observation.state.{source_name}'] = data_array
                    self._update_features(f'observation.state.{source_name}', data_array)
            
            lerobot_data.append(frame_data)
        
        return lerobot_data
    
    def _update_features(self, key: str, data):
        """更新特征定义"""
        if key in self.features:
            return
        
        if isinstance(data, np.ndarray):
            if len(data.shape) == 3:  # 图像
                self.features[key] = Array3D(dtype="uint8", shape=data.shape)
            elif len(data.shape) == 2:  # 2D数组
                self.features[key] = Array2D(dtype="float32", shape=data.shape)
            elif len(data.shape) == 1:  # 1D数组
                self.features[key] = Sequence(Value("float32"), length=len(data))
            else:
                self.features[key] = Value("float32")
        elif isinstance(data, (list, tuple)):
            self.features[key] = Sequence(Value("float32"), length=len(data))
        elif isinstance(data, (int, float)):
            self.features[key] = Value("float32")
        elif isinstance(data, str):
            self.features[key] = Value("string")
        else:
            self.features[key] = Value("string")  # 默认
    
    def _save_metadata(self, output_path: Path, h5_file_path: str, task_name: str):
        """保存元数据"""
        metadata = {
            "dataset_info": {
                "task": task_name,
                "source_file": str(h5_file_path),
                "conversion_time": str(np.datetime64('now')),
                "format": "lerobot_v1.0"
            },
            "features": {key: str(value) for key, value in self.features.items()}
        }
        
        with open(output_path / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _upload_to_hub(self, dataset: Dataset, repo_id: str):
        """上传到HuggingFace Hub"""
        try:
            print(f"🚀 上传到HuggingFace Hub: {repo_id}")
            dataset.push_to_hub(repo_id)
            print("✅ 上传完成")
        except Exception as e:
            print(f"❌ 上传失败: {e}")

def convert_simple_data_to_lerobot(h5_file: str, output_dir: str = "./lerobot_dataset", 
                                  repo_id: str = None, task_name: str = "robot_manipulation"):
    """便捷函数：转换简单数据收集器的数据为LeRobot格式"""
    
    converter = LeRobotFormatConverter()
    return converter.convert_h5_to_lerobot(h5_file, output_dir, repo_id, task_name)

# 使用示例
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python lerobot_format_converter.py <h5_file_path> [output_dir] [repo_id]")
        sys.exit(1)
    
    h5_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./lerobot_dataset"
    repo_id = sys.argv[3] if len(sys.argv) > 3 else None
    
    # 转换数据
    dataset = convert_simple_data_to_lerobot(
        h5_file=h5_file,
        output_dir=output_dir,
        repo_id=repo_id,
        task_name="humanoid_manipulation"
    )
    
    print("🎉 转换完成！")
    print(f"📁 输出目录: {output_dir}")
    if repo_id:
        print(f"🌐 HuggingFace仓库: https://huggingface.co/datasets/{repo_id}")
