"""
version 003
"""
import os
import sys
from datetime import datetime
import pandas as pd

# 获取当前脚本文件所在的目录 (modelEnsemble/)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录 (modelEnsemble/ 的上一级目录)
project_root = os.path.dirname(current_dir)
# 将项目根目录添加到 Python 搜索路径的最前面
sys.path.insert(0, project_root)
# ================== 🚀 新增修改区域 END 🚀 ==================

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
from conf import configs # 现在这个导入可以正常工作了



# --- 全局设置 ---
ImageFile.LOAD_TRUNCATED_IMAGES = True

# 新增：定义强共识阶段的置信度阈值
T_UNANIMOUS = 0.4 
# 模拟一个简化的配置对象，用于 get_network
class SimpleConfig:
    def __init__(self, model_name, num_classes):
        self.model = model_name
        self.num_classes = num_classes

# --- 核心功能函数 ---

def load_ensemble_models(model_configs, class_mapping, ckpts_dir, device):
    """加载集成所需的三个模型"""
    models = []
    print("="*60)
    print("🚀 开始加载集成模型...")
    for config in model_configs:
        model_name = config['model_name']
        ckpt_version = config['ckpt_version']
        ckpt_epoch = config['ckpt_epoch']
        ckpt_type = config.get('ckpt_type', 'best') # 默认为 best
        
        print(f"  -> 正在加载模型: {model_name} (版本: {ckpt_version}, Epoch: {ckpt_epoch})")
        
        # 创建一个临时的配置对象来调用 get_network
        temp_config = SimpleConfig(model_name=model_name, num_classes=len(class_mapping))
        net = get_network(temp_config).to(device)
        
        weight_path = os.path.join(ckpts_dir, model_name, ckpt_version, f'{model_name}-{ckpt_epoch}-{ckpt_type}.pth')
        
        if not os.path.exists(weight_path):
            raise FileNotFoundError(f"权重文件未找到: {weight_path}")
            
        try:
            checkpoint = torch.load(weight_path, map_location=device,weights_only=True)
            # 兼容 DataParallel 训练的模型
            new_state_dict = {k.replace("module.", ""): v for k, v in checkpoint.items()}
            net.load_state_dict(new_state_dict, strict=True)
            net.eval()
            models.append(net)
            print(f"  ✅ 模型 {model_name} 加载成功!")
        except Exception as e:
            print(f"  ❌ 加载模型 {model_name} 失败: {e}")
            raise e
            
    if len(models) != 3:
        raise ValueError(f"预期加载3个模型，但实际只成功加载了 {len(models)} 个。")
        
    print("="*60)
    return models

class OpenSetDataset(Dataset):
    """为开集测试定制的数据集"""
    def __init__(self, data_dir, transform, class_to_idx=None, is_known=True):
        self.data_dir = data_dir
        self.transform = transform
        self.is_known = is_known
        self.class_to_idx = class_to_idx
        self.samples = self._find_samples()

    def _find_samples(self):
        samples = []
        for class_name in os.listdir(self.data_dir):
            class_path = os.path.join(self.data_dir, class_name)
            if not os.path.isdir(class_path):
                continue
            
            # 对于已知类别，我们使用真实的标签索引；对于未知类别，我们用-1作为占位符
            target_idx = self.class_to_idx.get(class_name, -1) if self.is_known else -1
            if self.is_known and target_idx == -1:
                print(f"警告: 已知集中的文件夹 '{class_name}' 在 class_mapping.json 中未找到，将被跳过。")
                continue

            for img_name in os.listdir(class_path):
                if img_name.lower().endswith(('.png', '.jpg', '.jpeg','bmp')):
                    samples.append((os.path.join(class_path, img_name), target_idx))
        return samples

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        path, target = self.samples[index]
        try:
            with open(path, 'rb') as f:
                img = Image.open(f).convert('RGB')
        except Exception as e:
            print(f"\n警告: 加载图片失败 {path}. Error: {e}")
            return None, None, None # 返回None以便collate_fn处理

        if self.transform:
            img = self.transform(img)
            
        return img, target, path

def collate_fn_filter_none(batch):
    """过滤掉加载失败的样本"""
    batch = list(filter(lambda x: x[0] is not None, batch))
    return torch.utils.data.dataloader.default_collate(batch) if batch else (None, None, None)


def evaluate_open_set(models, known_loader, unknown_loader, threshold, device, idx_to_class):
    """执行开集评估并计算指标 (两阶段“共识-仲裁”投票版本)"""
    

    # 初始化统计变量
    known_total, known_accepted, known_correct_in_acceptance = 0, 0, 0
    unknown_total, unknown_rejected = 0, 0
    detailed_results = []
    per_class_totals = {}
    per_class_accepted = {}
    
    # 1. 评估已知类别
    print("\n--- 正在评估已知类别 (Known Classes) ---")
    with torch.no_grad():
        for images, true_labels, paths in tqdm(known_loader, desc="处理已知样本"):
            if images is None: continue
            images = images.to(device)

            # 收集每个模型的完整概率向量和原始预测
            all_full_probs = []
            raw_preds_indices = []
            raw_confs = []
            for model in models:
                outputs = model(images)
                probs = F.softmax(outputs, dim=1)
                max_confs, preds = torch.max(probs, dim=1)
                
                all_full_probs.append(probs)
                raw_preds_indices.append(preds)
                raw_confs.append(max_confs)
            
            # 对Batch中的每个样本应用决策逻辑
            for i in range(images.size(0)):
                known_total += 1
                true_label_idx = true_labels[i].item()
                per_class_totals[true_label_idx] = per_class_totals.get(true_label_idx, 0) + 1

                # --- 两阶段决策逻辑 ---
                current_preds = [p[i].item() for p in raw_preds_indices]
                current_confs = [c[i].item() for c in raw_confs]

                # 阶段一：检查强共识
                is_unanimous = (current_preds[0] == current_preds[1] == current_preds[2])
                all_highly_confident = all(c >= T_UNANIMOUS for c in current_confs)

                if is_unanimous and all_highly_confident:
                    # 满足强共识，直接接受
                    final_decision = "ACCEPT"
                    final_prediction_idx = current_preds[0]
                else:
                    # 阶段二：回退到置信度加权仲裁
                    prob_vecs = [p[i] for p in all_full_probs]
                    weights = current_confs
                    sum_of_weights = sum(weights)
                    
                    if sum_of_weights < 1e-9:
                        weighted_avg_probs = torch.mean(torch.stack(prob_vecs), dim=0)
                    else:
                        weighted_avg_probs = sum(p * w for p, w in zip(prob_vecs, weights)) / sum_of_weights
                    
                    final_confidence, final_prediction_idx_tensor = torch.max(weighted_avg_probs, dim=0)
                    
                    # 使用主阈值 T 进行判断
                    if final_confidence.item() >= threshold:
                        final_decision = "ACCEPT"
                        final_prediction_idx = final_prediction_idx_tensor.item()
                    else:
                        final_decision = "REJECT"
                        final_prediction_idx = -1
                
                # --- 更新统计数据 ---
                is_correct = None
                if final_decision == "ACCEPT":
                    known_accepted += 1
                    per_class_accepted[true_label_idx] = per_class_accepted.get(true_label_idx, 0) + 1
                    is_correct = (final_prediction_idx == true_label_idx)
                    if is_correct:
                        known_correct_in_acceptance += 1
                
                detailed_results.append({
                    'image_path': paths[i], 'true_label': idx_to_class.get(true_label_idx, 'N/A'),
                    'decision': final_decision, 'predicted_label': idx_to_class.get(final_prediction_idx, 'N/A'),
                    'is_correct': is_correct, 'model_1_pred': idx_to_class.get(current_preds[0]), 'model_1_conf': f"{current_confs[0]:.4f}",
                    'model_2_pred': idx_to_class.get(current_preds[1]), 'model_2_conf': f"{current_confs[1]:.4f}",
                    'model_3_pred': idx_to_class.get(current_preds[2]), 'model_3_conf': f"{current_confs[2]:.4f}"
                })

    # 2. 评估未知类别 (逻辑完全相同)
    print("\n--- 正在评估未知类别 (Unknown Classes) ---")
    with torch.no_grad():
        for images, _, paths in tqdm(unknown_loader, desc="处理未知样本"):
            if images is None: continue
            images = images.to(device)
            
            all_full_probs, raw_preds_indices, raw_confs = [], [], []
            for model in models:
                outputs = model(images); probs = F.softmax(outputs, dim=1); max_confs, preds = torch.max(probs, dim=1)
                all_full_probs.append(probs); raw_preds_indices.append(preds); raw_confs.append(max_confs)
                
            for i in range(images.size(0)):
                unknown_total += 1
                current_preds = [p[i].item() for p in raw_preds_indices]
                current_confs = [c[i].item() for c in raw_confs]

                # 阶段一
                is_unanimous = (current_preds[0] == current_preds[1] == current_preds[2])
                all_highly_confident = all(c >= T_UNANIMOUS for c in current_confs)

                if is_unanimous and all_highly_confident:
                    final_decision = "ACCEPT"
                    final_prediction_idx = current_preds[0]
                else:
                    # 阶段二
                    prob_vecs = [p[i] for p in all_full_probs]
                    weights = current_confs
                    sum_of_weights = sum(weights)
                    if sum_of_weights < 1e-9: weighted_avg_probs = torch.mean(torch.stack(prob_vecs), dim=0)
                    else: weighted_avg_probs = sum(p * w for p, w in zip(prob_vecs, weights)) / sum_of_weights
                    
                    final_confidence, final_prediction_idx_tensor = torch.max(weighted_avg_probs, dim=0)
                    
                    if final_confidence.item() >= threshold:
                        final_decision = "ACCEPT"
                        final_prediction_idx = final_prediction_idx_tensor.item()
                    else:
                        final_decision = "REJECT"
                        final_prediction_idx = -1

                if final_decision == "REJECT":
                    unknown_rejected += 1

                detailed_results.append({
                    'image_path': paths[i], 'true_label': 'UNKNOWN', 'decision': final_decision,
                    'predicted_label': idx_to_class.get(final_prediction_idx, 'N/A'),
                    'is_correct': None, 'model_1_pred': idx_to_class.get(current_preds[0]), 'model_1_conf': f"{current_confs[0]:.4f}",
                    'model_2_pred': idx_to_class.get(current_preds[1]), 'model_2_conf': f"{current_confs[1]:.4f}",
                    'model_3_pred': idx_to_class.get(current_preds[2]), 'model_3_conf': f"{current_confs[2]:.4f}"
                })
                    
    # 3. 计算并返回最终指标 (此部分无需改动)
    metrics = {}
    frr = (known_total - known_accepted) / known_total if known_total > 0 else 0
    metrics['known_acceptance_rate_1_minus_FRR'] = 1 - frr
    far = (unknown_total - unknown_rejected) / unknown_total if unknown_total > 0 else 0
    metrics['unknown_rejection_rate_1_minus_FAR'] = 1 - far
    metrics['in_domain_accuracy'] = known_correct_in_acceptance / known_accepted if known_accepted > 0 else 0
    metrics['raw_stats'] = {
        'known_total': known_total, 'known_accepted': known_accepted, 'known_rejected': known_total - known_accepted,
        'unknown_total': unknown_total, 'unknown_accepted': unknown_total - unknown_rejected, 'unknown_rejected': unknown_rejected,
        'correctly_classified_when_accepted': known_correct_in_acceptance
    }
    metrics['details'] = detailed_results
    
    per_class_rates = {}
    for class_idx, total_count in per_class_totals.items():
        accepted_count = per_class_accepted.get(class_idx, 0)
        rate = accepted_count / total_count if total_count > 0 else 0
        class_name = idx_to_class.get(class_idx, f"Unknown_Index_{class_idx}")
        per_class_rates[class_name] = {"rate": rate, "accepted": accepted_count, "total": total_count}
    metrics['per_class_acceptance_rates'] = per_class_rates

    return metrics


# --- 主函数 ---
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Open-Set Ensemble Evaluation')
    parser.add_argument('--ensemble_config', type=str, default='model_ensemble_config.json', help='JSON文件，定义三个模型的配置')
    parser.add_argument('--data_dir', type=str, required=True, help='开集测试数据的根目录 (包含 0.已知 和 1.未知 子文件夹)')
    parser.add_argument('--custom_mappings_path', type=str, default='custom_mapping.json', help='类别到索引的JSON映射文件')
    
    # ================= 🚀 关键修正 START 🚀 =================
    # 新增命令行参数，用于明确指定使用哪个数据集配置
    parser.add_argument('--dataset_name', type=str, default='medicine_99', help='要从custom_mapping.json中加载的数据集名称')
    # ================== 🚀 关键修正 END 🚀 ==================

    parser.add_argument('--confidence_threshold', type=float, default=0.9, help='Softmax置信度阈值 T')
    parser.add_argument('--img_size', type=int, default=640, help='图像分辨率')
    parser.add_argument('--batch_size', type=int, default=16, help='批处理大小')
    parser.add_argument('--num_workers', type=int, default=4, help='数据加载器的工作线程数')
    parser.add_argument('--gpu', type=str, default='0', help="使用的GPU, e.g., '0,1,2,...'")
    parser.add_argument('--output_dir', type=str, default=None, help='指定报告保存目录。如果未指定，将自动创建。')
    
    args = parser.parse_args()
    
    # --- 1. 初始化 ---
    configs.run_mode = 'test' 
    configs.path_init() 
    os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # --- 2. 加载配置和模型 ---
    with open(args.ensemble_config, 'r', encoding='utf-8') as f:
        model_configs = json.load(f)
    
    # ================= 🚀 关键修正 START 🚀 =================
    # 使用新的、明确的 --dataset_name 参数来加载正确的类别映射
    with open(args.custom_mappings_path, 'r', encoding='utf-8') as f:
        all_mappings = json.load(f)
    
    dataset_name = args.dataset_name
    if dataset_name not in all_mappings:
        raise ValueError(f"错误: 数据集 '{dataset_name}' 在文件 '{args.custom_mappings_path}' 中未找到。")
    
    class_to_idx = all_mappings[dataset_name]['class_to_idx']
    print(f"✅ 成功加载数据集 '{dataset_name}' 的类别映射，共 {len(class_to_idx)} 类。")
    # ================== 🚀 关键修正 END 🚀 ==================
    
    idx_to_class = {v: k for k, v in class_to_idx.items()}
    
    models = load_ensemble_models(model_configs, class_to_idx, configs.ckpts_dir, device)

    # --- 3. 准备数据加载器 ---
    transform = transforms.Compose([
        transforms.Resize((args.img_size, args.img_size)),
        transforms.ToTensor(),
        transforms.Normalize(configs.mean, configs.std)
    ])
    
    known_data_path = os.path.join(args.data_dir, '0.已知')
    unknown_data_path = os.path.join(args.data_dir, '1.未知')

    if not os.path.isdir(known_data_path): raise FileNotFoundError(f"已知类文件夹不存在: {known_data_path}")
    if not os.path.isdir(unknown_data_path): raise FileNotFoundError(f"未知类文件夹不存在: {unknown_data_path}")

    known_dataset = OpenSetDataset(known_data_path, transform, class_to_idx, is_known=True)
    unknown_dataset = OpenSetDataset(unknown_data_path, transform, is_known=False)
    
    known_loader = DataLoader(known_dataset, batch_size=args.batch_size, num_workers=args.num_workers, collate_fn=collate_fn_filter_none, shuffle=False)
    unknown_loader = DataLoader(unknown_dataset, batch_size=args.batch_size, num_workers=args.num_workers, collate_fn=collate_fn_filter_none, shuffle=False)

    # --- 4. 执行评估 ---
    results = evaluate_open_set(models, known_loader, unknown_loader, args.confidence_threshold, device, idx_to_class)

    # --- 5. 创建输出目录 ---
    output_dir = args.output_dir
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join('modelEnsemble/test/twosteps', f"run_{timestamp}_twosteps{T_UNANIMOUS}_T{args.confidence_threshold}")
        print(f"\n未指定输出目录，将使用默认路径: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    # --- 6. 生成详细的报告内容 ---

    # 格式化模型详情
    model_details_lines = []
    for i, config in enumerate(model_configs):
        model_str = (
            f"    - Model {i+1}: {config['model_name']}"
            f"-v{config['ckpt_version']}"
            f"-e{config['ckpt_epoch']}"
            f"-{config.get('ckpt_type', 'best')}"
        )
        model_details_lines.append(model_str)
    model_details_formatted = "\n".join(model_details_lines)

    # 构建主报告字符串
    report_content = f"""==================================================
📊 开集测试评估报告 (Open-Set Evaluation Report) 置信度加权
==================================================
评估参数:
  - 集成模型配置: {args.ensemble_config}
  - 集成模型详情:
{model_details_formatted}
  - 强共识阈值 (T_UNANIMOUS): {T_UNANIMOUS}
  - 置信度阈值 (T): {args.confidence_threshold}
  - 已知类数据源: {known_data_path}
  - 未知类数据源: {unknown_data_path}
  - 评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
--------------------------------------------------
核心指标:
  ✅ 已知类接受率 (1 - FRR): {results['known_acceptance_rate_1_minus_FRR']:.2%}
     (含义: {results['raw_stats']['known_accepted']} / {results['raw_stats']['known_total']} 个已知样本被正确识别为'已知')

  🛡️ 未知类拒绝率 (1 - FAR): {results['unknown_rejection_rate_1_minus_FAR']:.2%}
     (含义: {results['raw_stats']['unknown_rejected']} / {results['raw_stats']['unknown_total']} 个未知样本被正确识别为'未知')

  🎯 接受域内的闭集准确率: {results['in_domain_accuracy']:.2%}
     (含义: 在所有被接受的已知样本中，{results['raw_stats']['correctly_classified_when_accepted']} / {results['raw_stats']['known_accepted']} 个被正确分类)
==================================================
原始统计数据:
{json.dumps(results['raw_stats'], indent=4)}
"""
    
    # 构建并附加每个已知类别的接受率报告
    per_class_lines = ["\n==================================================", "各已知类别接受率详情 (Per-Class Acceptance Rate)"]
    
    # 按类别名称排序以确保报告顺序一致
    sorted_rates = sorted(results.get('per_class_acceptance_rates', {}).items())

    if not sorted_rates:
        per_class_lines.append("  (无已知类样本进行评估)")
    else:
        for class_name, data in sorted_rates:
            rate_str = f"{data['rate']:.2%}"
            count_str = f"({data['accepted']}/{data['total']})"
            # 使用格式化来对齐文本
            line = f"  - {class_name:<20}: {rate_str:<8} {count_str}"
            per_class_lines.append(line)
    
    per_class_report_str = "\n".join(per_class_lines)
    report_content += per_class_report_str

    # 打印到控制台
    print("\n" + report_content)

    # 保存文本报告
    report_path = os.path.join(output_dir, "evaluation_summary_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    print(f"✅ 汇总评估报告已保存到: {report_path}")

    # 保存详细的CSV报告
    details_df = pd.DataFrame(results['details'])
    csv_path = os.path.join(output_dir, "detailed_evaluation_report.csv")
    details_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"✅ 详细逐样本评估结果已保存到: {csv_path}")