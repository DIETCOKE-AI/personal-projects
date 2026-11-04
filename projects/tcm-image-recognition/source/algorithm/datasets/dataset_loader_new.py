import torch
from torchvision import transforms, datasets
from torch.utils.data import Dataset, DataLoader, RandomSampler, SequentialSampler, Subset
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("Warning: cv2 not available. CropLargestContourSquare will be disabled.")
import numpy as np
from torchvision import transforms
from PIL import Image
import os
import random
import json

from torchvision.datasets.folder import default_loader # 确保导入了 default_loader

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

class ClassSpecificAugmentDataset(Dataset):
    """
    一个支持对特定类别应用不同数据增强策略的数据集类。
    """
    def __init__(self, root, class_to_idx, special_transform, default_transform, special_classes):
        super().__init__()
        self.root = root
        self.class_to_idx = class_to_idx
        self.idx_to_class = {v: k for k, v in class_to_idx.items()}
        
        self.special_transform = special_transform
        self.default_transform = default_transform
        self.special_classes = set(special_classes)

        self.samples = self._make_dataset()
        self.targets = [s[1] for s in self.samples]
        self.loader = default_loader

    def _make_dataset(self):
        instances = []
        directory = os.path.expanduser(self.root)
        valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp')

        for class_name in sorted(self.class_to_idx.keys()):
            class_index = self.class_to_idx[class_name]
            class_dir = os.path.join(directory, class_name)
            if not os.path.isdir(class_dir):
                continue
            
            for root, _, fnames in sorted(os.walk(class_dir, followlinks=True)):
                for fname in sorted(fnames):
                    if fname.lower().endswith(valid_extensions):
                        path = os.path.join(root, fname)
                        item = (path, class_index)
                        instances.append(item)
        return instances

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        path, target_idx = self.samples[index]
        sample = self.loader(path)
        class_name = self.idx_to_class[target_idx]
        
        if class_name in self.special_classes:
            transformed_sample = self.special_transform(sample)
        else:
            transformed_sample = self.default_transform(sample)
            
        return transformed_sample, target_idx


# =================================================================================
# 以下部分保持不变
# =================================================================================

class CropLargestContourSquare(object):
    def __init__(self, debug=False, debug_dir='./debug_crop'):
        if not CV2_AVAILABLE:
            print("Warning: CropLargestContourSquare requires cv2, which is not available. This transform will act as identity.")
        self.debug = debug
        self.debug_dir = debug_dir
        if self.debug and not os.path.exists(self.debug_dir):
            os.makedirs(self.debug_dir)
            
    def __call__(self, img):
        if not CV2_AVAILABLE:
            # 如果没有cv2，直接返回原图像
            return img
            
        img_cv = np.array(img)
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if len(contours) == 0:
            return img
        max_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(max_contour)
        side_length = max(w, h)
        x_end = min(x + side_length, img_cv.shape[1])
        y_end = min(y + side_length, img_cv.shape[0])
        square = img_cv[y:y_end, x:x_end]
        if self.debug:
            debug_image = img_cv.copy()
            cv2.rectangle(debug_image, (x, y), (x_end, y_end), (0, 255, 0), 2)
            save_path = os.path.join(self.debug_dir, f'debug_crop_{np.random.randint(10000)}.png')
            cv2.imwrite(save_path, debug_image)
            print(f"Saved debug image to {save_path}")
        square = cv2.cvtColor(square, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(square)
        return img_pil

class CustomImageFolder(datasets.ImageFolder):
    def __init__(self, root, transform=None, class_to_idx=None):
        def find_classes(directory):
            classes = sorted(entry.name for entry in os.scandir(directory) if entry.is_dir())
            class_to_idx = {cls_name: i for i, cls_name in enumerate(classes)}
            return classes, class_to_idx
        def make_dataset(directory, class_to_idx, extensions=None, is_valid_file=None):
            instances = []
            directory = os.path.expanduser(directory)
            valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
            for class_name in class_to_idx:
                class_dir = os.path.join(directory, class_name)
                if not os.path.isdir(class_dir):
                    continue
                for sub in os.scandir(class_dir):
                    if not sub.is_dir():
                        if sub.is_file() and sub.name.lower().endswith(valid_extensions):
                            instances.append((sub.path, class_to_idx[class_name]))
                        continue
                    for file in os.scandir(sub.path):
                        if file.is_file() and file.name.lower().endswith(valid_extensions):
                            instances.append((file.path, class_to_idx[class_name]))
            return instances
        self.root = root
        self.transform = transform
        if class_to_idx is not None:
            self.class_to_idx = class_to_idx.copy()
            self.classes = sorted(self.class_to_idx.keys(), key=lambda k: self.class_to_idx[k])
        else:
            self.classes, self.class_to_idx = find_classes(root)
        self.samples = make_dataset(self.root, self.class_to_idx, extensions=('.jpg', '.jpeg', '.png', '.bmp'))
        if not self.samples:
            raise FileNotFoundError(f"在路径 '{root}' 中没有找到任何图片。请检查文件夹结构和图片格式。")
        self.targets = [s[1] for s in self.samples]
        actual_classes_indices = set(self.targets)
        self.classes = [cls for cls, idx in self.class_to_idx.items() if idx in actual_classes_indices]
        self.classes.sort(key=lambda cls: self.class_to_idx[cls])
        self.loader = datasets.folder.default_loader
    def __getitem__(self, index):
        path, target = self.samples[index]
        try:
            sample = self.loader(path)
            if self.transform is not None:
                sample = self.transform(sample)
            return sample, target
        except Exception as e:
            print(f"警告: 无法加载图像 {path}: {e}")
            # 返回None，将在collate_fn中被过滤掉
            return None, target
    def __len__(self):
        return len(self.samples)

def split_dataset(dataset, shuffle=True, seed=42, load_ratio=1.0, stratify=True):
    """分割数据集为训练集和验证集
    
    Args:
        dataset: 要分割的数据集
        shuffle: 是否打乱数据
        seed: 随机种子
        load_ratio: 数据加载比例
        stratify: 是否使用分层分割（确保各类别按相同比例分配）
    
    Returns:
        train_dataset, test_dataset: 训练集和测试集
    """
    train_ratio = 0.9
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
    
    dataset_size = len(dataset)
    actual_size = int(dataset_size * load_ratio)
    
    if stratify:
        # 分层分割：确保每个类别按相同比例分配到训练集和验证集
        from collections import defaultdict
        
        # 按类别分组索引
        class_indices = defaultdict(list)
        for idx in range(dataset_size):
            label = dataset.targets[idx]
            class_indices[label].append(idx)
        
        train_indices = []
        test_indices = []
        
        for class_label, indices in class_indices.items():
            # 对每个类别的样本进行打乱
            if shuffle:
                random.shuffle(indices)
            
            # 计算该类别实际使用的样本数
            actual_class_size = int(len(indices) * load_ratio)
            class_indices_to_use = indices[:actual_class_size]
            
            # 按训练比例分割
            class_train_size = int(actual_class_size * train_ratio)
            class_train_indices = class_indices_to_use[:class_train_size]
            class_test_indices = class_indices_to_use[class_train_size:]
            
            train_indices.extend(class_train_indices)
            test_indices.extend(class_test_indices)
        
        # 如果需要打乱，重新打乱最终的索引
        if shuffle:
            random.shuffle(train_indices)
            random.shuffle(test_indices)
    
    else:
        # 原始的简单随机分割
        train_size = int(train_ratio * actual_size)
        indices = list(range(dataset_size))
        if shuffle:
            random.shuffle(indices)
        indices = indices[:actual_size]
        train_indices = indices[:train_size]
        test_indices = indices[train_size:]
    
    train_dataset = Subset(dataset, train_indices)
    test_dataset = Subset(dataset, test_indices)
    return train_dataset, test_dataset

def load_custom_mappings(json_path):
    if not os.path.exists(json_path):
        print(f"警告: 自定义映射文件未找到: {json_path}")
        return {}
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# =================================================================================
# 🚀 新增的辅助函数，用于简洁地打印信息
# =================================================================================

def print_dataset_info_preview(title, dataset_obj, limit=5):
    """
    以预览模式打印数据集信息（总数、标签分布等）。

    :param title: 打印块的标题
    :param dataset_obj: 数据集对象 (可以是 Subset 或 完整的 ImageFolder)
    :param limit: 显示的类别数量上限
    """
    print(f"\n{title}:")
    print(f"总样本数: {len(dataset_obj)}")

    # 确定标签和类别映射的来源
    if isinstance(dataset_obj, Subset):
        source_dataset = dataset_obj.dataset
        labels = [source_dataset.targets[i] for i in dataset_obj.indices]
        class_to_idx = source_dataset.class_to_idx
        print_title = "标签分布 (来自划分):"
    else: # 适用于完整的 ImageFolder 等对象
        labels = dataset_obj.targets
        class_to_idx = dataset_obj.class_to_idx
        print_title = "标签分布 (来自完整文件夹):"
    
    print(print_title)
    
    # 统计每个类别的数量
    label_counts = {}
    for label in labels:
        label_counts[label] = label_counts.get(label, 0) + 1
    
    idx_to_class = {v: k for k, v in class_to_idx.items()}
    
    # 只打印前 limit 个类别
    sorted_items = sorted(label_counts.items())
    for i, (label, count) in enumerate(sorted_items):
        if i < limit:
            print(f"类别 '{idx_to_class.get(label, '未知')}' (索引 {label}): {count} 张图片")
        elif i == limit:
            print(f"... 等等 (共 {len(label_counts)} 个类别)")
            break

def print_mapping_preview(title, mapping_dict, limit=5):
    """打印映射字典的预览信息。"""
    print(f"\n{title}:")
    preview_items = list(mapping_dict.items())[:limit]
    for key, value in preview_items:
        print(f"'{key}': {value}", end=", ")
    
    if len(mapping_dict) > limit:
        print(f"... (共 {len(mapping_dict)} 项)")
    else:
        print()

# =================================================================================
# ✨ 2. 修改 get_train_loader 函数
# =================================================================================
def get_train_loader(configs):
    
    custom_mappings = load_custom_mappings(configs.custom_mappings_path)
    
    if configs.dataset not in custom_mappings:
        raise ValueError(f"未知的数据集 '{configs.dataset}'。请在 {configs.custom_mappings_path} 中定义。")
        
    print(f"从 JSON 加载自定义数据集: {configs.dataset}")
    dataset_info = custom_mappings[configs.dataset]

    # ✨ 1. 根据配置选择数据增强策略
    force_resize_mode = getattr(configs, 'force_resize', False)
    
    if force_resize_mode:
        print("[INFO] 定义默认数据增强策略 (force_resize)...")
        transform_default = transforms.Compose([
            transforms.Resize((configs.img_size, configs.img_size)),  # 强制resize到指定尺寸
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
    # transform_default = transforms.Compose([
    #     transforms.Resize(720),
    #     transforms.RandomCrop(640),
    #     transforms.RandomHorizontalFlip(),
    #     transforms.RandomVerticalFlip(),
    #     transforms.RandomRotation(20),
    #     transforms.ColorJitter(
    #         brightness=0.3, contrast=0.2, saturation=0.1, hue=0.05
    #     ),
    #     transforms.ToTensor(),
    #     transforms.Normalize(configs.mean, configs.std)
    # ])

    # ✨ 2. 从JSON配置中读取特殊处理类别列表
    special_classes_set = set(dataset_info.get('special_aug_classes', []))

    # ✨ 3. 根据是否存在特殊类别，来决定数据加载方式
    if special_classes_set:
        # --- 如果定义了特殊类别，则启用“类别特定增强” ---
        print("[INFO] 检测到 special_aug_classes 配置，启用类别特定数据增强策略。")
        print(f"       特殊处理类别 ({len(special_classes_set)}个): {list(special_classes_set)}")

        # 检查是否为柴胡类数据集，如果是，则使用灰度变换
        # 检查是否为柴胡类数据集，如果是，则使用灰度变换
        if configs.dataset == '柴胡类':
            print("[INFO] 检测到柴胡类数据集，为所有类别应用灰度变换。")
            # 为柴胡类定义特殊的灰度变换策略
            if force_resize_mode:
                transform_special = transforms.Compose([
                    GrayscaleTransform(num_output_channels=3),  # 转换为灰度图，保持3通道
                    transforms.Resize((configs.img_size, configs.img_size)),  # force_resize模式
                    transforms.RandomHorizontalFlip(),
                    transforms.RandomVerticalFlip(),
                    transforms.RandomRotation(20),
                    transforms.ColorJitter(brightness=0.3, contrast=0.2, saturation=0.1, hue=0.05),
                    transforms.ToTensor(),
                    transforms.Normalize(configs.mean, configs.std)
                ])
            else:
                transform_special = transforms.Compose([
                    GrayscaleTransform(num_output_channels=3),  # 转换为灰度图，保持3通道
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
            # 其他数据集的特殊策略
            if force_resize_mode:
                print("[INFO] 特殊类别使用 force_resize 策略。")
                transform_special = transforms.Compose([
                    transforms.Resize((configs.img_size, configs.img_size)),  # force_resize模式
                    transforms.RandomHorizontalFlip(),
                    transforms.RandomVerticalFlip(),
                    transforms.RandomRotation(20, fill=0),
                    transforms.ColorJitter(brightness=0.3, contrast=0.2, saturation=0.1, hue=0.05),
                    transforms.ToTensor(),
                    transforms.Normalize(configs.mean, configs.std)
                ])
            else:
                # 保持原有逻辑（center_crop风格）
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

        # 使用之前定义好的 transform_default 和这里定义的 transform_special
        full_dataset = ClassSpecificAugmentDataset(
            root=data_path,
            class_to_idx=full_class_to_idx,
            special_transform=transform_special,
            default_transform=transform_default,
            special_classes=special_classes_set
        )
    else:
        # --- 如果没有定义特殊类别，则直接使用上面定义好的默认策略 ---
        print("[INFO] 未检测到 special_aug_classes 配置，所有类别将使用统一的默认数据增强策略。")
        
        data_path = dataset_info['train_path']
        full_class_to_idx = dataset_info['class_to_idx']

        # 直接使用之前定义好的 transform_default
        full_dataset = CustomImageFolder(
            root=data_path,
            transform=transform_default,
            class_to_idx=full_class_to_idx
        )

    # --- 后续的划分和加载逻辑保持不变 ---
    train_dataset, _ = split_dataset(full_dataset, shuffle=True, seed=configs.seed, load_ratio=getattr(configs, 'load_ratio', 1.0), stratify=True)
    trainset = train_dataset
    
    # (如果您本地保留了 print_dataset_info_preview 函数，可以取消这里的注释)
    print_dataset_info_preview("训练集信息", trainset)

    train_sampler = RandomSampler(trainset)
    train_loader = DataLoader(
        trainset, sampler=train_sampler, batch_size=configs.batch_size,
        num_workers=configs.num_workers, pin_memory=True, drop_last=True
    )
    return train_loader

def get_test_loader(configs):
    # 根据配置选择预处理策略
    force_resize_mode = getattr(configs, 'force_resize', False)
    
    # 根据数据集类型决定是否使用灰度变换
    if configs.dataset == '柴胡类':
        print("[INFO] 柴胡类数据集，测试阶段使用灰度变换。")
        if force_resize_mode:
            print("[INFO] 测试阶段使用 force_resize 策略。")
            transform_test = transforms.Compose([
                GrayscaleTransform(num_output_channels=3),  # 转换为灰度图，保持3通道
                transforms.Resize((configs.img_size, configs.img_size)),  # force_resize
                transforms.ToTensor(),
                transforms.Normalize(configs.mean, configs.std)
            ])
        else:
            transform_test = transforms.Compose([
                GrayscaleTransform(num_output_channels=3),  # 转换为灰度图，保持3通道
                transforms.Resize(configs.img_size),
                transforms.CenterCrop(configs.img_size),
                transforms.ToTensor(),
                transforms.Normalize(configs.mean, configs.std)
            ])
    else:
        if force_resize_mode:
            print("[INFO] 测试阶段使用 force_resize 策略。")
            transform_test = transforms.Compose([
                transforms.Resize((configs.img_size, configs.img_size)),  # force_resize
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


    custom_mappings = load_custom_mappings(configs.custom_mappings_path)
    
    full_dataset_for_info = None # 用于信息打印的完整数据集
    testset = None

    if configs.dataset == "cifar10":
        testset = datasets.CIFAR10(root=configs.data_path['cifar10'], train=False, download=True, transform=transform_test)
        full_dataset_for_info = testset
    elif configs.dataset == "cifar100":
        testset = datasets.CIFAR100(root=configs.data_path['cifar100'], train=False, download=True, transform=transform_test)
        full_dataset_for_info = testset
    elif configs.dataset in custom_mappings:
        dataset_info = custom_mappings[configs.dataset]
        custom_class_to_idx = dataset_info['class_to_idx']

        # ✨ 使用新的辅助函数打印类别映射预览
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
                stratify=True  # 启用分层分割
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

        # ✨ 使用新的辅助函数来打印简洁的信息
        print_dataset_info_preview(mode_title, testset)

    else:
        raise ValueError(f"未知的数据集 '{configs.dataset}'。")
    
    test_sampler = SequentialSampler(testset)
    test_loader = DataLoader(
        testset, sampler=test_sampler, batch_size=configs.eval_batch_size,
        num_workers=configs.num_workers, pin_memory=True, drop_last=False
    )
    return test_loader

# main 函数无需改动
def main():
    pass
if __name__ == "__main__":
    main()