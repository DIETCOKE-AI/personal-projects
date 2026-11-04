import torch
import timm
from torch import nn

class MobileViT_large(nn.Module):
    """MobileViT v2-175 模型，基于 timm 库实现，适用于高分辨率输入。"""

    def __init__(self, num_classes=4, pretrained=True, finetune_head_only=True, finetune_last_n=2):
        """
        初始化 MobileViT v2-175 模型。

        参数:
            num_classes (int): 分类类别数。
            pretrained (bool): 是否加载 ImageNet 预训练权重。
            finetune_head_only (bool): 是否只微调分类头。
            finetune_last_n (int): 解冻最后N层。
        """
        super().__init__()
        self.model = timm.create_model(
            "mobilevitv2_175",        # 最大变体
            pretrained=False,
            num_classes=num_classes
        )
        if finetune_head_only:
            # 冻结除分类头以外的参数
            for name, param in self.model.named_parameters():
                if not ("head" in name or "classifier" in name or "fc" in name):
                    param.requires_grad = False
        if finetune_last_n is not None:
            self.freeze_except_last_n(finetune_last_n)

    def freeze_except_last_n(self, n=2):
        # 获取所有block的名字
        block_names = [f"blocks.{i}" for i in range(5)]  # 5是block总数，需根据实际调整
        # 需要解冻的block
        unfreeze_blocks = block_names[-n:]
        for name, param in self.model.named_parameters():
            # 如果是最后N个block或分类头就解冻，否则冻结
            if any(block in name for block in unfreeze_blocks) or ("head" in name or "classifier" in name or "fc" in name):
                param.requires_grad = True
            else:
                param.requires_grad = False

    def forward(self, x):
        """
        前向传播。

        参数:
            x (torch.Tensor): 输入图像张量，形状为 (B, 3, H, W)。

        返回:
            torch.Tensor: 输出 logits，形状为 (B, num_classes)。
        """
        return self.model(x)

    def print_parameters(self):
        for name, _ in self.model.named_parameters():
            print(name)


# 示例用法
if __name__ == "__main__":
    # 创建模型实例（假设有 65 个类别）
    model = MobileViT_large(num_classes=155, pretrained=True)

    # 打印模型结构（可选）
    print(model)

    # 构造随机输入 (batch_size=2, channels=3, height=640, width=640)
    dummy_input = torch.randn(2, 3, 640, 640)

    # 执行前向传播
    output = model(dummy_input)

    # 打印输出信息
    print("Input shape:", dummy_input.shape)
    print("Output logits shape:", output.shape)
    print("Output logits:", output)

    # 打印所有参数名
    model.print_parameters()
