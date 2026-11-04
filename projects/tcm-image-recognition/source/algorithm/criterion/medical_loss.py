import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

class MedicalClassificationLoss(nn.Module):
    """
    医疗分类专用损失函数
    特点：
    1. 安全性分级加权
    2. 混淆矩阵惩罚
    3. 不确定性感知
    4. 类别重要性权重
    """
    def __init__(self, num_classes, safety_config=None, confusion_pairs=None, 
                 gamma=2.0, uncertainty_weight=0.2):
        """
        参数:
            safety_config (dict): 安全性配置 {class_idx: safety_level}
            confusion_pairs (list): 易混淆类别对 [(class1, class2), ...]
            gamma (float): focal参数
            uncertainty_weight (float): 不确定性权重
        """
        super(MedicalClassificationLoss, self).__init__()
        self.num_classes = num_classes
        self.gamma = gamma
        self.uncertainty_weight = uncertainty_weight
        
        # 安全性权重矩阵
        self.safety_matrix = self._build_safety_matrix(safety_config)
        
        # 混淆惩罚矩阵
        self.confusion_matrix = self._build_confusion_matrix(confusion_pairs)
        
    def _build_safety_matrix(self, safety_config):
        """构建安全性权重矩阵"""
        matrix = torch.ones(self.num_classes, self.num_classes)
        
        if safety_config is not None:
            for class_idx, safety_level in safety_config.items():
                # 对安全性要求高的类别，错误分类惩罚更重
                matrix[class_idx, :] *= safety_level
                matrix[:, class_idx] *= safety_level
                
        return nn.Parameter(matrix, requires_grad=False)
    
    def _build_confusion_matrix(self, confusion_pairs):
        """构建混淆惩罚矩阵"""
        matrix = torch.ones(self.num_classes, self.num_classes)
        
        if confusion_pairs is not None:
            for class1, class2 in confusion_pairs:
                # 对易混淆类别加重惩罚
                matrix[class1, class2] *= 2.0
                matrix[class2, class1] *= 2.0
                
        return nn.Parameter(matrix, requires_grad=False)
    
    def forward(self, logits, targets):
        """
        logits: (B, C) 模型输出
        targets: (B,) 真实标签
        """
        device = logits.device
        self.safety_matrix = self.safety_matrix.to(device)
        self.confusion_matrix = self.confusion_matrix.to(device)
        
        # 计算softmax概率
        probs = F.softmax(logits, dim=1)
        
        # 计算预测不确定性（熵）
        entropy = -torch.sum(probs * torch.log(probs + 1e-8), dim=1)
        max_entropy = np.log(self.num_classes)
        uncertainty = entropy / max_entropy
        
        # 基础交叉熵损失
        ce_loss = F.cross_entropy(logits, targets, reduction='none')
        
        # 计算pt用于focal loss
        pt = torch.exp(-ce_loss)
        
        # 获取预测类别
        pred_classes = torch.argmax(logits, dim=1)
        
        # 应用安全性权重
        safety_weights = self.safety_matrix[targets, pred_classes]
        
        # 应用混淆惩罚权重
        confusion_weights = self.confusion_matrix[targets, pred_classes]
        
        # 不确定性惩罚
        uncertainty_penalty = 1.0 + self.uncertainty_weight * uncertainty
        
        # 组合所有权重
        focal_weight = (1 - pt) ** self.gamma
        total_weight = safety_weights * confusion_weights * uncertainty_penalty * focal_weight
        
        # 最终损失
        final_loss = total_weight * ce_loss
        
        return final_loss.mean()

class AdaptiveMedicalLoss(nn.Module):
    """
    自适应医疗损失函数
    能够根据训练过程动态调整权重
    """
    def __init__(self, num_classes, adaptation_rate=0.01):
        super(AdaptiveMedicalLoss, self).__init__()
        self.num_classes = num_classes
        self.adaptation_rate = adaptation_rate
        
        # 动态权重矩阵
        self.register_buffer('dynamic_weights', torch.ones(num_classes, num_classes))
        self.register_buffer('error_counts', torch.zeros(num_classes, num_classes))
        self.register_buffer('total_counts', torch.zeros(num_classes, num_classes))
        
    def update_weights(self, targets, predictions):
        """根据预测结果更新权重"""
        for true_label, pred_label in zip(targets, predictions):
            self.total_counts[true_label, pred_label] += 1
            if true_label != pred_label:
                self.error_counts[true_label, pred_label] += 1
        
        # 计算错误率并更新权重
        error_rates = self.error_counts / (self.total_counts + 1e-8)
        self.dynamic_weights = 1.0 + error_rates * 2.0  # 错误率高的类别对权重更大
        
    def forward(self, logits, targets):
        # 获取预测
        predictions = torch.argmax(logits, dim=1)
        
        # 更新动态权重
        self.update_weights(targets.cpu(), predictions.cpu())
        
        # 计算损失
        ce_loss = F.cross_entropy(logits, targets, reduction='none')
        
        # 应用动态权重
        weights = self.dynamic_weights[targets, predictions].to(logits.device)
        weighted_loss = weights * ce_loss
        
        return weighted_loss.mean()

class CostSensitiveLoss(nn.Module):
    """
    成本敏感损失函数
    不同类别的误分类成本不同
    """
    def __init__(self, cost_matrix):
        """
        参数:
            cost_matrix: 成本矩阵 [num_classes, num_classes]
                        cost_matrix[i][j] 表示将类别i误分为类别j的成本
        """
        super(CostSensitiveLoss, self).__init__()
        self.register_buffer('cost_matrix', torch.tensor(cost_matrix, dtype=torch.float32))
        
    def forward(self, logits, targets):
        # 计算每个样本对所有类别的预测概率
        probs = F.softmax(logits, dim=1)
        
        # 计算期望成本
        batch_size = logits.size(0)
        expected_costs = torch.zeros(batch_size, device=logits.device)
        
        for i in range(batch_size):
            true_class = targets[i]
            # 计算该样本的期望误分类成本
            costs = self.cost_matrix[true_class] * probs[i]
            expected_costs[i] = costs.sum()
            
        return expected_costs.mean()

# 中药分类专用配置示例
def get_medicine_loss_config():
    """
    获取中药分类的损失函数配置
    """
    # 安全性配置（毒性中药安全等级更高）
    safety_config = {
        # 假设这些是毒性较大的中药类别索引
        15: 3.0,   # 假设某种毒性中药
        32: 2.5,   # 另一种需要特别注意的中药
        67: 2.0,   # 等等...
    }
    
    # 易混淆类别对
    confusion_pairs = [
        (12, 45),  # 假设这两类容易混淆
        (23, 67),  # 另一对易混淆的类别
        (34, 89),  # 等等...
    ]
    
    # 成本矩阵示例（简化版本）
    num_classes = 155
    cost_matrix = np.ones((num_classes, num_classes))
    
    # 对角线为0（正确分类无成本）
    np.fill_diagonal(cost_matrix, 0)
    
    # 特定的高成本误分类
    high_cost_pairs = [
        (15, 16, 10.0),  # 将毒性中药误分为相似无毒中药，成本很高
        (32, 33, 8.0),   # 另一个高成本误分类
    ]
    
    for true_class, pred_class, cost in high_cost_pairs:
        cost_matrix[true_class][pred_class] = cost
        
    return safety_config, confusion_pairs, cost_matrix