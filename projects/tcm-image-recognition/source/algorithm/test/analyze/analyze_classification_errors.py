#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版图像分类错误分析工具
支持通过命令行参数指定CSV文件路径和输出目录
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from collections import defaultdict, Counter
import os
import sys
import argparse

# 添加项目根目录到Python路径，以便导入自定义模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# 导入中文字体配置模块
try:
    from utils.chinese_font_config import setup_chinese_fonts
    HAS_CHINESE_FONT_MODULE = True
except ImportError:
    HAS_CHINESE_FONT_MODULE = False
    print("警告: 无法导入中文字体配置模块，图表中的中文可能无法正常显示")

def analyze_classification_errors(csv_file_path, output_dir=None):
    """
    分析图像分类结果中的错误信息并生成详细报告
    
    参数:
    csv_file_path: CSV文件路径
    output_dir: 输出目录路径，如果为None则使用CSV文件所在目录下的error_analysis子目录
    """
    
    # 如果未指定输出目录，则使用CSV文件所在目录下的error_analysis子目录
    if output_dir is None:
        csv_dir = os.path.dirname(csv_file_path)
        output_dir = os.path.join(csv_dir, "error_analysis")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 读取CSV文件
    df = pd.read_csv(csv_file_path)
    
    # 统计基本信息
    total_samples = len(df)
    correct_predictions = df['is_correct'].sum()
    error_predictions = total_samples - correct_predictions
    accuracy = correct_predictions / total_samples
    
    print("=" * 60)
    print("图像分类错误详细分析报告")
    print("=" * 60)
    print(f"分析文件: {csv_file_path}")
    print(f"总样本数: {total_samples}")
    print(f"正确预测: {correct_predictions}")
    print(f"错误预测: {error_predictions}")
    print(f"准确率: {accuracy:.4f} ({accuracy*100:.2f}%)")
    print()
    
    # 筛选出错误分类的样本
    error_df = df[df['is_correct'] == False]
    
    if error_predictions == 0:
        print("恭喜！没有错误分类的样本。")
        return
    
    # 1. 按真实类别统计错误数量
    errors_by_true_class = error_df['true_class'].value_counts()
    print("按真实类别统计的错误数量 (前15类):")
    print("-" * 40)
    for true_class, count in errors_by_true_class.head(15).items():
        class_total = len(df[df['true_class'] == true_class])
        error_rate = count / class_total if class_total > 0 else 0
        print(f"{true_class}: {count} (占该类别的{error_rate:.2%})")
    print()
    
    # 2. 按预测错误的类别统计
    error_predictions_count = error_df['predicted_class'].value_counts()
    print("被错误预测为其他类别的统计 (前15类):")
    print("-" * 40)
    for predicted_class, count in error_predictions_count.head(15).items():
        print(f"{predicted_class}: {count}")
    print()
    
    # 3. 最常见的错误分类对
    error_pairs = error_df.groupby(['true_class', 'predicted_class']).size().sort_values(ascending=False)
    print("最常见的错误分类对 (前15对):")
    print("-" * 40)
    for (true_class, predicted_class), count in error_pairs.head(15).items():
        print(f"{true_class} -> {predicted_class}: {count}")
    print()
    
    # 4. 错误分类的置信度分析
    print("错误分类的置信度分析:")
    print("-" * 40)
    print(f"平均置信度: {error_df['confidence'].mean():.4f}")
    print(f"最高置信度: {error_df['confidence'].max():.4f}")
    print(f"最低置信度: {error_df['confidence'].min():.4f}")
    print()
    
    # 5. 按置信度区间统计错误
    print("按置信度区间统计错误:")
    print("-" * 40)
    bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    error_by_confidence = pd.cut(error_df['confidence'], bins=bins).value_counts().sort_index()
    for interval, count in error_by_confidence.items():
        print(f"{interval}: {count}")
    print()
    
    # 6. 高置信度错误 (置信度 > 0.8 但分类错误)
    high_confidence_errors = error_df[error_df['confidence'] > 0.8]
    print(f"高置信度错误 (置信度 > 0.8): {len(high_confidence_errors)}")
    if len(high_confidence_errors) > 0:
        print("高置信度错误分类对 (前10对):")
        high_conf_errors_pairs = high_confidence_errors.groupby(['true_class', 'predicted_class']).size().sort_values(ascending=False)
        for (true_class, predicted_class), count in high_conf_errors_pairs.head(10).items():
            print(f"  {true_class} -> {predicted_class}: {count}")
    print()
    
    # 7. 生成详细错误报告CSV文件
    error_analysis_file = os.path.join(output_dir, 'detailed_error_analysis.csv')
    error_df.to_csv(error_analysis_file, index=False, encoding='utf-8')
    print(f"详细错误信息已保存到: {error_analysis_file}")
    
    # 8. 生成错误统计汇总报告
    summary_data = []
    for true_class, count in errors_by_true_class.items():
        class_total = len(df[df['true_class'] == true_class])
        error_rate = count / class_total if class_total > 0 else 0
        summary_data.append({
            '真实类别': true_class,
            '错误数量': count,
            '类别总数': class_total,
            '错误率': f"{error_rate:.2%}"
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_df = summary_df.sort_values('错误数量', ascending=False)
    summary_file = os.path.join(output_dir, 'error_summary_by_class.csv')
    summary_df.to_csv(summary_file, index=False, encoding='utf-8')
    print(f"按类别错误汇总已保存到: {summary_file}")
    
    # 9. 生成最常见的错误对报告
    error_pairs_data = []
    for (true_class, predicted_class), count in error_pairs.items():
        error_pairs_data.append({
            '真实类别': true_class,
            '错误预测为': predicted_class,
            '错误次数': count
        })
    
    error_pairs_df = pd.DataFrame(error_pairs_data)
    error_pairs_file = os.path.join(output_dir, 'common_error_pairs.csv')
    error_pairs_df.to_csv(error_pairs_file, index=False, encoding='utf-8')
    print(f"常见错误对已保存到: {error_pairs_file}")
    
    # 10. 生成可视化图表
    try:
        create_visualizations(error_df, output_dir)
    except Exception as e:
        print(f"生成可视化图表时出错: {str(e)}")
    
    return {
        'total_samples': total_samples,
        'correct_predictions': correct_predictions,
        'error_predictions': error_predictions,
        'accuracy': accuracy,
        'errors_by_true_class': errors_by_true_class,
        'error_predictions_count': error_predictions_count,
        'error_pairs': error_pairs
    }

def create_visualizations(error_df, output_dir):
    """
    创建错误分析的可视化图表
    """
    # 设置图表样式
    try:
        plt.style.use('seaborn-v0_8')
    except:
        try:
            plt.style.use('seaborn')
        except:
            try:
                plt.style.use('darkgrid')
            except:
                pass  # 使用默认样式
    
    # 设置中文字体支持
    if HAS_CHINESE_FONT_MODULE:
        setup_chinese_fonts(force=True)
    else:
        # 备用设置
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False
    
    fig_size = (12, 8)
    
    # 1. 错误数量最多的前10个真实类别
    errors_by_true_class = error_df['true_class'].value_counts().head(10)
    plt.figure(figsize=fig_size)
    errors_by_true_class.plot(kind='bar')
    plt.title('错误数量最多的前10个真实类别', fontsize=16)
    plt.xlabel('类别', fontsize=12)
    plt.ylabel('错误数量', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'top_10_error_classes.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print("图表已保存: top_10_error_classes.png")
    
    # 2. 被错误预测为最多的前10个类别
    error_predictions_count = error_df['predicted_class'].value_counts().head(10)
    plt.figure(figsize=fig_size)
    error_predictions_count.plot(kind='bar')
    plt.title('被错误预测为最多的前10个类别', fontsize=16)
    plt.xlabel('类别', fontsize=12)
    plt.ylabel('被错误预测次数', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'top_10_misclassified_as.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print("图表已保存: top_10_misclassified_as.png")
    
    # 3. 错误置信度分布直方图
    plt.figure(figsize=fig_size)
    plt.hist(error_df['confidence'], bins=20, edgecolor='black', alpha=0.7)
    plt.title('错误分类的置信度分布', fontsize=16)
    plt.xlabel('置信度', fontsize=12)
    plt.ylabel('错误数量', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'error_confidence_distribution.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print("图表已保存: error_confidence_distribution.png")
    
    # 4. 最常见的错误对热力图（前15对）
    error_pairs = error_df.groupby(['true_class', 'predicted_class']).size().sort_values(ascending=False).head(15)
    error_pairs_df = error_pairs.reset_index()
    error_pairs_df.columns = ['真实类别', '预测类别', '错误次数']
    
    # 创建透视表
    pivot_table = error_pairs_df.pivot_table(values='错误次数', index='真实类别', columns='预测类别', fill_value=0)
    
    plt.figure(figsize=(12, 10))
    sns.heatmap(pivot_table, annot=True, fmt='d', cmap='YlOrRd', cbar_kws={'label': '错误次数'})
    plt.title('最常见的错误分类对热力图', fontsize=16)
    plt.xlabel('预测类别', fontsize=12)
    plt.ylabel('真实类别', fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'common_error_pairs_heatmap.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print("图表已保存: common_error_pairs_heatmap.png")

def main():
    """主函数，处理命令行参数"""
    parser = argparse.ArgumentParser(description='图像分类错误分析工具')
    parser.add_argument('csv_file', help='CSV文件路径')
    parser.add_argument('-o', '--output', help='输出目录路径（可选）')
    
    args = parser.parse_args()
    
    # 检查输入文件是否存在
    if not os.path.exists(args.csv_file):
        print(f"错误: 文件 '{args.csv_file}' 不存在")
        sys.exit(1)
    
    # 执行错误分析
    try:
        results = analyze_classification_errors(args.csv_file, args.output)
    except Exception as e:
        print(f"分析过程中出现错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()