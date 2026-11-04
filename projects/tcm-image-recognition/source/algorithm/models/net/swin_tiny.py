import torch
import timm
from ._local_weights_loader import load_local_pretrained_weights
from torch import nn

class Swin_Tiny(nn.Module):
    """Swin Transformer (Tiny version), 一个纯粹的、层级化的Vision Transformer。"""

    def __init__(self, num_classes=99, pretrained=True, finetune_last_n=None,img_size=640):
        """
        初始化 Swin-Tiny Transformer 模型。

        参数:
            num_classes (int): 分类类别数。
            pretrained (bool): 是否加载 ImageNet-1k 预训练权重。
            finetune_last_n (int or None): Swin Transformer 的参数通常整体微调，
                                         但为保持接口一致性，保留此参数。
                                         如果非None，则解冻最后N个参数组（stage + norm + head）。
        """
        super().__init__()
        
        # timm库中Swin-Tiny的模型名称
        timm_model_name = "swin_tiny_patch4_window7_224"
        
        self.model = timm.create_model(
            timm_model_name, pretrained=False, num_classes=num_classes,img_size=img_size
        )
        
        # 加载本地预训练权重
        if pretrained:
            load_local_pretrained_weights(self.model, 'Swin_Tiny', pretrained=True)

        # Swin Transformer的参数冻结逻辑可能更复杂，通常建议全部微调或只微调最后几层
        # 为简单起见，这里提供一个基础的、与你现有代码一致的冻结逻辑
        if finetune_last_n is not None:
            parameters = list(self.model.named_parameters())
            total_params = len(parameters)
            for i, (name, param) in enumerate(parameters):
                param.requires_grad = i >= total_params - finetune_last_n

    def forward(self, x):
        """前向传播。"""
        return self.model(x)

    def print_parameters(self):
        """打印每个参数的名字和训练状态（是否需要梯度）。"""
        for name, param in self.model.named_parameters():
            print(f"{name} - requires_grad: {param.requires_grad}")


# 示例用法
if __name__ == "__main__":
    # 创建模型实例
    model = Swin_Tiny(num_classes=155, pretrained=True)

    # Swin Transformer的标准输入尺寸是 224x224
    dummy_input = torch.randn(2, 3, 640, 640)

    # 前向传播
    output = model(dummy_input)

    # 输出信息
    print(f"模型: {model.model.default_cfg['architecture']}")
    print("输入形状:", dummy_input.shape)
    print("输出形状:", output.shape)
    
    # 打印参数量
    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"可训练参数量: {total_params / 1e6:.2f}M")