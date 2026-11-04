import os
import torch
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib as mpl
import time 
from datetime import datetime
from datasets.dataset_loader_new import CropLargestContourSquare
from datasets.dataset_loader_new import get_test_loader

mpl.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']
mpl.rcParams['axes.unicode_minus'] = False

from tqdm import tqdm
from PIL import Image, ImageFile
from sklearn.metrics import classification_report, confusion_matrix
from models.get_network import get_network 
import torch.nn.functional as F
from torch.utils.data import DataLoader, SequentialSampler
from torchvision import datasets, transforms
import json

def load_custom_mappings(json_path):
    if not os.path.exists(json_path):
        print(f"警告: 自定义映射文件未找到: {json_path}")
        return {}
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

ImageFile.LOAD_TRUNCATED_IMAGES = True

class ImageFolderWithPaths(datasets.ImageFolder):
    def __getitem__(self, index):
        original_tuple = super(ImageFolderWithPaths, self).__getitem__(index)
        path = self.imgs[index][0]
        image, label = original_tuple
        return image, label, path

def safe_loader(path: str) -> Image.Image:
    try:
        with open(path, 'rb') as f:
            img = Image.open(f)
            return img.convert('RGB')
    except Exception as e:
        print(f"\nWarning: Failed to load image {path}. Error: {e}")
        return None

def collate_fn(batch):
    batch = list(filter(lambda x: x is not None and x[0] is not None, batch))
    if len(batch) == 0:
        return None
    images, labels, paths = zip(*batch)
    images_collated = torch.utils.data.dataloader.default_collate(images)
    labels_collated = torch.utils.data.dataloader.default_collate(labels)
    return images_collated, labels_collated, paths

def plot_confusion_matrix(cm, class_names, output_path):
    plt.figure(figsize=(max(20, len(class_names) // 4), max(20, len(class_names) // 4)))
    sns.set(font_scale=1.0)
    heatmap = sns.heatmap(cm, annot=False, cmap='Blues', 
                          xticklabels=class_names, yticklabels=class_names)
    plt.xlabel('Predicted Label', fontsize=15)
    plt.ylabel('True Label', fontsize=15)
    plt.title('Confusion Matrix', fontsize=20)
    plt.xticks(rotation=90)
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"\nConfusion matrix saved to {output_path}")

def evaluate_generalization_accuracy(__C):
    start_time = time.time()
    output_dir = __C.output_dir
    os.makedirs(output_dir, exist_ok=True)

    data_dir = None
    class_mapping = None

    custom_mappings = load_custom_mappings(__C.custom_mappings_path)
    
    if __C.dataset in custom_mappings:
        print(f"Info: Found '{__C.dataset}' in custom mappings. Using specified test path.")
        dataset_info = custom_mappings[__C.dataset]
        if 'test_path' not in dataset_info:
            raise ValueError(f"'{__C.dataset}' in custom_mappings.json does not have a 'test_path' key.")
        
        data_dir = dataset_info['test_path']
        class_mapping = dataset_info['class_to_idx']
    else:
        print(f"Warning: '{__C.dataset}' not found in custom mappings. Falling back to default data_dir.")
        data_dir = __C.data_dir
        raise ValueError(f"Dataset '{__C.dataset}' requires a definition in {__C.custom_mappings_path} for generalization test.")

    if not data_dir or not class_mapping:
        raise ValueError("Failed to determine data_dir or class_mapping. Aborting.")
    
    print("="*50)
    print("Starting Generalization Evaluation")
    print(f"  - Test Data Source: {data_dir}")
    print(f"  - Results will be saved to: {output_dir}")
    print(f"  - Class Count: {len(class_mapping)}")
    print("="*50)

    index_to_class = {v: k for k, v in class_mapping.items()}
    class_names = list(class_mapping.keys())

    # 使用与训练时相同的数据加载器来确保预处理一致性
    # 这样可以自动支持所有训练时使用的预处理策略（force_resize、ROI、细粒度增强等）
    try:
        from datasets.enhanced_dataset_loader import get_enhanced_transforms
        transform_test = get_enhanced_transforms(__C, is_training=False)
        print("[INFO] 使用与训练时一致的预处理策略（通过 enhanced_dataset_loader）")
    except ImportError:
        # 如果导入失败，回退到原有逻辑
        print("[WARNING] 无法导入 enhanced_dataset_loader，使用简化版预处理策略")
        # 根据训练时的配置选择测试时的数据预处理策略
        if hasattr(__C, 'roi_enable') and __C.roi_enable:
            # 使用ROI聚焦策略的测试变换
            from datasets.enhanced_dataset_loader import ROIExtractTransform
            transform_test = transforms.Compose([
                ROIExtractTransform(
                    edge_low_threshold=getattr(__C, 'roi_edge_low_threshold', getattr(__C, 'roi_edge_low', 50)),
                    edge_high_threshold=getattr(__C, 'roi_edge_high_threshold', getattr(__C, 'roi_edge_high', 150)),
                    min_area_ratio=getattr(__C, 'roi_min_area_ratio', getattr(__C, 'roi_min_area', 0.01))
                ),
                transforms.Resize(__C.img_size),
                transforms.CenterCrop(__C.img_size),
                transforms.ToTensor(),
                transforms.Normalize(__C.mean, __C.std)
            ])
            print(f"[INFO] 测试时使用ROI聚焦策略 (edge_low={getattr(__C, 'roi_edge_low_threshold', getattr(__C, 'roi_edge_low', 50))}, "
                  f"edge_high={getattr(__C, 'roi_edge_high_threshold', getattr(__C, 'roi_edge_high', 150))})")
        else:
            # 标准测试变换（考虑force_resize）
            force_resize_mode = getattr(__C, 'force_resize', False)
            if force_resize_mode:
                transform_test = transforms.Compose([
                    transforms.Resize((__C.img_size, __C.img_size)),
                    transforms.ToTensor(),
                    transforms.Normalize(__C.mean, __C.std)
                ])
                print("[INFO] 测试时使用 force_resize 预处理策略")
            else:
                transform_test = transforms.Compose([
                    transforms.Resize(__C.img_size),
                    transforms.CenterCrop(__C.img_size),
                    transforms.ToTensor(),
                    transforms.Normalize(__C.mean, __C.std)
                ])
                print("[INFO] 测试时使用标准预处理策略 (CenterCrop)")

    test_dataset = ImageFolderWithPaths(root=data_dir, transform=transform_test)
    test_dataset.loader = safe_loader
    original_sample_count = len(test_dataset.samples)
    filtered_samples = [
        (path, class_mapping[os.path.basename(os.path.dirname(path))])
        for path, _ in test_dataset.samples
        if os.path.basename(os.path.dirname(path)) in class_mapping
    ]
    test_dataset.samples = test_dataset.imgs = filtered_samples
    test_dataset.targets = [label for _, label in test_dataset.samples]
    test_dataset.classes = class_names
    test_dataset.class_to_idx = class_mapping
    print(f"Filtered dataset: {len(test_dataset.samples)} / {original_sample_count} samples will be evaluated.")
    if not test_dataset.samples:
        print("Error: No valid images found after filtering. Aborting evaluation.")
        return
    # 优化num_workers以充分利用多GPU（测试时降低worker数量避免资源竞争）
    # 对于测试，使用较少的worker可以避免创建过多进程导致资源竞争
    num_workers = min(getattr(__C, 'num_workers', 4), 4)  # 测试时最多使用4个worker
    
    test_loader = DataLoader(
        test_dataset, batch_size=__C.batch_size, sampler=SequentialSampler(test_dataset),
        num_workers=num_workers, pin_memory=True, drop_last=False, collate_fn=collate_fn
    )

    # --- 3. 模型加载 ---
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    ### MODIFIED START: 动态构建权重文件路径 ###
    if __C.ckpt_type == 'best':
        # 'best' 权重文件名不包含epoch
        file_name = f'{__C.model}-best.pth'
    elif __C.ckpt_type == 'regular':
        # 'regular' 权重文件名包含epoch
        file_name = f'{__C.model}-{__C.ckpt_epoch}-regular.pth'
    else:
        # 此处应不会触发，因为主脚本已做校验
        raise ValueError(f"不支持的 ckpt_type: '{__C.ckpt_type}'")
    
    weight_path = os.path.join(__C.ckpts_dir, __C.model, __C.ckpt_version, file_name)
    ### MODIFIED END ###
    
    if not os.path.exists(weight_path):
        print(f"Error: Weight file not found at {weight_path}\nEvaluation aborted.")
        return
    
    # 先加载权重，确定是否需要DataParallel
    try:
        checkpoint = torch.load(weight_path, map_location=device, weights_only=False)
        
        # 检查checkpoint是否是一个包含多个键的字典
        if isinstance(checkpoint, dict) and 'model' in checkpoint:
            print("[INFO] 检测到包含多个组件的checkpoint文件")
            state_dict = checkpoint['model']
        else:
            state_dict = checkpoint
        
        # 检查权重键名格式，判断是否使用了DataParallel训练
        first_key = list(state_dict.keys())[0] if state_dict else ""
        is_data_parallel_checkpoint = first_key.startswith("module.")
        
        # 处理权重键名：去除'module.'前缀
        new_state_dict = {k.replace("module.", ""): v for k, v in state_dict.items()}
        
        # 创建模型并加载权重
        # 测试时强制禁用预训练权重，因为我们会加载训练好的checkpoint
        original_use_pretrained = getattr(__C, 'use_pretrained', True)
        __C.use_pretrained = False
        net = get_network(__C).to(device)
        __C.use_pretrained = original_use_pretrained  # 恢复原值
        
        net.load_state_dict(new_state_dict, strict=True)
        
        # 加载权重后再应用DataParallel（如果需要多GPU测试）
        if hasattr(__C, 'n_gpu') and __C.n_gpu > 1:
            import torch.nn as nn
            net = nn.DataParallel(net, device_ids=__C.devices)
            print(f"[INFO] 使用 {__C.n_gpu} 个GPU进行加速测试: {__C.devices}")
        
        net.eval()
        print(f"Successfully loaded weights from {weight_path}")
        print(f"Model device: {next(net.parameters()).device}")
    except Exception as e:
        print(f"Error loading state_dict: {e}\nEvaluation aborted.")
        return

    all_preds, all_labels, all_classification_details = [], [], []
    
    # 检查是否启用测试时增强（TTA）
    use_tta = hasattr(__C, 'fine_grain_enable') and __C.fine_grain_enable
    
    if use_tta:
        print("[INFO] 启用测试时增强（TTA），将进行2次预测并平均结果")
        print("      - 原始图像预测")
        print("      - 水平翻转预测")
    else:
        print("[INFO] 使用单次预测模式")
    
    with torch.no_grad():
        for batch in tqdm(test_loader, desc='Generalization Test', unit='batch'):
            if batch is None: continue
            images, labels, paths = batch
            images, labels = images.to(device), labels.to(device)
            
            if use_tta:
                # 使用基础TTA进行2次预测并平均结果
                all_outputs = []
                
                # 1. 原始预测
                outputs = net(images)
                all_outputs.append(outputs)
                
                # 2. 水平翻转预测
                flipped_images = torch.flip(images, dims=[3])  # 水平翻转
                flipped_outputs = net(flipped_images)
                all_outputs.append(flipped_outputs)
                
                # 平均所有预测结果
                outputs = torch.stack(all_outputs).mean(dim=0)
            else:
                outputs = net(images)
            
            probabilities = F.softmax(outputs, dim=1)
            preds = torch.argmax(probabilities, dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            for i in range(len(paths)):
                true_label, pred_label = labels[i].item(), preds[i].item()
                confidence = probabilities[i, pred_label].item()
                all_classification_details.append({
                    'image_path': paths[i],
                    'true_class': index_to_class[true_label],
                    'predicted_class': index_to_class[pred_label],
                    'confidence': f"{confidence:.4f}",
                    'is_correct': true_label == pred_label
                })

    if not all_labels:
        print("Error: Evaluation completed without processing any valid samples.")
        return

    end_time = time.time()
    evaluation_duration = end_time - start_time

    ### MODIFIED START: 在报告头中安全地获取epoch信息 ###
    report_header = (
        f"==================================================\n"
        f" Classification Evaluation Summary\n"
        f"==================================================\n"
        f"Model:                {__C.model}\n"
        f"Checkpoint Version:   {__C.ckpt_version}\n"
        # 使用 getattr 安全地访问 ckpt_epoch，如果不存在（例如 type=best），则显示 N/A
        f"Checkpoint Epoch:     {getattr(__C, 'ckpt_epoch', 'N/A (best)')}\n"
        f"Checkpoint Type:      {__C.ckpt_type}\n"
        f"Evaluation Date:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Total Evaluation Time:{evaluation_duration:.2f} seconds\n"
        f"Total Samples:        {len(all_labels)}\n"
        f"--------------------------------------------------\n\n"
    )
    ### MODIFIED END ###
    
    # 获取实际出现的类别标签，避免类别数量不匹配错误
    unique_labels = sorted(set(all_labels) | set(all_preds))
    actual_class_names = [class_names[i] for i in unique_labels if i < len(class_names)]
    
    report_body_str = classification_report(
        all_labels, all_preds, 
        labels=unique_labels,
        target_names=actual_class_names, 
        zero_division=0, 
        digits=4
    )

    cm = confusion_matrix(all_labels, all_preds, labels=unique_labels)
    cm_df = pd.DataFrame(cm, index=actual_class_names, columns=actual_class_names)
    np.fill_diagonal(cm_df.values, 0)
    top_errors = cm_df.unstack().sort_values(ascending=False)
    top_20_errors = top_errors[top_errors > 0].head(20)
    
    top_errors_header = "\n--- Top 20 Misclassification Report ---\n"
    if top_20_errors.empty:
        top_errors_body = "Congratulations! No misclassifications found."
    else:
        errors_list = ["The most common misclassifications were:"]
        for (predicted_class, true_class), count in top_20_errors.items():
            errors_list.append(f"    - True Class: '{true_class}' was misclassified as '{predicted_class}' {int(count)} time(s).")
        top_errors_body = "\n".join(errors_list)
    top_errors_str = top_errors_header + top_errors_body

    full_report_str = report_header + report_body_str + "\n" + top_errors_str
    
    report_path = os.path.join(output_dir, "classification_summary.txt")
    with open(report_path, "w", encoding='utf-8') as f:
        f.write(full_report_str)
    
    print("\n" + full_report_str)
    print(f"\nComprehensive summary saved to {report_path}")

    details_df = pd.DataFrame(all_classification_details)
    csv_path = os.path.join(output_dir, "detailed_classification_report.csv")
    details_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"Detailed report for each sample saved to {csv_path}")
    
    cm_df_path = os.path.join(output_dir, "confusion_matrix.csv")
    pd.DataFrame(cm, index=actual_class_names, columns=actual_class_names).to_csv(cm_df_path, encoding='utf-8-sig')
    print(f"Confusion matrix data saved to {cm_df_path}")

    print("\nEvaluation finished successfully.")
    print("="*50)