import os
import sys
import importlib
from importlib import import_module
import torch
from torchvision.models import resnet50

def get_network(__C):
    try:
        model_path = 'models.net'
        net = getattr(import_module(model_path),__C.model)
        # 使用 getattr 安全地获取属性，如果不存在则返回 None
        finetune_arg = getattr(__C, 'finetune_last_n', None)
        
        # 检查是否禁用预训练权重（当网络连接有问题时）
        use_pretrained = getattr(__C, 'use_pretrained', True)
        img_size = getattr(__C, 'img_size', 640)
        
        # 对于支持预训练权重的模型，传递相应参数
        if __C.model in ['ConvNeXt_Small', 'ConvNeXt_Large', 'ConvNeXt_V2_Tiny']:
            return net(num_classes=__C.num_classes, 
                      finetune_last_n=finetune_arg, 
                      pretrained=use_pretrained)
        # MaxViT 需要传入 img_size 以自动选择合适的模型分辨率
        elif __C.model in ['MaxViT_Small']:
            return net(num_classes=__C.num_classes,
                       finetune_last_n=finetune_arg,
                       pretrained=use_pretrained,
                       img_size=img_size)
        # Swin Transformer V3 需要传入 img_size 以适配窗口/权重
        elif __C.model in ['Swin_V3_Base', 'Swin_V3_Tiny', 'Swin_V3_Base_Pruned', 'Swin_V3_Base_Enhanced']:
            return net(num_classes=__C.num_classes,
                       finetune_last_n=finetune_arg,
                       pretrained=use_pretrained,
                       img_size=img_size)
        # FastViT 需要传入 img_size 和 pretrained 参数
        elif __C.model in ['FastViT_SA24']:
            return net(num_classes=__C.num_classes,
                       finetune_last_n=finetune_arg,
                       pretrained=use_pretrained,
                       img_size=img_size)
        # MNv4_Conv_AA_Large 需要传入 pretrained 参数（使用本地预训练权重）
        elif __C.model in ['MNv4_Conv_AA_Large']:
            return net(num_classes=__C.num_classes,
                       finetune_last_n=finetune_arg,
                       pretrained=use_pretrained)
        # MobileViT 系列需要传入 pretrained 参数
        elif __C.model in ['MobileViT_large', 'MobileViT_large_PAFPN']:
            return net(num_classes=__C.num_classes,
                       finetune_last_n=finetune_arg,
                       pretrained=use_pretrained)
        else:
            # 其他模型保持原有逻辑
            return net(num_classes=__C.num_classes, finetune_last_n=finetune_arg)
    except ImportError as e:
        print(f'the network name you have entered is not supported yet')
        print(f'ImportError details: {e}')
        sys.exit()
    except Exception as e:
        print(f'Error creating network: {type(e).__name__}: {e}')
        print(f'Model: {__C.model}')
        print(f'Trying to create with pretrained={use_pretrained if "use_pretrained" in locals() else "unknown"}')
        sys.exit()

# class config:
#     def __init__(self):
#         self.model = 'lambda_resnet50'
# def count_parameters(net):
#     params = sum([param.nelement() for param in net.parameters() if param.requires_grad])
#     print("Params: %f M" % (params/1000000))
#
# c = config()
# model = get_network(c)
# # model = resnet50(num_classes=100)
# x = torch.randn(1,3,32,32)
# count_parameters(model)
# print(model(x).size())