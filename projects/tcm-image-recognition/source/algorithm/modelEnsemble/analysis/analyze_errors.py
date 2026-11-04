#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误分析脚本
分析模型集成预测结果中的错误情况，包括：
1. 已知类别的误分类（真实类别与预测类别不符）
2. 已知样本未被接受（被拒绝）
3. 未知样本的错误接受

使用方法:
python analyze_errors.py --csv_file path/to/detailed_predictions.csv
"""

import pandas as pd
import argparse
import os
import sys
from collections import defaultdict, Counter
from datetime import datetime

def analyze_errors(csv_file, output_file=None):
    """
    分析预测错误
    
    Args:
        csv_file: CSV文件路径
        output_file: 输出文件路径，如果为None则自动生成
    """
    print(f"正在分析文件: {csv_file}")
    print("=" * 80)
    
    # 读取CSV文件
    try:
        df = pd.read_csv(csv_file)
        print(f"成功读取 {len(df)} 条记录")
    except Exception as e:
        print(f"读取CSV文件失败: {e}")
        return
    
    # 如果没有指定输出文件，则自动生成
    if output_file is None:
        # 获取输入文件的目录和基础名称
        input_dir = os.path.dirname(csv_file)
        input_basename = os.path.basename(csv_file)
        # 生成输出文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"error_analysis_report_{timestamp}.txt"
        output_file = os.path.join(input_dir, output_filename)
    
    # 重定向stdout到文件
    original_stdout = sys.stdout
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # 同时输出到控制台和文件
            class TeeOutput:
                def __init__(self, *files):
                    self.files = files
                def write(self, obj):
                    for f in self.files:
                        f.write(obj)
                        f.flush()
                def flush(self):
                    for f in self.files:
                        f.flush()
            
            sys.stdout = TeeOutput(original_stdout, f)
            
            # 打印分析头部信息
            print(f"错误分析报告")
            print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"输入文件: {csv_file}")
            print(f"输出文件: {output_file}")
            print("=" * 80)
            
            # 统计变量
            known_misclassified = defaultdict(list)  # 已知类别误分类: {真实类别: [(预测类别, 图片路径), ...]}
            known_rejected = defaultdict(list)       # 已知类别被拒绝: {真实类别: [图片路径, ...]}
            unknown_accepted = defaultdict(list)     # 未知类别被接受: {真实类别: [(预测类别, 图片路径), ...]}
            
            total_samples = len(df)
            correct_predictions = 0
            
            for idx, row in df.iterrows():
                image_path = row['图片路径']
                true_class = row['真实类别']
                decision = row['集成决策']
                predicted_class = row['预测类别'] if pd.notna(row['预测类别']) else 'REJECT'
                is_correct = row['是否正确']
                
                # 判断是否为已知类别（通过路径判断）
                if "0.已知" in image_path:
                    # 已知类别
                    if decision == "REJECT":
                        # 已知样本被拒绝
                        known_rejected[true_class].append(image_path)
                    elif predicted_class != true_class:
                        # 已知样本被误分类
                        known_misclassified[true_class].append((predicted_class, image_path))
                    else:
                        # 正确预测
                        correct_predictions += 1
                elif "1.未知" in image_path:
                    # 未知类别 - 从路径中提取真实类别名称
                    # 路径格式: /path/to/1.未知/类别名/图片文件
                    path_parts = image_path.split('/')
                    actual_unknown_class = None
                    for i, part in enumerate(path_parts):
                        if "1.未知" in part and i + 1 < len(path_parts):
                            actual_unknown_class = path_parts[i + 1]
                            break
                    
                    if actual_unknown_class is None:
                        actual_unknown_class = "UNKNOWN_CLASS"  # 备用名称
                    
                    if decision == "ACCEPT":
                        # 未知样本被错误接受
                        unknown_accepted[actual_unknown_class].append((predicted_class, image_path))
                    else:
                        # 未知样本被正确拒绝
                        correct_predictions += 1
                else:
                    # 无法判断已知/未知，根据is_correct字段
                    if is_correct:
                        correct_predictions += 1
            
            # 打印统计结果
            print("\n📊 总体统计:")
            print(f"总样本数: {total_samples}")
            print(f"正确预测: {correct_predictions}")
            print(f"错误预测: {total_samples - correct_predictions}")
            print(f"准确率: {correct_predictions/total_samples*100:.2f}%")
            
            # 1. 已知类别误分类统计
            print("\n🔴 已知类别误分类统计:")
            print("-" * 60)
            if known_misclassified:
                total_misclassified = 0
                for true_class, predictions in known_misclassified.items():
                    print(f"\n真实类别 '{true_class}' 被误分类 {len(predictions)} 次:")
                    # 统计被误分类为哪些类别
                    pred_counter = Counter([pred[0] for pred in predictions])
                    for pred_class, count in pred_counter.most_common():
                        print(f"  → 被误分类为 '{pred_class}': {count} 次")
                    total_misclassified += len(predictions)
                print(f"\n总误分类次数: {total_misclassified}")
            else:
                print("没有发现已知类别的误分类!")
            
            # 2. 已知样本被拒绝统计
            print("\n🚫 已知样本被拒绝统计:")
            print("-" * 60)
            if known_rejected:
                total_rejected = 0
                for true_class, paths in known_rejected.items():
                    print(f"真实类别 '{true_class}' 被拒绝: {len(paths)} 次")
                    total_rejected += len(paths)
                print(f"\n总拒绝次数: {total_rejected}")
            else:
                print("没有发现已知样本被拒绝!")
            
            # 3. 未知样本错误接受统计
            print("\n❌ 未知样本错误接受统计:")
            print("-" * 60)
            if unknown_accepted:
                total_false_accepted = 0
                for true_unknown_class, predictions in unknown_accepted.items():
                    print(f"\n未知类别 '{true_unknown_class}' 被错误接受 {len(predictions)} 次:")
                    # 统计被误识别为哪些已知类别
                    pred_counter = Counter([pred[0] for pred in predictions])
                    for pred_class, count in pred_counter.most_common():
                        print(f"  → 被误识别为 '{pred_class}': {count} 次")
                    total_false_accepted += len(predictions)
                print(f"\n总错误接受次数: {total_false_accepted}")
            else:
                print("没有发现未知样本被错误接受!")
            
            # 4. 详细错误列表（可选，如果需要具体的图片路径）
            print("\n📋 详细错误信息:")
            print("-" * 60)
            
            # 误分类详情
            if known_misclassified:
                print("\n误分类详情 (前10个):")
                count = 0
                for true_class, predictions in known_misclassified.items():
                    for pred_class, image_path in predictions[:3]:  # 每个类别只显示前3个
                        if count < 10:
                            filename = os.path.basename(image_path)
                            print(f"  {filename}: {true_class} → {pred_class}")
                            count += 1
                        else:
                            break
                    if count >= 10:
                        break
            
            # 被拒绝详情
            if known_rejected:
                print("\n被拒绝详情 (前5个):")
                count = 0
                for true_class, paths in known_rejected.items():
                    for image_path in paths[:2]:  # 每个类别只显示前2个
                        if count < 5:
                            filename = os.path.basename(image_path)
                            print(f"  {filename}: {true_class} → REJECTED")
                            count += 1
                        else:
                            break
                    if count >= 5:
                        break
            
            # 错误接受详情
            if unknown_accepted:
                print("\n错误接受详情 (前10个):")
                count = 0
                for true_unknown_class, predictions in unknown_accepted.items():
                    for pred_class, image_path in predictions[:3]:  # 每个类别只显示前3个
                        if count < 10:
                            filename = os.path.basename(image_path)
                            print(f"  {filename}: {true_unknown_class} → {pred_class}")
                            count += 1
                        else:
                            break
                    if count >= 10:
                        break
            
            print("\n" + "=" * 80)
            print("分析完成!")
    
    finally:
        # 恢复stdout
        sys.stdout = original_stdout
    
    print(f"\n分析报告已保存到: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='分析模型预测错误')
    parser.add_argument('--csv_file', type=str, required=True, 
                        help='预测结果CSV文件路径')
    parser.add_argument('--output_file', type=str, default=None,
                        help='输出报告文件路径（可选，默认自动生成）')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.csv_file):
        print(f"错误: 文件不存在 {args.csv_file}")
        return
    
    analyze_errors(args.csv_file, args.output_file)

if __name__ == "__main__":
    main()