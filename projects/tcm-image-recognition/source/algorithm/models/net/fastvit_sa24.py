import torch
import timm
from torch import nn
from ._local_weights_loader import load_local_pretrained_weights

class FastViT_SA24(nn.Module):
    """
    FastViT-SA24 模型，基于 timm 库实现。
    
    FastViT 是一个高效的视觉Transformer架构，结合了结构重参数化和自注意力机制。
    SA24 是中等规模版本，在速度和精度之间取得良好平衡。
    
    主要特点：
    - 使用 RepMixer 模块实现高效的特征混合
    - 结构重参数化技术，推理时可转换为纯卷积，速度更快
    - 支持多种分辨率输入（默认224x224，也支持384x384等）
    """

    def __init__(self, num_classes=99, pretrained=True, finetune_last_n=None, img_size=224):
        """
        初始化 FastViT-SA24 模型。

        参数:
            num_classes (int): 分类类别数。默认99。
            pretrained (bool): 是否加载 ImageNet-1k 预训练权重。默认True。
            finetune_last_n (int or None): 解冻最后N层参数（包括分类头）。
                                           如果为 None，则全部参数可训练。
            img_size (int): 输入图像尺寸。FastViT默认使用256x256，此参数仅用于接口兼容。
        """
        super().__init__()
        
        # 使用 timm 创建 fastvit_sa24 模型（不加载在线权重）
        # SA24 表示 Self-Attention 24层架构
        # 注意：FastViT不接受img_size参数，默认使用256x256
        self.model = timm.create_model(
            "fastvit_sa24", 
            pretrained=False,  # 先不加载在线权重
            num_classes=num_classes
        )
        
        # 如果指定使用预训练权重，从本地加载
        if pretrained:
            load_local_pretrained_weights(self.model, 'FastViT_SA24', pretrained=True)

        # 如果指定了 finetune_last_n，则冻结除最后 N 层外的所有层
        if finetune_last_n is not None:
            parameters = list(self.model.named_parameters())
            total_params = len(parameters)
            for i, (name, param) in enumerate(parameters):
                # 仅解冻最后 N 层
                param.requires_grad = i >= total_params - finetune_last_n
                if i >= total_params - finetune_last_n and i < total_params:
                    print(f"[Finetune] 解冻层: {name}")
        # 否则默认全部参数可训练（timm 默认行为）

    def forward(self, x):
        """
        前向传播。
        
        参数:
            x (Tensor): 输入张量，形状为 [B, 3, H, W]
        
        返回:
            Tensor: 分类logits，形状为 [B, num_classes]
        """
        return self.model(x)

    def print_parameters(self):
        """打印每个参数的名字和训练状态（是否需要梯度），用于调试。"""
        print("\n" + "="*80)
        print("FastViT-SA24 模型参数状态:")
        print("="*80)
        trainable_params = 0
        frozen_params = 0
        for name, param in self.model.named_parameters():
            if param.requires_grad:
                trainable_params += param.numel()
                status = "✓ 可训练"
            else:
                frozen_params += param.numel()
                status = "✗ 冻结"
            print(f"{status} | {name}")
        
        print("="*80)
        print(f"可训练参数: {trainable_params:,} ({trainable_params/1e6:.2f}M)")
        print(f"冻结参数:   {frozen_params:,} ({frozen_params/1e6:.2f}M)")
        print(f"总参数:     {trainable_params + frozen_params:,} ({(trainable_params + frozen_params)/1e6:.2f}M)")
        print("="*80 + "\n")


# 示例用法和测试
if __name__ == "__main__":
    print("\n" + "="*80)
    print("FastViT-SA24 模型测试")
    print("="*80 + "\n")
    
    # 测试1: 标准配置（155类，加载预训练，全参数训练）
    print(">>> 测试1: 标准配置（155类，全参数训练）")
    model = FastViT_SA24(num_classes=155, pretrained=True, img_size=224)
    dummy_input = torch.randn(2, 3, 224, 224)
    output = model(dummy_input)
    print(f"输入形状: {dummy_input.shape}")
    print(f"输出形状: {output.shape}")
    print(f"模型架构: FastViT-SA24")
    
    # 测试2: 微调模式（只训练最后20层）
    print("\n>>> 测试2: 微调模式（只解冻最后20层）")
    model_finetune = FastViT_SA24(
        num_classes=200, 
        pretrained=True, 
        finetune_last_n=20,
        img_size=224
    )
    
    # 打印参数状态（仅显示最后25层）
    print("\n参数训练状态（显示最后25层）:")
    all_params = list(model_finetune.model.named_parameters())
    for name, param in all_params[-25:]:
        status = "✓ 可训练" if param.requires_grad else "✗ 冻结"
        print(f"{status} | {name}")
    
    # 测试3: 高分辨率输入（384x384）
    print("\n>>> 测试3: 高分辨率输入（384x384）")
    model_high_res = FastViT_SA24(num_classes=200, pretrained=True, img_size=384)
    dummy_input_384 = torch.randn(1, 3, 384, 384)
    output_384 = model_high_res(dummy_input_384)
    print(f"输入形状: {dummy_input_384.shape}")
    print(f"输出形状: {output_384.shape}")
    
    # 统计参数量
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\n总参数量: {total_params:,} ({total_params/1e6:.2f}M)")
    print(f"可训练参数: {trainable_params:,} ({trainable_params/1e6:.2f}M)")
    
    print("\n" + "="*80)
    print("测试完成！FastViT-SA24 模型可以正常使用。")
    print("="*80 + "\n")
