import conf.global_configs as global_configs
from types import MethodType
import os
import torch
import numpy as np
import random

class Settings:
    def __init__(self, settings):

        for attr in dir(settings):
            if not attr.startswith('__'):
                setattr(self,attr,getattr(settings,attr))

    def parse_to_dict(self, args):
        args_dict = {}
        for arg in dir(args):
            if not arg.startswith('_') and not isinstance(getattr(args, arg), MethodType):
                if getattr(args, arg) is not None:
                    args_dict[arg] = getattr(args, arg)
        return args_dict

    def add_args(self, args_dict):
        for arg in args_dict:
            setattr(self, arg, args_dict[arg])

    def training_init(self):
        os.environ['CUDA_VISIBLE_DEVICES'] = self.gpu
        self.n_gpu = len(self.gpu.split(','))
        self.devices = [ _ for _ in range(self.n_gpu) ]
        torch.set_num_threads(2)

        # fix seed
        torch.manual_seed(self.seed)
        if self.n_gpu < 2:
            torch.cuda.manual_seed(self.seed)
        else:
            torch.cuda.manual_seed_all(self.seed)
        torch.backends.cudnn.deterministic = True
        np.random.seed(self.seed)
        random.seed(self.seed)

        # Gradient accumulate setup
        assert self.batch_size % self.gradient_accumulation_steps == 0
        self.sub_batch_size = int(self.batch_size / self.gradient_accumulation_steps)
        self.eval_batch_size = int(self.sub_batch_size / 2)

    def path_init(self):
        # --- 新增的、更智能的逻辑：根据 run_mode 设置 data_dir ---
        if self.run_mode == 'general':
            # 对于 general 模式，优先从 data_path 中查找当前数据集的训练路径
            # 然后自动生成测试路径（作为备用，实际会从 custom_mapping.json 读取）
            if hasattr(self, 'dataset') and self.dataset:
                base_train_path = self.data_path.get(self.dataset)
                if base_train_path:
                    # 根据依赖关系，进行字符串替换，动态生成测试集路径
                    self.data_dir = base_train_path.replace(
                        '0.大类训练集', 
                        '1.大类测试集'
                    )
                    print(f"Info: Automatically derived generalization test path: {self.data_dir}")
                else:
                    # 如果在 data_path 中找不到，设置为 None
                    # evaluate_generalization_accuracy 会从 custom_mapping.json 读取 test_path
                    self.data_dir = None
            else:
                self.data_dir = None

        else:
            # 对于其他模式（如 train, test），保留原有逻辑
            self.data_dir = self.data_path.get(self.dataset)

        # 检查 data_dir 是否被成功设置
        if not hasattr(self, 'data_dir') or self.data_dir is None:
            if self.run_mode == 'general':
                # 对于 general 模式，data_dir 为 None 是正常的，因为会从 custom_mapping.json 读取 test_path
                print(f"Info: data_dir not set in path_init for 'general' mode. Will use test_path from custom_mapping.json.")
            else:
                print(f"Warning: data_dir could not be set for dataset '{self.dataset}' and run_mode '{self.run_mode}'")


        # --- 保留并优化了您原有的目录创建逻辑 ---
        for attr in dir(self):
            if 'dir' in attr and not attr.startswith('__'):
                attr_value = getattr(self, attr)
                if isinstance(attr_value, str) and not os.path.exists(attr_value):
                    os.makedirs(attr_value, exist_ok=True)

    def __str__(self):
        # print Hyper Parameters
        settings_str = ''
        for attr in dir(self):
            # 如果不加 attr.startwith('__')会打印出很多额外的参数，是自身自带的一些默认方法和属性
            if not 'np' in attr and not 'random' in attr and not attr.startswith('__') and not isinstance(getattr(self, attr), MethodType):
                settings_str += '{ %-17s }->' % attr + str(getattr(self, attr)) + '\n'
        return settings_str

configs = Settings(global_configs)




