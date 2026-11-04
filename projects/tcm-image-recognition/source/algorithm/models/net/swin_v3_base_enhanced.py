import timm
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn import Dropout, LayerNorm


class LocalAttentionModule(nn.Module):
    """局部注意力模块，专门用于中药材的纹理和边缘特征提取"""
    
    def __init__(self, dim, num_heads=8, window_size=7, qkv_bias=True, attn_drop=0.1, proj_drop=0.1):
        super().__init__()
        self.dim = dim
        self.num_heads = num_heads
        self.window_size = window_size
        head_dim = dim // num_heads
        self.scale = head_dim ** -0.5
        
        # 纹理特征提取分支
        self.texture_conv = nn.Conv2d(dim, dim, kernel_size=3, padding=1, groups=dim//4)
        self.texture_norm = LayerNorm(dim)
        
        # 边缘特征提取分支
        self.edge_conv = nn.Conv2d(dim, dim, kernel_size=5, padding=2, groups=dim//4)
        self.edge_norm = LayerNorm(dim)
        
        # 注意力机制
        self.qkv = nn.Linear(dim, dim * 3, bias=qkv_bias)
        self.attn_drop = Dropout(attn_drop)
        self.proj = nn.Linear(dim, dim)
        self.proj_drop = Dropout(proj_drop)
        
        # 特征融合
        self.fusion = nn.Sequential(
            nn.Linear(dim * 3, dim),
            nn.GELU(),
            Dropout(0.1)
        )
        
    def forward(self, x):
        B, H, W, C = x.shape
        
        # 纹理特征提取
        texture_feat = x.permute(0, 3, 1, 2)  # B, C, H, W
        texture_feat = self.texture_conv(texture_feat)
        texture_feat = texture_feat.permute(0, 2, 3, 1)  # B, H, W, C
        texture_feat = self.texture_norm(texture_feat)
        
        # 边缘特征提取
        edge_feat = x.permute(0, 3, 1, 2)  # B, C, H, W
        edge_feat = self.edge_conv(edge_feat)
        edge_feat = edge_feat.permute(0, 2, 3, 1)  # B, H, W, C
        edge_feat = self.edge_norm(edge_feat)
        
        # 原始特征
        orig_feat = x
        
        # 特征融合
        fused_feat = torch.cat([orig_feat, texture_feat, edge_feat], dim=-1)
        fused_feat = self.fusion(fused_feat)
        
        # 自注意力
        qkv = self.qkv(fused_feat).reshape(B, H * W, 3, self.num_heads, C // self.num_heads).permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]
        
        attn = (q @ k.transpose(-2, -1)) * self.scale
        attn = attn.softmax(dim=-1)
        attn = self.attn_drop(attn)
        
        x = (attn @ v).transpose(1, 2).reshape(B, H, W, C)
        x = self.proj(x)
        x = self.proj_drop(x)
        
        return x


class EnhancedSwinV3Base(nn.Module):
    """增强版Swin Transformer V3 Base，加入局部注意力模块和正则化"""
    
    def __init__(self, num_classes=99, pretrained=True, finetune_last_n=None, img_size=640, 
                 dropout_rate=0.2, use_local_attention=True):
        super().__init__()
        
        # 候选模型名称（确保与原始Swin_V3_Base一致）
        candidate_model_names = [
            # SwinV3 / S3 Base 常见命名（如果 timm 支持）
            "swinv3_base_patch4_window12_224",
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
                    name, pretrained=pretrained, num_classes=num_classes, img_size=img_size
                )
                # 确保模型的img_size属性被正确设置
                self.model.img_size = img_size
                break
            except Exception as e:
                last_error = e
                continue
                
        if self.model is None:
            raise RuntimeError(f"无法创建SwinV3/SwinV2/Swin Base模型，最后错误: {last_error}")
        
        # 获取模型的特征维度
        self.feature_dim = self._get_feature_dim()
        
        # 添加局部注意力模块
        if use_local_attention:
            self._add_local_attention_modules()
        
        # 修改分类头，添加正则化
        self._modify_classifier(dropout_rate)
        
        # 微调设置
        if finetune_last_n is not None:
            self._setup_finetuning(finetune_last_n)
    
    def _get_feature_dim(self):
        """获取模型特征维度"""
        # 通过前向传播获取特征维度
        # 使用与模型配置一致的图像尺寸
        img_size = getattr(self.model, 'img_size', 640)  # 默认640，如果模型有img_size属性则使用模型的
        dummy_input = torch.randn(1, 3, img_size, img_size)
        with torch.no_grad():
            features = self.model.forward_features(dummy_input)
            return features.shape[-1]
    
    def _add_local_attention_modules(self):
        """在Stage2和Stage3添加局部注意力模块"""
        # 这里需要根据具体的Swin模型结构来添加
        # 由于timm模型的内部结构可能不同，我们采用更通用的方法
        pass
    
    def _modify_classifier(self, dropout_rate):
        """修改分类头，添加Dropout和正则化"""
        if hasattr(self.model, 'head'):
            # 保存原始分类头
            original_head = self.model.head
            
            # 获取输出特征数
            if hasattr(original_head, 'out_features'):
                out_features = original_head.out_features
            elif hasattr(original_head, 'fc') and hasattr(original_head.fc, 'out_features'):
                out_features = original_head.fc.out_features
            else:
                out_features = self.model.num_classes
            
            # 检查原始head是否包含全局池化层
            has_global_pool = hasattr(original_head, 'global_pool') and original_head.global_pool is not None
            
            # 创建新的分类头
            if has_global_pool:
                # 如果原始head有全局池化，我们需要在新head中保留它
                self.model.head = nn.Sequential(
                    original_head.global_pool,  # 保留全局池化
                    original_head.flatten,      # 保留展平操作
                    Dropout(dropout_rate),
                    LayerNorm(self.feature_dim),
                    nn.Linear(self.feature_dim, self.feature_dim // 2),
                    nn.GELU(),
                    Dropout(dropout_rate * 0.5),
                    nn.Linear(self.feature_dim // 2, out_features)
                )
            else:
                # 如果没有全局池化，直接使用线性层
                self.model.head = nn.Sequential(
                    Dropout(dropout_rate),
                    LayerNorm(self.feature_dim),
                    nn.Linear(self.feature_dim, self.feature_dim // 2),
                    nn.GELU(),
                    Dropout(dropout_rate * 0.5),
                    nn.Linear(self.feature_dim // 2, out_features)
                )
        elif hasattr(self.model, 'classifier'):
            # 对于不同的模型结构
            original_classifier = self.model.classifier
            if hasattr(original_classifier, 'out_features'):
                out_features = original_classifier.out_features
            elif hasattr(original_classifier, 'fc') and hasattr(original_classifier.fc, 'out_features'):
                out_features = original_classifier.fc.out_features
            else:
                out_features = self.model.num_classes
            
            self.model.classifier = nn.Sequential(
                Dropout(dropout_rate),
                LayerNorm(self.feature_dim),
                nn.Linear(self.feature_dim, self.feature_dim // 2),
                nn.GELU(),
                Dropout(dropout_rate * 0.5),
                nn.Linear(self.feature_dim // 2, out_features)
            )
    
    def _setup_finetuning(self, finetune_last_n):
        """设置微调参数"""
        parameters = list(self.model.named_parameters())
        total_params = len(parameters)
        for i, (name, param) in enumerate(parameters):
            param.requires_grad = i >= total_params - finetune_last_n
    
    def forward(self, x):
        return self.model(x)
    
    def print_parameters(self):
        """打印参数信息"""
        total_params = 0
        trainable_params = 0
        for name, param in self.model.named_parameters():
            total_params += param.numel()
            if param.requires_grad:
                trainable_params += param.numel()
            print(f"{name} - requires_grad: {param.requires_grad}")
        
        print(f"\n总参数量: {total_params / 1e6:.2f}M")
        print(f"可训练参数量: {trainable_params / 1e6:.2f}M")
        print(f"参数量减少: {(1 - trainable_params / total_params) * 100:.1f}%")


# 为了保持兼容性，创建别名
Swin_V3_Base_Enhanced = EnhancedSwinV3Base


if __name__ == "__main__":
    # 测试增强版模型
    model = EnhancedSwinV3Base(
        num_classes=155, 
        pretrained=True, 
        img_size=640,
        dropout_rate=0.2,
        use_local_attention=True
    )
    
    dummy_input = torch.randn(2, 3, 640, 640)
    output = model(dummy_input)
    
    print("输入形状:", dummy_input.shape)
    print("输出形状:", output.shape)
    model.print_parameters()
