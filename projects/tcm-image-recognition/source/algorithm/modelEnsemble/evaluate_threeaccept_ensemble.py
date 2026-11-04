# ================= 🚀 新增修改区域 START 🚀 =================
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
# 模拟一个简化的配置对象，用于 get_network
class SimpleConfig:
    def __init__(self, model_name, num_classes):
        self.model = model_name
        self.num_classes = num_classes
        # 兼容 get_network 函数
        self.finetune_last_n = None 

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
            checkpoint = torch.load(weight_path, map_location=device, weights_only=True)
            # 兼容 DataParallel 训练的模型
            new_state_dict = {k.replace("module.", ""): v for k, v in checkpoint.items()}
            net.load_state_dict(new_state_dict, strict=True)
            net.eval()
            models.append(net)
            print(f"  ✅ 模型 {model_name} 加载成功!")
        except Exception as e:
            print(f"  ❌ 加载模型 {model_name} 失败: {e}")
            raise e
            
    #if len(models) != 3:
        #raise ValueError(f"预期加载3个模型，但实际只成功加载了 {len(models)} 个。")
    print(f"✅ 共 {len(models)} 个模型加载成功!")    
    print("="*60)
    return models

class OpenSetDataset(Dataset):
    """为开集测试定制的数据集"""
    def __init__(self, data_dir, transform, class_to_idx=None, is_known=True):
        self.data_dir = data_dir
        self.transform = transform
        self.is_known = is_known
        self.class_to_idx = class_to_idx if class_to_idx is not None else {}
        self.samples = self._find_samples()

    def _find_samples(self):
        samples = []
        for class_name in os.listdir(self.data_dir):
            class_path = os.path.join(self.data_dir, class_name)
            if not os.path.isdir(class_path):
                continue
            
            target_idx = self.class_to_idx.get(class_name, -1)
            if self.is_known and target_idx == -1:
                print(f"警告: 已知集中的文件夹 '{class_name}' 在 JSON 中未找到，将被跳过。")
                continue

            for root, _, filenames in os.walk(class_path):
                for filename in filenames:
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                        samples.append((os.path.join(root, filename), target_idx))
        
        print(f"🔎 在路径 '{self.data_dir}' 中通过递归搜索，共找到 {len(samples)} 个样本。")
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
            return None, None, None

        if self.transform:
            img = self.transform(img)
            
        return img, target, path

def collate_fn_filter_none(batch):
    batch = list(filter(lambda x: x[0] is not None, batch))
    return torch.utils.data.dataloader.default_collate(batch) if batch else (None, None, None)


def evaluate_open_set(models, known_loader, unknown_loader, threshold, device, idx_to_class):
    """执行开集评估并计算指标 (一致性优先+多数票表决 版本)"""
    
    known_total, known_accepted, known_correct_in_acceptance = 0, 0, 0
    unknown_total, unknown_rejected = 0, 0
    detailed_results = []
    per_class_totals = {}
    per_class_accepted = {}
    
    print("\n--- 正在评估已知类别 (Known Classes) ---")
    with torch.no_grad():
        for images, true_labels, paths in tqdm(known_loader, desc="处理已知样本"):
            if images is None: continue
            images = images.to(device)

            all_probs, all_preds_indices = [], []
            for model in models:
                outputs = model(images)
                probs = F.softmax(outputs, dim=1)
                max_probs, preds = torch.max(probs, dim=1)
                all_probs.append(max_probs)
                all_preds_indices.append(preds)
            
            for i in range(images.size(0)):
                known_total += 1
                true_label_idx = true_labels[i].item()
                per_class_totals[true_label_idx] = per_class_totals.get(true_label_idx, 0) + 1
                
                preds_indices = [p[i].item() for p in all_preds_indices]
                confs = [c[i].item() for c in all_probs]
                
                # ================= 🚀 核心修改区域 START 🚀 =================
                # --- 一致性优先 + 多数票表决 逻辑 ---
                is_unanimous = (preds_indices[0] == preds_indices[1] == preds_indices[2])

                if is_unanimous:
                    # 规则1：如果三个模型预测完全一致，则无视阈值，直接接受
                    final_decision = "ACCEPT"
                    final_prediction_idx = preds_indices[0]
                else:
                    # 规则2：如果不一致，则回退到原来的多数票表决逻辑
                    final_decision = "REJECT" 
                    final_prediction_idx = -1
                    
                    votes = {}
                    for p_idx, c_val in zip(preds_indices, confs):
                        if c_val >= threshold:
                            votes[p_idx] = votes.get(p_idx, 0) + 1
                    
                    if votes:
                        max_votes = 0
                        best_pred = -1
                        for pred_idx, num_votes in votes.items():
                            if num_votes > max_votes:
                                max_votes = num_votes
                                best_pred = pred_idx
                        
                        if max_votes >= 2:
                            final_decision = "ACCEPT"
                            final_prediction_idx = best_pred
                # ================== 🚀 核心修改区域 END 🚀 =================
                
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
                    'is_correct': is_correct, 'model_1_pred': idx_to_class.get(preds_indices[0]), 'model_1_conf': f"{confs[0]:.4f}",
                    'model_2_pred': idx_to_class.get(preds_indices[1]), 'model_2_conf': f"{confs[1]:.4f}",
                    'model_3_pred': idx_to_class.get(preds_indices[2]), 'model_3_conf': f"{confs[2]:.4f}"
                })

    print("\n--- 正在评估未知类别 (Unknown Classes) ---")
    with torch.no_grad():
        for images, _, paths in tqdm(unknown_loader, desc="处理未知样本"):
            if images is None: continue
            images = images.to(device)
            
            all_probs, all_preds_indices = [], []
            for model in models:
                outputs = model(images); probs = F.softmax(outputs, dim=1); max_probs, preds = torch.max(probs, dim=1)
                all_probs.append(max_probs); all_preds_indices.append(preds)
                
            for i in range(images.size(0)):
                unknown_total += 1
                preds_indices = [p[i].item() for p in all_preds_indices]
                confs = [c[i].item() for c in all_probs]
                
                # ================= 🚀 核心修改区域 START 🚀 =================
                is_unanimous = (preds_indices[0] == preds_indices[1] == preds_indices[2])
                
                if is_unanimous:
                    final_decision = "ACCEPT"
                    final_prediction_idx = preds_indices[0]
                else:
                    final_decision = "REJECT" 
                    final_prediction_idx = -1
                    votes = {}
                    for p_idx, c_val in zip(preds_indices, confs):
                        if c_val >= threshold:
                            votes[p_idx] = votes.get(p_idx, 0) + 1
                    
                    if votes:
                        max_votes = 0
                        best_pred = -1
                        for pred_idx, num_votes in votes.items():
                            if num_votes > max_votes:
                                max_votes = num_votes
                                best_pred = pred_idx
                        
                        if max_votes >= 2:
                            final_decision = "ACCEPT"
                            final_prediction_idx = best_pred
                # ================== 🚀 核心修改区域 END 🚀 =================
                
                if final_decision == "REJECT":
                    unknown_rejected += 1

                detailed_results.append({
                    'image_path': paths[i], 'true_label': 'UNKNOWN', 'decision': final_decision,
                    'predicted_label': idx_to_class.get(final_prediction_idx, 'N/A'),
                    'is_correct': None, 'model_1_pred': idx_to_class.get(preds_indices[0]), 'model_1_conf': f"{confs[0]:.4f}",
                    'model_2_pred': idx_to_class.get(preds_indices[1]), 'model_2_conf': f"{confs[1]:.4f}",
                    'model_3_pred': idx_to_class.get(preds_indices[2]), 'model_3_conf': f"{confs[2]:.4f}"
                })
                    
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
    parser.add_argument('--dataset_name', type=str, default='medicine_99', help='要从custom_mapping.json中加载的数据集名称')
    parser.add_argument('--confidence_threshold', type=float, default=0.9, help='Softmax置信度阈值 T')
    parser.add_argument('--img_size', type=int, default=640, help='图像分辨率')
    parser.add_argument('--batch_size', type=int, default=16, help='批处理大小')
    parser.add_argument('--num_workers', type=int, default=4, help='数据加载器的工作线程数')
    parser.add_argument('--gpu', type=str, default='0', help="使用的GPU, e.g., '0,1,2,...'")
    parser.add_argument('--output_dir', type=str, default=None, help='指定报告保存目录。如果未指定，将自动创建。')
    
    args = parser.parse_args()
    
    configs.run_mode = 'test' 
    configs.path_init() 
    os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    with open(args.ensemble_config, 'r', encoding='utf-8') as f:
        model_configs = json.load(f)
    
    with open(args.custom_mappings_path, 'r', encoding='utf-8') as f:
        all_mappings = json.load(f)
    
    dataset_name = args.dataset_name
    if dataset_name not in all_mappings:
        raise ValueError(f"错误: 数据集 '{dataset_name}' 在文件 '{args.custom_mappings_path}' 中未找到。")
    
    class_to_idx = all_mappings[dataset_name]['class_to_idx']
    print(f"✅ 成功加载数据集 '{dataset_name}' 的类别映射，共 {len(class_to_idx)} 类。")
    
    idx_to_class = {v: k for k, v in class_to_idx.items()}
    
    models = load_ensemble_models(model_configs, class_to_idx, configs.ckpts_dir, device)

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
    unknown_dataset = OpenSetDataset(unknown_data_path, transform, class_to_idx=class_to_idx, is_known=False)
    
    known_loader = DataLoader(known_dataset, batch_size=args.batch_size, num_workers=args.num_workers, collate_fn=collate_fn_filter_none, shuffle=False)
    unknown_loader = DataLoader(unknown_dataset, batch_size=args.batch_size, num_workers=args.num_workers, collate_fn=collate_fn_filter_none, shuffle=False)

    results = evaluate_open_set(models, known_loader, unknown_loader, args.confidence_threshold, device, idx_to_class)

    output_dir = args.output_dir
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join('modelEnsemble/test/threeaccept', f"run_{timestamp}_threeaccept_T{args.confidence_threshold}")
        print(f"\n未指定输出目录，将使用默认路径: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

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

    report_content = f"""==================================================
📊 开集测试评估报告 (Open-Set Evaluation Report)
==================================================
评估参数:
  - 集成模型配置: {args.ensemble_config}
  - 集成模型详情:
{model_details_formatted}
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
    
    per_class_lines = ["\n==================================================", "各已知类别接受率详情 (Per-Class Acceptance Rate)"]
    sorted_rates = sorted(results.get('per_class_acceptance_rates', {}).items())
    if not sorted_rates:
        per_class_lines.append("  (无已知类样本进行评估)")
    else:
        for class_name, data in sorted_rates:
            rate_str = f"{data['rate']:.2%}"
            count_str = f"({data['accepted']}/{data['total']})"
            line = f"  - {class_name:<20}: {rate_str:<8} {count_str}"
            per_class_lines.append(line)
    
    per_class_report_str = "\n".join(per_class_lines)
    report_content += per_class_report_str

    print("\n" + report_content)

    report_path = os.path.join(output_dir, "evaluation_summary_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    print(f"✅ 汇总评估报告已保存到: {report_path}")

    details_df = pd.DataFrame(results['details'])
    csv_path = os.path.join(output_dir, "detailed_evaluation_report.csv")
    details_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"✅ 详细逐样本评估结果已保存到: {csv_path}")