#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义数据预处理变换类
包含ROI聚焦策略、细粒度特征增强策略和类别平衡增强策略
"""

import torch
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("Warning: cv2 not available. ROI and CLAHE transforms will be disabled.")
import random
from torchvision import transforms
import warnings

class ROIExtractTransform(object):
    """
    ROI聚焦策略：通过边缘检测提取药材主体区域，减少背景干扰
    适用于背景复杂的药材图像
    """
    def __init__(self, edge_low_threshold=50, edge_high_threshold=150, 
                 fill_color=(128, 128, 128), min_area_ratio=0.01):
        """
        Args:
            edge_low_threshold: Canny边缘检测低阈值
            edge_high_threshold: Canny边缘检测高阈值
            fill_color: 填充背景的颜色 (R, G, B)
            min_area_ratio: ROI最小面积比例，小于此比例则使用原图
        """
        self.edge_low = edge_low_threshold
        self.edge_high = edge_high_threshold
        self.fill_color = fill_color
        self.min_area_ratio = min_area_ratio
        
    def __call__(self, img):
        """
        Args:
            img (PIL Image): 输入的PIL图像
        Returns:
            PIL Image: 提取ROI后的图像
        """
        if not CV2_AVAILABLE:
            # 如果没有cv2，直接返回原图
            return img
            
        # 转换为numpy数组
        img_array = np.array(img)
        original_size = img_array.shape[:2]
        
        # 转换为灰度图进行边缘检测
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
            
        # Canny边缘检测
        edges = cv2.Canny(gray, self.edge_low, self.edge_high)
        
        # 形态学操作，填充边缘间的空隙
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        edges = cv2.morphologyEx(edges, cv2.MORPH_DILATE, kernel)
        
        # 查找轮廓
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            # 如果没有找到轮廓，返回原图
            return img
            
        # 找到最大轮廓
        max_contour = max(contours, key=cv2.contourArea)
        contour_area = cv2.contourArea(max_contour)
        total_area = original_size[0] * original_size[1]
        
        # 如果ROI面积太小，返回原图
        if contour_area / total_area < self.min_area_ratio:
            return img
            
        # 创建掩码
        mask = np.zeros(gray.shape, dtype=np.uint8)
        cv2.fillPoly(mask, [max_contour], 255)
        
        # 创建输出图像
        if len(img_array.shape) == 3:
            result = np.full_like(img_array, self.fill_color)
            for c in range(3):
                result[:, :, c] = np.where(mask > 0, img_array[:, :, c], self.fill_color[c])
        else:
            result = np.where(mask > 0, img_array, self.fill_color[0])
            
        return Image.fromarray(result)
    
    def __repr__(self):
        return f'{self.__class__.__name__}(edge_low={self.edge_low}, edge_high={self.edge_high})'


class CLAHETransform(object):
    """
    对比度受限的自适应直方图均衡化，增强局部细节
    适用于需要突出纹理特征的药材图像
    """
    def __init__(self, clip_limit=2.0, tile_grid_size=(8, 8)):
        """
        Args:
            clip_limit: 对比度限制阈值
            tile_grid_size: 网格大小
        """
        self.clip_limit = clip_limit
        self.tile_grid_size = tile_grid_size
        
    def __call__(self, img):
        """
        Args:
            img (PIL Image): 输入的PIL图像
        Returns:
            PIL Image: CLAHE处理后的图像
        """
        if not CV2_AVAILABLE:
            # 如果没有cv2，直接返回原图
            return img
            
        # 转换为numpy数组
        img_array = np.array(img)
        
        if len(img_array.shape) == 3:
            # RGB图像，转换为LAB色彩空间
            lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
            
            # 创建CLAHE对象
            clahe = cv2.createCLAHE(clipLimit=self.clip_limit, tileGridSize=self.tile_grid_size)
            
            # 只对L通道（亮度）应用CLAHE
            lab[:, :, 0] = clahe.apply(lab[:, :, 0])
            
            # 转换回RGB
            result = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
        else:
            # 灰度图像
            clahe = cv2.createCLAHE(clipLimit=self.clip_limit, tileGridSize=self.tile_grid_size)
            result = clahe.apply(img_array)
            
        return Image.fromarray(result)
    
    def __repr__(self):
        return f'{self.__class__.__name__}(clip_limit={self.clip_limit}, tile_grid_size={self.tile_grid_size})'


class RandomEraseTransform(object):
    """
    随机擦除变换，随机遮挡图像的小区域
    强迫模型关注多个特征而不是依赖单一特征
    """
    def __init__(self, probability=0.5, scale=(0.02, 0.33), ratio=(0.3, 3.3), 
                 value=0, inplace=False):
        """
        Args:
            probability: 应用变换的概率
            scale: 擦除区域面积的比例范围
            ratio: 擦除区域的宽高比范围
            value: 填充值，可以是int、float、tuple或'random'
            inplace: 是否就地修改
        """
        self.probability = probability
        self.scale = scale
        self.ratio = ratio
        self.value = value
        self.inplace = inplace
        
    def __call__(self, img):
        """
        Args:
            img (PIL Image): 输入的PIL图像
        Returns:
            PIL Image: 随机擦除后的图像
        """
        if random.random() > self.probability:
            return img
            
        img_array = np.array(img)
        if not self.inplace:
            img_array = img_array.copy()
            
        height, width = img_array.shape[:2]
        area = height * width
        
        # 随机选择擦除区域的面积和宽高比
        target_area = random.uniform(*self.scale) * area
        aspect_ratio = random.uniform(*self.ratio)
        
        h = int(round(np.sqrt(target_area * aspect_ratio)))
        w = int(round(np.sqrt(target_area / aspect_ratio)))
        
        if w < width and h < height:
            x1 = random.randint(0, width - w)
            y1 = random.randint(0, height - h)
            
            if self.value == 'random':
                # 使用随机值填充
                if len(img_array.shape) == 3:
                    fill_value = np.random.randint(0, 256, (h, w, img_array.shape[2]), dtype=img_array.dtype)
                else:
                    fill_value = np.random.randint(0, 256, (h, w), dtype=img_array.dtype)
            else:
                fill_value = self.value
                
            img_array[y1:y1+h, x1:x1+w] = fill_value
            
        return Image.fromarray(img_array)
    
    def __repr__(self):
        return f'{self.__class__.__name__}(p={self.probability}, scale={self.scale}, ratio={self.ratio})'


class MixUpTransform(object):
    """
    MixUp数据增强，将两张图像线性混合
    特别适用于类别不平衡的数据集
    """
    def __init__(self, alpha=0.2, probability=0.5):
        """
        Args:
            alpha: Beta分布的参数，控制混合比例
            probability: 应用MixUp的概率
        """
        self.alpha = alpha
        self.probability = probability
        
    def __call__(self, img):
        """
        注意：这个版本只是为了接口一致性，真正的MixUp需要在数据加载器层面实现
        因为需要访问其他样本
        """
        # 在单个transform中无法实现真正的MixUp
        # 这里只是一个占位符实现
        return img
    
    def __repr__(self):
        return f'{self.__class__.__name__}(alpha={self.alpha}, p={self.probability})'


class AdaptiveAugmentTransform(object):
    """
    自适应增强策略，根据图像特征动态调整增强强度
    """
    def __init__(self, base_probability=0.5):
        """
        Args:
            base_probability: 基础增强概率
        """
        self.base_probability = base_probability
        
    def _calculate_image_complexity(self, img_array):
        """计算图像复杂度（基于边缘密度）"""
        if not CV2_AVAILABLE:
            # 如果没有cv2，返回默认复杂度
            return 0.1
            
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY) if len(img_array.shape) == 3 else img_array
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
        return edge_density
        
    def __call__(self, img):
        """
        Args:
            img (PIL Image): 输入的PIL图像
        Returns:
            PIL Image: 自适应增强后的图像
        """
        img_array = np.array(img)
        complexity = self._calculate_image_complexity(img_array)
        
        # 根据复杂度调整增强概率
        # 复杂度高的图像减少增强强度，复杂度低的图像增加增强强度
        adjusted_probability = self.base_probability * (1.0 - complexity * 0.5)
        
        if random.random() < adjusted_probability:
            # 应用轻微的颜色增强
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(random.uniform(0.8, 1.2))
            
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(random.uniform(0.9, 1.1))
            
        return img
    
    def __repr__(self):
        return f'{self.__class__.__name__}(base_probability={self.base_probability})'


class TargetedNoiseTransform(object):
    """
    针对性噪声增强，添加符合药材图像特征的噪声
    """
    def __init__(self, noise_types=['gaussian', 'salt_pepper'], intensity_range=(0.01, 0.05), 
                 probability=0.3):
        """
        Args:
            noise_types: 噪声类型列表
            intensity_range: 噪声强度范围
            probability: 应用噪声的概率
        """
        self.noise_types = noise_types
        self.intensity_range = intensity_range
        self.probability = probability
        
    def _add_gaussian_noise(self, img_array, intensity):
        """添加高斯噪声"""
        noise = np.random.normal(0, intensity * 255, img_array.shape)
        noisy_img = img_array + noise
        return np.clip(noisy_img, 0, 255).astype(np.uint8)
        
    def _add_salt_pepper_noise(self, img_array, intensity):
        """添加椒盐噪声"""
        noise = np.random.random(img_array.shape[:2])
        img_copy = img_array.copy()
        
        # 盐噪声（白点）
        salt_mask = noise < intensity / 2
        img_copy[salt_mask] = 255
        
        # 椒噪声（黑点）
        pepper_mask = noise > (1 - intensity / 2)
        img_copy[pepper_mask] = 0
        
        return img_copy
        
    def __call__(self, img):
        """
        Args:
            img (PIL Image): 输入的PIL图像
        Returns:
            PIL Image: 添加噪声后的图像
        """
        if random.random() > self.probability:
            return img
            
        img_array = np.array(img)
        intensity = random.uniform(*self.intensity_range)
        noise_type = random.choice(self.noise_types)
        
        if noise_type == 'gaussian':
            result = self._add_gaussian_noise(img_array, intensity)
        elif noise_type == 'salt_pepper':
            result = self._add_salt_pepper_noise(img_array, intensity)
        else:
            result = img_array
            
        return Image.fromarray(result)
    
    def __repr__(self):
        return f'{self.__class__.__name__}(noise_types={self.noise_types}, intensity={self.intensity_range})'


# 为了向后兼容，重新导出原有的GrayscaleTransform
class GrayscaleTransform(object):
    """
    将图像转换为灰度图的自定义变换类
    专门为柴胡类等中药材图像设计
    """
    def __init__(self, num_output_channels=3):
        """
        Args:
            num_output_channels (int): 输出通道数，3表示RGB格式的灰度图，1表示单通道灰度图
        """
        self.num_output_channels = num_output_channels
    
    def __call__(self, img):
        """
        Args:
            img (PIL Image): 输入的PIL图像
        
        Returns:
            PIL Image: 灰度化后的图像
        """
        if self.num_output_channels == 3:
            # 转换为灰度图但保持3通道（RGB格式）
            grayscale = transforms.Grayscale(num_output_channels=3)(img)
        else:
            # 转换为单通道灰度图
            grayscale = transforms.Grayscale(num_output_channels=1)(img)
        
        return grayscale
    
    def __repr__(self):
        return f'{self.__class__.__name__}(num_output_channels={self.num_output_channels})'