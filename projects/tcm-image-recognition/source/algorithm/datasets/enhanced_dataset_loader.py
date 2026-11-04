#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版数据加载器
支持新的预处理策略：ROI聚焦、细粒度特征增强、类别平衡增强
同时保持与原有策略的完全兼容性
"""

import torch
from torchvision import transforms, datasets
from torch.utils.data import Dataset, DataLoader, RandomSampler, SequentialSampler, Subset
import numpy as np
from PIL import Image
import os
import random
import json

# 导入原有的自定义变换和数据集类
from datasets.dataset_loader_new import (
    CustomImageFolder, ClassSpecificAugmentDataset, split_dataset,
    load_custom_mappings, print_dataset_info_preview, print_mapping_preview,
    CropLargestContourSquare
)

# 导入新的自定义变换
from datasets.custom_transforms import (
    ROIExtractTransform, CLAHETransform, RandomEraseTransform,
    AdaptiveAugmentTransform, TargetedNoiseTransform, GrayscaleTransform
)

def get_enhanced_transforms(configs, is_training=True):
    """
    根据配置获取增强的预处理变换
    
    Args:
        configs: 配置对象
        is_training: 是否为训练模式
    
    Returns:
        transforms.Compose: 组合的变换
    """
    transform_list = []
    
    # 检查是否为柴胡类数据集（需要灰度变换）
    if getattr(configs, 'dataset', '') == '柴胡类':
        transform_list.append(GrayscaleTransform(num_output_channels=3))
    
    # ROI聚焦策略
    if getattr(configs, 'roi_enable', False):
        print(f"[INFO] 启用ROI聚焦策略 (edge_low={getattr(configs, 'roi_edge_low_threshold', 50)}, "
              f"edge_high={getattr(configs, 'roi_edge_high_threshold', 150)})")
        transform_list.append(
            ROIExtractTransform(
                edge_low_threshold=getattr(configs, 'roi_edge_low_threshold', 50),
                edge_high_threshold=getattr(configs, 'roi_edge_high_threshold', 150),
                min_area_ratio=getattr(configs, 'roi_min_area_ratio', 0.01)
            )
        )
    
    # 基础几何变换
    force_resize_mode = getattr(configs, 'force_resize', False)
    
    if force_resize_mode:
        transform_list.extend([
            transforms.Resize((configs.img_size, configs.img_size))
        ])
    else:
        if is_training:
            transform_list.extend([
                transforms.Resize(configs.img_size),
                transforms.Pad(50, padding_mode='reflect'),
                transforms.RandomCrop(configs.img_size)
            ])
        else:
            transform_list.extend([
                transforms.Resize(configs.img_size),
                transforms.CenterCrop(configs.img_size)
            ])
    
    # 训练时的增强策略
    if is_training:
        # 细粒度特征增强策略
        if getattr(configs, 'fine_grain_enable', False):
            print(f"[INFO] 启用细粒度特征增强策略 (CLAHE clip_limit={getattr(configs, 'clahe_clip_limit', 2.0)})")
            
            # 轻微模糊增强纹理鲁棒性
            transform_list.append(
                transforms.RandomApply([
                    transforms.GaussianBlur(kernel_size=(3, 3), sigma=(0.1, 0.5))
                ], p=0.2)
            )
            
            # CLAHE增强局部对比度
            transform_list.append(
                CLAHETransform(clip_limit=getattr(configs, 'clahe_clip_limit', 2.0))
            )
            
            # 随机擦除
            transform_list.append(
                RandomEraseTransform(
                    probability=getattr(configs, 'erase_prob', 0.3),
                    scale=getattr(configs, 'erase_scale', (0.02, 0.1)),
                    ratio=getattr(configs, 'erase_ratio', (0.3, 3.3))
                )
            )
        
        # 类别平衡增强策略
        if getattr(configs, 'balanced_aug_enable', False):
            print(f"[INFO] 启用类别平衡增强策略 (noise_prob={getattr(configs, 'noise_prob', 0.3)})")
            
            # 针对性噪声增强
            transform_list.append(
                TargetedNoiseTransform(
                    probability=getattr(configs, 'noise_prob', 0.3),
                    intensity_range=getattr(configs, 'noise_intensity', (0.01, 0.05))
                )
            )
            
            # 自适应增强
            transform_list.append(
                AdaptiveAugmentTransform(
                    base_probability=getattr(configs, 'adaptive_aug_prob', 0.5)
                )
            )
        
        # 基础增强（保持原有逻辑）
        if not force_resize_mode:
            transform_list.append(
                transforms.RandomResizedCrop(configs.img_size, scale=(0.8, 1.2))
            )
            
        transform_list.extend([
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.RandomRotation(20),
            transforms.ColorJitter(brightness=0.3, contrast=0.2, saturation=0.1, hue=0.05)
        ])
    else:
        # 测试时也应用某些增强以保持一致性
        if getattr(configs, 'fine_grain_enable', False):
            transform_list.append(
                CLAHETransform(clip_limit=getattr(configs, 'clahe_clip_limit', 2.0))
            )
    
    # 最终的标准化
    transform_list.extend([
        transforms.ToTensor(),
        transforms.Normalize(configs.mean, configs.std)
    ])
    
    return transforms.Compose(transform_list)


def get_enhanced_train_loader(configs):
    """
    获取增强版训练数据加载器
    支持新的预处理策略，同时保持与原有代码的兼容性
    """
    custom_mappings = load_custom_mappings(configs.custom_mappings_path)
    
    if configs.dataset not in custom_mappings:
        raise ValueError(f"未知的数据集 '{configs.dataset}'。请在 {configs.custom_mappings_path} 中定义。")
        
    print(f"从 JSON 加载自定义数据集: {configs.dataset}")
    dataset_info = custom_mappings[configs.dataset]

    # 检查是否启用了任何新的预处理策略
    use_enhanced_strategy = any([
        getattr(configs, 'roi_enable', False),
        getattr(configs, 'fine_grain_enable', False),
        getattr(configs, 'balanced_aug_enable', False)
    ])
    
    if use_enhanced_strategy:
        print("[INFO] 检测到新的预处理策略，使用增强版数据加载器")
        
        # 打印启用的策略
        enabled_strategies = []
        if getattr(configs, 'roi_enable', False):
            enabled_strategies.append("ROI聚焦策略")
        if getattr(configs, 'fine_grain_enable', False):
            enabled_strategies.append("细粒度特征增强策略")
        if getattr(configs, 'balanced_aug_enable', False):
            enabled_strategies.append("类别平衡增强策略")
        
        print(f"       启用的策略: {', '.join(enabled_strategies)}")
        
        # 获取增强的变换
        transform_default = get_enhanced_transforms(configs, is_training=True)
    else:
        print("[INFO] 使用传统预处理策略")
        # 使用原有的策略逻辑
        force_resize_mode = getattr(configs, 'force_resize', False)
        
        if force_resize_mode:
            print("[INFO] 定义默认数据增强策略 (force_resize)...")
            transform_default = transforms.Compose([
                transforms.Resize((configs.img_size, configs.img_size)),
                transforms.RandomHorizontalFlip(),
                transforms.RandomVerticalFlip(),
                transforms.RandomRotation(20),
                transforms.ColorJitter(brightness=0.3, contrast=0.2, saturation=0.1, hue=0.05),
                transforms.ToTensor(),
                transforms.Normalize(configs.mean, configs.std)
            ])
        else:
            print("[INFO] 定义默认数据增强策略 (center_crop 风格)...")
            transform_default = transforms.Compose([
                transforms.Resize(configs.img_size),
                transforms.Pad(50, padding_mode='reflect'),
                transforms.RandomCrop(configs.img_size),
                transforms.RandomResizedCrop(configs.img_size, scale=(0.8, 1.2)),
                transforms.RandomHorizontalFlip(),
                transforms.RandomVerticalFlip(),
                transforms.RandomRotation(20),
                transforms.ColorJitter(brightness=0.3, contrast=0.2, saturation=0.1, hue=0.05),
                transforms.ToTensor(),
                transforms.Normalize(configs.mean, configs.std)
            ])

    # 处理特殊类别（保持原有逻辑）
    special_classes_set = set(dataset_info.get('special_aug_classes', []))
    grayscale_classes_set = set(dataset_info.get('grayscale_classes', []))
    
    if special_classes_set:
        print("[INFO] 检测到 special_aug_classes 配置，启用类别特定数据增强策略。")
        print(f"       特殊处理类别 ({len(special_classes_set)}个): {list(special_classes_set)}")
        
        if grayscale_classes_set:
            print(f"[INFO] 检测到 grayscale_classes 配置，为以下类别应用灰度处理: {list(grayscale_classes_set)}")
        
        # 为特殊类别定义变换
        if configs.dataset == '柴胡类':
            print("[INFO] 检测到柴胡类数据集，为特殊类别应用灰度变换。")
            if use_enhanced_strategy:
                transform_special = get_enhanced_transforms(configs, is_training=True)
            else:
                # 使用原有的柴胡类逻辑
                force_resize_mode = getattr(configs, 'force_resize', False)
                if force_resize_mode:
                    transform_special = transforms.Compose([
                        GrayscaleTransform(num_output_channels=3),
                        transforms.Resize((configs.img_size, configs.img_size)),
                        transforms.RandomHorizontalFlip(),
                        transforms.RandomVerticalFlip(),
                        transforms.RandomRotation(20),
                        transforms.ColorJitter(brightness=0.3, contrast=0.2, saturation=0.1, hue=0.05),
                        transforms.ToTensor(),
                        transforms.Normalize(configs.mean, configs.std)
                    ])
                else:
                    transform_special = transforms.Compose([
                        GrayscaleTransform(num_output_channels=3),
                        transforms.Resize(configs.img_size),
                        transforms.Pad(50, padding_mode='reflect'),
                        transforms.RandomCrop(configs.img_size),
                        transforms.RandomResizedCrop(configs.img_size, scale=(0.8, 1.2)),
                        transforms.RandomHorizontalFlip(),
                        transforms.RandomVerticalFlip(),
                        transforms.RandomRotation(20),
                        transforms.ColorJitter(brightness=0.3, contrast=0.2, saturation=0.1, hue=0.05),
                        transforms.ToTensor(),
                        transforms.Normalize(configs.mean, configs.std)
                    ])
        else:
            # 对于大类数据集，需要区分灰度类别和其他特殊类别
            if grayscale_classes_set and len(grayscale_classes_set) > 0:
                # 为灰度类别创建包含灰度处理的变换
                def get_grayscale_transform():
                    transform_list = [GrayscaleTransform(num_output_channels=3)]
                    if use_enhanced_strategy:
                        # 获取增强变换，但跳过灰度处理（因为已经添加了）
                        base_transform = get_enhanced_transforms(configs, is_training=True)
                        # 从 base_transform 中提取除灰度外的所有变换
                        # 由于 get_enhanced_transforms 已经检查了 dataset == '柴胡类'，我们需要手动构建
                        if getattr(configs, 'roi_enable', False):
                            transform_list.append(
                                ROIExtractTransform(
                                    edge_low_threshold=getattr(configs, 'roi_edge_low_threshold', 50),
                                    edge_high_threshold=getattr(configs, 'roi_edge_high_threshold', 150),
                                    min_area_ratio=getattr(configs, 'roi_min_area_ratio', 0.01)
                                )
                            )
                        force_resize_mode = getattr(configs, 'force_resize', False)
                        if force_resize_mode:
                            transform_list.append(transforms.Resize((configs.img_size, configs.img_size)))
                        else:
                            transform_list.extend([
                                transforms.Resize(configs.img_size),
                                transforms.Pad(50, padding_mode='reflect'),
                                transforms.RandomCrop(configs.img_size)
                            ])
                        if getattr(configs, 'fine_grain_enable', False):
                            transform_list.append(
                                transforms.RandomApply([
                                    transforms.GaussianBlur(kernel_size=(3, 3), sigma=(0.1, 0.5))
                                ], p=0.2)
                            )
                            transform_list.append(
                                CLAHETransform(clip_limit=getattr(configs, 'clahe_clip_limit', 2.0))
                            )
                            transform_list.append(
                                RandomEraseTransform(
                                    probability=getattr(configs, 'erase_prob', 0.3),
                                    scale=(0.02, 0.15),
                                    ratio=(0.3, 3.3)
                                )
                            )
                        transform_list.extend([
                            transforms.RandomHorizontalFlip(),
                            transforms.RandomVerticalFlip(),
                            transforms.RandomRotation(20, fill=0),
                            transforms.ColorJitter(brightness=0.3, contrast=0.2, saturation=0.1, hue=0.05),
                            transforms.ToTensor(),
                            transforms.Normalize(configs.mean, configs.std)
                        ])
                    else:
                        force_resize_mode = getattr(configs, 'force_resize', False)
                        if force_resize_mode:
                            transform_list.extend([
                                transforms.Resize((configs.img_size, configs.img_size)),
                                transforms.RandomHorizontalFlip(),
                                transforms.RandomVerticalFlip(),
                                transforms.RandomRotation(20, fill=0),
                                transforms.ColorJitter(brightness=0.3, contrast=0.2, saturation=0.1, hue=0.05),
                                transforms.ToTensor(),
                                transforms.Normalize(configs.mean, configs.std)
                            ])
                        else:
                            transform_list.extend([
                                transforms.Resize(configs.img_size),
                                transforms.Pad(50, padding_mode='reflect'),
                                transforms.RandomCrop(configs.img_size),
                                transforms.RandomResizedCrop(configs.img_size, scale=(0.8, 1.2)),
                                transforms.RandomHorizontalFlip(),
                                transforms.RandomVerticalFlip(),
                                transforms.RandomRotation(20, fill=0),
                                transforms.ColorJitter(brightness=0.3, contrast=0.2, saturation=0.1, hue=0.05),
                                transforms.ToTensor(),
                                transforms.Normalize(configs.mean, configs.std)
                            ])
                    return transforms.Compose(transform_list)
                
                transform_special_grayscale = get_grayscale_transform()
                
                # 为其他特殊类别（非灰度）创建变换
                if use_enhanced_strategy:
                    transform_special = get_enhanced_transforms(configs, is_training=True)
                else:
                    force_resize_mode = getattr(configs, 'force_resize', False)
                    if force_resize_mode:
                        transform_special = transforms.Compose([
                            transforms.Resize((configs.img_size, configs.img_size)),
                            transforms.RandomHorizontalFlip(),
                            transforms.RandomVerticalFlip(),
                            transforms.RandomRotation(20, fill=0),
                            transforms.ColorJitter(brightness=0.3, contrast=0.2, saturation=0.1, hue=0.05),
                            transforms.ToTensor(),
                            transforms.Normalize(configs.mean, configs.std)
                        ])
                    else:
                        transform_special = transforms.Compose([
                            transforms.Resize((configs.img_size, configs.img_size)),
                            transforms.RandomHorizontalFlip(),
                            transforms.RandomVerticalFlip(),
                            transforms.RandomRotation(20, fill=0),
                            transforms.ColorJitter(brightness=0.3, contrast=0.2, saturation=0.1, hue=0.05),
                            transforms.ToTensor(),
                            transforms.Normalize(configs.mean, configs.std)
                        ])
            else:
                # 其他数据集的特殊策略（无灰度类别）
                if use_enhanced_strategy:
                    transform_special = get_enhanced_transforms(configs, is_training=True)
                else:
                    force_resize_mode = getattr(configs, 'force_resize', False)
                    if force_resize_mode:
                        transform_special = transforms.Compose([
                            transforms.Resize((configs.img_size, configs.img_size)),
                            transforms.RandomHorizontalFlip(),
                            transforms.RandomVerticalFlip(),
                            transforms.RandomRotation(20, fill=0),
                            transforms.ColorJitter(brightness=0.3, contrast=0.2, saturation=0.1, hue=0.05),
                            transforms.ToTensor(),
                            transforms.Normalize(configs.mean, configs.std)
                        ])
                    else:
                        transform_special = transforms.Compose([
                            transforms.Resize((configs.img_size, configs.img_size)),
                            transforms.RandomHorizontalFlip(),
                            transforms.RandomVerticalFlip(),
                            transforms.RandomRotation(20, fill=0),
                            transforms.ColorJitter(brightness=0.3, contrast=0.2, saturation=0.1, hue=0.05),
                            transforms.ToTensor(),
                            transforms.Normalize(configs.mean, configs.std)
                        ])
        
        data_path = dataset_info['train_path']
        full_class_to_idx = dataset_info['class_to_idx']

        # 如果有灰度类别，需要创建支持多类别特定变换的数据集
        if grayscale_classes_set and len(grayscale_classes_set) > 0 and configs.dataset != '柴胡类':
            # 创建支持多类别特定变换的数据集类
            from datasets.dataset_loader_new import ClassSpecificAugmentDataset
            
            # 为灰度类别使用灰度变换，为其他特殊类别使用普通特殊变换
            # 将变换作为闭包变量传递
            grayscale_transform = transform_special_grayscale
            special_transform = transform_special
            grayscale_set = grayscale_classes_set
            special_set = special_classes_set
            
            class MultiClassSpecificDataset(ClassSpecificAugmentDataset):
                def __getitem__(self, index):
                    path, target_idx = self.samples[index]
                    sample = self.loader(path)
                    class_name = self.idx_to_class[target_idx]
                    
                    if class_name in grayscale_set:
                        transformed_sample = grayscale_transform(sample)
                    elif class_name in special_set:
                        transformed_sample = special_transform(sample)
                    else:
                        transformed_sample = self.default_transform(sample)
                    
                    return transformed_sample, target_idx
            
            full_dataset = MultiClassSpecificDataset(
                root=data_path,
                class_to_idx=full_class_to_idx,
                special_transform=transform_special,  # 用于非灰度特殊类别
                default_transform=transform_default,
                special_classes=special_classes_set
            )
        else:
            full_dataset = ClassSpecificAugmentDataset(
                root=data_path,
                class_to_idx=full_class_to_idx,
                special_transform=transform_special,
                default_transform=transform_default,
                special_classes=special_classes_set
            )
    else:
        print("[INFO] 未检测到 special_aug_classes 配置，所有类别将使用统一的数据增强策略。")
        
        data_path = dataset_info['train_path']
        full_class_to_idx = dataset_info['class_to_idx']

        full_dataset = CustomImageFolder(
            root=data_path,
            transform=transform_default,
            class_to_idx=full_class_to_idx
        )

    # 数据集划分（保持原有逻辑）
    train_dataset, _ = split_dataset(
        full_dataset, 
        shuffle=True, 
        seed=configs.seed, 
        load_ratio=getattr(configs, 'load_ratio', 1.0), 
        stratify=True
    )
    trainset = train_dataset
    
    print_dataset_info_preview("训练集信息", trainset)

    train_sampler = RandomSampler(trainset)
    train_loader = DataLoader(
        trainset, sampler=train_sampler, batch_size=configs.batch_size,
        num_workers=configs.num_workers, pin_memory=True, drop_last=True
    )
    return train_loader


def get_enhanced_test_loader(configs):
    """
    获取增强版测试数据加载器
    在测试时保持与训练时相同的预处理策略（除了数据增强）
    """
    # 检查是否启用了任何新的预处理策略
    use_enhanced_strategy = any([
        getattr(configs, 'roi_enable', False),
        getattr(configs, 'fine_grain_enable', False),
        getattr(configs, 'balanced_aug_enable', False)
    ])
    
    if use_enhanced_strategy:
        print("[INFO] 测试阶段使用增强版预处理策略")
        transform_test = get_enhanced_transforms(configs, is_training=False)
    else:
        # 使用原有的测试策略
        force_resize_mode = getattr(configs, 'force_resize', False)
        
        if configs.dataset == '柴胡类':
            print("[INFO] 柴胡类数据集，测试阶段使用灰度变换。")
            if force_resize_mode:
                print("[INFO] 测试阶段使用 force_resize 策略。")
                transform_test = transforms.Compose([
                    GrayscaleTransform(num_output_channels=3),
                    transforms.Resize((configs.img_size, configs.img_size)),
                    transforms.ToTensor(),
                    transforms.Normalize(configs.mean, configs.std)
                ])
            else:
                transform_test = transforms.Compose([
                    GrayscaleTransform(num_output_channels=3),
                    transforms.Resize(configs.img_size),
                    transforms.CenterCrop(configs.img_size),
                    transforms.ToTensor(),
                    transforms.Normalize(configs.mean, configs.std)
                ])
        else:
            if force_resize_mode:
                print("[INFO] 测试阶段使用 force_resize 策略。")
                transform_test = transforms.Compose([
                    transforms.Resize((configs.img_size, configs.img_size)),
                    transforms.ToTensor(),
                    transforms.Normalize(configs.mean, configs.std)
                ])
            else:
                transform_test = transforms.Compose([
                    transforms.Resize(configs.img_size),
                    transforms.CenterCrop(configs.img_size),
                    transforms.ToTensor(),
                    transforms.Normalize(configs.mean, configs.std)
                ])

    # 使用原有的测试数据加载逻辑
    custom_mappings = load_custom_mappings(configs.custom_mappings_path)
    
    testset = None

    if configs.dataset == "cifar10":
        testset = datasets.CIFAR10(root=configs.data_path['cifar10'], train=False, download=True, transform=transform_test)
    elif configs.dataset == "cifar100":
        testset = datasets.CIFAR100(root=configs.data_path['cifar100'], train=False, download=True, transform=transform_test)
    elif configs.dataset in custom_mappings:
        dataset_info = custom_mappings[configs.dataset]
        custom_class_to_idx = dataset_info['class_to_idx']

        print_mapping_preview("=== 数据集来源完整信息 (预览) ===", custom_class_to_idx)

        data_path = None
        mode_title = ""

        if configs.run_mode == 'train':
            mode_title = "验证集信息 (从训练数据划分)"
            if 'train_path' not in dataset_info:
                raise ValueError(f"'{configs.dataset}' 在 custom_mappings.json 中没有定义 'train_path'")
            data_path = dataset_info['train_path']
            
            full_train_dataset = CustomImageFolder(
                root=data_path,
                transform=transform_test,
                class_to_idx=custom_class_to_idx
            )
            _, testset = split_dataset(
                full_train_dataset, 
                shuffle=True, 
                seed=configs.seed, 
                load_ratio=getattr(configs, 'load_ratio', 1.0),
                stratify=True
            )
        
        elif configs.run_mode == 'test':
            mode_title = "测试集信息 (来自专用测试文件夹)"
            if 'test_path' not in dataset_info:
                raise ValueError(f"'{configs.dataset}' 在 custom_mappings.json 中没有定义 'test_path'")
            data_path = dataset_info['test_path']
            
            testset = CustomImageFolder(
                root=data_path,
                transform=transform_test,
                class_to_idx=custom_class_to_idx
            )
        else:
             mode_title = "测试集信息 (General模式)"
             if 'test_path' not in dataset_info:
                raise ValueError(f"'{configs.dataset}' 在 custom_mappings.json 中没有定义 'test_path'")
             data_path = dataset_info['test_path']
             testset = CustomImageFolder(root=data_path, transform=transform_test, class_to_idx=custom_class_to_idx)

        print_dataset_info_preview(mode_title, testset)

    else:
        raise ValueError(f"未知的数据集 '{configs.dataset}'。")
    
    test_sampler = SequentialSampler(testset)
    test_loader = DataLoader(
        testset, sampler=test_sampler, batch_size=configs.eval_batch_size,
        num_workers=configs.num_workers, pin_memory=True, drop_last=False
    )
    return test_loader


# 为了向后兼容，提供与原有函数相同的接口
def get_train_loader(configs):
    """向后兼容的训练数据加载器接口，支持层次化分类"""
    # 检查是否使用层次化分类
    custom_mappings = load_custom_mappings(configs.custom_mappings_path)
    dataset_name = getattr(configs, 'dataset', '')
    
    if dataset_name in custom_mappings:
        dataset_info = custom_mappings[dataset_name]
        # 检查是否有合并类别配置（层次化分类）
        if 'merged_classes' in dataset_info:
            from datasets.hierarchical_dataset_loader import get_hierarchical_train_loader
            return get_hierarchical_train_loader(configs)
        # 检查是否有类别过滤配置（小类分类器）
        elif 'class_filter' in dataset_info:
            from datasets.hierarchical_dataset_loader import get_filtered_train_loader
            return get_filtered_train_loader(configs)
    
    # 默认使用增强版数据加载器
    return get_enhanced_train_loader(configs)


def get_test_loader(configs):
    """向后兼容的测试数据加载器接口，支持层次化分类"""
    # 检查是否使用层次化分类
    custom_mappings = load_custom_mappings(configs.custom_mappings_path)
    dataset_name = getattr(configs, 'dataset', '')
    
    if dataset_name in custom_mappings:
        dataset_info = custom_mappings[dataset_name]
        # 检查是否有合并类别配置（层次化分类）
        if 'merged_classes' in dataset_info:
            from datasets.hierarchical_dataset_loader import get_hierarchical_test_loader
            return get_hierarchical_test_loader(configs)
        # 检查是否有类别过滤配置（小类分类器）
        elif 'class_filter' in dataset_info:
            from datasets.hierarchical_dataset_loader import get_filtered_test_loader
            return get_filtered_test_loader(configs)
    
    # 默认使用增强版数据加载器
    return get_enhanced_test_loader(configs)


if __name__ == "__main__":
    # 测试代码
    pass