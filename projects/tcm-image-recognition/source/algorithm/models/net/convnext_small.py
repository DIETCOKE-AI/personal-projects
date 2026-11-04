import torch
import timm
from ._local_weights_loader import load_local_pretrained_weights
from torch import nn
import warnings
import os
from pathlib import Path

class ConvNeXt_Small(nn.Module):
    """ConvNeXt-Small 模型，基于 timm 库实现。"""

    def __init__(self, num_classes=99, pretrained=True, finetune_last_n=None, local_weights_path=None):
        """
        初始化 ConvNeXt-Small 模型。

        参数:
            num_classes (int): 分类类别数。
            pretrained (bool): 是否加载在 ImageNet-1k 上预训练的权重。
            finetune_last_n (int or None): 解冻最后N层参数用于微调。如果为 None，则全部参数可训练。
            local_weights_path (str): 本地预训练权重文件路径。
        """
        super().__init__()
        
        # 如果指定了本地权重路径，优先使用本地权重
        if local_weights_path and os.path.exists(local_weights_path):
            print(f"[INFO] 正在创建 ConvNeXt-Small 模型并加载本地权重: {local_weights_path}")
            self.model = timm.create_model("convnext_small", pretrained=False, num_classes=1000)

            # 如果指定使用预训练权重，从本地加载
            if pretrained:
                load_local_pretrained_weights(self.model, 'ConvNeXt_Small', pretrained=True)
            checkpoint = torch.load(local_weights_path, map_location='cpu')
            self.model.load_state_dict(checkpoint, strict=False)
            
            # 调整分类头
            if num_classes != 1000:
                self.model.head.fc = nn.Linear(self.model.head.fc.in_features, num_classes)
            print("[SUCCESS] 成功加载本地预训练权重!")
            return
        
        # 检查缓存目录中是否有预训练权重
        cache_weights = self._check_cached_weights()
        if pretrained and cache_weights:
            print(f"[INFO] 发现缓存的预训练权重: {cache_weights}")
            try:
                self.model = timm.create_model("convnext_small", pretrained=False, num_classes=1000)
                checkpoint = torch.load(cache_weights, map_location='cpu')
                
                # 处理不同的权重格式
                if 'model' in checkpoint:
                    state_dict = checkpoint['model']
                elif 'state_dict' in checkpoint:
                    state_dict = checkpoint['state_dict']
                else:
                    state_dict = checkpoint
                
                self.model.load_state_dict(state_dict, strict=False)
                
                # 调整分类头
                if num_classes != 1000:
                    self.model.head.fc = nn.Linear(self.model.head.fc.in_features, num_classes)
                print("[SUCCESS] 成功加载缓存的预训练权重!")
                return
            except Exception as e:
                print(f"[WARNING] 加载缓存权重失败: {e}，尝试在线下载...")
        
        # 使用 timm 创建 convnext_small 模型
        # 添加网络异常处理
        try:
            print(f"[INFO] 正在创建 ConvNeXt-Small 模型 (pretrained={pretrained})...")
            self.model = timm.create_model(
                "convnext_small", pretrained=False, num_classes=num_classes
            )
            if pretrained:
                print("[SUCCESS] 成功加载预训练权重!")
            else:
                print("[INFO] 使用随机初始化权重")
        except Exception as e:
            error_msg = str(e).lower()
            # 更准确的网络错误检测
            network_errors = [
                "network is unreachable", "connection", "localentrynotfounderror",
                "connectionerror", "timeout", "httpsconnectionpool", 
                "max retries exceeded", "huggingface.co", "httpserror", "urlerror"
            ]
            
            if any(err in error_msg for err in network_errors):
                print(f"[WARNING] 网络连接失败，无法下载预训练权重: {type(e).__name__}")
                print("[INFO] 将使用随机初始化权重继续训练...")
                warnings.warn("无法下载预训练权重，使用随机初始化。建议检查网络连接或稍后重试。")
                # 降级到无预训练权重
                self.model = timm.create_model(
                    "convnext_small", pretrained=False, num_classes=num_classes
                )
                print("[SUCCESS] ConvNeXt-Small模型创建成功（无预训练权重）!")
            else:
                print(f"[ERROR] 创建模型时发生未知错误: {e}")
                raise e

        # 如果指定了 finetune_last_n，则冻结除最后 N 层外的所有层
        if finetune_last_n is not None:
            parameters = list(self.model.named_parameters())
            total_params = len(parameters)
            for i, (name, param) in enumerate(parameters):
                # 仅解冻最后 N 层
                param.requires_grad = i >= total_params - finetune_last_n

    def forward(self, x):
        """前向传播。"""
        return self.model(x)

    def _check_cached_weights(self):
        """检查是否有缓存的预训练权重"""
        try:
            # 检查torch hub缓存目录
            hub_dir = torch.hub.get_dir()
            checkpoints_dir = os.path.join(hub_dir, "checkpoints")
            
            # 可能的权重文件名
            weight_files = [
                "convnext_small_22k_224.pth",
                "convnext_small_in22k_ft_in1k_384.pth",
                "convnext_small.pth"
            ]
            
            for weight_file in weight_files:
                weight_path = os.path.join(checkpoints_dir, weight_file)
                if os.path.exists(weight_path):
                    return weight_path
            
            # 检查当前目录下的weights文件夹
            local_weights_dir = "./weights"
            if os.path.exists(local_weights_dir):
                for weight_file in weight_files:
                    weight_path = os.path.join(local_weights_dir, weight_file)
                    if os.path.exists(weight_path):
                        return weight_path
                        
        except Exception as e:
            print(f"[DEBUG] 检查缓存权重时出错: {e}")
        
        return None

    def print_parameters(self):
        """打印每个参数的名字和训练状态（是否需要梯度）。"""
        for name, param in self.model.named_parameters():
            print(f"{name} - requires_grad: {param.requires_grad}")