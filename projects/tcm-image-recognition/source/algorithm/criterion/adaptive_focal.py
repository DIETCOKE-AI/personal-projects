import torch
import torch.nn as nn
import torch.nn.functional as F

class AdaptiveFocalLoss(nn.Module):
    def __init__(self, gamma_init=2.0, alpha=1.0, reduction='mean'):
        """
        自适应 Focal Loss

        参数:
            gamma_init (float): 初始 gamma 值。
            alpha (float): 类别平衡因子。
            reduction (str): 'none' | 'mean' | 'sum'。
        """
        super(AdaptiveFocalLoss, self).__init__()
        self.gamma_init = gamma_init
        self.alpha = alpha
        self.reduction = reduction

    def forward(self, logits, targets):
        """
        logits: shape (B, C) —— 模型原始输出
        targets: shape (B,) —— 真实标签
        """
        ce_loss = F.cross_entropy(logits, targets, reduction='none')  # 普通交叉熵 loss
        pt = torch.exp(-ce_loss)  # pt 越小表示越困难的样本
        gamma = self.gamma_init + (1 - pt)  # 动态调整 gamma

        focal_loss = self.alpha * (1 - pt) ** gamma * ce_loss

        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        else:
            return focal_loss
