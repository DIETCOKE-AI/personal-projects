import os
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from datetime import datetime
from matplotlib.animation import FuncAnimation  # 新增导入

# 导入中文字体配置模块
try:
    from utils.chinese_font_config import setup_chinese_fonts
    CHINESE_FONT_SUPPORT = True
except ImportError:
    CHINESE_FONT_SUPPORT = False

class TrainingVisualizer:
    def __init__(self, log_dir, model_name, version, dataset=None, live_update=True):
        self.log_dir = log_dir
        self.model_name = model_name
        self.version = version
        self.dataset = dataset  # 保存数据集名称
        self.metrics_history = {
            'train_loss': [],
            'test_loss': [],
            'test_acc': [],
            'lr': []
        }
        # 设置中文字体
        if CHINESE_FONT_SUPPORT:
            setup_chinese_fonts(force=True)
        else:
            # 备用字体设置
            plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'SimHei', 'Microsoft YaHei', 'Noto Sans CJK SC', 'Noto Sans CJK', 'Source Han Sans CN', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
        # 替换seaborn样式为Matplotlib内置样式或移除
        try:
            plt.style.use('seaborn')
        except OSError:
            # 如果seaborn样式不可用，使用ggplot样式或不设置
            plt.style.use('ggplot')
        
        # 配置实时更新相关属性
        self.live_update = live_update
        self.fig, self.axes = None, None
        self.animation = None
        
        if self.live_update:
            plt.ion()  # 开启交互模式
            # 创建一个包含两个子图的图表
            self.fig, self.axes = plt.subplots(1, 2, figsize=(15, 6))
            window_title = f'训练监控 - {model_name}'
            if self.dataset:
                window_title += f'_{self.dataset}'
            window_title += f'_{version}'
            self.fig.canvas.manager.set_window_title(window_title)
            
            # 设置 FuncAnimation，间隔200毫秒更新一次
            self.animation = FuncAnimation(
                self.fig, 
                self.update_live_plots_animation, 
                interval=200,  # 更新间隔(毫秒)
                blit=False  # 不使用blitting以简化实现
            )

    def record_metrics(self, epoch, train_loss, test_loss, test_acc, lr):
        """记录每个epoch的指标"""
        self.metrics_history['train_loss'].append(train_loss)
        self.metrics_history['test_loss'].append(test_loss)
        self.metrics_history['test_acc'].append(test_acc)
        self.metrics_history['lr'].append(lr)
        
        # FuncAnimation会自动处理更新，这里不需要额外调用
        # 但如果想立即更新可以添加：plt.draw()

    def update_live_plots_animation(self, frame):
        """使用FuncAnimation更新图表的回调函数"""
        if not self.live_update or self.fig is None:
            return
        
        epochs = range(1, len(self.metrics_history['train_loss']) + 1)
        
        # 清空并更新损失曲线图
        self.axes[0].clear()
        if len(epochs) > 0:
            # 使用小圆圈标注训练损失点，小方块标注测试损失点
            self.axes[0].plot(epochs, self.metrics_history['train_loss'], 'b-o', label='训练损失', linewidth=1.5, markersize=4)
            if len(self.metrics_history['test_loss']) > 0:
                self.axes[0].plot(epochs, self.metrics_history['test_loss'], 'r-s', label='测试损失', linewidth=1.5, markersize=4)
        
        loss_title = '训练和测试损失曲线'
        if self.dataset:
            loss_title += f' ({self.model_name}, {self.dataset})'
        self.axes[0].set_title(loss_title)
        self.axes[0].set_xlabel('Epoch')
        self.axes[0].set_ylabel('损失值')
        self.axes[0].legend()
        
        # 设置正方形网格
        self.axes[0].grid(True, linestyle='--', alpha=0.7)
        # 统一坐标轴标度
        self.axes[0].set_aspect('auto', adjustable='datalim')
        
        # 清空并更新准确率曲线图
        self.axes[1].clear()
        if len(epochs) > 0 and len(self.metrics_history['test_acc']) > 0:
            # 使用小圆圈标注准确率点
            self.axes[1].plot(epochs, self.metrics_history['test_acc'], 'g-o', label='测试准确率', linewidth=1.5, markersize=4)
        
        acc_title = '测试准确率曲线'
        if self.dataset:
            acc_title += f' ({self.model_name}, {self.dataset})'
        self.axes[1].set_title(acc_title)
        self.axes[1].set_xlabel('Epoch')
        self.axes[1].set_ylabel('准确率')
        self.axes[1].legend()
        
        # 设置正方形网格
        self.axes[1].grid(True, linestyle='--', alpha=0.7)
        # 统一坐标轴标度
        self.axes[1].set_aspect('auto', adjustable='datalim')
        
        # 设置坐标轴范围，使曲线更美观
        if len(epochs) > 1:
            self.axes[0].set_ylim(max(0, min(self.metrics_history['train_loss'] + self.metrics_history['test_loss']) * 0.9), 
                                  max(self.metrics_history['train_loss'] + self.metrics_history['test_loss']) * 1.1)
            if len(self.metrics_history['test_acc']) > 0:
                self.axes[1].set_ylim(max(0, min(self.metrics_history['test_acc']) * 0.9), 
                                      min(1.0, max(self.metrics_history['test_acc']) * 1.1))
        
        # 调整布局
        self.fig.tight_layout()

    def plot_loss_curve(self, save_path=None):
        """绘制训练和测试损失曲线"""
        # 确保中文字体设置
        if CHINESE_FONT_SUPPORT:
            setup_chinese_fonts(force=True)
        else:
            # 备用字体设置
            plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'SimHei', 'Microsoft YaHei', 'Noto Sans CJK SC', 'Noto Sans CJK', 'Source Han Sans CN', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            
        plt.figure(figsize=(10, 6))
        epochs = range(1, len(self.metrics_history['train_loss']) + 1)
        # 使用小圆圈标注训练损失点，小方块标注测试损失点
        plt.plot(epochs, self.metrics_history['train_loss'], 'b-o', label='训练损失', linewidth=1.5, markersize=4)
        plt.plot(epochs, self.metrics_history['test_loss'], 'r-s', label='测试损失', linewidth=1.5, markersize=4)
        loss_title = '训练和测试损失曲线'
        if self.dataset:
            loss_title += f' ({self.model_name}, {self.dataset})'
        plt.title(loss_title)
        plt.xlabel('Epoch')
        plt.ylabel('损失值')
        plt.legend()
        # 设置正方形网格
        plt.grid(True, linestyle='--', alpha=0.7)
        # 统一坐标轴标度
        plt.gca().set_aspect('auto', adjustable='datalim')
        if save_path:
            plt.savefig(save_path, dpi=300)
        else:
            plt.show()
        plt.close()

    def plot_accuracy_curve(self, save_path=None):
        """绘制测试准确率曲线"""
        # 确保中文字体设置
        if CHINESE_FONT_SUPPORT:
            setup_chinese_fonts(force=True)
        else:
            # 备用字体设置
            plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'SimHei', 'Microsoft YaHei', 'Noto Sans CJK SC', 'Noto Sans CJK', 'Source Han Sans CN', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            
        plt.figure(figsize=(10, 6))
        epochs = range(1, len(self.metrics_history['test_acc']) + 1)
        # 使用小圆圈标注准确率点
        plt.plot(epochs, self.metrics_history['test_acc'], 'g-o', label='测试准确率', linewidth=1.5, markersize=4)
        acc_title = '测试准确率曲线'
        if self.dataset:
            acc_title += f' ({self.model_name}, {self.dataset})'
        plt.title(acc_title)
        plt.xlabel('Epoch')
        plt.ylabel('准确率')
        plt.legend()
        # 设置正方形网格
        plt.grid(True, linestyle='--', alpha=0.7)
        # 统一坐标轴标度
        plt.gca().set_aspect('auto', adjustable='datalim')
        if save_path:
            plt.savefig(save_path, dpi=300)
        else:
            plt.show()
        plt.close()

    def plot_lr_curve(self, save_path=None):
        """绘制学习率变化曲线"""
        # 确保中文字体设置
        if CHINESE_FONT_SUPPORT:
            setup_chinese_fonts(force=True)
        else:
            # 备用字体设置
            plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'SimHei', 'Microsoft YaHei', 'Noto Sans CJK SC', 'Noto Sans CJK', 'Source Han Sans CN', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            
        plt.figure(figsize=(10, 6))
        epochs = range(1, len(self.metrics_history['lr']) + 1)
        # 使用小圆圈标注学习率点
        plt.plot(epochs, self.metrics_history['lr'], 'm-o', label='学习率', linewidth=1.5, markersize=4)
        lr_title = '学习率变化曲线'
        if self.dataset:
            lr_title += f' ({self.model_name}, {self.dataset})'
        plt.title(lr_title)
        plt.xlabel('Epoch')
        plt.ylabel('学习率')
        plt.legend()
        # 设置正方形网格
        plt.grid(True, linestyle='--', alpha=0.7)
        # 统一坐标轴标度
        plt.gca().set_aspect('auto', adjustable='datalim')
        if save_path:
            plt.savefig(save_path, dpi=300)
        else:
            plt.show()
        plt.close()

    def plot_class_weights(self, class_weights, class_names, save_path=None):
        """绘制类别权重柱状图"""
        # 确保中文字体设置
        if CHINESE_FONT_SUPPORT:
            setup_chinese_fonts(force=True)
        else:
            # 备用字体设置
            plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'SimHei', 'Microsoft YaHei', 'Noto Sans CJK SC', 'Noto Sans CJK', 'Source Han Sans CN', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            
        plt.figure(figsize=(12, 8))
        sorted_indices = np.argsort(class_weights)[::-1]
        sorted_weights = class_weights[sorted_indices]
        sorted_names = [class_names[i] for i in sorted_indices]
        plt.bar(range(len(sorted_weights)), sorted_weights)
        weights_title = '类别权重分布'
        if self.dataset:
            weights_title += f' ({self.model_name}, {self.dataset})'
        plt.title(weights_title)
        plt.xlabel('类别')
        plt.ylabel('权重值')
        plt.xticks(range(len(sorted_names)), sorted_names, rotation=90)
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300)
        else:
            plt.show()
        plt.close()

    def save_all_plots(self):
        """保存所有图表到日志目录"""
        plots_dir = os.path.join(self.log_dir, 'plots')
        os.makedirs(plots_dir, exist_ok=True)
        
        # 构建固定文件名，不包含时间戳，以便覆盖
        base_filename = f'{self.model_name}'
        if self.dataset:
            base_filename += f'_{self.dataset}'
        base_filename += f'_{self.version}'
        
        self.plot_loss_curve(os.path.join(plots_dir, f'{base_filename}_loss_curve.png'))
        self.plot_accuracy_curve(os.path.join(plots_dir, f'{base_filename}_accuracy_curve.png'))
        self.plot_lr_curve(os.path.join(plots_dir, f'{base_filename}_lr_curve.png'))

        print(f'[INFO] 所有训练图表已保存至: {plots_dir}')
        
        # 训练结束后关闭交互模式
        if self.live_update:
            plt.ioff() 
            plt.close('all')
