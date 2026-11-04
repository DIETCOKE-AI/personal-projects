import torch
import timm
from ._local_weights_loader import load_local_pretrained_weights
from torch import nn
import torch.nn.functional as F

class MobileViT_large_PAFPN(nn.Module):
    """MobileViT v2-175 模型，集成PAFPN网络用于多尺度特征融合。
    注意：此模型训练时使用 mobilevitv2_175 版本。"""

    def __init__(self, num_classes=155, pretrained=True, finetune_last_n=None):
        """
        初始化集成PAFPN的MobileViT v2-175 模型。

        参数:
            num_classes (int): 分类类别数。
            pretrained (bool): 是否加载 ImageNet 预训练权重。
            finetune_last_n (int or None): 解冻最后N层。如果为 None，则全部解冻。
        """
        super().__init__()
        
        # 1. 创建基础模型，使用 features_only=True 直接获取多尺度特征
        # 注意：此模型训练时使用 mobilevitv2_175 版本
        self.backbone = timm.create_model(
            "mobilevitv2_175", 
            pretrained=False,
            features_only=True, # <-- 关键修改：让模型返回一个特征列表
        )
        
        # 加载本地预训练权重
        if pretrained:
            load_local_pretrained_weights(self.backbone, 'MobileViT_large_PAFPN', pretrained=True)
        
        # 2. 自动从 backbone 获取中间特征层的输出通道数
        feature_channels = self.backbone.feature_info.channels()
        
        # 3. PAFPN 参数
        self.pafpn = PAFPN(
            in_channels=feature_channels,
            out_channels=256,
            num_outs=len(feature_channels) # PAFPN输出的特征数量应与输入匹配
        )
        
        # 4. 全局平均池化和分类头
        self.global_pool = nn.AdaptiveAvgPool2d(1)
        
        # 5. 修正分类头的输入维度
        # 输入维度 = PAFPN输出通道数 * PAFPN输出特征数
        classifier_in_features = self.pafpn.out_channels * self.pafpn.num_outs
        self.classifier = nn.Linear(classifier_in_features, num_classes)
        
        # 冻结参数
        if finetune_last_n is not None:
            self._freeze_parameters(finetune_last_n)

    def _freeze_parameters(self, finetune_last_n):
        """冻结模型参数，只解冻最后n层"""
        # 注意：这里的逻辑可能需要根据timm模型参数的实际组织方式微调
        parameters = list(self.backbone.named_parameters())
        total_params = len(parameters)
        for i, (name, param) in enumerate(parameters):
            param.requires_grad = i >= total_params - finetune_last_n

    def forward(self, x):
        """前向传播，包含特征提取、PAFPN融合和分类。"""
        # 1. 提取多尺度特征（现在变得非常简单）
        features = self.extract_features(x)
        
        # 2. 通过PAFPN进行特征融合
        pafpn_features = self.pafpn(features)
        
        # 3. 合并所有尺度的特征
        pooled_features = []
        for feat in pafpn_features:
            pooled = self.global_pool(feat).flatten(1)
            pooled_features.append(pooled)
        
        # 4. 连接所有特征
        combined = torch.cat(pooled_features, dim=1)
        
        # 5. 通过分类器得到结果
        out = self.classifier(combined)
        
        return out

    def extract_features(self, x):
        """
        从backbone中提取多尺度特征。
        由于使用了 features_only=True，直接调用 backbone 即可。
        """
        return self.backbone(x)

    def print_parameters(self):
        """打印每个参数的名字和训练状态（是否需要梯度）。"""
        for name, param in self.named_parameters():
            print(f"{name} - requires_grad: {param.requires_grad}")


class PAFPN(nn.Module):
    """
    Path Aggregation Feature Pyramid Network (PAFPN)
    用于多尺度特征融合，在FPN的基础上增加了自底向上的路径。
    （已修正逻辑错误）
    """
    
    def __init__(self, in_channels, out_channels, num_outs, start_level=0, end_level=-1):
        super().__init__()
        
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.num_ins = len(in_channels)
        self.num_outs = num_outs
        self.start_level = start_level
        
        if end_level == -1:
            self.backbone_end_level = self.num_ins
        else:
            self.backbone_end_level = end_level
            assert end_level <= len(in_channels)
        
        # 构建自上而下的路径 (Top-Down Path)
        self.lateral_convs = nn.ModuleList()
        for i in range(self.start_level, self.backbone_end_level):
            l_conv = nn.Conv2d(in_channels[i], out_channels, 1)
            self.lateral_convs.append(l_conv)
        
        # 构建自下而上的路径 (Bottom-Up Path)
        self.downsample_convs = nn.ModuleList()
        self.pafpn_convs = nn.ModuleList()
        
        # downsample_convs 用于连接更低层的特征 (数量为 N-1)
        for i in range(self.start_level, self.backbone_end_level - 1):
            down_conv = nn.Conv2d(out_channels, out_channels, 3, stride=2, padding=1)
            self.downsample_convs.append(down_conv)
        
        # pafpn_convs 是每个融合后特征的输出卷积 (数量为 N)
        for i in range(self.start_level, self.backbone_end_level):
            pafpn_conv = nn.Conv2d(out_channels, out_channels, 3, padding=1)
            self.pafpn_convs.append(pafpn_conv)

    def forward(self, inputs):
        """前向传播PAFPN网络 (已修正)"""
        assert len(inputs) == self.num_ins
        
        # 1. 侧向连接 (Lateral Connections)
        laterals = [
            lateral_conv(inputs[i + self.start_level])
            for i, lateral_conv in enumerate(self.lateral_convs)
        ]
        
        # 2. 自顶向下路径 (Top-Down FPN path)
        used_backbone_levels = len(laterals)
        for i in range(used_backbone_levels - 1, 0, -1):
            prev_shape = laterals[i - 1].shape[2:]
            laterals[i - 1] += F.interpolate(
                laterals[i], size=prev_shape, mode='nearest')
        
        # `laterals` 此时已成为 FPN 的输出 [P2, P3, P4, P5]
        
        # 3. 自底向上路径 (Bottom-Up PAN path) - 修正后的逻辑
        # 从最底层的特征 P2 开始向上聚合
        pan_outs = [laterals[0]]
        for i in range(used_backbone_levels - 1):
            # 将前一层的输出 pan_outs[-1] (即 Ni) 进行下采样
            downsampled_feat = self.downsample_convs[i](pan_outs[-1])
            # 与 FPN 对应层 (Pi+1) 的特征相加
            pan_outs.append(laterals[i + 1] + downsampled_feat)
        
        # 4. 应用最终的卷积并输出
        outs = []
        for i in range(used_backbone_levels):
            outs.append(self.pafpn_convs[i](pan_outs[i]))
            
        return outs


# 示例用法
if __name__ == "__main__":
    # 创建模型实例，只解冻最后 20 层
    model = MobileViT_large_PAFPN(num_classes=155, pretrained=True, finetune_last_n=20)
    model.eval() # 切换到评估模式

    # 构造随机输入
    # 注意：timm 模型通常需要 224x224 或 384x384 的输入尺寸，这里用 256x256 作为示例
    dummy_input = torch.randn(2, 3, 256, 256)
    
    # 前向传播
    try:
        output = model(dummy_input)
        
        # 输出信息
        print("Model created and forward pass successful!")
        print("Input shape:", dummy_input.shape)
        print("Output shape:", output.shape)
        
        # 打印部分参数的训练状态
        # model.print_parameters()
    except Exception as e:
        print(f"An error occurred during forward pass: {e}")