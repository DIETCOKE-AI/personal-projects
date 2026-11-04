# File: modelEnsemble/run_threshold_sweep.py
# Version: 8.3 (Optimized & High-Performance with Per-Class Reporting)
# Description: A streamlined script for running ensemble analysis with a single,
#              uniform transform, leveraging parallel data processing for maximum speed.
#              Includes intelligent plotting, configuration summary, and detailed
#              per-class performance reporting for specified thresholds.

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
STRATEGY_CONFIGS = {
    'Voting':        {'name': 'voting', 'params': {}},
    'Weighting':     {'name': 'weighting', 'params': {}},
    'ThreeAccept':   {'name': 'three_accept', 'params': {}},
    'TwoSteps_T0.4': {'name': 'two_steps', 'params': {'t_unanimous': 0.4}},
}

PLOT_CONFIGS = {
    'Voting':        {'label': '置信度投票 (>=3票)', 'color': 'royalblue', 'marker': 'o', 'style': '--'},
    'Weighting':     {'label': '置信度加权 (Weighting)', 'color': 'darkorange', 'marker': '^', 'style': '--'},
    'ThreeAccept':   {'label': '一致性优先 (4票一致或>=3票)', 'color': 'forestgreen', 'marker': 's', 'style': '--'},
    'TwoSteps_T0.4': {'label': '两阶段 (4票一致或加权)', 'color': 'crimson', 'marker': 'D', 'style': '-'},
}

# ==============================================================================
# 헬 헬퍼 함수 및 클래스
# ==============================================================================

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

        if self.transform:
            img = self.transform(img)
            
        return img, target, path

def collate_fn_filter_none(batch):
    """过滤掉加载失败的样本 (值为 None)"""
    batch = list(filter(lambda x: x is not None and x[0] is not None, batch))
    if not batch:
        return None, None, None
    return torch.utils.data.dataloader.default_collate(batch)

def load_ensemble_models(model_configs, num_classes, ckpts_dir, device):
    """根据配置加载集成模型。"""
    models = []
    print("="*60 + "\n🚀 开始加载集成模型...")
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
            checkpoint = torch.load(ckpt_path, map_location=device, weights_only=True)
            
            is_data_parallel_ckpt = next(iter(checkpoint)).startswith('module.')
            if isinstance(net, nn.DataParallel):
                if not is_data_parallel_ckpt:
                    net.load_state_dict({f'module.{k}': v for k, v in checkpoint.items()}, strict=True)
                else:
                    net.load_state_dict(checkpoint, strict=True)
            else:
                if is_data_parallel_ckpt:
                    net.load_state_dict({k.replace("module.", ""): v for k, v in checkpoint.items()}, strict=True)
                else:
                    net.load_state_dict(checkpoint, strict=True)
            
            net.eval()
            models.append(net)
            print(f"  ✅ 模型 {model_name} 加载成功!")
        except Exception as e:
            print(f"  ❌ 加载模型 {model_name} 失败: {e}")
    
    if len(models) != len(model_configs):
        raise ValueError(f"预期加载 {len(model_configs)} 个模型，但只成功加载了 {len(models)} 个。")

    print(f"✅ 共 {len(models)} 个模型加载成功!\n" + "="*60)
    return models

def generate_report_header(model_configs, unified_transform_name):
    """根据模型配置列表，生成一份格式化的、用于报告的文本头。"""
    header_lines = [
        "==================================================",
        "           Ensemble Configuration Summary",
        "==================================================",
        f"Evaluation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total Models:    {len(model_configs)}",
        f"Unified Transform: {unified_transform_name}",
        "--------------------------------------------------",
    ]
    for i, config in enumerate(model_configs):
        model_name = config.get('model_name', 'N/A')
        ckpt_version = config.get('ckpt_version', 'N/A')
        ckpt_epoch = config.get('ckpt_epoch', 'N/A')
        
        header_lines.append(f"Model {i+1}:")
        header_lines.append(f"  - Name:       {model_name}")
        header_lines.append(f"  - Checkpoint: v{ckpt_version}, epoch_{ckpt_epoch}")
        header_lines.append("")

    header_lines.append("==================================================")
    return "\n".join(header_lines)

# ==============================================================================
# 核心功能函数区域
# ==============================================================================

def get_raw_predictions(models, known_loader, unknown_loader, device):
    """ (函数1 - 高效版) 遍历已预处理好的数据，获取原始预测。"""
    raw_results = []
    print("="*60 + f"\n🚀 Stage 1: Running inference with {len(models)} models...\n" + "="*60)
    with torch.no_grad():
        print("\n--- Processing Known Classes ---")
        for batch_data in tqdm(known_loader, desc="Known Samples"):
            if batch_data is None: continue
            images, true_labels, paths = batch_data
            images = images.to(device)
            
            model_outputs = [F.softmax(model(images), dim=1) for model in models]
            
            for i in range(images.size(0)):
                raw_results.append({
                    'type': 'known', 'true_label_idx': true_labels[i].item(),
                    'preds_indices': [torch.max(p[i], dim=0)[1].item() for p in model_outputs],
                    'confs':         [torch.max(p[i], dim=0)[0].item() for p in model_outputs],
                    'full_probs':    [p[i] for p in model_outputs]
                })

        print("\n--- Processing Unknown Classes ---")
        for batch_data in tqdm(unknown_loader, desc="Unknown Samples"):
            if batch_data is None: continue
            images, _, paths = batch_data
            images = images.to(device)
            
            model_outputs = [F.softmax(model(images), dim=1) for model in models]
            
            for i in range(images.size(0)):
                raw_results.append({
                    'type': 'unknown', 'true_label_idx': -1,
                    'preds_indices': [torch.max(p[i], dim=0)[1].item() for p in model_outputs],
                    'confs':         [torch.max(p[i], dim=0)[0].item() for p in model_outputs],
                    'full_probs':    [p[i] for p in model_outputs]
                })
                
    print(f"\n✅ Raw predictions for {len(raw_results)} samples collected.")
    return raw_results

def calculate_metrics_from_raw(raw_results, threshold, strategy, t_unanimous=0.4):
    """(函数2) 根据缓存的原始预测结果，快速计算不同策略下的性能指标。"""
    known_total, known_accepted, known_correct, unknown_total, unknown_rejected = 0, 0, 0, 0, 0
    for res in raw_results:
        preds, confs, full_probs = res['preds_indices'], res['confs'], res['full_probs']
        final_decision, final_pred_idx = "REJECT", -1
        
        if strategy == 'voting':
            votes = {}
            for p_idx, c_val in zip(preds, confs):
                if c_val >= threshold: votes[p_idx] = votes.get(p_idx, 0) + 1
            if votes and max(votes.values()) >= 3:
                final_decision, final_pred_idx = "ACCEPT", [p for p,v in votes.items() if v==max(votes.values())][0]
        elif strategy == 'weighting':
            sum_w = sum(confs)
            avg_probs = sum(p * w for p, w in zip(full_probs, confs)) / sum_w if sum_w > 1e-9 else torch.mean(torch.stack(full_probs), dim=0)
            final_conf, final_pred_idx_tensor = torch.max(avg_probs, dim=0)
            if final_conf.item() >= threshold: final_decision, final_pred_idx = "ACCEPT", final_pred_idx_tensor.item()
        elif strategy == 'three_accept':
            if len(set(preds)) == 1:
                final_decision, final_pred_idx = "ACCEPT", preds[0]
            else:
                votes = {}
                for p_idx, c_val in zip(preds, confs):
                    if c_val >= threshold: votes[p_idx] = votes.get(p_idx, 0) + 1
                if votes and max(votes.values()) >= 3:
                    final_decision, final_pred_idx = "ACCEPT", [p for p,v in votes.items() if v==max(votes.values())][0]
        elif strategy == 'two_steps':
            if len(set(preds)) == 1 and all(c >= t_unanimous for c in confs):
                final_decision, final_pred_idx = "ACCEPT", preds[0]
            else:
                sum_w = sum(confs)
                avg_probs = sum(p * w for p, w in zip(full_probs, confs)) / sum_w if sum_w > 1e-9 else torch.mean(torch.stack(full_probs), dim=0)
                final_conf, final_pred_idx_tensor = torch.max(avg_probs, dim=0)
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
    try:
        from utils.chinese_font_config import setup_chinese_fonts
        setup_chinese_fonts()
        print("✅ Matplotlib 绘图将使用中文字体。")
    except ImportError:
        # 备用字体设置
        font_list = ['WenQuanYi Zen Hei', 'SimHei', 'Microsoft YaHei', 'Noto Sans CJK SC', 'Noto Sans CJK', 'Source Han Sans CN', 'DejaVu Sans', 'sans-serif']
        try:
            plt.rcParams['font.sans-serif'] = font_list
            plt.rcParams['axes.unicode_minus'] = False
            print("✅ Matplotlib 绘图将使用中文字体。")
        except Exception as e:
            print(f"警告: 设置字体失败 - {e}。绘图中的中文可能无法显示。")

def plot_performance_curves(df_results, output_image_path, report_header_str=""):
    """(函数3 - 优化版) 绘制权衡曲线图，并自适应坐标轴范围。"""
    print("\n" + "="*60 + "\n🚀 Stage 3: Generating performance tradeoff curve...\n" + "="*60)
    setup_fonts()
    fig, ax = plt.subplots(figsize=(18, 12))
    MIN_LABEL_DISTANCE = 4.5
    for key, config in PLOT_CONFIGS.items():
        ax.plot(df_results[f'{key}_Known_Accept_Rate'], df_results[f'{key}_Unknown_Reject_Rate'],label=config['label'], color=config['color'], marker=config['marker'], linestyle=config['style'], lw=2.5, markersize=8, alpha=0.8)
        last_labeled_coord = (-100, -100)
        thresholds = df_results['Threshold']
        for i, t in enumerate(thresholds):
            x, y = df_results.loc[i, f'{key}_Known_Accept_Rate'], df_results.loc[i, f'{key}_Unknown_Reject_Rate']
            distance = math.sqrt((x - last_labeled_coord[0])**2 + (y - last_labeled_coord[1])**2)
            if distance > MIN_LABEL_DISTANCE:
                ax.text(x, y + 0.8, t, ha='center', va='bottom', fontsize=9, color=config['color'], alpha=0.9)
                last_labeled_coord = (x, y)
    
    ax.set_title('四种模型集成方法性能权衡曲线 (4模型)', fontsize=22, pad=20)
    ax.set_xlabel('已知类接受率 (1-FRR) %  →  可用性更高', fontsize=16)
    ax.set_ylabel('未知类拒绝率 (1-FAR) %  →  安全性更高', fontsize=16)
    
    try:
        all_known_rates = df_results[[c for c in df_results.columns if 'Known_Accept_Rate' in c]]
        min_val = all_known_rates.min().min(); max_val = all_known_rates.max().max()
        ax.set_xlim(left=max(0, min_val - 5), right=min(101, max_val + 2))
    except:
        ax.set_xlim(0, 101)
    
    try:
        all_unknown_rates = df_results[[c for c in df_results.columns if 'Unknown_Reject_Rate' in c]]
        min_val = all_unknown_rates.min().min(); max_val = all_unknown_rates.max().max()
        ax.set_ylim(bottom=max(-5, min_val - 5), top=min(101, max_val + 2))
    except:
        ax.set_ylim(-5, 101)
        
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    ax.legend(loc='best', fontsize=15)
    ax.annotate('理想性能点', xy=(100, 100), xytext=(98, 98), 
                arrowprops=dict(facecolor='black', shrink=0.05, width=1), 
                fontsize=15, ha='right', va='top', color='black')
    
    if report_header_str:
        fig.text(0.01, 0.01, report_header_str, ha='left', va='bottom', 
                 fontsize=10, family='monospace', color='gray',
                 bbox=dict(boxstyle='round,pad=0.5', fc='aliceblue', ec='grey', lw=1, alpha=0.8))

    ax.tick_params(axis='both', which='major', labelsize=13)
    plt.tight_layout(rect=[0.0, 0.15, 1.0, 0.95]) # 为底部文本留出更多空间
    plt.savefig(output_image_path, dpi=300, bbox_inches='tight')
    print(f"✅ 权衡曲线图已成功导出为: '{output_image_path}'")
    plt.close(fig)

def plot_worst_classes(raw_results, threshold, strategy_config, idx_to_class, output_path):
    """(函数4) 🎯 识别并可视化表现最差的N个类别。"""
    print("\n" + "="*60 + f"\n🚀 Stage 4: Analyzing worst-performing classes at T={threshold}...\n" + "="*60)
    setup_fonts()
    per_class_stats = {idx: {'total': 0, 'accepted': 0} for idx in idx_to_class.keys()}
    for res in raw_results:
        if res['type'] == 'known':
            true_idx = res['true_label_idx']
            per_class_stats[true_idx]['total'] += 1
            preds, confs, full_probs = res['preds_indices'], res['confs'], res['full_probs']
            final_decision = "REJECT"
            strategy = strategy_config['name']
            if strategy == 'voting':
                votes = {}
                for p_idx, c_val in zip(preds, confs):
                    if c_val >= threshold: votes[p_idx] = votes.get(p_idx, 0) + 1
                if votes and max(votes.values()) >= 3: final_decision = "ACCEPT"
            elif strategy == 'weighting':
                sum_w = sum(confs); avg_probs = sum(p * w for p, w in zip(full_probs, confs)) / sum_w if sum_w > 1e-9 else torch.mean(torch.stack(full_probs), dim=0)
                if torch.max(avg_probs, dim=0)[0].item() >= threshold: final_decision = "ACCEPT"
            elif strategy == 'three_accept':
                if len(set(preds)) == 1: final_decision = "ACCEPT"
                else:
                    votes = {}
                    for p_idx, c_val in zip(preds, confs):
                        if c_val >= threshold: votes[p_idx] = votes.get(p_idx, 0) + 1
                    if votes and max(votes.values()) >= 3: final_decision = "ACCEPT"
            elif strategy == 'two_steps':
                if len(set(preds)) == 1 and all(c >= strategy_config['params']['t_unanimous'] for c in confs): final_decision = "ACCEPT"
                else:
                    sum_w = sum(confs); avg_probs = sum(p * w for p, w in zip(full_probs, confs)) / sum_w if sum_w > 1e-9 else torch.mean(torch.stack(full_probs), dim=0)
                    if torch.max(avg_probs, dim=0)[0].item() >= threshold: final_decision = "ACCEPT"
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

def analyze_failures(raw_results, threshold, strategy_config, idx_to_class, output_path):
    """(函数5) 🕵️ 深入分析失败案例并生成文本报告。"""
    print("\n" + "="*60 + f"\n🚀 Stage 5: Performing failure analysis at T={threshold}...\n" + "="*60)
    false_accepts_preds, substitution_errors = [], []
    for res in raw_results:
        preds, confs, full_probs = res['preds_indices'], res['confs'], res['full_probs']
        final_decision, final_pred_idx = "REJECT", -1
        strategy = strategy_config['name']
        if strategy == 'voting':
            votes = {}
            for p_idx, c_val in zip(preds, confs):
                if c_val >= threshold: votes[p_idx] = votes.get(p_idx, 0) + 1
            if votes and max(votes.values()) >= 3: final_decision, final_pred_idx = "ACCEPT", max(votes, key=votes.get)
        elif strategy == 'weighting':
            sum_w = sum(confs); avg_probs = sum(p * w for p, w in zip(full_probs, confs)) / sum_w if sum_w > 1e-9 else torch.mean(torch.stack(full_probs), dim=0)
            final_conf, final_pred_idx_tensor = torch.max(avg_probs, dim=0)
            if final_conf.item() >= threshold: final_decision, final_pred_idx = "ACCEPT", final_pred_idx_tensor.item()
        elif strategy == 'three_accept':
            if len(set(preds)) == 1: final_decision, final_pred_idx = "ACCEPT", preds[0]
            else:
                votes = {}
                for p_idx, c_val in zip(preds, confs):
                    if c_val >= threshold: votes[p_idx] = votes.get(p_idx, 0) + 1
                if votes and max(votes.values()) >= 3: final_decision, final_pred_idx = "ACCEPT", max(votes, key=votes.get)
        elif strategy == 'two_steps':
            if len(set(preds)) == 1 and all(c >= strategy_config['params']['t_unanimous'] for c in confs): final_decision, final_pred_idx = "ACCEPT", preds[0]
            else:
                sum_w = sum(confs); avg_probs = sum(p * w for p, w in zip(full_probs, confs)) / sum_w if sum_w > 1e-9 else torch.mean(torch.stack(full_probs), dim=0)
                final_conf, final_pred_idx_tensor = torch.max(avg_probs, dim=0)
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

# ==============================================================================
# ✨ 新增功能: 按类别生成详细性能报告
# ==============================================================================

def generate_per_class_report(raw_predictions, threshold, strategy_config, class_to_idx, output_path):
    """ (函数6) 📊 根据指定阈值，生成一份详细的、按类别划分的性能报告。"""
    print("\n" + "="*60 + f"\n🚀 Stage 6: Generating detailed per-class report at T={threshold}...\n" + "="*60)
    
    idx_to_class = {v: k for k, v in class_to_idx.items()}
    # 初始化统计数据结构
    per_class_stats = {idx: {'total': 0, 'accepted': 0, 'correct': 0} for idx in idx_to_class.keys()}
    
    # 遍历所有原始预测结果
    for res in raw_predictions:
        if res['type'] != 'known':
            continue
            
        true_idx = res['true_label_idx']
        # 确保 true_idx 存在于统计字典中
        if true_idx in per_class_stats:
            per_class_stats[true_idx]['total'] += 1
        else:
            # 如果出现意外的类别索引，则跳过
            continue

        preds, confs, full_probs = res['preds_indices'], res['confs'], res['full_probs']
        final_decision, final_pred_idx = "REJECT", -1
        strategy = strategy_config['name']
        
        # --- START: 决策逻辑 (与 analyze_failures 函数保持一致) ---
        if strategy == 'voting':
            votes = {}
            for p_idx, c_val in zip(preds, confs):
                if c_val >= threshold: votes[p_idx] = votes.get(p_idx, 0) + 1
            if votes and max(votes.values()) >= 3:
                final_decision, final_pred_idx = "ACCEPT", max(votes, key=votes.get)
        elif strategy == 'weighting':
            sum_w = sum(confs)
            avg_probs = sum(p * w for p, w in zip(full_probs, confs)) / sum_w if sum_w > 1e-9 else torch.mean(torch.stack(full_probs), dim=0)
            final_conf, final_pred_idx_tensor = torch.max(avg_probs, dim=0)
            if final_conf.item() >= threshold:
                final_decision, final_pred_idx = "ACCEPT", final_pred_idx_tensor.item()
        elif strategy == 'three_accept':
            if len(set(preds)) == 1:
                final_decision, final_pred_idx = "ACCEPT", preds[0]
            else:
                votes = {}
                for p_idx, c_val in zip(preds, confs):
                    if c_val >= threshold: votes[p_idx] = votes.get(p_idx, 0) + 1
                if votes and max(votes.values()) >= 3:
                    final_decision, final_pred_idx = "ACCEPT", max(votes, key=votes.get)
        elif strategy == 'two_steps':
            if len(set(preds)) == 1 and all(c >= strategy_config['params']['t_unanimous'] for c in confs):
                final_decision, final_pred_idx = "ACCEPT", preds[0]
            else:
                sum_w = sum(confs)
                avg_probs = sum(p * w for p, w in zip(full_probs, confs)) / sum_w if sum_w > 1e-9 else torch.mean(torch.stack(full_probs), dim=0)
                final_conf, final_pred_idx_tensor = torch.max(avg_probs, dim=0)
                if final_conf.item() >= threshold:
                    final_decision, final_pred_idx = "ACCEPT", final_pred_idx_tensor.item()
        # --- END: 决策逻辑 ---
        
        if final_decision == "ACCEPT":
            per_class_stats[true_idx]['accepted'] += 1
            if final_pred_idx == true_idx:
                per_class_stats[true_idx]['correct'] += 1

    report_data = []
    # 按照 class_to_idx 中的顺序（即按ID升序）生成报告
    sorted_class_items = sorted(class_to_idx.items(), key=lambda item: item[1])

    for class_name, class_idx in sorted_class_items:
        stats = per_class_stats.get(class_idx)
        if not stats or stats['total'] == 0:
            # 如果测试集中没有这个类的样本，可以跳过
            continue

        total = stats['total']
        accepted = stats['accepted']
        correct = stats['correct']

        acceptance_rate = (accepted / total * 100) if total > 0 else 0
        in_domain_accuracy = (correct / accepted * 100) if accepted > 0 else 0
        # 综合准确率 = (正确接受数 / 总数) * 100
        overall_accuracy = (correct / total * 100) if total > 0 else 0

        report_data.append({
            'ID': class_idx,
            '类别名': class_name,
            '已知类接受率(%)': acceptance_rate,
            '域内准确率(%)': in_domain_accuracy,
            '综合准确率(%)': overall_accuracy
        })

    df_report = pd.DataFrame(report_data)

    # 格式化输出，保留3位小数
    for col in ['已知类接受率(%)', '域内准确率(%)', '综合准确率(%)']:
        df_report[col] = df_report[col].apply(lambda x: f"{x:.3f}")

    df_report.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"✅ 已知类详细分类报告已保存至: '{output_path}'")


# ==============================================================================
# 🚀 主函数 (Orchestrator) - 高效版
# ==============================================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='High-Performance Open-Set Ensemble Analysis')
    parser.add_argument('--data_dir', type=str, required=True)
    parser.add_argument('--known_data_dir', type=str, default=None, help='Path to the known classes test set')
    parser.add_argument('--unknown_data_dir', type=str, default=None, help='Path to the unknown classes test set')
    parser.add_argument('--ensemble_config', type=str, default='modelEnsemble/model_ensemble_config.json')
    parser.add_argument('--custom_mappings_path', type=str, default='custom_mapping.json')
    parser.add_argument('--dataset_name', type=str, default='medicine_155')
    parser.add_argument('--img_size', type=int, default=640)
    parser.add_argument('--batch_size', type=int, default=16)
    parser.add_argument('--num_workers', type=int, default=4)
    parser.add_argument('--gpu', type=str, default='0')
    parser.add_argument('--output_dir', type=str, default=None)
    # --- MODIFIED: 接受一个或多个阈值 ---
    parser.add_argument('--analysis_threshold', type=float, nargs='+', default=[0.6, 0.56, 0.4, 0.2], help='用于生成详细报告的一个或多个特定阈值 (e.g., 0.7 0.85)')
    args = parser.parse_args()
    
    # 初始化配置
    configs.run_mode = 'test'
    configs.path_init()
    configs.img_size = args.img_size
    os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    with open(args.ensemble_config, 'r', encoding='utf-8') as f: model_configs = json.load(f)
    with open(args.custom_mappings_path, 'r', encoding='utf-8') as f: class_to_idx = json.load(f)[args.dataset_name]['class_to_idx']
    idx_to_class = {v: k for k, v in class_to_idx.items()}
    
    # --- 1. 定义统一的、高性能的 transform ---
    # 采用 Resize + CenterCrop 策略
    unified_transform = transforms.Compose([
        transforms.Resize(args.img_size),
        transforms.CenterCrop(args.img_size),
        transforms.ToTensor(),
        transforms.Normalize(configs.mean, configs.std)
    ])
    unified_transform_name = "Resize+CenterCrop" # 为报告头指定一个清晰的名称

    # --- 2. 加载模型 ---
    models = load_ensemble_models(model_configs, len(class_to_idx), configs.ckpts_dir, device)
    
    # --- 3. 创建 DataLoader，并将统一的 transform 传递给它 ---
    if args.known_data_dir and args.unknown_data_dir:
        known_loader = DataLoader(
            OpenSetDataset(args.known_data_dir, transform=unified_transform, class_to_idx=class_to_idx, is_known=True),
            batch_size=args.batch_size, num_workers=args.num_workers, collate_fn=collate_fn_filter_none
        )
        unknown_loader = DataLoader(
            OpenSetDataset(args.unknown_data_dir, transform=unified_transform, is_known=False),
            batch_size=args.batch_size, num_workers=args.num_workers, collate_fn=collate_fn_filter_none
        )
    else:
        known_loader = DataLoader(
            OpenSetDataset(os.path.join(args.data_dir, '0.已知'), transform=unified_transform, class_to_idx=class_to_idx, is_known=True),
            batch_size=args.batch_size, num_workers=args.num_workers, collate_fn=collate_fn_filter_none
        )
        unknown_loader = DataLoader(
            OpenSetDataset(os.path.join(args.data_dir, '1.未知'), transform=unified_transform, is_known=False),
            batch_size=args.batch_size, num_workers=args.num_workers, collate_fn=collate_fn_filter_none
        )

    # --- 4. 调用高效版的 get_raw_predictions ---
    raw_predictions = get_raw_predictions(models, known_loader, unknown_loader, device)
    
    # --- 5. 后续的指标计算和报告生成 ---
    print("\n" + "="*60 + "\n🚀 Stage 2: Calculating metrics for all strategies...\n" + "="*60)
    thresholds_to_test = np.arange(0.1, 1.01, 0.02)
    all_results = []
    for threshold in tqdm(thresholds_to_test, desc="Sweeping Thresholds"):
        t = round(threshold, 2)
        result_row = {'Threshold': t}
        for key, config in STRATEGY_CONFIGS.items():
            metrics = calculate_metrics_from_raw(raw_predictions, t, config['name'], **config['params'])
            result_row[f'{key}_Known_Accept_Rate'] = metrics['Known_Accept_Rate']
            result_row[f'{key}_Unknown_Reject_Rate'] = metrics['Unknown_Reject_Rate']
            result_row[f'{key}_In_Domain_Accuracy'] = metrics['In_Domain_Accuracy']
        all_results.append(result_row)
    results_df = pd.DataFrame(all_results)
    
    if args.output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(current_dir, 'test', 'full_analysis_report', f"{timestamp}_{args.dataset_name}")
    else:
        output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    # --- 6. 生成并保存配置报告 ---
    report_header_text = generate_report_header(model_configs, unified_transform_name)
    header_path = os.path.join(output_dir, 'ensemble_configuration.txt')
    with open(header_path, 'w', encoding='utf-8') as f:
        f.write(report_header_text)
    print(f"\n✅ Ensemble configuration summary saved to: {header_path}")

    # --- 7. 创建一个更具可读性的中文报告 ---
    CHINESE_COLUMN_MAP = {'Threshold': '阈值'}
    for key, plot_config in PLOT_CONFIGS.items():
        label = plot_config['label']
        CHINESE_COLUMN_MAP[f'{key}_Known_Accept_Rate'] = f"{label}_已知类接受率"
        CHINESE_COLUMN_MAP[f'{key}_Unknown_Reject_Rate'] = f"{label}_未知类拒绝率"
        CHINESE_COLUMN_MAP[f'{key}_In_Domain_Accuracy'] = f"{label}_域内准确率"
        CHINESE_COLUMN_MAP[f'{key}_Overall_Accuracy'] = f"{label}_已知类综合准确率"

    df_to_export = results_df.copy()
    for key in PLOT_CONFIGS.keys():
        known_accept_rate_col = f'{key}_Known_Accept_Rate'
        in_domain_accuracy_col = f'{key}_In_Domain_Accuracy'
        overall_accuracy_col = f'{key}_Overall_Accuracy'
        df_to_export[overall_accuracy_col] = df_to_export[known_accept_rate_col] * df_to_export[in_domain_accuracy_col] / 100

    final_column_order = ['阈值']
    for key in PLOT_CONFIGS.keys():
        label = PLOT_CONFIGS[key]['label']
        final_column_order.extend([
            f"{label}_已知类接受率",
            f"{label}_未知类拒绝率",
            f"{label}_已知类综合准确率",
            f"{label}_域内准确率",
        ])

    for col in df_to_export.columns:
        if col != 'Threshold':
            df_to_export[col] = df_to_export[col].apply(lambda x: f"{x:.3f}%")

    df_to_export.rename(columns=CHINESE_COLUMN_MAP, inplace=True)
    final_column_order_existing = [col for col in final_column_order if col in df_to_export.columns]
    df_to_export = df_to_export[final_column_order_existing]

    csv_path = os.path.join(output_dir, 'full_comparison_report_formatted.csv')
    df_to_export.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ Formatted Chinese CSV report with improved column order saved to: {csv_path}")

    # --- 8. 将配置报告传递给绘图函数 ---
    plot_path = os.path.join(output_dir, 'performance_tradeoff_curve.png')
    plot_performance_curves(results_df, plot_path)

    # --- 9. [MODIFIED] 运行后续详细分析 ---
    # 可在此处指定用于详细分析的策略，或将其作为命令行参数
    analysis_strategy_key = 'Voting'
    analysis_strategy_config = {**STRATEGY_CONFIGS[analysis_strategy_key], 'label': PLOT_CONFIGS[analysis_strategy_key]['label']}
    
    # 遍历所有指定的分析阈值
    for threshold_val in args.analysis_threshold:
        print(f"\n" + "="*80)
        print(f"🔬 开始为阈值 T={threshold_val} 运行详细分析 (策略: {analysis_strategy_config['label']})")
        print("="*80)
        
        # 文件名中用下划线替换小数点，避免歧义
        t_str = str(threshold_val).replace('.', '_')
        
        # 1. 瓶颈类别分析 (Stage 4)
        worst_classes_plot_path = os.path.join(output_dir, f'worst_classes_at_T{t_str}_{analysis_strategy_key}.png')
        plot_worst_classes(raw_predictions, threshold_val, analysis_strategy_config, idx_to_class, worst_classes_plot_path)
        
        # 2. 失败案例分析 (Stage 5)
        failure_report_path = os.path.join(output_dir, f'failure_analysis_at_T{t_str}_{analysis_strategy_key}.txt')
        analyze_failures(raw_predictions, threshold_val, analysis_strategy_config, idx_to_class, failure_report_path)
        
        # 3. [NEW] 已知类详细分类报告 (Stage 6)
        class_report_path = os.path.join(output_dir, f'per_class_report_at_T{t_str}_{analysis_strategy_key}.csv')
        generate_per_class_report(raw_predictions, threshold_val, analysis_strategy_config, class_to_idx, class_report_path)


    print("\n\n🎉 All analysis complete!")