import numpy as np
import random
from datetime import datetime

# path configs
data_path = {
    'cifar10': './data/cifar10',
    'cifar100': './data/cifar100',
    'imagenet': './data/imagenet',
    'medicine_99': './data/medicine_99',
    'medicine_155': './data/medicine_155',
    'medicine_175': './data/medicine_175',
    'medicine_200': './data/medicine_200',
    '栀子类':'./data/栀子类',
    '沙苑子类':'./data/沙苑子类',
    '拳参类':'./data/拳参类',
    '菝葜类':'./data/菝葜类',
    '陈皮类':'./data/陈皮类',
    '麦冬类':'./data/麦冬类',
    '山麦冬类':'./data/山麦冬类',
    '巴戟天类':'./data/巴戟天类',
    '北沙参类':'./data/北沙参类',
    '柏子仁类':'./data/柏子仁类',
    '柴胡类':'./data/柴胡类',
    '覆盆子类':'./data/覆盆子类',
    '太子参类':'./data/太子参类',
    '郁金类':'./data/郁金类',
    '浙贝母类':'./data/浙贝母类'
}
result_log_dir = 'log'
ckpts_dir = 'ckpts'
tensorboard_log_dir = 'runs'

# training configs
milestones = [100,200,300,400,500,600,700]
save_epoch = 15
gpu = '0'
# 生成随机种子作为版本号
seed = random.randint(0, 9999999)
# 默认使用随机种子作为版本号
version = str(seed)
# 注意：当使用--resume恢复训练时，在epoch_run.py和epoch_train_engine.py中会根据--ckpt_version参数覆盖version的值
dataset = 'cifar100'
batch_size = 64
eval_batch_size = 16  # 或者 8，建议先从16开始尝试

# data preprocessing configs
force_resize = False  # 是否使用force_resize预处理策略，默认为False使用center_crop

# 新增的预处理策略配置
roi_enable = False  # ROI聚焦策略开关
roi_edge_low_threshold = 50  # ROI边缘检测低阈值
roi_edge_high_threshold = 150  # ROI边缘检测高阈值
roi_min_area_ratio = 0.01  # ROI最小面积比例

fine_grain_enable = False  # 细粒度特征增强策略开关
clahe_clip_limit = 2.0  # CLAHE对比度限制
erase_prob = 0.3  # 随机擦除概率
erase_scale = (0.02, 0.1)  # 随机擦除面积比例范围
erase_ratio = (0.3, 3.3)  # 随机擦除宽高比范围

balanced_aug_enable = False  # 类别平衡增强策略开关
noise_prob = 0.3  # 添加噪声的概率
noise_intensity = (0.01, 0.05)  # 噪声强度范围
adaptive_aug_prob = 0.5  # 自适应增强基础概率
# data configs
mean = (0.5070751592371323, 0.48654887331495095, 0.4409178433670343)
std = (0.2673342858792401, 0.2564384629170883, 0.27615047132568404)
num_workers = 16
pin_memory = True
eval_every_epoch = True

# create time
time_now = datetime.now().strftime('%A_%d_%B_%Y_%Hh_%Mm_%Ss')
