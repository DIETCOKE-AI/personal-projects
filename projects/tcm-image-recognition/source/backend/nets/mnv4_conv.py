# tcm/nets/mnv4.py

import torch
import timm
from torch import nn

class MNv4_Conv_AA_Large(nn.Module):
    """
    MobileNetV4 Conv AA Large 模型，基于 timm 库实现。
    这是一个用于后端推理的简洁版本。
    它只定义网络结构，权重的加载由外部的 ModelManager 负责。
    """
    def __init__(self, num_classes=99):
        """
        初始化模型。

        参数:
            num_classes (int): 分类任务的类别总数。
        """
        super().__init__()
        
        # 在后端推理时，我们不使用 timm 的预训练功能，
        # 因为我们将加载自己 fine-tune 过的权重。
        self.model = timm.create_model(
            'mobilenetv4_conv_aa_large',
            pretrained=False,  # 这里必须是 False
            num_classes=num_classes
        )

    def forward(self, x):
        """
        前向传播。
        """
        return self.model(x)

# 可以在此添加一个简单的测试，以确保文件可以独立运行
if __name__ == '__main__':
    # 假设已知大类是99个
    model = MNv4_Conv_AA_Large(num_classes=99)
    print("MNv4_Conv_AA_Large 模型结构创建成功 (用于后端)。")
    
    # 模拟输入
    dummy_input = torch.randn(1, 3, 448, 448) # MNv4 常用输入尺寸
    output = model(dummy_input)
    
    print("输入形状:", dummy_input.shape)
    print("输出形状:", output.shape)
    # print(model) # 取消注释可以查看详细结构
