import torch
import timm
from torch import nn

class ConvNeXt_V2_Tiny(nn.Module):
    """ConvNeXt V2 Tiny 模型，基于 timm 库实现。
    
    注意：本地权重文件格式与 timm 不兼容，因此直接使用 timm 在线预训练权重。
    预训练策略：ImageNet-22k -> ImageNet-1k（与 EfficientNetV2 等模型相同）
    """

    def __init__(self, num_classes=99, pretrained=True, finetune_last_n=None):
        """
        初始化 ConvNeXt V2 Tiny 模型。

        参数:
            num_classes (int): 分类类别数。
            pretrained (bool): 是否加载 ImageNet-22k -> 1k 预训练权重。
            finetune_last_n (int or None): 解冻最后N层参数用于微调。如果为 None，则全部参数可训练。
        """
        super().__init__()
        # 使用 timm 创建 convnextv2_tiny 模型
        # 直接使用 timm 的在线预训练权重（ImageNet-22k -> ImageNet-1k）
        # 注意：本地权重文件格式不兼容，因此使用在线加载
        model_name = "convnextv2_tiny.fcmae_ft_in22k_in1k" if pretrained else "convnextv2_tiny"
        self.model = timm.create_model(
            model_name, pretrained=pretrained, num_classes=num_classes
        )
        
        if pretrained:
            print(f"[ConvNeXt_V2_Tiny] 成功加载 timm 在线预训练权重: {model_name}")

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

    def print_parameters(self):
        """打印每个参数的名字和训练状态（是否需要梯度）。"""
        for name, param in self.model.named_parameters():
            print(f"{name} - requires_grad: {param.requires_grad}")


# 示例用法
if __name__ == "__main__":
    # 创建模型实例，分类数为 155，加载预训练权重，并只解冻最后 10 层用于微调
    model = ConvNeXt_V2_Tiny(num_classes=155, pretrained=True, finetune_last_n=10)

    # ConvNeXt V2 的标准输入尺寸也是 224x224
    # 我们构造一个批次为2的随机输入
    dummy_input = torch.randn(2, 3, 224, 224)

    # 前向传播
    output = model(dummy_input)

    # 输出信息
    print(f"模型架构: {model.model.default_cfg['architecture']}")
    print("输入形状:", dummy_input.shape)
    print("输出形状:", output.shape)
    print("-" * 30)

    # 打印参数的训练状态，以验证微调设置
    print("打印最后10个参数的训练状态来验证设置:")
    all_params = list(model.model.named_parameters())
    for name, param in all_params[-10:]:
          print(f"{name} - requires_grad: {param.requires_grad}")