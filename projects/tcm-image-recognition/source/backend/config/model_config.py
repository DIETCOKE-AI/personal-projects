# config/model_config.py

import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# 0. 路径动态计算 (核心修复)
# ==============================================================================
def get_base_path():
    """
    获取应用的根目录路径。
    - 在开发环境中 (运行 .py)，它返回项目根目录。
    - 在生产环境中 (运行 .exe)，它返回 PyInstaller 创建的包含所有数据文件的临时目录 (_MEIPASS)。
    """
    if hasattr(sys, '_MEIPASS'):
        # 如果应用被打包 (frozen)
        return sys._MEIPASS
    else:
        # 如果是作为普通脚本运行
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# 获取根目录
BASE_PATH = get_base_path()

# ==============================================================================
# 1. 模型注册表 (保持不变)
# ==============================================================================
# 确保所有用到的模型类都已在此注册
from nets.mobilevit import MobileViT
from nets.efficientnet import EfficientNetB7
from nets.mobilevit_large import MobileViT_large
from nets.mobilevit_large_pafpn import MobileViT_large_PAFPN
from nets.mnv4_conv import MNv4_Conv_AA_Large
from nets.efficientnetv2_m import EfficientNetV2_M

MODEL_REGISTRY = {
    "MobileViT": MobileViT,
    "EfficientNetB7": EfficientNetB7,
    "MobileViT_large": MobileViT_large,
    "MobileViT_large_PAFPN": MobileViT_large_PAFPN,
    "MNv4_Conv_AA_Large": MNv4_Conv_AA_Large,
    "EfficientNetV2_M": EfficientNetV2_M,
}

# ==============================================================================
# 2. 🚀 开集分类与集成模型配置 (核心修改)
# ==============================================================================

  
# ==============================================================================
#  ⚙️ 推理与服务器配置 (Inference and Server Configuration)
# ==============================================================================

# 经过在RTX 3060上针对5个集成模型的反复测试，
# 8 是在吞吐量、速度和稳定性上表现最佳的批处理大小。
INFERENCE_BATCH_SIZE = 8

# 🚀 1. 更新为测试得出的最优置信度阈值
OPEN_SET_CONFIDENCE_THRESHOLD = 0.51

# 🚀 2. 新增投票阈值，4票及以上才接受
#VOTE_THRESHOLD = 4

# 🚀 3. 更新为5个模型，并为每个模型指定 transform_type
#    请确保 ckpt_path 指向正确的模型权重文件。
MAIN_ENSEMBLE_CONFIG = [
    {
        "model_name": "MobileViT_large",
        "ckpt_path": "checkpoints/大类模型/MobileViT_large-268-regular.pth", # 来自 v9701516
        "transform_type": "force_resize"
    },
    {
        "model_name": "MobileViT_large_PAFPN",
        "ckpt_path": "checkpoints/大类模型/MobileViT_large_PAFPN-89-regular.pth", # 来自 v2529771
        "transform_type": "center_crop"
    },
    {
        "model_name": "MNv4_Conv_AA_Large",
        "ckpt_path": "checkpoints/大类模型/MNv4_Conv_AA_Large-89-regular.pth", # 来自 v5594918
        "transform_type": "center_crop"
    },
    {
        "model_name": "EfficientNetV2_M",
        "ckpt_path": "checkpoints/大类模型/EfficientNetV2_M-44-regular.pth", # 来自 v1781028
        "transform_type": "center_crop"
    },
    {
        "model_name": "MobileViT_large",
        "ckpt_path": "checkpoints/大类模型/MobileViT_large-42-regular.pth", # 来自 v5400839
        "transform_type": "center_crop"
    }
]

# 🚀 4. 更新已知大类的数量
NUM_KNOWN_CLASSES = 99


# ==============================================================================
# 3. 现有配置 (保持不变)
# ==============================================================================
NORMALIZATION_MEAN = [0.5070751592371323, 0.48654887331495095, 0.4409178433670343]
NORMALIZATION_STD = [0.2673342858792401, 0.2564384629170883, 0.27615047132568404]

SEGMENTATION_CLASSES = {'陈皮类'}
HIGH_RESOLUTION_CLASSES = {'拳参类', '栀子类'}
PAFPN_CLASSES = {'菝葜类','枣仁类'}
RESIZE_CROP_CLASSES = {'麦冬类','山麦冬类','沙苑子类'}



MODEL_TYPE_CONFIG = {
    "麦冬类": "MNv4_Conv_AA_Large",
    "山麦冬类": "MNv4_Conv_AA_Large",
    "栀子类": "MobileViT_large",
    "拳参类": "MobileViT_large",
    "沙苑子类": "MNv4_Conv_AA_Large",
    "枣仁类": "MobileViT_large_PAFPN",
    "菝葜类": "MobileViT_large_PAFPN",
    "default": "EfficientNetB7"
}

# 图像尺寸配置保持不变，因为测试脚本中也主要使用了 640x640
IMAGE_SIZE_CONFIG = {
    "default": (640, 640),
    "high_resolution": (1280, 1280),
    #"shayuanzi": 640,
    "pafpn": (640, 640)
}

MODEL_PATH_CONFIG = {
    "麦冬类": "checkpoints/测试权重/麦冬类/MNv4_Conv_AA_Large-34-regular.pth",
    "栀子类": "checkpoints/栀子类.pth",  
    "枣仁类": "checkpoints/测试权重/枣仁类/MobileViT_large_PAFPN-23-model-only.pth",  
    "半夏类": "checkpoints/半夏类.pth",  
    "陈皮类": "checkpoints/测试权重/陈皮类/EfficientNetB7-15-regular.pth",
    "拳参类": "checkpoints/拳参类.pth",   
    "沙苑子类": "checkpoints/测试权重/沙苑子类/MNv4_Conv_AA_Large-32-regular.pth",
    "菝葜类": "checkpoints/测试权重/菝葜类/MobileViT_large_PAFPN-2-regular.pth",
    "山麦冬类": "checkpoints/测试权重/山麦冬类/MNv4_Conv_AA_Large-best.pth",
}

DB_CONFIG = {
    'host': os.environ.get('TCM_DB_HOST', '127.0.0.1'),
    'port': int(os.environ.get('TCM_DB_PORT', '3306')),
    'user': os.environ['TCM_DB_USER'],
    'password': os.environ['TCM_DB_PASSWORD'],
    'database': os.environ['TCM_DB_NAME'],
    'charset': 'utf8',
    'pool_name': 'mypool',
    'pool_size': 5
}
