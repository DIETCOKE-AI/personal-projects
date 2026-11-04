import os
import torch
import timm
from torch import nn

class MNv4_Conv_AA_Large(nn.Module):
    def __init__(self, num_classes=99, pretrained=True, finetune_last_n=None):
        super().__init__()
        
        base_model_name = 'mobilenetv4_conv_aa_large'
        
        self.model = timm.create_model(
            base_model_name,
            pretrained=False,
            num_classes=num_classes
        )

        if pretrained:
            checkpoint_path = os.environ.get('TCM_MNV4_PRETRAINED_PATH', './weights/mnv4_conv_aa_large.bin')
            #print(f"从本地路径加载预训练权重: {checkpoint_path}")

            # 1. 加载本地权重文件到内存
            #    同时，我们处理一下日志中出现的 FutureWarning，加入 weights_only=True 参数
            state_dict = torch.load(checkpoint_path, map_location='cpu', weights_only=True)

            # --- 关键修复在这里 ---
            # 2. 手术刀式移除不匹配的键
            #    因为我们知道是 classifier 层不匹配，所以在加载前直接从字典里删除它们
            if 'classifier.weight' in state_dict:
                del state_dict['classifier.weight']
                del state_dict['classifier.bias']
                #print("已手动从预训练权重中移除不匹配的 'classifier' 层。")

            # 3. 加载这个被“净化”过的权重字典
            #    现在，因为冲突的键已经被移除了，所以加载过程不会再有尺寸不匹配的问题
            incompatible_keys = self.model.load_state_dict(state_dict, strict=False)
            
            #print("成功加载预训练权重。剩余不匹配的键 (理论上应为空列表或只包含非预期键):")
            #print(incompatible_keys)

        # 参数冻结/解冻逻辑 (保持不变)
        if finetune_last_n is not None:
            parameters = list(self.model.named_parameters())
            total_params = len(parameters)
            for param in self.model.parameters():
                param.requires_grad = False
            for i, (name, param) in enumerate(parameters):
                if i >= total_params - finetune_last_n:
                    param.requires_grad = True
    def forward(self, x):
        return self.model(x)

    def print_parameters(self):
        for name, param in self.model.named_parameters():
            print(f"{name:<60} - requires_grad: {param.requires_grad}")


# 示例用法
if __name__ == "__main__":
    # --- 配置 ---
    NUM_CLASSES = 200  # 假设您的中药材分类任务有 200 个类别
    FINETUNE_LAST_N_LAYERS = 30 # 指定解冻最后 30 层参数
    
    print("--- 开始创建模型实例 ---")
    # --- 创建模型 ---
    # 创建模型实例，只解冻最后 30 层进行微调
    model = MNv4_Conv_AA_Large(
        num_classes=NUM_CLASSES, 
        pretrained=True, # 设置为 True 来加载预训练权重
        finetune_last_n=FINETUNE_LAST_N_LAYERS
    )
    print("--- 模型实例创建完成 ---\n")

    # --- 构造随机输入 ---
    # 注意：该模型在 448x448 分辨率上微调，建议使用不低于此分辨率的输入
    dummy_input = torch.randn(2, 3, 448, 448) 

    # --- 前向传播 ---
    print("--- 开始前向传播测试 ---")
    output = model(dummy_input)
    print("--- 前向传播测试完成 ---\n")


    # --- 输出信息 ---
    print("--- 模型与数据信息 ---")
    try:
        # 尝试打印从模型配置中获取的架构名称
        print(f"模型名称 (from config): {model.model.default_cfg['architecture']}")
    except KeyError:
        print("模型名称 (from config): 未找到")
    print("-" * 30)
    print("输入张量形状:", dummy_input.shape)
    print("输出张量形状:", output.shape)
    print("-" * 30)
    
    # --- 打印参数的训练状态 ---
    # 取消下面一行的注释，可以查看所有参数的状态
    # model.print_parameters()

    # 为了避免刷屏，只打印一部分参数的状态来验证
    print("模型参数训练状态验证 (只显示部分):")
    params_to_show = list(model.model.named_parameters())
    print("... (前面的层应被冻结) ...")
    # 打印最后解冻的层和之前几层作为对比
    for name, param in params_to_show[-(FINETUNE_LAST_N_LAYERS + 5) : -(FINETUNE_LAST_N_LAYERS - 5 if FINETUNE_LAST_N_LAYERS > 5 else 0)]: 
         print(f"{name:<60} - requires_grad: {param.requires_grad}")
    print("... (最后的层应被解冻) ...")