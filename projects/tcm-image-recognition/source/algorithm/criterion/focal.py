import torch
import torch.nn as nn
import torch.nn.functional as F

class FocalLoss(nn.Module):
    def __init__(self, alpha=None, gamma=2.0, reduction='mean'):
        """
        标准的 Focal Loss.
        
        参数:
            alpha (list or torch.Tensor, optional): 一个权重列表，长度为类别数。
                                                     用于处理类别不平衡。默认为 None。
            gamma (float): 聚焦参数，用于关注困难样本。
            reduction (str): 'none' | 'mean' | 'sum'。
        """
        super(FocalLoss, self).__init__()
        # 如果提供了 alpha 列表，确保它是 tensor 格式
        if alpha is not None:
            if isinstance(alpha, list):
                alpha = torch.tensor(alpha)
            self.alpha = alpha
        else:
            self.alpha = None
            
        self.gamma = gamma
        self.reduction = reduction

    def forward(self, logits, targets):
        """
        logits: shape (B, C) - 模型的原始输出
        targets: shape (B,) - 真实标签
        """
        # 计算基础的交叉熵损失，但不进行-reduction
        ce_loss = F.cross_entropy(logits, targets, reduction='none')
        
        # 计算 pt，即正确类别的预测概率
        pt = torch.exp(-ce_loss)
        
        # 这是 Focal Loss 的核心公式
        focal_term = (1 - pt) ** self.gamma
        
        loss = focal_term * ce_loss

        # 如果提供了 alpha，则应用类别权重
        if self.alpha is not None:
            # 确保 alpha 和 loss 在同一个设备上 (e.g., 'cuda:0')
            alpha_t = self.alpha[targets].to(logits.device)
            loss = alpha_t * loss

        # 应用 reduction
        if self.reduction == 'mean':
            return loss.mean()
        elif self.reduction == 'sum':
            return loss.sum()
        else:
            return loss