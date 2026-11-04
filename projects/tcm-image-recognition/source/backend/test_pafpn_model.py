#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
菝葜类模型批量测试脚本

功能:
1. 从指定文件夹加载所有图片进行测试。
2. 输出每张图片的预测类别和置信度。
3. 所有配置项集中管理，方便修改。
"""
import os
import sys
import torch
import time
from PIL import Image
from torchvision import transforms

# 确保脚本可以找到nets和config目录
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from nets.mobilevit_large_pafpn import MobileViT_large_PAFPN
    # 假设您的配置文件在 'config' 目录下
    # from config.model_config import NORMALIZATION_MEAN, NORMALIZATION_STD, IMAGE_SIZE_CONFIG
except ImportError:
    print("错误：请确保您的项目路径正确，并且 nets/ 和 config/ 目录可访问。")
    sys.exit(1)


# ==============================================================================
# 1. 配置区域 (请在此处修改所有参数)
# ==============================================================================
CONFIG = {
    # 模型权重文件的路径
    "model_path": r"checkpoints/测试权重/MobileViT_large_PAFPN-2-regular.pth",

    # 包含待测试图片的文件夹路径
    "image_folder_path": os.environ.get("TCM_TEST_IMAGE_DIR", "data/test-images"),

    # 类别索引到类别名称的映射 (请根据您的模型训练情况修改)
    # 键是模型的输出索引(0, 1, 2...)，值是对应的类别名
    "class_mapping": {
        0: "菝葜",
        1: "肖菝葜",
        # 如果有更多子类，请继续添加
        # 2: "其他菝葜",
        # 3: "另一品种",
    },

    # 模型输入图像的尺寸 (请确保与训练时一致)
    "image_size": (640, 640), # 例如: (640, 640) 或从 IMAGE_SIZE_CONFIG["pafpn"] 获取

    # 图像归一化参数 (请确保与训练时一致)
    "normalization_mean": [0.5070751592371323, 0.48654887331495095, 0.4409178433670343], # 或从 NORMALIZATION_MEAN 获取
    "normalization_std": [0.2673342858792401, 0.2564384629170883, 0.27615047132568404],    # 或从 NORMALIZATION_STD 获取
}
# ==============================================================================


def load_model_and_transform(config):
    """
    根据配置加载模型和图像转换器。
    """
    model_path = config["model_path"]
    num_classes = len(config["class_mapping"])
    
    print("--- 模型加载开始 ---")
    if not os.path.exists(model_path):
        print(f"❌ 错误：模型文件不存在: {model_path}")
        return None, None, None

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"使用设备: {device}")
    
    try:
        # 1. 创建模型实例
        model = MobileViT_large_PAFPN(num_classes=num_classes, pretrained=False)
        
        # 2. 加载模型权重
        print(f"正在从 {model_path} 加载权重...")
        checkpoint = torch.load(model_path, map_location=device)
        
        # 处理可能的 'module.' 前缀
        state_dict = {k.replace("module.", ""): v for k, v in checkpoint.items()}
        model.load_state_dict(state_dict, strict=False)
        model.eval()
        model.to(device)
        print("✅ 模型加载成功！")

        # 3. 创建图像转换器
        transform = transforms.Compose([
            transforms.Resize(config["image_size"]),
            transforms.ToTensor(),
            transforms.Normalize(mean=config["normalization_mean"], std=config["normalization_std"])
        ])
        print("✅ 图像转换器创建成功！")
        print("--- 模型加载完成 ---\n")
        
        return model, transform, device

    except Exception as e:
        print(f"❌ 模型或转换器加载失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


def predict_single_image(model, image_path, transform, device, class_mapping):
    """
    对单张图片进行预测。
    """
    try:
        # 加载并预处理图片
        image = Image.open(image_path).convert("RGB")
        input_tensor = transform(image).unsqueeze(0).to(device)

        # 执行预测
        with torch.no_grad():
            output = model(input_tensor)
            probabilities = torch.nn.functional.softmax(output, dim=1)
            
            # 获取最高概率的预测结果
            confidence, predicted_idx = torch.max(probabilities, 1)
            
            predicted_idx = predicted_idx.item()
            confidence = confidence.item()
            
            # 映射到类别名称
            predicted_class = class_mapping.get(predicted_idx, f"未知类别索引 {predicted_idx}")
            
            return predicted_class, confidence

    except Exception as e:
        return f"预测失败: {e}", 0.0


def test_folder(config):
    """
    测试指定文件夹内的所有图片。
    """
    image_folder = config["image_folder_path"]
    class_mapping = config["class_mapping"]

    # 1. 加载模型和转换器
    model, transform, device = load_model_and_transform(config)
    if not model:
        return

    # 2. 检查图片文件夹
    if not os.path.isdir(image_folder):
        print(f"❌ 错误：图片文件夹不存在: {image_folder}")
        return

    # 3. 获取所有图片文件
    image_files = [f for f in os.listdir(image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not image_files:
        print(f"⚠️ 警告：在文件夹 {image_folder} 中未找到任何图片文件。")
        return

    print(f"--- 开始批量预测 ({len(image_files)} 张图片) ---")
    start_time = time.time()
    
    # 4. 遍历并预测每张图片
    for i, filename in enumerate(image_files):
        image_path = os.path.join(image_folder, filename)
        predicted_class, confidence = predict_single_image(model, image_path, transform, device, class_mapping)
        
        print(f"({i+1}/{len(image_files)}) 文件: {filename:<40} -> 预测类别: {predicted_class} (置信度: {confidence:.4f})")
    
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / len(image_files) if image_files else 0
    
    print("\n--- 预测完成 ---")
    print(f"总计处理图片: {len(image_files)} 张")
    print(f"总耗时: {total_time:.2f} 秒")
    print(f"平均每张图片耗时: {avg_time:.4f} 秒")
    print("🎉 批量测试结束。")


if __name__ == "__main__":
    print("=" * 60)
    print("         菝葜类 PAFPN 模型批量测试工具")
    print("=" * 60)
    
    # 直接调用主函数，使用顶部的CONFIG进行测试
    test_folder(CONFIG)
