import timm
from ._local_weights_loader import load_local_pretrained_weights
import torch
from torch import nn


class Swin_V3_Base(nn.Module):
    """Swin Transformer V3 Base 封装，带有健壮的回退逻辑。

    优先尝试 SwinV3（S3）base 的模型名称；若该名称在当前 timm 版本不可用，
    则依次回退到 SwinV2 Base、Swin Base（V1）。
    支持传入 img_size 以便在 timm>=0.9 的实现中进行权重/窗口适配。
    """

    def __init__(self, num_classes=99, pretrained=True, finetune_last_n=None, img_size=640):
        super().__init__()

        candidate_model_names = [
            # SwinV3 / S3 Base 常见命名（如果 timm 支持）
            "swinv3_base_patch4_window12_224",
            "swin_s3_base_224",
            # SwinV2 Base 回退
            "swinv2_base_window12to16_192to256",
            # SwinV1 Base 回退
            "swin_base_patch4_window7_224",
        ]

        self.model = None
        last_error = None
        for name in candidate_model_names:
            try:
                self.model = timm.create_model(
                    name, pretrained=False, num_classes=num_classes, img_size=img_size
                )
                break
            except Exception as e:
                last_error = e
                continue

        if self.model is None:
            raise RuntimeError(f"无法创建SwinV3/SwinV2/Swin Base模型，最后错误: {last_error}")
        
        # 加载本地预训练权重
        if pretrained:
            load_local_pretrained_weights(self.model, 'Swin_V3_Base', pretrained=True)

        if finetune_last_n is not None:
            parameters = list(self.model.named_parameters())
            total_params = len(parameters)
            for i, (name, param) in enumerate(parameters):
                param.requires_grad = i >= total_params - finetune_last_n

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)

    def print_parameters(self):
        for name, param in self.model.named_parameters():
            print(f"{name} - requires_grad: {param.requires_grad}")


if __name__ == "__main__":
    model = Swin_V3_Base(num_classes=155, pretrained=True, img_size=640)
    dummy_input = torch.randn(2, 3, 640, 640)
    output = model(dummy_input)
    print("输入形状:", dummy_input.shape)
    print("输出形状:", output.shape)
    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"可训练参数量: {total_params / 1e6:.2f}M")