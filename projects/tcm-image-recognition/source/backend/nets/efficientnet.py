# Define EfficientNetB7 model
import timm
import torch

class EfficientNetB7(torch.nn.Module):
    def __init__(self, num_classes=50, pretrained=False):
        super().__init__()
        self.model = timm.create_model("tf_efficientnet_b7", pretrained=pretrained, num_classes=num_classes)

    def forward(self, x):
        return self.model(x)
