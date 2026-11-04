import torch
import timm
from torch import nn
from ._local_weights_loader import load_local_pretrained_weights

class ConvNeXt_Large(nn.Module):
    """ConvNeXt-Large 模型，基于 timm 库实现，旨在提供与 Transformer 媲美的性能。"""

    def __init__(self, num_classes=99, pretrained=True, finetune_last_n=None):
        """
        初始化 ConvNeXt-Large 模型。

        参数:
            num_classes (int): 分类类别数。
            pretrained (bool): 是否加载在 ImageNet-22k 上预训练并在 ImageNet-1k 上微调的权重。
            finetune_last_n (int or None): 解冻最后N层参数（包括分类头）。如果为 None，则全部参数可训练。
        """
        super().__init__()
        # 使用 timm 创建 convnext_large 模型（不加载在线权重）
        # 将从本地加载 ImageNet-12k 预训练权重（与MNv4_Conv_AA_Large相同策略）
        self.model = timm.create_model(
            "convnext_large", pretrained=False, num_classes=num_classes
        )
        
        # 如果指定使用预训练权重，从本地加载
        if pretrained:
            load_local_pretrained_weights(self.model, 'ConvNeXt_Large', pretrained=True)

        # 如果指定了 finetune_last_n，则冻结除最后 N 层外的所有层
        if finetune_last_n is not None:
            parameters = list(self.model.named_parameters())
            total_params = len(parameters)
            for i, (name, param) in enumerate(parameters):
                # 仅解冻最后 N 层
                param.requires_grad = i >= total_params - finetune_last_n
        # 否则默认全部参数可训练（timm 默认行为）

    def forward(self, x):
        """前向传播。"""
        return self.model(x)

    def print_parameters(self):
        """打印每个参数的名字和训练状态（是否需要梯度）。"""
        for name, param in self.model.named_parameters():
            print(f"{name} - requires_grad: {param.requires_grad}")


# 示例用法
if __name__ == "__main__":
    # 创建模型实例，分类数为 155，加载预训练权重，并只解冻最后 25 层用于微调
    model = ConvNeXt_Large(num_classes=155, pretrained=True, finetune_last_n=25)

    # ConvNeXt-Large 的标准输入尺寸是 224x224 或 384x384
    # 我们构造一个批次为2的随机输入
    dummy_input = torch.randn(2, 3, 224, 224)

    # 前向传播
    output = model(dummy_input)

    # 输出信息
    print(f"模型: {model.model.default_cfg['architecture']}")
    print("输入形状:", dummy_input.shape)
    print("输出形状:", output.shape)
    print("-" * 30)

    # 打印参数的训练状态，以验证微调设置
    print("打印部分参数的训练状态（最后15层）来验证设置:")
    all_params = list(model.model.named_parameters())
    for name, param in all_params[-15:]:
         print(f"{name} - requires_grad: {param.requires_grad}")