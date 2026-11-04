"""
高级集成评估脚本 v1.0
支持:
1. 多模型集成（不限于3个）
2. 每个模型独立的数据预处理策略（center_crop/force_resize）
3. TTA（Test-Time Augmentation）支持
4. 多种集成策略：置信度加权、投票（3票/4票接受）
5. 闭集/开集测试
"""
import os
import sys
from datetime import datetime
import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

import torch
import torch.nn.functional as F
import numpy as np
import json
import argparse
from PIL import Image, ImageFile
from tqdm import tqdm
from torchvision import transforms
from torch.utils.data import DataLoader, Dataset
from models.get_network import get_network
from conf import configs
from concurrent.futures import ThreadPoolExecutor
import threading

ImageFile.LOAD_TRUNCATED_IMAGES = True


class SimpleConfig:
    def __init__(self, model_name, num_classes):
        self.model = model_name
        self.num_classes = num_classes
        self.finetune_last_n = None


def get_transform(img_size, transform_type, use_enhanced=False, is_tta=False):
    """
    获取数据预处理transform
    
    Args:
        img_size: 图像尺寸
        transform_type: 'center_crop' 或 'force_resize'
        use_enhanced: 是否使用增强预处理
        is_tta: 是否为TTA（水平翻转）
    """
    mean = configs.mean
    std = configs.std
    
    transform_list = []
    
    if transform_type == 'center_crop':
        transform_list.append(transforms.Resize(int(img_size / 0.875)))
        transform_list.append(transforms.CenterCrop(img_size))
    else:  # force_resize
        transform_list.append(transforms.Resize((img_size, img_size)))
    
    if is_tta:
        transform_list.append(transforms.RandomHorizontalFlip(p=1.0))
    
    if use_enhanced:
        # 增强预处理（可以根据需要添加更多增强）
        pass
    
    transform_list.append(transforms.ToTensor())
    transform_list.append(transforms.Normalize(mean, std))
    
    return transforms.Compose(transform_list)


def load_ensemble_models(model_configs, class_mapping, ckpts_dir, device, gpu_ids=None):
    """
    加载集成所需的所有模型
    
    Args:
        gpu_ids: GPU ID列表，如 [0,1,2,3]。如果提供，将模型分配到不同GPU
    """
    models_info = []
    print("=" * 60)
    print("🚀 开始加载集成模型...")
    
    # 如果提供了多个GPU，将模型分配到不同GPU
    if gpu_ids is not None and len(gpu_ids) > 1:
        print(f"📊 使用 {len(gpu_ids)} 个GPU进行模型级并行: {gpu_ids}")
    
    for idx, config in enumerate(model_configs):
        model_name = config['model_name']
        ckpt_version = config['ckpt_version']
        ckpt_epoch = config['ckpt_epoch']
        ckpt_type = config.get('ckpt_type', 'best')
        transform_type = config.get('transform_type', 'force_resize')
        use_tta = config.get('use_tta', False)
        use_enhanced = config.get('use_enhanced', False)
        
        # 选择GPU（如果提供了多个GPU）
        if gpu_ids is not None and len(gpu_ids) > 1:
            model_gpu_id = gpu_ids[idx % len(gpu_ids)]
            model_device = torch.device(f'cuda:{model_gpu_id}')
        else:
            model_device = device
        
        print(f"  -> 正在加载模型: {model_name}")
        print(f"     版本: {ckpt_version}, Epoch: {ckpt_epoch}, Type: {ckpt_type}")
        print(f"     Transform: {transform_type}, TTA: {use_tta}, Enhanced: {use_enhanced}")
        print(f"     GPU: {model_device}")
        
        # 创建模型（禁用预训练权重，因为我们会加载训练好的 checkpoint）
        temp_config = SimpleConfig(model_name=model_name, num_classes=len(class_mapping))
        temp_config.use_pretrained = False  # 禁用预训练权重
        net = get_network(temp_config).to(model_device)
        
        # 加载权重
        weight_path = os.path.join(ckpts_dir, model_name, ckpt_version, 
                                   f'{model_name}-{ckpt_epoch}-{ckpt_type}.pth')
        
        if not os.path.exists(weight_path):
            raise FileNotFoundError(f"权重文件未找到: {weight_path}")
        
        try:
            checkpoint = torch.load(weight_path, map_location=model_device, weights_only=False)
            
            # 处理包含多个组件的 checkpoint
            if isinstance(checkpoint, dict) and 'model' in checkpoint:
                print(f"     检测到多组件 checkpoint，提取 'model' 部分")
                state_dict = checkpoint['model']
            else:
                state_dict = checkpoint
            
            # 处理 DataParallel 训练的模型（移除 'module.' 前缀）
            new_state_dict = {k.replace("module.", ""): v for k, v in state_dict.items()}
            
            net.load_state_dict(new_state_dict, strict=True)
            net.eval()
            
            models_info.append({
                'model': net,
                'name': model_name,
                'transform_type': transform_type,
                'use_tta': use_tta,
                'use_enhanced': use_enhanced,
                'config': config,
                'device': model_device  # 记录模型所在的GPU
            })
            print(f"  ✅ 模型 {model_name} 加载成功!")
        except Exception as e:
            print(f"  ❌ 加载模型 {model_name} 失败: {e}")
            raise e
    
    print(f"✅ 共 {len(models_info)} 个模型加载成功!")
    print("=" * 60)
    return models_info


class ClosedSetDataset(Dataset):
    """闭集测试数据集"""
    def __init__(self, data_dir, class_to_idx):
        self.data_dir = data_dir
        self.class_to_idx = class_to_idx
        self.samples = self._find_samples()
    
    def _find_samples(self):
        samples = []
        for class_name in os.listdir(self.data_dir):
            class_path = os.path.join(self.data_dir, class_name)
            if not os.path.isdir(class_path):
                continue
            
            target_idx = self.class_to_idx.get(class_name, -1)
            if target_idx == -1:
                print(f"警告: 文件夹 '{class_name}' 不在类别映射中，将被跳过。")
                continue
            
            for root, _, filenames in os.walk(class_path):
                for filename in filenames:
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                        samples.append((os.path.join(root, filename), target_idx, class_name))
        
        print(f"🔎 在路径 '{self.data_dir}' 中共找到 {len(samples)} 个样本。")
        return samples
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, index):
        path, target, class_name = self.samples[index]
        try:
            with open(path, 'rb') as f:
                img = Image.open(f).convert('RGB')
        except Exception as e:
            print(f"\n警告: 加载图片失败 {path}. Error: {e}")
            return None, None, None, None
        
        return img, target, path, class_name


def collate_fn_filter_none(batch):
    batch = list(filter(lambda x: x[0] is not None, batch))
    if not batch:
        return None, None, None, None
    
    images, targets, paths, class_names = zip(*batch)
    return list(images), torch.tensor(targets), list(paths), list(class_names)


def predict_single_model(model_info, images, img_size):
    """
    单个模型的预测函数（用于多线程）
    
    Returns:
        probs: [batch_size, num_classes] probability tensor (on CPU)
        preds: [batch_size] prediction indices (on CPU)
        confs: [batch_size] confidence scores (on CPU)
    """
    model = model_info['model']
    model_device = model_info['device']
    transform_type = model_info['transform_type']
    use_tta = model_info['use_tta']
    use_enhanced = model_info['use_enhanced']
    
    # 准备transform
    transform = get_transform(img_size, transform_type, use_enhanced, is_tta=False)
    
    # 转换图像并发送到模型所在的GPU
    batch_tensors = []
    for img in images:
        img_tensor = transform(img)
        batch_tensors.append(img_tensor)
    batch_tensor = torch.stack(batch_tensors).to(model_device)
    
    # 预测
    with torch.no_grad():
        outputs = model(batch_tensor)
        probs = F.softmax(outputs, dim=1)
        
        # 如果使用TTA
        if use_tta:
            transform_flip = get_transform(img_size, transform_type, use_enhanced, is_tta=True)
            batch_tensors_flip = []
            for img in images:
                img_tensor_flip = transform_flip(img)
                batch_tensors_flip.append(img_tensor_flip)
            batch_tensor_flip = torch.stack(batch_tensors_flip).to(model_device)
            
            outputs_flip = model(batch_tensor_flip)
            probs_flip = F.softmax(outputs_flip, dim=1)
            
            # 平均两次预测
            probs = (probs + probs_flip) / 2.0
        
        max_probs, preds = torch.max(probs, dim=1)
        # 将结果移回CPU以节省GPU显存
        return probs.cpu(), preds.cpu(), max_probs.cpu()


def predict_with_models(models_info, images, img_size, use_parallel=True):
    """
    使用多个模型对图像进行预测（支持真正的并行推理）
    
    Args:
        use_parallel: 是否使用多线程并行（默认True）
    
    Returns:
        all_probs: List of [batch_size, num_classes] probability tensors (on CPU)
        all_preds: List of [batch_size] prediction indices (on CPU)
        all_confs: List of [batch_size] confidence scores (on CPU)
    """
    if use_parallel and len(models_info) > 1:
        # 使用多线程并行推理
        with ThreadPoolExecutor(max_workers=len(models_info)) as executor:
            # 提交所有模型的推理任务
            futures = [
                executor.submit(predict_single_model, model_info, images, img_size)
                for model_info in models_info
            ]
            
            # 收集结果
            all_probs, all_preds, all_confs = [], [], []
            for future in futures:
                probs, preds, confs = future.result()
                all_probs.append(probs)
                all_preds.append(preds)
                all_confs.append(confs)
    else:
        # 串行推理（用于调试或单模型）
        all_probs, all_preds, all_confs = [], [], []
        for model_info in models_info:
            probs, preds, confs = predict_single_model(model_info, images, img_size)
            all_probs.append(probs)
            all_preds.append(preds)
            all_confs.append(confs)
    
    return all_probs, all_preds, all_confs


def ensemble_strategy_weighted(all_probs, all_confs):
    """置信度加权集成策略"""
    weighted_probs_list = []
    
    for i in range(all_probs[0].size(0)):  # For each sample in batch
        prob_vecs = [p[i] for p in all_probs]
        weights = [c[i].item() for c in all_confs]
        
        sum_of_weights = sum(weights)
        if sum_of_weights < 1e-9:
            weighted_avg_probs = torch.mean(torch.stack(prob_vecs), dim=0)
        else:
            weighted_avg_probs = sum(p * w for p, w in zip(prob_vecs, weights)) / sum_of_weights
        
        weighted_probs_list.append(weighted_avg_probs)
    
    weighted_probs = torch.stack(weighted_probs_list)
    final_confs, final_preds = torch.max(weighted_probs, dim=1)
    
    return final_preds, final_confs


def ensemble_strategy_voting(all_preds, all_confs, threshold, min_votes=3):
    """
    置信度阈值投票策略
    
    Args:
        min_votes: 最少需要多少票才接受（3票或4票）
    """
    final_preds_list = []
    final_confs_list = []
    
    for i in range(all_preds[0].size(0)):  # For each sample
        preds_indices = [p[i].item() for p in all_preds]
        confs = [c[i].item() for c in all_confs]
        
        # 统计投票
        votes = {}
        for pred_idx, conf in zip(preds_indices, confs):
            if conf >= threshold:
                votes[pred_idx] = votes.get(pred_idx, 0) + 1
        
        # 找出得票最多的类别
        if votes:
            max_votes = max(votes.values())
            if max_votes >= min_votes:
                # 获胜的类别
                for pred_idx, num_votes in votes.items():
                    if num_votes == max_votes:
                        final_pred = pred_idx
                        break
                
                # 计算该类别的平均置信度
                conf_sum = sum(confs[j] for j, p in enumerate(preds_indices) if p == final_pred)
                conf_count = sum(1 for p in preds_indices if p == final_pred)
                final_conf = conf_sum / conf_count if conf_count > 0 else 0.0
            else:
                final_pred = -1
                final_conf = 0.0
        else:
            final_pred = -1
            final_conf = 0.0
        
        final_preds_list.append(final_pred)
        final_confs_list.append(final_conf)
    
    return torch.tensor(final_preds_list), torch.tensor(final_confs_list)


def evaluate_closed_set(models_info, data_loader, idx_to_class, 
                       ensemble_strategy='weighted', threshold=0.9, min_votes=3):
    """执行闭集评估"""
    
    total_samples = 0
    correct_samples = 0
    detailed_results = []
    per_class_correct = {}
    per_class_total = {}
    
    print(f"\n--- 正在评估闭集（策略: {ensemble_strategy}）---")
    print(f"    模型分布:")
    for i, model_info in enumerate(models_info):
        print(f"      模型{i+1} ({model_info['name']}): {model_info['device']}, TTA: {model_info['use_tta']}")
    
    with torch.no_grad():
        for images, true_labels, paths, class_names in tqdm(data_loader, desc="处理样本"):
            if images is None:
                continue
            
            # 使用所有模型进行预测（模型级并行）
            all_probs, all_preds, all_confs = predict_with_models(
                models_info, images, configs.img_size
            )
            
            # 将结果移到CPU进行集成（节省GPU显存）
            all_probs = [p if p.device.type == 'cpu' else p.cpu() for p in all_probs]
            all_preds = [p if p.device.type == 'cpu' else p.cpu() for p in all_preds]
            all_confs = [c if c.device.type == 'cpu' else c.cpu() for c in all_confs]
            
            # 应用集成策略
            if ensemble_strategy == 'weighted':
                final_preds, final_confs = ensemble_strategy_weighted(all_probs, all_confs)
            elif ensemble_strategy == 'voting':
                final_preds, final_confs = ensemble_strategy_voting(
                    all_preds, all_confs, threshold, min_votes
                )
            else:
                raise ValueError(f"未知的集成策略: {ensemble_strategy}")
            
            # 统计结果
            for i in range(len(images)):
                total_samples += 1
                true_label_idx = true_labels[i].item()
                final_pred_idx = final_preds[i].item()
                final_conf = final_confs[i].item()
                
                per_class_total[true_label_idx] = per_class_total.get(true_label_idx, 0) + 1
                
                is_correct = (final_pred_idx == true_label_idx)
                if is_correct:
                    correct_samples += 1
                    per_class_correct[true_label_idx] = per_class_correct.get(true_label_idx, 0) + 1
                
                # 收集每个模型的原始预测
                model_preds = []
                model_confs = []
                for j, model_info in enumerate(models_info):
                    pred_idx = all_preds[j][i].item()
                    conf = all_confs[j][i].item()
                    model_preds.append(idx_to_class.get(pred_idx, 'N/A'))
                    model_confs.append(f"{conf:.4f}")
                
                # 记录详细信息
                result_dict = {
                    'image_path': paths[i],
                    'true_label': class_names[i],
                    'predicted_label': idx_to_class.get(final_pred_idx, 'REJECTED' if final_pred_idx == -1 else 'N/A'),
                    'final_confidence': f"{final_conf:.4f}",
                    'is_correct': is_correct
                }
                
                # 添加每个模型的预测
                for j, model_info in enumerate(models_info):
                    result_dict[f'model_{j+1}_name'] = model_info['name']
                    result_dict[f'model_{j+1}_pred'] = model_preds[j]
                    result_dict[f'model_{j+1}_conf'] = model_confs[j]
                
                detailed_results.append(result_dict)
    
    # 计算指标
    overall_accuracy = correct_samples / total_samples if total_samples > 0 else 0
    
    # 计算每个类别的准确率
    per_class_accuracy = {}
    for class_idx in per_class_total.keys():
        correct = per_class_correct.get(class_idx, 0)
        total = per_class_total[class_idx]
        accuracy = correct / total if total > 0 else 0
        class_name = idx_to_class.get(class_idx, f"Unknown_{class_idx}")
        per_class_accuracy[class_name] = {
            'accuracy': accuracy,
            'correct': correct,
            'total': total
        }
    
    metrics = {
        'overall_accuracy': overall_accuracy,
        'total_samples': total_samples,
        'correct_samples': correct_samples,
        'per_class_accuracy': per_class_accuracy,
        'details': detailed_results
    }
    
    return metrics


def main():
    parser = argparse.ArgumentParser(description='高级集成评估')
    parser.add_argument('--ensemble_config', type=str, required=True,
                       help='集成模型配置JSON文件')
    parser.add_argument('--data_dir', type=str, required=True,
                       help='测试数据根目录')
    parser.add_argument('--custom_mappings_path', type=str, default='custom_mapping.json',
                       help='类别映射JSON文件')
    parser.add_argument('--dataset_name', type=str, default='medicine_200',
                       help='数据集名称')
    parser.add_argument('--ensemble_strategy', type=str, default='weighted',
                       choices=['weighted', 'voting'],
                       help='集成策略: weighted（置信度加权）或 voting（投票）')
    parser.add_argument('--confidence_threshold', type=float, default=0.9,
                       help='投票策略的置信度阈值')
    parser.add_argument('--min_votes', type=int, default=3,
                       help='投票策略最少需要的票数（3或4）')
    parser.add_argument('--img_size', type=int, default=640,
                       help='图像分辨率')
    parser.add_argument('--batch_size', type=int, default=16,
                       help='批处理大小')
    parser.add_argument('--num_workers', type=int, default=4,
                       help='数据加载器工作线程数')
    parser.add_argument('--gpu', type=str, default='0',
                       help='使用的GPU，多GPU用逗号分隔（如：0,1,2,3）')
    parser.add_argument('--output_dir', type=str, default=None,
                       help='输出目录')
    
    args = parser.parse_args()
    
    # 初始化
    configs.run_mode = 'test'
    configs.path_init()
    configs.img_size = args.img_size
    
    # 解析GPU配置
    gpu_ids = [int(x) for x in args.gpu.split(',') if x.strip()]
    os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    
    # 如果有多个GPU，重新映射GPU ID（因为CUDA_VISIBLE_DEVICES会重新编号）
    if len(gpu_ids) > 1:
        gpu_ids = list(range(len(gpu_ids)))  # 重新映射为 0,1,2,3...
        print(f"🔧 检测到 {len(gpu_ids)} 个GPU，启用模型级并行")
    
    # 加载配置
    with open(args.ensemble_config, 'r', encoding='utf-8') as f:
        model_configs = json.load(f)
    
    with open(args.custom_mappings_path, 'r', encoding='utf-8') as f:
        all_mappings = json.load(f)
    
    if args.dataset_name not in all_mappings:
        raise ValueError(f"数据集 '{args.dataset_name}' 不在映射文件中")
    
    class_to_idx = all_mappings[args.dataset_name]['class_to_idx']
    idx_to_class = {v: k for k, v in class_to_idx.items()}
    print(f"✅ 加载数据集 '{args.dataset_name}'，共 {len(class_to_idx)} 类")
    
    # 加载模型（支持多GPU）
    models_info = load_ensemble_models(model_configs, class_to_idx, configs.ckpts_dir, device, gpu_ids)
    
    # 准备数据集
    dataset = ClosedSetDataset(args.data_dir, class_to_idx)
    data_loader = DataLoader(
        dataset, 
        batch_size=args.batch_size, 
        num_workers=args.num_workers,
        collate_fn=collate_fn_filter_none,
        shuffle=False
    )
    
    # 执行评估
    results = evaluate_closed_set(
        models_info, data_loader, idx_to_class,
        ensemble_strategy=args.ensemble_strategy,
        threshold=args.confidence_threshold,
        min_votes=args.min_votes
    )
    
    # 创建输出目录
    if args.output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        strategy_name = f"{args.ensemble_strategy}"
        if args.ensemble_strategy == 'voting':
            strategy_name += f"_T{args.confidence_threshold}_V{args.min_votes}"
        args.output_dir = os.path.join('modelEnsemble/test', f"run_{timestamp}_{strategy_name}")
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 生成报告
    model_details = []
    for i, config in enumerate(model_configs):
        model_str = (
            f"    Model {i+1}: {config['model_name']} "
            f"(v{config['ckpt_version']}, e{config['ckpt_epoch']}, "
            f"{config.get('transform_type', 'force_resize')}, "
            f"TTA: {config.get('use_tta', False)})"
        )
        model_details.append(model_str)
    
    report = f"""==================================================
📊 闭集测试评估报告 (Closed-Set Evaluation Report)
==================================================
评估参数:
  - 集成模型配置: {args.ensemble_config}
  - 集成模型详情:
{chr(10).join(model_details)}
  - 集成策略: {args.ensemble_strategy}
  - 数据集: {args.dataset_name} ({len(class_to_idx)} 类)
  - 测试数据路径: {args.data_dir}
  - 评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
--------------------------------------------------
核心指标:
  🎯 总体准确率: {results['overall_accuracy']:.2%}
     ({results['correct_samples']} / {results['total_samples']} 样本正确分类)
==================================================
"""
    
    # 添加每个类别的准确率
    report += "\n各类别准确率详情:\n"
    sorted_acc = sorted(results['per_class_accuracy'].items())
    for class_name, data in sorted_acc:
        acc_str = f"{data['accuracy']:.2%}"
        count_str = f"({data['correct']}/{data['total']})"
        report += f"  - {class_name:<25}: {acc_str:<8} {count_str}\n"
    
    print("\n" + report)
    
    # 保存报告
    report_path = os.path.join(args.output_dir, "evaluation_summary.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"✅ 报告已保存到: {report_path}")
    
    # 保存详细CSV
    details_df = pd.DataFrame(results['details'])
    csv_path = os.path.join(args.output_dir, "detailed_results.csv")
    details_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"✅ 详细结果已保存到: {csv_path}")


if __name__ == '__main__':
    main()

