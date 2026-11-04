#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文字体配置工具模块
用于解决Matplotlib绘图时中文显示问题
"""

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from typing import List, Optional

def get_available_chinese_fonts() -> List[str]:
    """
    获取系统中可用的中文字体列表
    
    Returns:
        List[str]: 可用的中文字体名称列表
    """
    # 常见中文字体名称模式
    chinese_font_patterns = [
        'SimHei', 'SimSun', 'Microsoft', 'WenQuanYi', 'FangSong', 
        'KaiTi', 'Noto', 'Source Han', 'Droid Sans Fallback'
    ]
    
    # 获取所有可用字体
    all_fonts = [f.name for f in fm.fontManager.ttflist]
    
    # 筛选出中文字体
    chinese_fonts = []
    for font_name in all_fonts:
        if any(pattern in font_name for pattern in chinese_font_patterns):
            chinese_fonts.append(font_name)
    
    # 添加一些常见的中文字体名称（即使系统中可能没有）
    common_chinese_fonts = [
        'WenQuanYi Zen Hei', 'SimHei', 'Microsoft YaHei', 
        'Noto Sans CJK SC', 'Noto Sans CJK', 'Source Han Sans CN',
        'DejaVu Sans', 'Droid Sans Fallback'
    ]
    
    # 合并并去重，保持顺序
    result_fonts = []
    for font in common_chinese_fonts:
        if font not in result_fonts:
            result_fonts.append(font)
    for font in chinese_fonts:
        if font not in result_fonts:
            result_fonts.append(font)
            
    return result_fonts

def setup_chinese_fonts(fallback_fonts: Optional[List[str]] = None, force: bool = False) -> bool:
    """
    设置Matplotlib的中文字体支持
    
    Args:
        fallback_fonts: 可选的备用字体列表
        force: 是否强制重新设置字体（即使已经设置过）
        
    Returns:
        bool: 是否成功设置中文字体
    """
    # 如果不是强制设置且已经设置过，则直接返回
    global __font_setup_done__
    if not force and 'setup_chinese_fonts' in globals() and __font_setup_done__:
        return True
    
    # 默认字体列表
    default_fonts = [
        'WenQuanYi Zen Hei', 'SimHei', 'Microsoft YaHei', 
        'Noto Sans CJK SC', 'Noto Sans CJK', 'Source Han Sans CN',
        'DejaVu Sans', 'Droid Sans Fallback', 'sans-serif'
    ]
    
    # 如果提供了备用字体，则使用备用字体
    if fallback_fonts:
        font_list = fallback_fonts + default_fonts
    else:
        font_list = default_fonts
    
    try:
        # 设置字体
        plt.rcParams['font.sans-serif'] = font_list
        plt.rcParams['axes.unicode_minus'] = False
        __font_setup_done__ = True
        return True
    except Exception as e:
        print(f"设置中文字体时出错: {e}")
        return False

def test_chinese_font_display() -> None:
    """
    测试中文字体显示功能
    """
    # 设置中文字体
    setup_chinese_fonts()
    
    # 创建测试图表
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # 添加中文文本
    ax.text(0.5, 0.7, '中文测试 - 模型训练结果', fontsize=16, ha='center')
    ax.text(0.5, 0.5, '准确率: 95.5%', fontsize=14, ha='center')
    ax.text(0.5, 0.3, '损失值: 0.123', fontsize=14, ha='center')
    
    # 设置坐标轴标签
    ax.set_xlabel('训练轮次 (Epoch)', fontsize=12)
    ax.set_ylabel('指标值', fontsize=12)
    ax.set_title('训练过程可视化', fontsize=14)
    
    # 显示网格
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # 显示图表
    plt.tight_layout()
    plt.show()
    
    print("中文字体测试完成！如果图表中的中文正常显示，则配置成功。")

# 创建一个全局标志，用于跟踪字体是否已设置
__font_setup_done__ = False

# 在模块导入时自动设置中文字体
setup_chinese_fonts()

# 更新全局标志
__font_setup_done__ = True

if __name__ == "__main__":
    # 运行测试
    test_chinese_font_display()