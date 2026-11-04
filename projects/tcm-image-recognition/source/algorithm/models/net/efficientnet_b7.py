import torch
import timm
from ._local_weights_loader import load_local_pretrained_weights
from torch import nn

class EfficientNetB7(nn.Module):
    """EfficientNet-B7 模型，基于 timm 库实现，支持指定微调最后 N 层。"""

    def __init__(self, num_classes=99, pretrained=True, finetune_last_n=1):
        """
        初始化 EfficientNet-B7 模型。

        参数:
            num_classes (int): 分类类别数。
            pretrained (bool): 是否加载预训练权重。
            finetune_last_n (int or None): 解冻最后 N 层参数（包括分类头）。若为 None，则全部参数可训练。
        """
        super().__init__()
        self.model = timm.create_model(
            "tf_efficientnet_b7",
            pretrained=False,
            num_classes=num_classes,
        )
        
        # 加载本地预训练权重
        if pretrained:
            load_local_pretrained_weights(self.model, 'EfficientNetB7', pretrained=True)

        if finetune_last_n is not None:
            parameters = list(self.model.named_parameters())
            total_params = len(parameters)
            for i, (name, param) in enumerate(parameters):
                # 仅解冻最后 N 层
                param.requires_grad = i >= total_params - finetune_last_n
        # 否则默认全部参数可训练

    def forward(self, x):
        return self.model(x)

    def print_parameters(self):
        """打印每个参数的名字和是否需要梯度。"""
        for name, param in self.model.named_parameters():
            print(f"{name} - requires_grad: {param.requires_grad}")


# 示例用法
if __name__ == "__main__":
    # 创建 EfficientNet-B7 模型实例，仅微调最后 20 层参数
    #model = EfficientNetB7(num_classes=65, pretrained=True, finetune_last_n=20)
    model = EfficientNetB7(num_classes=99, pretrained=False)
    # 打印模型结构（可选）
    print(model)

    # 随机输入数据
    dummy_input = torch.randn(2, 3, 600, 600)
    output = model(dummy_input)

    print("Input shape:", dummy_input.shape)
    print("Output logits shape:", output.shape)

    # 打印每个参数的 requires_grad 状态
    model.print_parameters()
