import torch
import timm
from ._local_weights_loader import load_local_pretrained_weights
from torch import nn

class MobileViT_large(nn.Module):
    """MobileViT v2-175 模型，基于 timm 库实现，适用于高分辨率输入。"""

    def __init__(self, num_classes=99, pretrained=True, finetune_last_n=None):
        """
        初始化 MobileViT v2-175 模型。

        参数:
            num_classes (int): 分类类别数。
            pretrained (bool): 是否加载 ImageNet 预训练权重。
            finetune_last_n (int or None): 解冻最后N层。如果为 None，则全部解冻。
        """
        super().__init__()
        # 注意：使用 mobilevitv2_200 以匹配 checkpoint 文件
        self.model = timm.create_model(
            "mobilevitv2_200", pretrained=False, num_classes=num_classes
        )
        
        # 加载本地预训练权重
        if pretrained:
            load_local_pretrained_weights(self.model, 'MobileViT_large', pretrained=True)

        # 冻结所有参数
        if finetune_last_n is not None:
            parameters = list(self.model.named_parameters())
            total_params = len(parameters)
            for i, (name, param) in enumerate(parameters):
                # 解冻最后 N 层
                param.requires_grad = i >= total_params - finetune_last_n
        # 否则默认全部参数可训练（即全解冻）

    def forward(self, x):
        """前向传播。"""
        return self.model(x)

    def print_parameters(self):
        """打印每个参数的名字和训练状态（是否需要梯度）。"""
        for name, param in self.model.named_parameters():
            print(f"{name} - requires_grad: {param.requires_grad}")


# 示例用法
if __name__ == "__main__":
    # 创建模型实例，只解冻最后 20 层
    model = MobileViT_large(num_classes=155, pretrained=True, finetune_last_n=20)

    # 构造随机输入
    dummy_input = torch.randn(2, 3, 640, 640)

    # 前向传播
    output = model(dummy_input)

    # 输出信息
    print("Input shape:", dummy_input.shape)
    print("Output shape:", output.shape)

    # 打印参数的训练状态
    model.print_parameters()
