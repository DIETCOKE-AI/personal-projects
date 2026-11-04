import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

class EnhancedFocalLoss(nn.Module):
    """
    增强版Focal Loss，专为中药图像分类优化
    特点：
    1. 动态α权重计算
    2. 温度缩放改善置信度校准
    3. 支持类别重要性权重
    """
    def __init__(self, num_classes, alpha=None, gamma=2.0, temperature=1.0, 
                 class_importance=None, reduction='mean'):
        """
        参数:
            num_classes (int): 类别数量
            alpha (list/tensor): 类别平衡权重，如果为None则自动计算
            gamma (float): 聚焦参数，关注困难样本
            temperature (float): 温度参数，用于置信度校准
            class_importance (dict): 重要类别的额外权重(如毒性中药)
            reduction (str): 损失聚合方式
        """
        super(EnhancedFocalLoss, self).__init__()
        self.num_classes = num_classes
        self.gamma = gamma
        self.temperature = temperature
        self.reduction = reduction
        
        if alpha is not None:
            if isinstance(alpha, list):
                alpha = torch.tensor(alpha, dtype=torch.float32)
            self.register_buffer('alpha', alpha)
        else:
            self.register_buffer('alpha', torch.ones(num_classes))
            
        # 重要类别权重（如毒性中药需要更准确识别）
        if class_importance is not None:
            importance_weights = torch.ones(num_classes)
            for class_idx, weight in class_importance.items():
                importance_weights[class_idx] = weight
            self.register_buffer('importance_weights', importance_weights)
        else:
            self.register_buffer('importance_weights', torch.ones(num_classes))

    def forward(self, logits, targets):
        """
        logits: (B, C) 模型原始输出
        targets: (B,) 真实标签
        """
        # 温度缩放改善置信度校准
        logits = logits / self.temperature
        
        # 计算交叉熵损失
        ce_loss = F.cross_entropy(logits, targets, reduction='none')
        
        # 计算预测概率
        pt = torch.exp(-ce_loss)
        
        # 确保所有张量在同一个设备上
        device = logits.device
        
        # 应用类别平衡权重
        alpha_t = self.alpha.to(device)[targets]
        
        # 应用重要性权重
        importance_t = self.importance_weights.to(device)[targets]
        
        # 计算Focal Loss
        focal_weight = (1 - pt) ** self.gamma
        focal_loss = alpha_t * importance_t * focal_weight * ce_loss
        
        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        else:
            return focal_loss

class MedicalFocalLoss(nn.Module):
    """
    医疗专用Focal Loss
    特点：
    1. 对混淆样本加重惩罚
    2. 支持安全性分级
    3. 自适应困难样本挖掘
    """
    def __init__(self, num_classes, alpha=None, gamma=2.0, 
                 safety_classes=None, confusion_penalty=1.5):
        """
        参数:
            safety_classes (list): 安全性要求高的类别索引
            confusion_penalty (float): 对易混淆类别的额外惩罚
        """
        super(MedicalFocalLoss, self).__init__()
        self.num_classes = num_classes
        self.gamma = gamma
        self.confusion_penalty = confusion_penalty
        
        if alpha is not None:
            if isinstance(alpha, list):
                alpha = torch.tensor(alpha, dtype=torch.float32)
            self.register_buffer('alpha', alpha)
        else:
            self.register_buffer('alpha', torch.ones(num_classes))
            
        # 安全性权重
        if safety_classes is not None:
            safety_weights = torch.ones(num_classes)
            for class_idx in safety_classes:
                safety_weights[class_idx] = 2.0  # 安全性要求高的类别权重加倍
            self.register_buffer('safety_weights', safety_weights)
        else:
            self.register_buffer('safety_weights', torch.ones(num_classes))

    def forward(self, logits, targets):
        # 标准Focal Loss计算
        ce_loss = F.cross_entropy(logits, targets, reduction='none')
        pt = torch.exp(-ce_loss)
        
        # 计算预测置信度分布的熵，熵高表示预测不确定
        probs = F.softmax(logits, dim=1)
        entropy = -torch.sum(probs * torch.log(probs + 1e-8), dim=1)
        max_entropy = np.log(self.num_classes)
        uncertainty = entropy / max_entropy
        
        # 对不确定样本增加惩罚
        uncertainty_penalty = 1.0 + uncertainty * self.confusion_penalty
        
        # 确保所有张量在同一个设备上
        device = logits.device
        
        # 应用各种权重
        alpha_t = self.alpha.to(device)[targets]
        safety_t = self.safety_weights.to(device)[targets]
        focal_weight = (1 - pt) ** self.gamma
        
        final_loss = alpha_t * safety_t * uncertainty_penalty * focal_weight * ce_loss
        
        return final_loss.mean()

class BalancedFocalLoss(nn.Module):
    """
    平衡版Focal Loss，自动处理类别不平衡
    """
    def __init__(self, num_classes, gamma=2.0, beta=0.9999):
        """
        参数:
            beta (float): 有效样本数计算参数
        """
        super(BalancedFocalLoss, self).__init__()
        self.num_classes = num_classes
        self.gamma = gamma
        self.beta = beta
        
        # 用于统计各类别样本数
        self.register_buffer('class_counts', torch.zeros(num_classes))
        self.register_buffer('total_samples', torch.tensor(0.0))

    def update_class_counts(self, targets):
        """更新类别统计信息"""
        for target in targets:
            self.class_counts[target] += 1
        self.total_samples += len(targets)

    def get_effective_numbers(self):
        """计算有效样本数"""
        effective_nums = 1.0 - torch.pow(self.beta, self.class_counts)
        return effective_nums

    def forward(self, logits, targets):
        # 更新类别统计
        self.update_class_counts(targets)
        
        # 计算动态权重
        effective_nums = self.get_effective_numbers()
        weights = (1.0 - self.beta) / effective_nums
        weights = weights / weights.sum() * self.num_classes
        
        # 标准Focal Loss
        ce_loss = F.cross_entropy(logits, targets, reduction='none')
        pt = torch.exp(-ce_loss)
        
        # 应用动态权重
        alpha_t = weights[targets]
        focal_weight = (1 - pt) ** self.gamma
        
        focal_loss = alpha_t * focal_weight * ce_loss
        
        return focal_loss.mean()