import torch
import timm
from torch import nn

class MaxViT_Small(nn.Module):
    """
    MaxViT Small 模型，基于 timm 库实现。
    
    MaxViT 是一种混合视觉架构，结合了：
    - CNN 的局部特征提取能力
    - Transformer 的全局建模能力
    - 多尺度窗口注意力机制
    
    特别适合细粒度分类任务（如中药图像识别）。
    
    ⚠️ 分辨率限制：
    - MaxViT 使用窗口注意力机制，输入尺寸必须是特定值的倍数
    - 原生支持: 224x224, 384x384, 512x512
    - 如果使用其他尺寸（如640x640），建议使用 MaxViT_Small_Flex 变体
    """

    def __init__(self, num_classes=99, pretrained=True, finetune_last_n=None, img_size=384):
        """
        初始化 MaxViT Small 模型。

        参数:
            num_classes (int): 分类类别数。
            pretrained (bool): 是否加载在 ImageNet-1k 上预训练的权重（384分辨率）。
            finetune_last_n (int or None): 解冻最后N层参数用于微调。如果为 None，则全部参数可训练。
            img_size (int): 输入图像尺寸。推荐使用 224/384/512。默认 384。
        """
        super().__init__()
        
        self.img_size = img_size
        
        # 根据输入尺寸选择合适的 MaxViT 变体
        # 对于非标准尺寸（如640），使用512版本并让模型自适应
        if img_size <= 224:
            model_name = "maxvit_small_tf_224.in1k"  # 224分辨率优化
        elif img_size <= 384:
            model_name = "maxvit_small_tf_384.in1k"  # 384分辨率优化（推荐）
        else:
            # 对于更大的输入（如640），使用512版本
            model_name = "maxvit_small_tf_512.in21k_ft_in1k"  # 512分辨率，ImageNet-21k预训练
        
        # 使用 timm 创建 maxvit 模型
        # 注意：创建时指定 img_size 参数以适配窗口大小
        try:
            self.model = timm.create_model(
                model_name, 
                pretrained=pretrained, 
                num_classes=num_classes,
                img_size=img_size  # 传入目标图像尺寸
            )
            self.model_variant = model_name
        except Exception as e:
            # 如果指定的变体不可用，回退到384版本
            print(f"警告: {model_name} 不可用，回退到 maxvit_small_tf_384.in1k")
            print(f"错误详情: {e}")
            self.model = timm.create_model(
                "maxvit_small_tf_384.in1k", 
                pretrained=pretrained, 
                num_classes=num_classes
            )
            self.model_variant = "maxvit_small_tf_384.in1k"
            self.img_size = 384  # 重置为384

        # 如果指定了 finetune_last_n，则冻结除最后 N 层外的所有层
        if finetune_last_n is not None:
            parameters = list(self.model.named_parameters())
            total_params = len(parameters)
            for i, (name, param) in enumerate(parameters):
                # 仅解冻最后 N 层
                param.requires_grad = i >= total_params - finetune_last_n

    def forward(self, x):
        """
        前向传播。
        
        参数:
            x (torch.Tensor): 输入图像张量，形状为 [batch_size, 3, H, W]
                             推荐分辨率：384x384 或更高（如640x640）
        
        返回:
            torch.Tensor: 分类 logits，形状为 [batch_size, num_classes]
        """
        return self.model(x)

    def print_parameters(self):
        """打印每个参数的名字和训练状态（是否需要梯度）。"""
        for name, param in self.model.named_parameters():
            print(f"{name} - requires_grad: {param.requires_grad}")

    def get_model_info(self):
        """获取模型的详细信息。"""
        total_params = sum(p.numel() for p in self.model.parameters())
        trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        
        return {
            "architecture": "MaxViT Small",
            "base_model": "maxvit_small_tf_384.in1k",
            "total_parameters": f"{total_params / 1e6:.2f}M",
            "trainable_parameters": f"{trainable_params / 1e6:.2f}M",
            "input_size": "384x384+ (supports higher resolution)",
            "features": "Multi-axis Self-Attention (CNN + Transformer Hybrid)"
        }


# 示例用法
if __name__ == "__main__":
    print("="*60)
    print("MaxViT Small 模型测试")
    print("="*60)
    
    # 创建模型实例，分类数为 200，加载预训练权重，并只解冻最后 20 层用于微调
    model = MaxViT_Small(num_classes=200, pretrained=True, finetune_last_n=20)
    
    # 获取模型信息
    info = model.get_model_info()
    print("\n模型信息:")
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # MaxViT Small 原生支持 384x384，但也可以处理更高分辨率如 640x640
    print("\n测试不同分辨率输入:")
    
    # 测试 384x384 (原生分辨率)
    dummy_input_384 = torch.randn(2, 3, 384, 384)
    output_384 = model(dummy_input_384)
    print(f"  384x384 输入形状: {dummy_input_384.shape} -> 输出形状: {output_384.shape}")
    
    # 测试 640x640 (项目使用的分辨率)
    dummy_input_640 = torch.randn(2, 3, 640, 640)
    output_640 = model(dummy_input_640)
    print(f"  640x640 输入形状: {dummy_input_640.shape} -> 输出形状: {output_640.shape}")
    
    print("\n" + "="*60)
    print("验证微调设置（打印最后10个参数的训练状态）:")
    print("="*60)
    all_params = list(model.model.named_parameters())
    for name, param in all_params[-10:]:
        print(f"  {name} - requires_grad: {param.requires_grad}")
    
    print("\n✅ MaxViT Small 模型创建成功！")
