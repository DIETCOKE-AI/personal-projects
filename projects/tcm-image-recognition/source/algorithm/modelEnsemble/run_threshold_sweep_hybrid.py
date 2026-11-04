# File: modelEnsemble/run_threshold_sweep_hybrid.py
# Version: 11.0 (Flexible N-Model Ensemble with Per-Class Reporting)
# Description: A high-performance script for ensemble analysis that supports
#              N-model ensembles with a configurable vote threshold (n),
#              while maintaining parallel data processing for speed.
#              Now includes detailed per-class report generation for multiple thresholds.

import os
import sys
from datetime import datetime
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import json
import argparse
from tqdm import tqdm
from PIL import Image
import math

# --- PyTorch Imports ---
from torch.utils.data import Dataset, DataLoader

# --- Plotting Imports ---
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

# --- 项目路径与模块导入 ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from conf import configs
from torchvision import transforms
from models.get_network import get_network

# ==============================================================================
# 🚀 全局配置定义
# ==============================================================================
# 注意：标签现在会根据模型数量和投票阈值动态生成
STRATEGY_CONFIGS = {
    'Voting':        {'name': 'voting', 'params': {}},
    'Weighting':     {'name': 'weighting', 'params': {}},
    'ThreeAccept':   {'name': 'three_accept', 'params': {}},
    'TwoSteps_T0.4': {'name': 'two_steps', 'params': {'t_unanimous': 0.4}},
}

# PLOT_CONFIGS 将在主函数中动态生成
PLOT_CONFIGS = {}

# ==============================================================================
# ==============================================================================

class HybridOpenSetDataset(Dataset):
    """高性能混合模式数据集。"""
    def __init__(self, data_dir, transforms_dict, class_to_idx=None, is_known=True):
        self.data_dir = data_dir
        self.transforms_dict = transforms_dict
        self.is_known = is_known
        self.class_to_idx = class_to_idx if class_to_idx is not None else {}
        self.samples = self._find_samples()

    def _find_samples(self):
        samples = []
        if not os.path.isdir(self.data_dir):
            print(f"❌ 错误: 数据目录不存在 -> {self.data_dir}")
            return samples
        for class_name in os.listdir(self.data_dir):
            class_path = os.path.join(self.data_dir, class_name)
            if not os.path.isdir(class_path): continue
            target_idx = self.class_to_idx.get(class_name, -1)
            if self.is_known and target_idx == -1:
                print(f"警告: 已知集中的文件夹 '{class_name}' 在 JSON 映射中未找到，将被跳过。")
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
        processed_images = {key: trans(img) for key, trans in self.transforms_dict.items()}
        return processed_images, target, path

def collate_fn_hybrid(batch):
    """为高性能混合模式定制的collate_fn。"""
    batch = list(filter(lambda x: x is not None and x[0] is not None, batch))
    if not batch:
        return None, None, None
    images_dict_list, labels, paths = zip(*batch)
    collated_images = {}
    transform_keys = images_dict_list[0].keys()
    for key in transform_keys:
        tensors_for_key = [d[key] for d in images_dict_list]
        collated_images[key] = torch.utils.data.dataloader.default_collate(tensors_for_key)
    collated_labels = torch.utils.data.dataloader.default_collate(labels)
    return collated_images, collated_labels, list(paths)

def load_ensemble_models(model_configs, num_classes, ckpts_dir, device):
    """根据配置加载集成模型。"""
    models = []
    print("="*60 + "\n🚀 开始加载集成模型...")
    
    # 检查是否有多个GPU可用
    gpu_count = torch.cuda.device_count()
    use_multi_gpu = gpu_count > 1
    
    if use_multi_gpu:
        print(f"💻 检测到 {gpu_count} 个GPU，将使用DataParallel进行多 GPU 并行推理")
    else:
        print(f"💻 检测到 {gpu_count} 个GPU，使用单GPU模式")
    
    for config in model_configs:
        model_name = config['model_name']
        ckpt_version = config['ckpt_version']
        ckpt_epoch = config['ckpt_epoch']
        ckpt_type = config.get('ckpt_type', 'regular')
        
        print(f"  -> 正在加载模型: {model_name} (版本: {ckpt_version}, Epoch: {ckpt_epoch})")
        ckpt_path = os.path.join(ckpts_dir, model_name, str(ckpt_version), f'{model_name}-{ckpt_epoch}-{ckpt_type}.pth')
        
        if not os.path.exists(ckpt_path):
            print(f"  ❌ 错误: 权重文件未找到: {ckpt_path}"); continue
        try:
            config_obj = argparse.Namespace(model=model_name, num_classes=num_classes, img_size=640)
            net = get_network(config_obj).to(device)
            
            # 如果有多个GPU，使用DataParallel
            if use_multi_gpu:
                net = nn.DataParallel(net)
                print(f"    ✓ 已将模型 {model_name} 包装为DataParallel（使用 {gpu_count} 个GPU）")
            
            checkpoint = torch.load(ckpt_path, map_location=device, weights_only=True)
            
            # 检查是否是包含'model'键的完整checkpoint
            if isinstance(checkpoint, dict) and 'model' in checkpoint:
                state_dict = checkpoint['model']
            else:
                state_dict = checkpoint
            
            # 修复权重键 - 处理'module.model.xxx'的情况
            fixed_state_dict = {}
            for key, value in state_dict.items():
                if key.startswith('module.model.'):
                    # 移除'module.'前缀，变为'model.xxx'
                    fixed_key = key[7:]
                    fixed_state_dict[fixed_key] = value
                else:
                    fixed_state_dict[key] = value
            
            # 检查是否是数据并行的权重
            is_data_parallel_ckpt = any(k.startswith('module.') for k in fixed_state_dict.keys())
            
            # 根据模型类型加载权重
            if isinstance(net, nn.DataParallel):
                if not is_data_parallel_ckpt:
                    net.load_state_dict({f'module.{k}': v for k, v in fixed_state_dict.items()}, strict=False)
                else:
                    net.load_state_dict(fixed_state_dict, strict=False)
            else:
                if is_data_parallel_ckpt:
                    net.load_state_dict({k.replace("module.", ""): v for k, v in fixed_state_dict.items()}, strict=False)
                else:
                    net.load_state_dict(fixed_state_dict, strict=False)
            net.eval()
            models.append(net)
            print(f"  ✅ 模型 {model_name} 加载成功!")
        except Exception as e:
            print(f"  ❌ 加载模型 {model_name} 失败: {e}")
    if len(models) != len(model_configs):
        raise ValueError(f"预期加载 {len(model_configs)} 个模型，但只成功加载了 {len(models)} 个。")
    print(f"✅ 共 {len(models)} 个模型加载成功!\n" + "="*60)
    return models

def generate_report_header(model_configs, vote_threshold):
    """根据模型配置列表，生成一份格式化的、用于报告的文本头。"""
    header_lines = [
        "==================================================",
        "           Ensemble Configuration Summary",
        "==================================================",
        f"Evaluation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total Models:    {len(model_configs)}",
        f"Vote Threshold:  {vote_threshold} (n)",
        "--------------------------------------------------",
    ]
    for i, config in enumerate(model_configs):
        model_name = config.get('model_name', 'N/A')
        ckpt_version = config.get('ckpt_version', 'N/A')
        ckpt_epoch = config.get('ckpt_epoch', 'N/A')
        transform_type = config.get('transform_type', 'N/A')
        header_lines.append(f"Model {i+1}:")
        header_lines.append(f"  - Name:        {model_name}")
        header_lines.append(f"  - Checkpoint:  v{ckpt_version}, epoch_{ckpt_epoch}")
        header_lines.append(f"  - Transform:   {transform_type}")
        header_lines.append("")
    header_lines.append("==================================================")
    return "\n".join(header_lines)

# ==============================================================================
# 核心功能函数区域
# ==============================================================================

def get_raw_predictions(models, model_configs, known_loader, unknown_loader, device):
    """ (函数1 - 高性能混合版) 从预处理好的数据字典中选择Tensor进行推理。"""
    raw_results = []
    print("="*60 + f"\n🚀 Stage 1: Running inference with {len(models)} models (High-Performance Hybrid Mode)...\n" + "="*60)
    
    with torch.no_grad():
        print("\n--- Processing Known Classes ---")
        for batch_data in tqdm(known_loader, desc="Known Samples"):
            if batch_data is None or batch_data[0] is None: continue
            images_dict, true_labels, paths = batch_data
            images_dict = {key: tensor.to(device) for key, tensor in images_dict.items()}
            
            model_outputs = []
            for model, config in zip(models, model_configs):
                transform_type = config.get('transform_type', 'force_resize')
                image_batch_for_model = images_dict[transform_type]
                output = F.softmax(model(image_batch_for_model), dim=1)
                model_outputs.append(output)
            
            for i in range(len(paths)):
                raw_results.append({
                    'type': 'known', 'true_label_idx': true_labels[i].item(),
                    'image_path': paths[i],
                    'preds_indices': [torch.max(p[i], dim=0)[1].item() for p in model_outputs],
                    'confs':         [torch.max(p[i], dim=0)[0].item() for p in model_outputs],
                    'full_probs':    [p[i] for p in model_outputs]
                })

        print("\n--- Processing Unknown Classes ---")
        for batch_data in tqdm(unknown_loader, desc="Unknown Samples"):
            if batch_data is None or batch_data[0] is None: continue
            images_dict, _, paths = batch_data
            images_dict = {key: tensor.to(device) for key, tensor in images_dict.items()}
            
            model_outputs = []
            for model, config in zip(models, model_configs):
                transform_type = config.get('transform_type', 'force_resize')
                image_batch_for_model = images_dict[transform_type]
                output = F.softmax(model(image_batch_for_model), dim=1)
                model_outputs.append(output)
            
            for i in range(len(paths)):
                raw_results.append({
                    'type': 'unknown', 'true_label_idx': -1,
                    'image_path': paths[i],
                    'preds_indices': [torch.max(p[i], dim=0)[1].item() for p in model_outputs],
                    'confs':         [torch.max(p[i], dim=0)[0].item() for p in model_outputs],
                    'full_probs':    [p[i] for p in model_outputs]
                })
                
    print(f"\n✅ Raw predictions for {len(raw_results)} samples collected.")
    return raw_results

def calculate_metrics_from_raw(raw_results, threshold, strategy_config, vote_threshold):
    """(函数2) 根据缓存的原始预测结果，快速计算不同策略下的性能指标。"""
    known_total, known_accepted, known_correct, unknown_total, unknown_rejected = 0, 0, 0, 0, 0
    strategy = strategy_config['name']
    params = strategy_config['params']
    
    for res in raw_results:
        preds, confs, full_probs = res['preds_indices'], res['confs'], res['full_probs']
        final_decision, final_pred_idx = "REJECT", -1
        num_models = len(preds)

        if strategy == 'voting':
            votes = {}
            for p_idx, c_val in zip(preds, confs):
                if c_val >= threshold: votes[p_idx] = votes.get(p_idx, 0) + 1
            if votes and max(votes.values()) >= vote_threshold:
                final_decision, final_pred_idx = "ACCEPT", [p for p,v in votes.items() if v==max(votes.values())][0]
        elif strategy == 'weighting':
            # 动态权重计算 - 使用置信度作为权重
            sum_weights = sum(confs)
            if sum_weights > 1e-9:
                # 加权平均：每个概率向量 × 其置信度权重
                weighted_avg_probs = sum(prob * w for prob, w in zip(full_probs, confs)) / sum_weights
            else:
                # 容错机制：简单平均
                weighted_avg_probs = torch.mean(torch.stack(full_probs), dim=0)
            final_conf, final_pred_idx_tensor = torch.max(weighted_avg_probs, dim=0)
            if final_conf.item() >= threshold: final_decision, final_pred_idx = "ACCEPT", final_pred_idx_tensor.item()
        elif strategy == 'three_accept': # '一致性优先'策略
            if len(set(preds)) == 1 and all(c > 0 for c in confs): # 一致同意
                 final_decision, final_pred_idx = "ACCEPT", preds[0]
            else:
                votes = {}
                for p_idx, c_val in zip(preds, confs):
                    if c_val >= threshold: votes[p_idx] = votes.get(p_idx, 0) + 1
                if votes and max(votes.values()) >= vote_threshold:
                    final_decision, final_pred_idx = "ACCEPT", [p for p,v in votes.items() if v==max(votes.values())][0]
        elif strategy == 'two_steps':
            t_unanimous = params.get('t_unanimous', 0.4)
            if len(set(preds)) == 1 and all(c >= t_unanimous for c in confs):
                final_decision, final_pred_idx = "ACCEPT", preds[0]
            else:
                # 动态权重计算 - 使用置信度作为权重
                sum_weights = sum(confs)
                if sum_weights > 1e-9:
                    # 加权平均：每个概率向量 × 其置信度权重
                    weighted_avg_probs = sum(prob * w for prob, w in zip(full_probs, confs)) / sum_weights
                else:
                    # 容错机制：简单平均
                    weighted_avg_probs = torch.mean(torch.stack(full_probs), dim=0)
                final_conf, final_pred_idx_tensor = torch.max(weighted_avg_probs, dim=0)
                if final_conf.item() >= threshold: final_decision, final_pred_idx = "ACCEPT", final_pred_idx_tensor.item()
        
        if res['type'] == 'known':
            known_total += 1
            if final_decision == "ACCEPT":
                known_accepted += 1
                if final_pred_idx == res['true_label_idx']: known_correct += 1
        elif res['type'] == 'unknown':
            unknown_total += 1
            if final_decision == "REJECT": unknown_rejected += 1
            
    return {'Known_Accept_Rate': (known_accepted / known_total * 100) if known_total > 0 else 0, 'Unknown_Reject_Rate': (unknown_rejected / unknown_total * 100) if unknown_total > 0 else 0, 'In_Domain_Accuracy': (known_correct / known_accepted * 100) if known_accepted > 0 else 0}

def setup_fonts():
    """尝试设置中文字体"""
    font_list = ['WenQuanYi Zen Hei', 'SimHei', 'sans-serif'];
    try:
        plt.rcParams['font.sans-serif'] = font_list; plt.rcParams['axes.unicode_minus'] = False
        print("✅ Matplotlib 绘图将使用中文字体。")
    except Exception as e:
        print(f"警告: 设置字体失败 - {e}。")

def plot_performance_curves(df_results, output_image_path, report_header_str="", num_models=4):
    """(函数3) 绘制权衡曲线图，并自适应坐标轴范围。"""
    print("\n" + "="*60 + "\n🚀 Stage 3: Generating performance tradeoff curve...\n" + "="*60)
    setup_fonts()
    fig, ax = plt.subplots(figsize=(18, 12))
    MIN_LABEL_DISTANCE = 4.5
    for key, config in PLOT_CONFIGS.items():
        ax.plot(df_results[f'{key}_Known_Accept_Rate'], df_results[f'{key}_Unknown_Reject_Rate'],label=config['label'], color=config['color'], marker=config['marker'], linestyle=config['style'], lw=2.5, markersize=8, alpha=0.8)
        last_labeled_coord = (-100, -100)
        for i, t in enumerate(df_results['Threshold']):
            x, y = df_results.loc[i, f'{key}_Known_Accept_Rate'], df_results.loc[i, f'{key}_Unknown_Reject_Rate']
            distance = math.sqrt((x - last_labeled_coord[0])**2 + (y - last_labeled_coord[1])**2)
            if distance > MIN_LABEL_DISTANCE:
                ax.text(x, y + 0.8, t, ha='center', va='bottom', fontsize=9, color=config['color'], alpha=0.9)
                last_labeled_coord = (x, y)
    
    ax.set_title(f'{num_models}模型集成方法性能权衡曲线', fontsize=22, pad=20)
    ax.set_xlabel('已知类接受率 (1-FRR) %  →  可用性更高', fontsize=16)
    ax.set_ylabel('未知类拒绝率 (1-FAR) %  →  安全性更高', fontsize=16)
    try:
        all_known_rates = df_results[[c for c in df_results.columns if 'Known_Accept_Rate' in c]]
        min_val, max_val = all_known_rates.min().min(), all_known_rates.max().max()
        ax.set_xlim(left=max(0, min_val - 2), right=min(101, max_val + 2))
    except: ax.set_xlim(0, 101)
    try:
        all_unknown_rates = df_results[[c for c in df_results.columns if 'Unknown_Reject_Rate' in c]]
        min_val, max_val = all_unknown_rates.min().min(), all_unknown_rates.max().max()
        ax.set_ylim(bottom=max(-2, min_val - 2), top=min(101, max_val + 2))
    except: ax.set_ylim(-5, 101)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    ax.legend(loc='best', fontsize=15)
    ax.annotate('理想性能点', xy=(100, 100), xytext=(98, 98), arrowprops=dict(facecolor='black', shrink=0.05, width=1), fontsize=15, ha='right', va='top', color='black')
    if report_header_str:
        fig.text(0.01, 0.01, report_header_str, ha='left', va='bottom', fontsize=10, family='monospace', color='gray', bbox=dict(boxstyle='round,pad=0.5', fc='aliceblue', ec='grey', lw=1, alpha=0.8))
    ax.tick_params(axis='both', which='major', labelsize=13)
    plt.tight_layout(rect=[0.0, 0.15, 1.0, 0.95])
    plt.savefig(output_image_path, dpi=300, bbox_inches='tight')
    print(f"✅ 权衡曲线图已成功导出为: '{output_image_path}'")
    plt.close(fig)

def plot_worst_classes(raw_results, threshold, strategy_config, idx_to_class, output_path, vote_threshold):
    """(函数4) 🎯 识别并可视化表现最差的N个类别。"""
    print("\n" + "="*60 + f"\n🚀 Stage 4: Analyzing worst-performing classes at T={threshold}...\n" + "="*60)
    setup_fonts()
    per_class_stats = {idx: {'total': 0, 'accepted': 0} for idx in idx_to_class.keys()}
    strategy = strategy_config['name']
    params = strategy_config['params']
    for res in raw_results:
        if res['type'] == 'known':
            true_idx = res['true_label_idx']
            per_class_stats[true_idx]['total'] += 1
            preds, confs, full_probs = res['preds_indices'], res['confs'], res['full_probs']
            final_decision = "REJECT"
            
            # --- 统一决策逻辑 ---
            if strategy == 'voting':
                votes = {}
                for p_idx, c_val in zip(preds, confs):
                    if c_val >= threshold: votes[p_idx] = votes.get(p_idx, 0) + 1
                if votes and max(votes.values()) >= vote_threshold: final_decision = "ACCEPT"
            elif strategy == 'weighting':
                # 动态权重计算 - 使用置信度作为权重
                sum_weights = sum(confs)
                if sum_weights > 1e-9:
                    # 加权平均：每个概率向量 × 其置信度权重
                    weighted_avg_probs = sum(prob * w for prob, w in zip(full_probs, confs)) / sum_weights
                else:
                    # 容错机制：简单平均
                    weighted_avg_probs = torch.mean(torch.stack(full_probs), dim=0)
                if torch.max(weighted_avg_probs, dim=0)[0].item() >= threshold: final_decision = "ACCEPT"
            elif strategy == 'three_accept':
                if len(set(preds)) == 1 and all(c > 0 for c in confs):
                    final_decision = "ACCEPT"
                else:
                    votes = {}
                    for p_idx, c_val in zip(preds, confs):
                        if c_val >= threshold: votes[p_idx] = votes.get(p_idx, 0) + 1
                    if votes and max(votes.values()) >= vote_threshold: final_decision = "ACCEPT"
            elif strategy == 'two_steps':
                if len(set(preds)) == 1 and all(c >= params['t_unanimous'] for c in confs):
                    final_decision = "ACCEPT"
                else:
                    # 动态权重计算 - 使用置信度作为权重
                    sum_weights = sum(confs)
                    if sum_weights > 1e-9:
                        # 加权平均：每个概率向量 × 其置信度权重
                        weighted_avg_probs = sum(prob * w for prob, w in zip(full_probs, confs)) / sum_weights
                    else:
                        # 容错机制：简单平均
                        weighted_avg_probs = torch.mean(torch.stack(full_probs), dim=0)
                    if torch.max(weighted_avg_probs, dim=0)[0].item() >= threshold: final_decision = "ACCEPT"
            
            if final_decision == "ACCEPT": per_class_stats[true_idx]['accepted'] += 1
            
    class_rates = [{'Class': idx_to_class[idx], 'Acceptance Rate': (stats['accepted'] / stats['total']) * 100, 'Count': f"{stats['accepted']}/{stats['total']}"} for idx, stats in per_class_stats.items() if stats['total'] > 0]
    df_rates = pd.DataFrame(class_rates).sort_values('Acceptance Rate', ascending=True)
    worst_n = 20
    plt.figure(figsize=(12, 10))
    sns.barplot(x='Acceptance Rate', y='Class', data=df_rates.head(worst_n), palette='viridis_r')
    plt.title(f'表现最差的 {worst_n} 个类别的接受率 (策略: {strategy_config["label"]}, T={threshold})', fontsize=16)
    plt.xlabel('已知类接受率 (%)', fontsize=12); plt.ylabel('类别', fontsize=12)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ 瓶颈类别分析图已保存至: '{output_path}'")
    plt.close()

def analyze_failures(raw_results, threshold, strategy_config, idx_to_class, output_path, vote_threshold):
    """(函数5) 🕵️ 深入分析失败案例并生成文本报告。"""
    print("\n" + "="*60 + f"\n🚀 Stage 5: Performing failure analysis at T={threshold}...\n" + "="*60)
    false_accepts_preds, substitution_errors = [], []
    strategy = strategy_config['name']
    params = strategy_config['params']
    for res in raw_results:
        preds, confs, full_probs = res['preds_indices'], res['confs'], res['full_probs']
        final_decision, final_pred_idx = "REJECT", -1

        # --- 统一决策逻辑 ---
        if strategy == 'voting':
            votes = {}
            for p_idx, c_val in zip(preds, confs):
                if c_val >= threshold: votes[p_idx] = votes.get(p_idx, 0) + 1
            if votes and max(votes.values()) >= vote_threshold:
                final_decision, final_pred_idx = "ACCEPT", [p for p,v in votes.items() if v==max(votes.values())][0]
        elif strategy == 'weighting':
            # 动态权重计算 - 使用置信度作为权重
            sum_weights = sum(confs)
            if sum_weights > 1e-9:
                # 加权平均：每个概率向量 × 其置信度权重
                weighted_avg_probs = sum(prob * w for prob, w in zip(full_probs, confs)) / sum_weights
            else:
                # 容错机制：简单平均
                weighted_avg_probs = torch.mean(torch.stack(full_probs), dim=0)
            final_conf, final_pred_idx_tensor = torch.max(weighted_avg_probs, dim=0)
            if final_conf.item() >= threshold: final_decision, final_pred_idx = "ACCEPT", final_pred_idx_tensor.item()
        elif strategy == 'three_accept':
            if len(set(preds)) == 1 and all(c > 0 for c in confs):
                final_decision, final_pred_idx = "ACCEPT", preds[0]
            else:
                votes = {}
                for p_idx, c_val in zip(preds, confs):
                    if c_val >= threshold: votes[p_idx] = votes.get(p_idx, 0) + 1
                if votes and max(votes.values()) >= vote_threshold:
                    final_decision, final_pred_idx = "ACCEPT", [p for p,v in votes.items() if v==max(votes.values())][0]
        elif strategy == 'two_steps':
            t_unanimous = params.get('t_unanimous', 0.4)
            if len(set(preds)) == 1 and all(c >= t_unanimous for c in confs):
                final_decision, final_pred_idx = "ACCEPT", preds[0]
            else:
                # 动态权重计算 - 使用置信度作为权重
                sum_weights = sum(confs)
                if sum_weights > 1e-9:
                    # 加权平均：每个概率向量 × 其置信度权重
                    weighted_avg_probs = sum(prob * w for prob, w in zip(full_probs, confs)) / sum_weights
                else:
                    # 容错机制：简单平均
                    weighted_avg_probs = torch.mean(torch.stack(full_probs), dim=0)
                    final_conf, final_pred_idx_tensor = torch.max(weighted_avg_probs, dim=0)
                    if final_conf.item() >= threshold: final_decision, final_pred_idx = "ACCEPT", final_pred_idx_tensor.item()
        
        if res['type'] == 'unknown' and final_decision == 'ACCEPT':
            false_accepts_preds.append(idx_to_class.get(final_pred_idx, 'N/A'))
        elif res['type'] == 'known' and final_decision == 'ACCEPT' and final_pred_idx != res['true_label_idx']:
            substitution_errors.append({'真实类别': idx_to_class.get(res['true_label_idx']), '预测类别': idx_to_class.get(final_pred_idx)})
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"失败案例分析报告 (策略: {strategy_config['label']}, 阈值 T={threshold})\n" + "="*60 + "\n\n")
        f.write("--- 1. 未知类被错误接受 (False Accepts) 的情况 ---\n")
        if false_accepts_preds:
            df_fa = pd.DataFrame(false_accepts_preds, columns=['预测类别']).value_counts().reset_index(name='次数')
            f.write("未知样本最常被错误识别为以下已知类别：\n" + df_fa.to_string(index=False) + "\n")
        else: f.write("表现完美！没有未知样本被错误接受。\n")
        f.write("\n\n" + "="*60 + "\n\n")
        f.write("--- 2. 已知类被错误分类 (Substitution Errors) 的情况 ---\n")
        if substitution_errors:
            df_se = pd.DataFrame(substitution_errors).groupby(['真实类别', '预测类别']).size().reset_index(name='次数').sort_values('次数', ascending=False)
            f.write("已知样本的混淆情况（真实 -> 预测）:\n" + df_se.to_string(index=False) + "\n")
        else: f.write("表现完美！没有已知样本在接受后被错误分类。\n")
    print(f"✅ 失败案例分析报告已保存至: '{output_path}'")

def generate_detailed_predictions_report(raw_results, threshold, strategy_config, idx_to_class, output_path, vote_threshold, model_configs):
    """生成每张图片的详细预测结果表格"""
    print(f"\n🚀 生成详细预测报告 (阈值 T={threshold}, 策略: {strategy_config['label']})...")
    
    detailed_predictions = []
    strategy = strategy_config['name']
    params = strategy_config['params']
    
    for res in raw_results:
        preds, confs, full_probs = res['preds_indices'], res['confs'], res['full_probs']
        final_decision, final_pred_idx = "REJECT", -1
        final_confidence = 0.0
        
        # 决策逻辑
        if strategy == 'voting':
            votes = {}
            for p_idx, c_val in zip(preds, confs):
                if c_val >= threshold:
                    votes[p_idx] = votes.get(p_idx, 0) + 1
            if votes and max(votes.values()) >= vote_threshold:
                final_decision = "ACCEPT"
                final_pred_idx = [p for p,v in votes.items() if v==max(votes.values())][0]
                final_confidence = max(confs)
        elif strategy == 'weighting':
            sum_weights = sum(confs)
            if sum_weights > 1e-9:
                weighted_avg_probs = sum(prob * w for prob, w in zip(full_probs, confs)) / sum_weights
            else:
                weighted_avg_probs = torch.mean(torch.stack(full_probs), dim=0)
            final_conf, final_pred_idx_tensor = torch.max(weighted_avg_probs, dim=0)
            final_confidence = final_conf.item()
            if final_confidence >= threshold:
                final_decision = "ACCEPT"
                final_pred_idx = final_pred_idx_tensor.item()
        elif strategy == 'three_accept':
            if len(set(preds)) == 1 and all(c > 0 for c in confs):
                final_decision = "ACCEPT"
                final_pred_idx = preds[0]
                final_confidence = min(confs)
            else:
                votes = {}
                for p_idx, c_val in zip(preds, confs):
                    if c_val >= threshold:
                        votes[p_idx] = votes.get(p_idx, 0) + 1
                if votes and max(votes.values()) >= vote_threshold:
                    final_decision = "ACCEPT"
                    final_pred_idx = [p for p,v in votes.items() if v==max(votes.values())][0]
                    final_confidence = max(confs)
        elif strategy == 'two_steps':
            t_unanimous = params.get('t_unanimous', 0.4)
            if len(set(preds)) == 1 and all(c >= t_unanimous for c in confs):
                final_decision = "ACCEPT"
                final_pred_idx = preds[0]
                final_confidence = min(confs)
            else:
                sum_weights = sum(confs)
                if sum_weights > 1e-9:
                    weighted_avg_probs = sum(prob * w for prob, w in zip(full_probs, confs)) / sum_weights
                else:
                    weighted_avg_probs = torch.mean(torch.stack(full_probs), dim=0)
                final_conf, final_pred_idx_tensor = torch.max(weighted_avg_probs, dim=0)
                final_confidence = final_conf.item()
                if final_confidence >= threshold:
                    final_decision = "ACCEPT"
                    final_pred_idx = final_pred_idx_tensor.item()
        
        # 构建预测结果记录
        true_label = "UNKNOWN" if res['type'] == 'unknown' else idx_to_class.get(res['true_label_idx'], 'N/A')
        predicted_label = idx_to_class.get(final_pred_idx, 'N/A') if final_decision == "ACCEPT" else "REJECTED"
        
        # 判断是否正确
        if res['type'] == 'unknown':
            is_correct = final_decision == "REJECT"
        else:
            is_correct = (final_decision == "ACCEPT" and final_pred_idx == res['true_label_idx'])
        
        # 构建每个模型的预测详情
        model_details = {}
        for i, (pred_idx, conf) in enumerate(zip(preds, confs)):
            model_name = model_configs[i]['model_name'] if i < len(model_configs) else f'Model_{i+1}'
            model_details[f'{model_name}_预测类别'] = idx_to_class.get(pred_idx, 'N/A')
            model_details[f'{model_name}_置信度'] = f"{conf:.4f}"
        
        prediction_record = {
            '图片路径': res.get('image_path', f'Sample_{len(detailed_predictions)+1}'),
            '真实类别': true_label,
            '集成决策': final_decision,
            '预测类别': predicted_label,
            '最终置信度': f"{final_confidence:.4f}",
            '是否正确': is_correct,
            **model_details
        }
        
        detailed_predictions.append(prediction_record)
    
    # 保存为CSV文件
    df_predictions = pd.DataFrame(detailed_predictions)
    df_predictions.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"✅ 详细预测报告已保存至: '{output_path}'")
    
    # 打印统计信息
    total_samples = len(detailed_predictions)
    correct_predictions = sum(1 for pred in detailed_predictions if pred['是否正确'])
    accuracy = (correct_predictions / total_samples * 100) if total_samples > 0 else 0
    print(f"📊 总样本数: {total_samples}, 正确预测: {correct_predictions}, 准确率: {accuracy:.2f}%")

def generate_per_class_report(raw_results, threshold, strategy_config, class_to_idx, idx_to_class, output_path, vote_threshold):
    """(函数6) 📊 生成指定阈值下，按类别划分的详细分类报告。"""
    print("\n" + "="*60 + f"\n🚀 Stage 6: Generating detailed per-class report at T={threshold}...\n" + "="*60)
    per_class_stats = {idx: {'total': 0, 'accepted': 0, 'correctly_accepted': 0} for idx in idx_to_class.keys()}
    strategy = strategy_config['name']
    params = strategy_config['params']

    for res in raw_results:
        if res['type'] != 'known': continue
        
        true_idx = res['true_label_idx']
        if true_idx not in per_class_stats: continue
        per_class_stats[true_idx]['total'] += 1

        preds, confs, full_probs = res['preds_indices'], res['confs'], res['full_probs']
        final_decision, final_pred_idx = "REJECT", -1

        # --- 统一决策逻辑 ---
        if strategy == 'voting':
            votes = {}
            for p_idx, c_val in zip(preds, confs):
                if c_val >= threshold: votes[p_idx] = votes.get(p_idx, 0) + 1
            if votes and max(votes.values()) >= vote_threshold:
                final_decision, final_pred_idx = "ACCEPT", [p for p,v in votes.items() if v==max(votes.values())][0]
        elif strategy == 'weighting':
            # 动态权重计算 - 使用置信度作为权重
            sum_weights = sum(confs)
            if sum_weights > 1e-9:
                # 加权平均：每个概率向量 × 其置信度权重
                weighted_avg_probs = sum(prob * w for prob, w in zip(full_probs, confs)) / sum_weights
            else:
                # 容错机制：简单平均
                weighted_avg_probs = torch.mean(torch.stack(full_probs), dim=0)
            final_conf, final_pred_idx_tensor = torch.max(weighted_avg_probs, dim=0)
            if final_conf.item() >= threshold: final_decision, final_pred_idx = "ACCEPT", final_pred_idx_tensor.item()
        elif strategy == 'three_accept':
            if len(set(preds)) == 1 and all(c > 0 for c in confs):
                final_decision, final_pred_idx = "ACCEPT", preds[0]
            else:
                votes = {}
                for p_idx, c_val in zip(preds, confs):
                    if c_val >= threshold: votes[p_idx] = votes.get(p_idx, 0) + 1
                if votes and max(votes.values()) >= vote_threshold:
                    final_decision, final_pred_idx = "ACCEPT", [p for p,v in votes.items() if v==max(votes.values())][0]
        elif strategy == 'two_steps':
            t_unanimous = params.get('t_unanimous', 0.4)
            if len(set(preds)) == 1 and all(c >= t_unanimous for c in confs):
                final_decision, final_pred_idx = "ACCEPT", preds[0]
            else:
                # 动态权重计算 - 使用置信度作为权重
                sum_weights = sum(confs)
                if sum_weights > 1e-9:
                    # 加权平均：每个概率向量 × 其置信度权重
                    weighted_avg_probs = sum(prob * w for prob, w in zip(full_probs, confs)) / sum_weights
                else:
                    # 容错机制：简单平均
                    weighted_avg_probs = torch.mean(torch.stack(full_probs), dim=0)
                    final_conf, final_pred_idx_tensor = torch.max(weighted_avg_probs, dim=0)
                    if final_conf.item() >= threshold: final_decision, final_pred_idx = "ACCEPT", final_pred_idx_tensor.item()

        if final_decision == "ACCEPT":
            per_class_stats[true_idx]['accepted'] += 1
            if final_pred_idx == true_idx:
                per_class_stats[true_idx]['correctly_accepted'] += 1

    report_data = []
    # 按 custom_mapping.json 的顺序生成报告
    for class_name, class_idx in class_to_idx.items():
        stats = per_class_stats[class_idx]
        total = stats['total']
        accepted = stats['accepted']
        correctly_accepted = stats['correctly_accepted']

        acceptance_rate = (accepted / total) * 100 if total > 0 else 0
        classification_accuracy = (correctly_accepted / accepted) * 100 if accepted > 0 else 0
        overall_accuracy = acceptance_rate * classification_accuracy / 100 # (correctly_accepted / total) * 100

        report_data.append({
            'ID': class_idx,
            '类别名': class_name,
            '已知类的接受率 (%)': f"{acceptance_rate:.2f}",
            '分类准确率 (域内) (%)': f"{classification_accuracy:.2f}",
            '综合准确率 (%)': f"{overall_accuracy:.2f}",
            '样本统计 (正确接受/总接受/总数)': f"{correctly_accepted}/{accepted}/{total}"
        })

    df_report = pd.DataFrame(report_data)
    df_report.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"✅ 按类别详细报告已保存至: '{output_path}'")

# ==============================================================================
# 🚀 主函数 (Orchestrator) - 高性能混合模式 + 动态投票阈值 + 多阈值报告
# ==============================================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='High-Performance Hybrid-Transform Open-Set Ensemble Analysis')
    parser.add_argument('--data_dir', type=str, required=True)
    parser.add_argument('--ensemble_config', type=str, default='modelEnsemble/model_ensemble_config_hybrid.json', help="指向模型配置的JSON文件路径")
    parser.add_argument('--custom_mappings_path', type=str, default='custom_mapping.json')
    parser.add_argument('--dataset_name', type=str, default='medicine_99')
    parser.add_argument('--img_size', type=int, default=640)
    parser.add_argument('--batch_size', type=int, default=16)
    parser.add_argument('--num_workers', type=int, default=4)
    parser.add_argument('--gpu', type=str, default='0')
    parser.add_argument('--output_dir', type=str, default=None)
    # --- 🚀 修改: 允许多个分析阈值 ---
    parser.add_argument('--analysis_threshold', type=float, nargs='+', default=[0.62,0.4,0.2], help='用于生成详细报告的一个或多个特定阈值 (例如: 0.6 0.7 0.8)')
    # --- 🚀 新增: 动态投票阈值参数 ---
    parser.add_argument('--vote_threshold', type=int, default=3, help='投票和一致性策略中接受预测所需的最小票数 (n)')
    args = parser.parse_args()
    
    # 初始化配置
    configs.run_mode = 'test'; configs.path_init(); configs.img_size = args.img_size
    
    # 处理GPU/CPU设置
    if args.gpu == '-1' or args.gpu == 'cpu':
        # 使用CPU模式
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        device = torch.device('cpu')
        print("🖥️  使用CPU模式进行推理")
    else:
        # 使用GPU模式
        os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"🚀 使用GPU: {args.gpu}")
    
    with open(args.ensemble_config, 'r', encoding='utf-8') as f: model_configs = json.load(f)
    with open(args.custom_mappings_path, 'r', encoding='utf-8') as f: class_to_idx = json.load(f)[args.dataset_name]['class_to_idx']
    idx_to_class = {v: k for k, v in class_to_idx.items()}
    
    num_models = len(model_configs)
    # --- 🚀 新增: 动态生成绘图标签 ---
    PLOT_CONFIGS = {
        'Voting':        {'label': f'置信度投票 (>= {args.vote_threshold}票)', 'color': 'royalblue', 'marker': 'o', 'style': '--'},
        'Weighting':     {'label': '置信度加权 (Weighting)', 'color': 'darkorange', 'marker': '^', 'style': '--'},
        'ThreeAccept':   {'label': f'一致性优先 ({num_models}票一致或>={args.vote_threshold}票)', 'color': 'forestgreen', 'marker': 's', 'style': '--'},
        'TwoSteps_T0.4': {'label': f'两阶段 ({num_models}票一致或加权)', 'color': 'crimson', 'marker': 'D', 'style': '-'},
    }
    
    TRANSFORMS_DICT = {
        'force_resize': transforms.Compose([transforms.Resize((args.img_size, args.img_size)), transforms.ToTensor(), transforms.Normalize(configs.mean, configs.std)]),
        'center_crop': transforms.Compose([transforms.Resize(args.img_size), transforms.CenterCrop(args.img_size), transforms.ToTensor(), transforms.Normalize(configs.mean, configs.std)])
    }

    models = load_ensemble_models(model_configs, len(class_to_idx), configs.ckpts_dir, device)
    
    known_loader = DataLoader(
        HybridOpenSetDataset(os.path.join(args.data_dir, '0.已知'), transforms_dict=TRANSFORMS_DICT, class_to_idx=class_to_idx, is_known=True),
        batch_size=args.batch_size, num_workers=args.num_workers, collate_fn=collate_fn_hybrid
    )
    unknown_loader = DataLoader(
        HybridOpenSetDataset(os.path.join(args.data_dir, '1.未知'), transforms_dict=TRANSFORMS_DICT, is_known=False),
        batch_size=args.batch_size, num_workers=args.num_workers, collate_fn=collate_fn_hybrid
    )

    raw_predictions = get_raw_predictions(models, model_configs, known_loader, unknown_loader, device)
    
    print("\n" + "="*60 + "\n🚀 Stage 2: Calculating metrics for all strategies...\n" + "="*60)
    thresholds_to_test = np.arange(0.1, 1.0, 0.01)
    all_results = []
    for threshold in tqdm(thresholds_to_test, desc="Sweeping Thresholds"):
        t = round(threshold, 2)
        result_row = {'Threshold': t}
        for key, config in STRATEGY_CONFIGS.items():
            # --- 🚀 修改: 将 vote_threshold 传递给指标计算函数 ---
            metrics = calculate_metrics_from_raw(raw_predictions, t, config, args.vote_threshold)
            result_row[f'{key}_Known_Accept_Rate'] = metrics['Known_Accept_Rate']
            result_row[f'{key}_Unknown_Reject_Rate'] = metrics['Unknown_Reject_Rate']
            result_row[f'{key}_In_Domain_Accuracy'] = metrics['In_Domain_Accuracy']
        all_results.append(result_row)
    results_df = pd.DataFrame(all_results)
    
    if args.output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(current_dir, 'test', f'full_analysis_report', timestamp+f'_{args.dataset_name}_{num_models}models_n{args.vote_threshold}')
    else:
        output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    report_header_text = generate_report_header(model_configs, args.vote_threshold)
    header_path = os.path.join(output_dir, 'ensemble_configuration.txt')
    with open(header_path, 'w', encoding='utf-8') as f:
        f.write(report_header_text)
    print(f"\n✅ Ensemble configuration summary saved to: {header_path}")
    
    CHINESE_COLUMN_MAP = {'Threshold': '阈值'}
    for key, plot_config in PLOT_CONFIGS.items():
        CHINESE_COLUMN_MAP[f'{key}_Known_Accept_Rate'] = f"{plot_config['label']}_已知类接受率"
        CHINESE_COLUMN_MAP[f'{key}_Unknown_Reject_Rate'] = f"{plot_config['label']}_未知类拒绝率"
        CHINESE_COLUMN_MAP[f'{key}_In_Domain_Accuracy'] = f"{plot_config['label']}_域内准确率"
    
    df_to_export = results_df.copy()
    for col in df_to_export.columns:
        if col != 'Threshold':
            df_to_export[col] = df_to_export[col].apply(lambda x: f"{x:.3f}%")
    df_to_export.rename(columns=CHINESE_COLUMN_MAP, inplace=True)
    csv_path = os.path.join(output_dir, 'full_comparison_report_formatted.csv')
    df_to_export.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ Formatted Chinese CSV report saved to: {csv_path}")
    
    plot_path = os.path.join(output_dir, 'performance_tradeoff_curve.png')
    plot_performance_curves(results_df, plot_path, num_models=num_models)

    # 🔄 修改：使用置信度加权策略进行详细分析
    analysis_strategy_key = 'Weighting'
    analysis_strategy_config = {**STRATEGY_CONFIGS[analysis_strategy_key], 'label': PLOT_CONFIGS[analysis_strategy_key]['label']}
    
    # --- 🚀 修改: 循环处理每个指定的分析阈值 ---
    for t_analysis in args.analysis_threshold:
        print(f"\n\n{'='*25} Generating Detailed Reports for Threshold T={t_analysis} {'='*25}")
        
        # --- Stage 4: 瓶颈类别分析 ---
        worst_classes_plot_path = os.path.join(output_dir, f'worst_classes_at_T{t_analysis}_{analysis_strategy_key}.png')
        plot_worst_classes(raw_predictions, t_analysis, analysis_strategy_config, idx_to_class, worst_classes_plot_path, args.vote_threshold)

        # --- Stage 5: 失败案例分析 ---
        failure_report_path = os.path.join(output_dir, f'failure_analysis_at_T{t_analysis}_{analysis_strategy_key}.txt')
        analyze_failures(raw_predictions, t_analysis, analysis_strategy_config, idx_to_class, failure_report_path, args.vote_threshold)

        # --- Stage 6: 新增！按类别生成详细报告 ---
        class_report_path = os.path.join(output_dir, f'per_class_report_at_T{t_analysis}_{analysis_strategy_key}.csv')
        generate_per_class_report(raw_predictions, t_analysis, analysis_strategy_config, class_to_idx, idx_to_class, class_report_path, args.vote_threshold)
        
        # --- Stage 7: 新增！生成每张图片的详细预测报告 ---
        detailed_predictions_path = os.path.join(output_dir, f'detailed_predictions_at_T{t_analysis}_{analysis_strategy_key}.csv')
        generate_detailed_predictions_report(raw_predictions, t_analysis, analysis_strategy_config, idx_to_class, detailed_predictions_path, args.vote_threshold, model_configs)
    
    print("\n\n🎉 All analysis complete!")