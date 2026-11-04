

import torch
from torchvision import transforms, datasets
from torch.utils.data import DataLoader, RandomSampler, SequentialSampler, Subset
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
            
        # img 是 PIL.Image，需要转成 OpenCV 格式
        img_cv = np.array(img)
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)

        # 转灰度
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

        # 二值化
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

        # 找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if len(contours) == 0:
            # 没轮廓，直接返回原图
            return img

        # 找最大轮廓
        max_contour = max(contours, key=cv2.contourArea)

        # 最小外接正方形
        x, y, w, h = cv2.boundingRect(max_contour)
        side_length = max(w, h)

        # 裁剪，防止越界
        x_end = min(x + side_length, img_cv.shape[1])
        y_end = min(y + side_length, img_cv.shape[0])
        square = img_cv[y:y_end, x:x_end]

        # debug模式下保存
        if self.debug:
            debug_image = img_cv.copy()
            cv2.rectangle(debug_image, (x, y), (x_end, y_end), (0, 255, 0), 2)  # 画个框
            save_path = os.path.join(self.debug_dir, f'debug_crop_{np.random.randint(10000)}.png')
            cv2.imwrite(save_path, debug_image)
            print(f"Saved debug image to {save_path}")

        # 转回 PIL.Image
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
                        continue
                    for file in os.scandir(sub.path):
                        if file.is_file() and file.name.lower().endswith(valid_extensions):
                            instances.append((file.path, class_to_idx[class_name]))
            return instances

        self.root = root
        self.transform = transform
        self.classes, default_class_to_idx = find_classes(root)

        if class_to_idx is not None:
            self.class_to_idx = class_to_idx.copy()
        else:
            self.class_to_idx = default_class_to_idx

        self.samples = make_dataset(
            self.root,
            self.class_to_idx,
            extensions=('.jpg', '.jpeg', '.png', '.bmp'),
            is_valid_file=lambda x: x.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))
        )
        self.targets = [s[1] for s in self.samples]

        # 只保留实际有图片的类别
        actual_classes = set()
        for _, label in self.samples:
            actual_classes.add(label)
        self.classes = [cls for cls, idx in self.class_to_idx.items() if idx in actual_classes]

        self.loader = datasets.folder.default_loader

    def __getitem__(self, index):
        path, target = self.samples[index]
        sample = self.loader(path)
        if self.transform is not None:
            sample = self.transform(sample)
        return sample, target

def split_dataset(dataset, shuffle=True, seed=42, load_ratio=1.0):
    """
    将数据集划分为训练集和测试集
    
    参数:
        dataset: 数据集
        shuffle: 是否打乱数据
        seed: 随机种子
        load_ratio: 加载数据集的百分比（0.0-1.0），默认为1.0表示加载全部数据
    
    返回:
        train_dataset, test_dataset
    """
    # 设置固定的划分比例
    train_ratio = 0.9  # 训练集比例
    
    # 设置随机种子
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
    
    # 获取数据集大小
    dataset_size = len(dataset)
    
    # 根据load_ratio计算实际要使用的数据量
    actual_size = int(dataset_size * load_ratio)
    
    # 计算每个集合的大小
    train_size = int(train_ratio * actual_size)
    test_size = actual_size - train_size
    
    # 创建索引列表
    indices = list(range(dataset_size))
    
    # 打乱索引
    if shuffle:
        random.shuffle(indices)
    
    # 只使用前load_ratio比例的数据
    indices = indices[:actual_size]
    
    # 划分索引
    train_indices = indices[:train_size]
    test_indices = indices[train_size:]
    
    # 创建子集
    train_dataset = Subset(dataset, train_indices)
    test_dataset = Subset(dataset, test_indices)
    
    return train_dataset, test_dataset

def get_train_loader(configs):
    # data transforms
    transform_train = transforms.Compose([
        transforms.Resize(640),
        transforms.Pad(50, padding_mode='reflect'),  # 填充50像素边缘
        transforms.RandomCrop(640),  # 随机裁剪回640x640
        transforms.RandomResizedCrop(640, scale=(0.7, 1.3)),  # 随机缩放0.7-1.3倍后resize
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(20),
        transforms.ColorJitter(                                # 加入颜色抖动（包括亮度等增强）
            brightness=0.2,    # 亮度增强幅度（±20%）
            contrast=0.2,      # 对比度增强
            saturation=0.1,    # 饱和度增强
            hue=0.05           # 色调微调（±0.05）
        ),
        transforms.ToTensor(),
        transforms.Normalize(configs.mean, configs.std)
    ])

    '''
    custom_class_to_idx = {
    '亚麻籽类': 0,
    '使君子类': 1,
    '决明子类': 2,
    '白芍类': 3,
    '土茯苓类': 4,
    '月季类': 5,
    '望江南类': 6,
    '枸杞类': 7,
    '栀子类': 8,
    '淡竹叶类': 9,
    '炒稻芽类': 10,
    '白扁豆类': 11,
    '板蓝根类': 12,
    '莪术类': 13,
    '蔓荆子类': 14,
    '麦冬类': 15,
    '黄荆子类': 16,
    '补骨脂类': 17,
    '苍术类': 18,
    '草豆蔻类': 19,
    '草果类': 20,
    '赤小豆类': 21,
    '川芎类': 22,
    '大枣类': 23,
    '茯神类': 24,
    '鼓槌石斛类': 25,
    '黑豆类': 26,
    '红参类': 27,
    '红花类': 28,
    '槐花类': 29,
    '黄连类': 30,
    '鸡血藤类': 31,
    '韭菜子类': 32,
    '莲须类': 33,
    '麦芽类': 34,
    '芡实类': 35,
    '人参类': 36,
    '三叶青类': 37,
    '山楂类': 38,
    '蛇床子类': 39,
    '锁阳类': 40,
    '通草类': 41,
    '夏枯草类': 42,
    '薏苡仁类': 43,
    '余甘子类': 44,
    '郁李仁类': 45,
    '沙苑子类': 46,
    '姜黄类': 47,
    '半夏类': 48,
    '枣仁类': 49,
    '菊花类': 50,
    '肉豆蔻类': 51,
    '三七类': 52,
    '仙茅类': 53,
    '浙石斛类': 54,
    '枳实类': 55,
    '白鲜皮类': 56,
    '楮实子类': 57,
    '川牛膝类': 58,
    '罗汉果类': 59,
    '山麦冬类': 60,
    '牛膝类': 61,
    '广藿香类': 62,
    '延胡索类': 63,
    '代代花类': 64,
    '千金子类': 65,
    '玫瑰类': 66,
    '苍耳子类': 67,
    '黑顺片类': 68,
    '火麻仁类': 69,
    '苦杏仁类': 70,
    '款冬花类': 71,
    '五味子类': 72,
    '玉米须类': 73,
    '枳壳类': 74,
    '拳参类': 75,
    '黑芝麻类': 76,
    '肺形草类': 77,
    '水半夏类': 78,
    '淮小麦类': 79,
    '菝葜类': 80,
    '防己类': 81,
    '梅花类': 82,
    '片姜黄类': 83,
    '桑葚类': 84,
    '天麻类': 85,
    '透骨草类': 86,
    '石菖蒲类': 87,
    '地黄类': 88,
    '瓜蒌子类': 89,
    '山茱萸类': 90,
    '天花粉类': 91,
    '小茴香类': 92,
    '土贝母类': 93,
    '白术类': 94,
    '山慈菇类': 95,
    '芦根类': 96,
    '陈皮类': 97,
    '干姜类': 98
    }
    '''
    custom_class_to_idx = {
    '亚麻籽类': 0,
    '使君子类': 1,
    '决明子类': 2,
    '白芍类': 3,
    '土茯苓类': 4,
    '月季类': 5,
    '望江南类': 6,
    '枸杞类': 7,
    '栀子类': 8,
    '淡竹叶类': 9,
    '炒稻芽类': 10,
    '白扁豆类': 11,
    '板蓝根类': 12,
    '莪术类': 13,
    '蔓荆子类': 14,
    '麦冬类': 15,
    '黄荆子类': 16,
    '补骨脂类': 17,
    '苍术类': 18,
    '草豆蔻类': 19,
    '草果类': 20,
    '赤小豆类': 21,
    '川芎类': 22,
    '大枣类': 23,
    '茯神类': 24,
    '鼓槌石斛类': 25,
    '黑豆类': 26,
    '红参类': 27,
    '红花类': 28,
    '槐花类': 29,
    '黄连类': 30,
    '鸡血藤类': 31,
    '韭菜子类': 32,
    '莲须类': 33,
    '麦芽类': 34,
    '芡实类': 35,
    '人参类': 36,
    '三叶青类': 37,
    '山楂类': 38,
    '蛇床子类': 39,
    '锁阳类': 40,
    '通草类': 41,
    '夏枯草类': 42,
    '薏苡仁类': 43,
    '余甘子类': 44,
    '郁李仁类': 45,
    '沙苑子类': 46,
    '姜黄类': 47,
    '半夏类': 48,
    '枣仁类': 49,
    '菊花类': 50,
    '肉豆蔻类': 51,
    '三七类': 52,
    '仙茅类': 53,
    '浙石斛类': 54,
    '枳实类': 55,
    '白鲜皮类': 56,
    '楮实子类': 57,
    '川牛膝类': 58,
    '罗汉果类': 59,
    '山麦冬类': 60,
    '牛膝类': 61,
    '广藿香类': 62,
    '延胡索类': 63,
    '代代花类': 64,
    '千金子类': 65,
    '玫瑰类': 66,
    '苍耳子类': 67,
    '黑顺片类': 68,
    '火麻仁类': 69,
    '苦杏仁类': 70,
    '款冬花类': 71,
    '五味子类': 72,
    '玉米须类': 73,
    '枳壳类': 74,
    '拳参类': 75,
    '黑芝麻类': 76,
    '肺形草类': 77,
    '水半夏类': 78,
    '淮小麦类': 79,
    '菝葜类': 80,
    '防己类': 81,
    '梅花类': 82,
    '片姜黄类': 83,
    '桑葚类': 84,
    '天麻类': 85,
    '透骨草类': 86,
    '石菖蒲类': 87,
    '地黄类': 88,
    '瓜蒌子类': 89,
    '山茱萸类': 90,
    '天花粉类': 91,
    '小茴香类': 92,
    '土贝母类': 93,
    '白术类': 94,
    '山慈菇类': 95,
    '芦根类': 96,
    '陈皮类': 97,
    '干姜类': 98,
    '紫苑类': 99,
    '紫苏叶类': 100,
    '紫草类（掉渣）': 101,
    '枳椇子类': 102,
    '知母类': 103,
    '浙黄精类': 104,
    '浙贝母类': 105,
    '泽泻类': 106,
    '远志类': 107,
    '郁金类': 108,
    '玉竹类': 109,
    '鱼腥草类': 110,
    '玄参类': 111,
    '续断类': 112,
    '细辛类': 113,
    '吴茱萸类': 114,
    '王不留行类': 115,
    '太子参类': 116,
    '首乌藤类': 117,
    '石斛类': 118,
    '射干类': 119,
    '忍冬藤类': 120,
    '青葙子类': 121,
    '青风藤类': 122,
    '羌活类': 123,
    '胖大海类': 124,
    '南沙参类': 125,
    '牡丹皮类': 126,
    '没药类': 127,
    '猫人参类': 128,
    '龙眼肉类': 129,
    '桔梗类': 130,
    '九节菖蒲类': 131,
    '金银花类': 132,
    '黄芪类': 133,
    '黄岑类': 134,
    '何首乌类': 135,
    '葛根类': 136,
    '甘草类': 137,
    '覆盆子类': 138,
    '防风类': 139,
    '番泻叶类': 140,
    '杜仲类': 141,
    '丁香类': 142,
    '地骨皮类': 143,
    '党参类': 144,
    '当归类': 145,
    '丹参类': 146,
    '车前子类': 147,
    '柴胡类': 148,
    '槟榔类': 149,
    '荜澄茄类': 150,
    '北沙参类': 151,
    '柏子仁类': 152,
    '百部类': 153,
    '巴戟天类': 154
    }

    #custom_class_to_idx={"栀子":0,"水栀子":1}
    # custom_class_to_idx={"川麦冬":0,"浙麦冬":1}
    # custom_class_to_idx={"沙大旺":0,"沙苑子":1,"猪屎豆":2,"紫云英":3}
    # get dataset
    if configs.dataset == "cifar10":
        trainset = datasets.CIFAR10(root=configs.data_path['cifar10'],
                                    train=True,
                                    download=True,
                                    transform=transform_train)
    elif configs.dataset == "cifar100":
        trainset = datasets.CIFAR100(root=configs.data_path['cifar100'],
                                    train=True,
                                    download=True,
                                    transform=transform_train)
    elif configs.dataset == "medicine":
        # 加载完整数据集
        full_dataset = CustomImageFolder(
            root=configs.data_path['medicine'],
            transform=transform_train,
            class_to_idx=custom_class_to_idx
        )
        
        # 划分数据集，使用load_ratio参数控制加载比例
        train_dataset, _ = split_dataset(
            full_dataset,
            shuffle=True,
            seed=configs.seed,
            load_ratio=getattr(configs, 'load_ratio', 1.0)  # 如果没有设置load_ratio，默认为1.0
        )
        trainset = train_dataset
        
        # 打印训练集索引信息
        print("\n训练集索引信息:")
        print(f"总样本数: {len(trainset)}")
        if isinstance(trainset, Subset):
            print("训练集索引范围:", trainset.indices[:10], "...", trainset.indices[-10:])
            print("训练集标签分布:")
            labels = [trainset.dataset.targets[i] for i in trainset.indices]
            label_counts = {}
            for label in labels:
                label_counts[label] = label_counts.get(label, 0) + 1
            for label, count in sorted(label_counts.items()):
                print(f"类别 {label}: {count} 张图片")
    else:
        # 对于其他数据集，使用ImageFolder加载
        trainset = datasets.ImageFolder(
            root=os.path.join(configs.data_path[configs.dataset], 'train'),
            transform=transform_train
        )
        print(f"Train Class to Index Mapping: {trainset.class_to_idx}")
    
    # 创建训练数据加载器
    train_sampler = RandomSampler(trainset)
    train_loader = DataLoader(
        trainset,
        sampler=train_sampler,
        batch_size=configs.batch_size,
        num_workers=8,
        pin_memory=True,
        drop_last=True
    )
    
    return train_loader

def get_test_loader(configs):
    # 测试集的数据变换
    transform_test = transforms.Compose([
        transforms.Resize(640),
        transforms.ToTensor(),
        transforms.Normalize(configs.mean, configs.std)
    ])
    '''
    custom_class_to_idx = {
        '亚麻籽类': 0,
        '使君子类': 1,
        '决明子类': 2,
        '白芍类': 3,
        '土茯苓类': 4,
        '月季类': 5,
        '望江南类': 6,
        '枸杞类': 7,
        '栀子类': 8,
        '淡竹叶类': 9,
        '炒稻芽类': 10,
        '白扁豆类': 11,
        '板蓝根类': 12,
        '莪术类': 13,
        '蔓荆子类': 14,
        '麦冬类': 15,
        '黄荆子类': 16,
        '补骨脂类': 17,
        '苍术类': 18,
        '草豆蔻类': 19,
        '草果类': 20,
        '赤小豆类': 21,
        '川芎类': 22,
        '大枣类': 23,
        '茯神类': 24,
        '鼓槌石斛类': 25,
        '黑豆类': 26,
        '红参类': 27,
        '红花类': 28,
        '槐花类': 29,
        '黄连类': 30,
        '鸡血藤类': 31,
        '韭菜子类': 32,
        '莲须类': 33,
        '麦芽类': 34,
        '芡实类': 35,
        '人参类': 36,
        '三叶青类': 37,
        '山楂类': 38,
        '蛇床子类': 39,
        '锁阳类': 40,
        '通草类': 41,
        '夏枯草类': 42,
        '薏苡仁类': 43,
        '余甘子类': 44,
        '郁李仁类': 45,
        '沙苑子类': 46,
        '姜黄类': 47,
        '半夏类': 48,
        '枣仁类': 49,
        '菊花类': 50,
        '肉豆蔻类': 51,
        '三七类': 52,
        '仙茅类': 53,
        '浙石斛类': 54,
        '枳实类': 55,
        '白鲜皮类': 56,
        '楮实子类': 57,
        '川牛膝类': 58,
        '罗汉果类': 59,
        '山麦冬类': 60,
        '牛膝类': 61,
        '广藿香类': 62,
        '延胡索类': 63,
        '代代花类': 64,
        '千金子类': 65,
        '玫瑰类': 66,
        '苍耳子类': 67,
        '黑顺片类': 68,
        '火麻仁类': 69,
        '苦杏仁类': 70,
        '款冬花类': 71,
        '五味子类': 72,
        '玉米须类': 73,
        '枳壳类': 74,
        '拳参类': 75,
        '黑芝麻类': 76,
        '肺形草类': 77,
        '水半夏类': 78,
        '淮小麦类': 79,
        '菝葜类': 80,
        '防己类': 81,
        '梅花类': 82,
        '片姜黄类': 83,
        '桑葚类': 84,
        '天麻类': 85,
        '透骨草类': 86,
        '石菖蒲类': 87,
        '地黄类': 88,
        '瓜蒌子类': 89,
        '山茱萸类': 90,
        '天花粉类': 91,
        '小茴香类': 92,
        '土贝母类': 93,
        '白术类': 94,
        '山慈菇类': 95,
        '芦根类': 96,
        '陈皮类': 97,
        '干姜类': 98
    }
    '''
    custom_class_to_idx = {
        '亚麻籽类': 0,
        '使君子类': 1,
        '决明子类': 2,
        '白芍类': 3,
        '土茯苓类': 4,
        '月季类': 5,
        '望江南类': 6,
        '枸杞类': 7,
        '栀子类': 8,
        '淡竹叶类': 9,
        '炒稻芽类': 10,
        '白扁豆类': 11,
        '板蓝根类': 12,
        '莪术类': 13,
        '蔓荆子类': 14,
        '麦冬类': 15,
        '黄荆子类': 16,
        '补骨脂类': 17,
        '苍术类': 18,
        '草豆蔻类': 19,
        '草果类': 20,
        '赤小豆类': 21,
        '川芎类': 22,
        '大枣类': 23,
        '茯神类': 24,
        '鼓槌石斛类': 25,
        '黑豆类': 26,
        '红参类': 27,
        '红花类': 28,
        '槐花类': 29,
        '黄连类': 30,
        '鸡血藤类': 31,
        '韭菜子类': 32,
        '莲须类': 33,
        '麦芽类': 34,
        '芡实类': 35,
        '人参类': 36,
        '三叶青类': 37,
        '山楂类': 38,
        '蛇床子类': 39,
        '锁阳类': 40,
        '通草类': 41,
        '夏枯草类': 42,
        '薏苡仁类': 43,
        '余甘子类': 44,
        '郁李仁类': 45,
        '沙苑子类': 46,
        '姜黄类': 47,
        '半夏类': 48,
        '枣仁类': 49,
        '菊花类': 50,
        '肉豆蔻类': 51,
        '三七类': 52,
        '仙茅类': 53,
        '浙石斛类': 54,
        '枳实类': 55,
        '白鲜皮类': 56,
        '楮实子类': 57,
        '川牛膝类': 58,
        '罗汉果类': 59,
        '山麦冬类': 60,
        '牛膝类': 61,
        '广藿香类': 62,
        '延胡索类': 63,
        '代代花类': 64,
        '千金子类': 65,
        '玫瑰类': 66,
        '苍耳子类': 67,
        '黑顺片类': 68,
        '火麻仁类': 69,
        '苦杏仁类': 70,
        '款冬花类': 71,
        '五味子类': 72,
        '玉米须类': 73,
        '枳壳类': 74,
        '拳参类': 75,
        '黑芝麻类': 76,
        '肺形草类': 77,
        '水半夏类': 78,
        '淮小麦类': 79,
        '菝葜类': 80,
        '防己类': 81,
        '梅花类': 82,
        '片姜黄类': 83,
        '桑葚类': 84,
        '天麻类': 85,
        '透骨草类': 86,
        '石菖蒲类': 87,
        '地黄类': 88,
        '瓜蒌子类': 89,
        '山茱萸类': 90,
        '天花粉类': 91,
        '小茴香类': 92,
        '土贝母类': 93,
        '白术类': 94,
        '山慈菇类': 95,
        '芦根类': 96,
        '陈皮类': 97,
        '干姜类': 98,
        '紫苑类': 99,
        '紫苏叶类': 100,
        '紫草类（掉渣）': 101,
        '枳椇子类': 102,
        '知母类': 103,
        '浙黄精类': 104,
        '浙贝母类': 105,
        '泽泻类': 106,
        '远志类': 107,
        '郁金类': 108,
        '玉竹类': 109,
        '鱼腥草类': 110,
        '玄参类': 111,
        '续断类': 112,
        '细辛类': 113,
        '吴茱萸类': 114,
        '王不留行类': 115,
        '太子参类': 116,
        '首乌藤类': 117,
        '石斛类': 118,
        '射干类': 119,
        '忍冬藤类': 120,
        '青葙子类': 121,
        '青风藤类': 122,
        '羌活类': 123,
        '胖大海类': 124,
        '南沙参类': 125,
        '牡丹皮类': 126,
        '没药类': 127,
        '猫人参类': 128,
        '龙眼肉类': 129,
        '桔梗类': 130,
        '九节菖蒲类': 131,
        '金银花类': 132,
        '黄芪类': 133,
        '黄岑类': 134,
        '何首乌类': 135,
        '葛根类': 136,
        '甘草类': 137,
        '覆盆子类': 138,
        '防风类': 139,
        '番泻叶类': 140,
        '杜仲类': 141,
        '丁香类': 142,
        '地骨皮类': 143,
        '党参类': 144,
        '当归类': 145,
        '丹参类': 146,
        '车前子类': 147,
        '柴胡类': 148,
        '槟榔类': 149,
        '荜澄茄类': 150,
        '北沙参类': 151,
        '柏子仁类': 152,
        '百部类': 153,
        '巴戟天类': 154
    }
    #custom_class_to_idx={"栀子":0,"水栀子":1}
    # custom_class_to_idx={"拳参":0,"珠芽蓼":1}
    # custom_class_to_idx={"沙大旺":0,"沙苑子":1,"猪屎豆":2,"紫云英":3}
    # get dataset
    if configs.dataset == "cifar10":
        testset = datasets.CIFAR10(root=configs.data_path['cifar10'],
                                    train=False,
                                    download=True,
                                    transform=transform_test)
    elif configs.dataset == "cifar100":
        testset = datasets.CIFAR100(root=configs.data_path['cifar100'],
                                    train=False,
                                    download=True,
                                    transform=transform_test)
    elif configs.dataset == "medicine":
        # 加载完整数据集
        full_dataset = CustomImageFolder(
            root=configs.data_path['medicine'],
            transform=transform_test,
            class_to_idx=custom_class_to_idx
        )
        
        # 划分数据集，使用load_ratio参数控制加载比例
        _, test_dataset = split_dataset(
            full_dataset,
            shuffle=True,
            seed=configs.seed,
            load_ratio=getattr(configs, 'load_ratio', 1.0)  # 如果没有设置load_ratio，默认为1.0
        )
        testset = test_dataset

        print("\n=== 完整数据集类别索引映射 ===")
        print(full_dataset.class_to_idx)
        
        # 打印测试集索引信息
        print("\n测试集索引信息:")
        print(f"总样本数: {len(testset)}")
        if isinstance(testset, Subset):
            print("测试集索引范围:", testset.indices[:10], "...", testset.indices[-10:])
            print("测试集标签分布:")
            labels = [testset.dataset.targets[i] for i in testset.indices]
            label_counts = {}
            for label in labels:
                label_counts[label] = label_counts.get(label, 0) + 1
            for label, count in sorted(label_counts.items()):
                print(f"类别 {label}: {count} 张图片")
    else:
        # 对于其他数据集，使用ImageFolder加载
        testset = datasets.ImageFolder(
            root=os.path.join(configs.data_path[configs.dataset], 'test'),
            transform=transform_test
        )
    
    # 创建测试数据加载器
    test_sampler = SequentialSampler(testset)
    test_loader = DataLoader(
        testset,
        sampler=test_sampler,
        batch_size=configs.eval_batch_size,
        num_workers=8,
        pin_memory=True,
        drop_last=False
    )
    
    return test_loader

def main():
    import torch
    from torch.utils.data import DataLoader
    import matplotlib.pyplot as plt

    # 测试配置类
    class TestConfig:
        def __init__(self):
            self.dataset = "medicine"
            self.data_path = {
                'medicine': './data/medicine'  # 请根据实际路径修改
            }
            self.batch_size = 32
            self.eval_batch_size = 32
            self.num_workers = 4
            self.pin_memory = True
            self.seed = 42
            self.mean = [0.485, 0.456, 0.406]
            self.std = [0.229, 0.224, 0.225]

    # 实例化配置
    config = TestConfig()

    print("=== 开始数据加载测试 ===")

    # 加载数据集
    try:
        train_loader = get_train_loader(config)
        test_loader = get_test_loader(config)
        print("数据加载成功！")
    except Exception as e:
        print("数据加载失败:", str(e))
        return

    # 打印数据加载器基本信息
    print(f"训练集批次数: {len(train_loader)}")
    print(f"测试集批次数: {len(test_loader)}")

    # 获取一个批次进行验证
    train_images, train_labels = next(iter(train_loader))
    test_images, test_labels = next(iter(test_loader))
    
    print("\n=== 批次数据维度检查 ===")
    print(f"训练图像 shape: {train_images.shape} (应为 [B, C, H, W])")
    print(f"训练标签 shape: {train_labels.shape} (应为 [B])")
    print(f"测试图像 shape: {test_images.shape}")
    print(f"测试标签 shape: {test_labels.shape}")

    # 打印类别信息
    dataset = train_loader.dataset.dataset  # 获取原始 CustomImageFolder 对象
    print("\n=== 类别索引映射 ===")
    for class_name, idx in sorted(dataset.class_to_idx.items(), key=lambda x: x[1]):
        print(f"{idx}: {class_name}")

    # 可视化一个图像样本
    def show_tensor_image(tensor, mean, std):
        unnormalize = transforms.Normalize(
            mean=[-m / s for m, s in zip(mean, std)],
            std=[1 / s for s in std]
        )
        img = unnormalize(tensor).permute(1, 2, 0).numpy()
        plt.imshow(img)
        plt.axis('off')
        plt.show()

    print("\n=== 显示一个训练样本 ===")
    show_tensor_image(train_images[0], config.mean, config.std)
    print("对应标签:", train_labels[0].item())

if __name__ == "__main__":
    main()

