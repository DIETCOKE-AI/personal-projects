from datetime import datetime
import argparse
import os 
import json

from conf import configs
from utils.training.epoch_train_engine import train_engine as epoch_train_engine
from utils.testing.epoch_test_engine import test_engine as epoch_test_engine
from utils.testing.epoch_generalizability_engine_new import evaluate_generalization_accuracy 

def parse_args():
    parser = argparse.ArgumentParser(description='MAC_Classification Args')
    # --- 通用参数 ---
    parser.add_argument('--model', type=str, required=True, help='choose a network')  
    parser.add_argument('--gpu', type=str, help="gpu choose, eg. '0,1,2,...' ",default='2')
    parser.add_argument('--run', type=str, dest='run_mode',choices=['train','test','general'], required=True)
    parser.add_argument('--seed', type=int, help='fix random seed')
    parser.add_argument('--img_size', type=int, default=640, help='Resolution size')
    parser.add_argument('--batch_size', type=int, default=12, help='batch size for dataloader')
    
    # --- 训练相关参数 ---
    parser.add_argument('--dataset', type=str, help='choose a dataset to learn')
    parser.add_argument('--custom_mappings_path', type=str, default='custom_mapping.json', help='自定义数据集映射JSON文件的路径')
    parser.add_argument('--save_epoch', type=int, default=1, help="save model after every N epoch")
    parser.add_argument('--gradient_accumulation_steps', type=int, default=1, help='warm up training phase')
    parser.add_argument('--lr', type=float, default=0.01, help='initial learning rate')
    parser.add_argument('--resume', action='store_true', default=False, help='resume training')
    parser.add_argument('--warmup_epoch', type=int, default=1, help='warmup epochs')
    parser.add_argument('--epoch', type=int, default=2000, help='total epochs')
    parser.add_argument('--eval_every_epoch', choices=['True','False'], type=str,default='True')
    parser.add_argument('--no_bias_decay', action='store_true', default=False, help='if using no bias decay')
    parser.add_argument('--mix', dest='mixed_training', action='store_true', default=False, help='if using mixed-up training, Pytorch >= 1.6')
    parser.add_argument('--optimizer', type=str, default='adam', choices=['adam', 'sgd', 'adamw'], help='Optimizer to use')
    parser.add_argument('--finetune_last_n', type=int, default=None, help="解冻最后N层参数进行微调。若不指定或设为0，则默认解冻所有层")
    parser.add_argument('--no_pretrained', action='store_true', default=False, help='禁用预训练权重，使用随机初始化（解决网络连接问题）')
    parser.add_argument('--weight_decay', type=float, default=5e-4, help='权重衰减参数，用于正则化')
    parser.add_argument('--dropout_rate', type=float, default=0.2, help='Dropout率，用于正则化')
    parser.add_argument('--use_local_attention', action='store_true', default=False, help='使用局部注意力模块')
    
    # --- 数据预处理相关参数 ---
    parser.add_argument('--force_resize', action='store_true', default=False, help='使用force_resize预处理策略，直接强制缩放到指定尺寸。默认使用center_crop策略')
    
    # ROI聚焦策略参数
    parser.add_argument('--roi_enable', action='store_true', default=False, help='启用ROI聚焦策略，适用于背景复杂的药材图像')
    parser.add_argument('--roi_edge_low', type=int, default=50, help='ROI边缘检测低阈值')
    parser.add_argument('--roi_edge_high', type=int, default=150, help='ROI边缘检测高阈值')
    parser.add_argument('--roi_min_area', type=float, default=0.01, help='ROI最小面积比例')
    
    # 细粒度特征增强策略参数
    parser.add_argument('--fine_grain_enable', action='store_true', default=False, help='启用细粒度特征增强策略，适用于近缘药材分类')
    parser.add_argument('--clahe_clip_limit', type=float, default=2.0, help='CLAHE对比度限制阈值')
    parser.add_argument('--erase_prob', type=float, default=0.3, help='随机擦除概率')
    
    # 类别平衡增强策略参数
    parser.add_argument('--balanced_aug_enable', action='store_true', default=False, help='启用类别平衡增强策略，适用于类别不平衡数据集')
    parser.add_argument('--noise_prob', type=float, default=0.3, help='添加噪声的概率')
    parser.add_argument('--adaptive_aug_prob', type=float, default=0.5, help='自适应增强基础概率')
    
    # --- 损失函数相关参数 ---
    parser.add_argument('--loss_fn', type=str, default='ce', choices=['ce', 'focal', 'labelsmoothing', 'enhanced_focal'], help="选择损失函数: 'ce' (CrossEntropy), 'focal' (FocalLoss), 'labelsmoothing', 'enhanced_focal'")
    parser.add_argument('--label_smoothing', action='store_true', default=False, help='if using label smoothing')
    parser.add_argument('--smoothing', type=float, default=0.0, help='control label smoothing value')
    parser.add_argument('--fl_gamma', type=float, default=2.0, help='Focal Loss 的 gamma 参数')
    parser.add_argument('--use_class_weights', action='store_true', default=False, help='启用自动类别权重 (基于反频率)')
    # 添加manual_boost_factor参数
    parser.add_argument('--manual_boost_factor', type=float, default=1.0, help='手动提升所有类别的权重因子')
    
    # =======================【核心修改区域：学习率调度器参数】=======================
    parser.add_argument('--scheduler', type=str, default='multistep', choices=['multistep', 'plateau', 'cosine'], help="学习率调度器类型: 'multistep' (按节点衰减), 'plateau' (按平台期衰减), 或 'cosine' (余弦退火)")
    parser.add_argument('--milestones', nargs='+', type=int, default=[100, 200, 300, 400, 500, 600, 700], help="MultiStepLR的衰减节点(epoch)。仅在 --scheduler=multistep 时生效")
    parser.add_argument('--lr_decay_rate', type=float, default=0.2, help="MultiStepLR的衰减率。仅在 --scheduler=multistep 时生效")
    parser.add_argument('--plateau_patience', type=int, default=3, help="ReduceLROnPlateau的patience。仅在 --scheduler=plateau 时生效")
    parser.add_argument('--plateau_factor', type=float, default=0.5, help="ReduceLROnPlateau的衰减率。仅在 --scheduler=plateau 时生效")
    parser.add_argument('--cosine_min_lr', type=float, default=0.0, help="余弦退火调度器的最小学习率。仅在 --scheduler=cosine 时生效")
    parser.add_argument('--cosine_restart_epochs', type=int, default=50, help="余弦退火调度器的重启周期(epoch)。若不指定则不重启，仅在 --scheduler=cosine 时生效")
    # =================================================================================

    # --- 测试/泛化相关参数 ---
    parser.add_argument('--ckpt_e', type=int, dest='ckpt_epoch', help="the model epoch you want to load (required for --ckpt_type=regular)")
    parser.add_argument('--ckpt_v', type=str, dest='ckpt_version', help="the model version you want to load")
    parser.add_argument('--ckpt_type', type=str, choices=['best','regular'], help='the model type you want to load')
    parser.add_argument('--output_dir', type=str, default=None, help='Directory to save evaluation results. Default is under the checkpoint folder.')
    parser.add_argument('--save_type', type=str, dest='type', choices=['best','regular'], required=False) # 兼容性参数
    parser.add_argument('--fast_dev_run', action='store_true', default=False, help='快速测试模式，只运行几个step来验证流程')
    parser.add_argument('--log_report_policy',type=str, default='best', choices=['always', 'best', 'final', 'never'], help="详细分类报告的记录策略")
    
    args = parser.parse_args()
    
    if args.run_mode == 'train' and not args.dataset:
        parser.error("--dataset is required when running in 'train' mode.")
        
    return args

if __name__ == '__main__':
    args = parse_args()
    args_dict = configs.parse_to_dict(args)
    configs.add_args(args_dict)
    
    # 处理 no_pretrained 参数，转换为 use_pretrained
    if hasattr(configs, 'no_pretrained') and configs.no_pretrained:
        configs.add_args({'use_pretrained': False})
        print("[INFO] 已禁用预训练权重，将使用随机初始化")
    else:
        configs.add_args({'use_pretrained': True})

    # 校验测试/泛化模式下的必要参数
    if configs.run_mode in ['test', 'general']:
        ### MODIFIED START: 修正了此处的属性名称 ###
        # 错误原因：应该检查 `ckpt_version` (dest的值)，而不是 `ckpt_v`。
        if not (hasattr(configs, 'ckpt_version') and configs.ckpt_version):
            raise ValueError("错误: 在 'test' 或 'general' 模式下必须提供 --ckpt_v (版本号).")
        ### MODIFIED END ###
            
        if not (hasattr(configs, 'ckpt_type') and configs.ckpt_type):
            raise ValueError("错误: 在 'test' 或 'general' 模式下必须提供 --ckpt_type ('best' 或 'regular').")
        
        # 只有当类型是 'regular' 时，才检查 epoch 参数
        if configs.ckpt_type == 'regular':
            if not (hasattr(configs, 'ckpt_epoch') and configs.ckpt_epoch):
                raise ValueError("错误: 当 --ckpt_type='regular' 时, 必须提供 --ckpt_e (epoch号).")

    if hasattr(configs, 'dataset') and configs.dataset:
        try:
            with open(configs.custom_mappings_path, 'r', encoding='utf-8') as f:
                mappings = json.load(f)
            
            dataset_name = configs.dataset
            if dataset_name in mappings:
                dataset_info = mappings[dataset_name]
                if 'num_classes' in dataset_info:
                    num_classes = dataset_info['num_classes']
                else:
                    num_classes = len(dataset_info.get('class_to_idx', {}))
                configs.add_args({'num_classes': num_classes})
                print(f"Loaded num_classes: {num_classes} for dataset: '{dataset_name}'")
            else:
                raise ValueError(f"错误: 数据集 '{dataset_name}' 在文件 '{configs.custom_mappings_path}' 中未找到。")
        except Exception as e:
            raise e

    configs.path_init()
    configs.training_init()

    # 自动生成泛化测试的输出目录
    if configs.run_mode == 'general' and (not hasattr(configs, 'output_dir') or configs.output_dir is None):
        if not all([configs.model, configs.ckpt_version]):
            raise ValueError("必须提供 --model 和 --ckpt_v 来自动生成输出目录。")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. 使用数据集名称，而不是类别数量
        dataset_part = f"_{configs.dataset}" if hasattr(configs, 'dataset') and configs.dataset else ""
        
        # 2. 根据ckpt_type决定后缀是 _best 还是 _e<epoch>
        if configs.ckpt_type == 'best':
            type_part = "_best"
        else: # 必须是 'regular', 因为前面已经校验过
            type_part = f"_e{configs.ckpt_epoch}"

        folder_name = f"{timestamp}{dataset_part}_v{configs.ckpt_version}{type_part}"
        
        configs.output_dir = os.path.join('test', configs.model, folder_name)
        print(f"未指定输出目录。将默认使用: {configs.output_dir}")

    print("\nHyper parameters:")
    print(configs)

    if configs.run_mode == 'train':
        if not hasattr(configs, 'num_classes'):
            raise ValueError("Configuration error: 'num_classes' is not set.")
        epoch_train_engine(configs)
    elif configs.run_mode == 'test':
        epoch_test_engine(configs)
    elif configs.run_mode == 'general':
        # 确保运行泛化测试时有 num_classes
        if not hasattr(configs, 'num_classes'):
             raise ValueError("Configuration error: 'num_classes' is not set for generalization test.")
        evaluate_generalization_accuracy(configs)
