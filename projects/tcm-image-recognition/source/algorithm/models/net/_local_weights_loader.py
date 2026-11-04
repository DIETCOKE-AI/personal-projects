"""
本地预训练权重加载辅助模块
用于统一管理所有模型的本地权重加载逻辑
"""

import torch
import os
from pathlib import Path

# 权重存储基础目录
WEIGHTS_BASE_DIR = Path(os.environ.get('TCM_PRETRAINED_ROOT', './weights/pretrained'))

# 定义每个模型的权重路径映射
MODEL_WEIGHT_PATHS = {
    'FastViT_SA24': 'fastvit_sa24.apple_in1k/pytorch_model.bin',
    'EfficientNetV2_S': 'tf_efficientnetv2_s.in21k_ft_in1k/pytorch_model.bin',
    'EfficientNetV2_M': 'tf_efficientnetv2_m.in21k_ft_in1k/pytorch_model.bin',
    'EfficientNetV2_L': 'tf_efficientnetv2_l.in21k_ft_in1k/pytorch_model.bin',
    'ConvNeXt_Large': 'convnext_large_mlp.clip_laion2b_soup_ft_in12k_in1k_384/pytorch_model.bin',
    'ConvNeXt_Small': 'convnext_small.fb_in22k_ft_in1k/pytorch_model.bin',
    'ConvNeXt_V2_Tiny': 'convnextv2_tiny.fcmae_ft_in22k_in1k/pytorch_model.bin',
    'MaxViT_Small': 'maxvit_small_tf_384.in1k/pytorch_model.bin',
    'MobileViT_large': 'mobilevitv2_200.cvnets_in22k_ft_in1k/pytorch_model.bin',
    'MobileViT_large_PAFPN': 'mobilevitv2_175.cvnets_in22k_ft_in1k/pytorch_model.bin',  # 使用mobilevitv2_175
    'Swin_V3_Base': 'swinv2_base_window12to16_192to256.ms_in22k_ft_in1k/pytorch_model.bin',
    'Swin_V3_Tiny': 'swinv2_tiny_window8_256.ms_in1k/pytorch_model.bin',
    'Swin_Base': 'swin_base_patch4_window7_224.ms_in22k_ft_in1k/pytorch_model.bin',
    'Swin_Tiny': 'swin_tiny_patch4_window7_224.ms_in22k_ft_in1k/pytorch_model.bin',
    'EfficientNetB7': 'tf_efficientnet_b7.ns_jft_in1k/pytorch_model.bin',
}


def load_local_pretrained_weights(model, model_name, pretrained=True, verbose=None):
    """
    为模型加载本地预训练权重
    
    参数:
        model: PyTorch模型实例
        model_name: 模型名称（用于查找权重路径）
        pretrained: 是否加载预训练权重
        verbose: 是否显示加载信息。如果为None，则自动检测运行模式（训练时显示，测试时不显示）
    
    返回:
        bool: 是否成功加载权重
    """
    # 自动检测运行模式：如果是测试模式，默认不显示信息
    if verbose is None:
        try:
            # 尝试从全局配置中获取运行模式
            import sys
            if 'conf' in sys.modules:
                from conf import configs
                if hasattr(configs, 'run_mode'):
                    # 测试模式不显示，训练模式显示
                    verbose = (configs.run_mode == 'train')
                else:
                    verbose = True  # 默认显示
            else:
                verbose = True  # 默认显示
        except:
            verbose = True  # 默认显示
    
    if not pretrained:
        return False
    
    # 获取权重路径
    if model_name not in MODEL_WEIGHT_PATHS:
        print(f"[{model_name}] 警告: 未找到本地权重路径配置，将使用随机初始化")
        return False
    
    weight_path = WEIGHTS_BASE_DIR / MODEL_WEIGHT_PATHS[model_name]
    
    if not weight_path.exists():
        print(f"[{model_name}] 警告: 本地权重文件不存在: {weight_path}")
        print(f"  提示: 请运行 download_pretrained_weights.py 下载权重")
        return False
    
    try:
        # 加载权重
        state_dict = torch.load(str(weight_path), map_location='cpu', weights_only=True)
        
        # 移除分类头（如果存在）
        keys_to_remove = []
        for key in state_dict.keys():
            if key.startswith('head.') or key.startswith('classifier.'):
                keys_to_remove.append(key)
            elif key in ['head.weight', 'head.bias', 'classifier.weight', 'classifier.bias']:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            if key in state_dict:
                del state_dict[key]
        
        # 加载权重到模型
        incompatible_keys = model.load_state_dict(state_dict, strict=False)
        
        # 根据verbose参数决定是否显示加载信息
        # 训练时显示，测试时不显示
        if verbose:
            missing = incompatible_keys.missing_keys
            unexpected = incompatible_keys.unexpected_keys
            
            if missing or unexpected:
                print(f"[{model_name}] 成功加载本地预训练权重: {weight_path}")
                if missing:
                    print(f"  缺失键: {len(missing)} 个（通常是分类头，已忽略）")
                if unexpected:
                    print(f"  意外键: {len(unexpected)} 个")
            else:
                print(f"[{model_name}] 成功加载本地预训练权重: {weight_path}")
        
        return True
        
    except Exception as e:
        print(f"[{model_name}] 错误: 加载本地权重失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_weight_path(model_name):
    """获取模型权重路径"""
    if model_name not in MODEL_WEIGHT_PATHS:
        return None
    return WEIGHTS_BASE_DIR / MODEL_WEIGHT_PATHS[model_name]

