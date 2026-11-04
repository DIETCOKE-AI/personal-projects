# 请替换整个文件内容为以下代码：
import os
import time
import json
from datetime import datetime
import numpy as np
from collections import OrderedDict
import torch
import torch.nn as nn
from torch.utils.data import Subset
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau
import warnings

from sklearn.metrics import classification_report

from datasets.enhanced_dataset_loader import get_train_loader, get_test_loader
from models.get_network import get_network
from utils.util import WarmUpLR, split_weights
from criterion import LabelSmoothingCrossEntropy, FocalLoss
from utils.visual_engine import TrainingVisualizer

warnings.filterwarnings("ignore", message="Detected call of `lr_scheduler.step()` before `optimizer.step()`.*")
warnings.filterwarnings("ignore", message="`torch.cuda.amp.autocast(args...)` is deprecated.*")

def train_engine(__C):
    # 1. 定义网络
    net = get_network(__C)
    net = net.cuda()
    if __C.n_gpu > 1:
        net = nn.DataParallel(net, device_ids=__C.devices)

    # 2. 定义数据加载器
    train_loader = get_train_loader(__C)
    test_loader = get_test_loader(__C)
    
    train_dataset = train_loader.dataset
    if isinstance(train_dataset, Subset):
        class_to_idx = train_dataset.dataset.class_to_idx
    else:
        class_to_idx = train_dataset.class_to_idx
    idx_to_class = {v: k for k, v in class_to_idx.items()}

    # 3. 计算类别权重
    class_weights = None
    override_log_messages = []

    if __C.use_class_weights:
        if isinstance(train_dataset, Subset): labels = [train_dataset.dataset.targets[i] for i in train_dataset.indices]
        else: labels = train_dataset.targets
        
        # 修复: 只计算实际存在的类别的权重
        class_counts = torch.bincount(torch.tensor(labels), minlength=__C.num_classes)
        
        # 找出训练集中实际存在的类别
        existing_classes_mask = class_counts > 0
        num_existing_classes = existing_classes_mask.sum().item()
        
        if num_existing_classes < __C.num_classes:
            print(f"[WARNING] 训练集仅包含 {num_existing_classes}/{__C.num_classes} 个类别的数据")
            missing_classes = [idx_to_class.get(i, f'Class_{i}') for i in range(__C.num_classes) if class_counts[i] == 0]
            if len(missing_classes) <= 10:
                print(f"[WARNING] 缺失的类别: {missing_classes}")
            else:
                print(f"[WARNING] 缺失的类别 (前10个): {missing_classes[:10]} ... (共{len(missing_classes)}个)")
        
        # 计算权重：只对存在的类别计算反频率权重
        class_weights = torch.zeros(__C.num_classes, dtype=torch.float32)
        
        # 对于存在的类别，使用反频率权重
        total_samples = len(labels)
        for i in range(__C.num_classes):
            if class_counts[i] > 0:
                # 反频率权重公式: total_samples / (num_classes * count_per_class)
                class_weights[i] = total_samples / (num_existing_classes * class_counts[i].float())
        
        # 归一化权重（只对非零权重）
        if existing_classes_mask.any():
            mean_weight = class_weights[existing_classes_mask].mean()
            if mean_weight > 0:
                class_weights = class_weights / mean_weight
        
        # 应用手动权重覆盖（只对训练集中存在的类别）
        with open(__C.custom_mappings_path, 'r', encoding='utf-8') as f: all_mappings = json.load(f)
        dataset_config = all_mappings.get(__C.dataset, {})
        weight_overrides = dataset_config.get('manual_weight_overrides', {})
        
        if weight_overrides:
            override_log_messages.append("\n[INFO] 手动权重调整已启用。详情 (Top 5):")
            sorted_overrides = sorted(weight_overrides.items(), key=lambda item: item[1], reverse=True)
            applied_count = 0
            skipped_classes = []
            
            for class_name, factor in sorted_overrides:
                class_idx = class_to_idx.get(class_name)
                if class_idx is not None:
                    # 检查该类别是否在训练集中存在
                    if class_counts[class_idx] > 0:
                        class_weights[class_idx] *= factor
                        if applied_count < 5:
                            override_log_messages.append(f"  - 类别 '{class_name}': 权重因子 x{factor:.2f}")
                        applied_count += 1
                    else:
                        skipped_classes.append(class_name)
            
            if applied_count > 5:
                override_log_messages.append(f"  ... (及其他 {applied_count - 5} 个)")
            
            if skipped_classes:
                override_log_messages.append(f"\n[WARNING] 以下类别不在训练集中，跳过权重调整: {skipped_classes[:5]}{'...' if len(skipped_classes) > 5 else ''}")

        else:
            override_log_messages.append("\n[INFO] 未找到或未启用手动权重调整。")

        class_weights = class_weights.cuda()
    for msg in override_log_messages:
        print(msg)
    
    # 4. 定义损失函数
    loss_function_info = ""
    if __C.loss_fn == 'focal':
        loss_function_info = f"FocalLoss (gamma={__C.fl_gamma}, class_weights={'启用' if __C.use_class_weights else '禁用'})"
        loss_function = FocalLoss(alpha=class_weights, gamma=__C.fl_gamma)
    elif __C.loss_fn == 'labelsmoothing':
        loss_function_info = f"LabelSmoothingCrossEntropy (smoothing={__C.smoothing})"
        loss_function = LabelSmoothingCrossEntropy(__C.smoothing)
    else: # 默认或 'ce'
        loss_function_info = f"CrossEntropyLoss (class_weights={'启用' if __C.use_class_weights else '禁用'})"
        loss_function = nn.CrossEntropyLoss(weight=class_weights)
    print(f"[INFO] 使用损失函数: {loss_function_info}")
    
    # 5. 定义优化器
    params = split_weights(net) if __C.no_bias_decay else net.parameters()
    
    # 获取权重衰减参数，支持自定义
    weight_decay = getattr(__C, 'weight_decay', 5e-4)
    
    if __C.optimizer == 'adam':
        optimizer = optim.Adam(params, lr=__C.lr, weight_decay=weight_decay)
    elif __C.optimizer == 'adamw':
        optimizer = optim.AdamW(params, lr=__C.lr, weight_decay=weight_decay)
    else:  # sgd
        optimizer = optim.SGD(params, lr=__C.lr, momentum=0.9, weight_decay=weight_decay)
    
    # 6. 定义日志和模型保存路径
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dataset_name_for_log = None
    if hasattr(__C, 'dataset') and hasattr(__C, 'custom_mappings_path'):
        try:
            with open(__C.custom_mappings_path, 'r', encoding='utf-8') as f:
                mappings = json.load(f)
            if __C.dataset in mappings:
                dataset_name_for_log = __C.dataset
        except Exception as e:
            print(f"[WARNING] Failed to load custom mappings for log naming: {e}")
    
    if dataset_name_for_log:
        log_filename = f"{timestamp}_{dataset_name_for_log}_{__C.version}.log"
    else:
        log_filename = f"{timestamp}_{__C.num_classes}cls_{__C.version}.log"
    log_dir_path = os.path.join(__C.result_log_dir, __C.model)
    if not os.path.exists(log_dir_path): os.makedirs(log_dir_path)
    log_path = os.path.join(log_dir_path, log_filename)
    print(f"[INFO] 日志文件将保存在: {log_path}")
    current_checkpoint_dir = os.path.join(__C.ckpts_dir, __C.model, __C.version)
    if not os.path.exists(current_checkpoint_dir): os.makedirs(current_checkpoint_dir)
    regular_checkpoint_template = os.path.join(current_checkpoint_dir, f'{__C.model}-{{epoch}}-regular.pth')
    best_checkpoint_path = os.path.join(current_checkpoint_dir, f'{__C.model}-best.pth')
    
    # 7. 混合精度训练标量
    if __C.mixed_training: scalar = torch.cuda.amp.GradScaler()
    
    # 8. 恢复训练逻辑
    start_epoch = 1
    best_acc = 0.0        
    if __C.resume:
        # 恢复训练时，使用ckpt_version作为当前版本号，这样日志文件会使用与原训练相同的版本号
        __C.version = __C.ckpt_version
        print(f"[INFO] 恢复训练模式已启用，使用ckpt_version: {__C.version}作为当前版本号")
        resume_checkpoint_dir = os.path.join(__C.ckpts_dir, __C.model, __C.ckpt_version)
        checkpoint_file_to_load = os.path.join(resume_checkpoint_dir, f'{__C.model}-{__C.ckpt_epoch}-regular.pth')
        if os.path.exists(checkpoint_file_to_load):
            print(f"[INFO] 正在从检查点恢复: {checkpoint_file_to_load}")
            
            checkpoint = torch.load(checkpoint_file_to_load, map_location=torch.device('cuda'), weights_only=True)
            
            # 检查checkpoint是否是一个包含多个键的字典
            if isinstance(checkpoint, dict) and 'model' in checkpoint:
                print("[INFO] 检测到包含多个组件的checkpoint文件")
                state_dict = checkpoint['model']
                # 如果checkpoint中包含优化器状态，也加载它
                if 'optimizer' in checkpoint:
                    optimizer.load_state_dict(checkpoint['optimizer'])
                    print("[INFO] 成功加载优化器状态")
                # 如果checkpoint中包含epoch信息，使用它
                if 'epoch' in checkpoint:
                    start_epoch = checkpoint['epoch'] + 1
                    print(f"[INFO] 从checkpoint中获取epoch信息: {checkpoint['epoch']}")
            else:
                state_dict = checkpoint
                
            is_data_parallel_model = isinstance(net, nn.DataParallel)
            is_data_parallel_ckpt = next(iter(state_dict)).startswith('module.')

            if is_data_parallel_model and not is_data_parallel_ckpt:
                print("[INFO] 检测到单卡权重，正在适配多卡模式 (添加 'module.' 前缀)...")
                new_state_dict = OrderedDict()
                for k, v in state_dict.items():
                    name = 'module.' + k
                    new_state_dict[name] = v
                state_dict = new_state_dict
            elif not is_data_parallel_model and is_data_parallel_ckpt:
                print("[INFO] 检测到多卡权重，正在适配单卡模式 (移除 'module.' 前缀)...")
                new_state_dict = OrderedDict()
                for k, v in state_dict.items():
                    name = k[7:]  # 移除 'module.'
                    new_state_dict[name] = v
                state_dict = new_state_dict
            
            net.load_state_dict(state_dict)
            
            start_epoch = __C.ckpt_epoch + 1
            print(f"[SUCCESS] 成功恢复模型权重。将从 Epoch {start_epoch} 开始训练。")
        else:
            print(f"[WARNING] 检查点文件 {checkpoint_file_to_load} 未找到。将从头开始训练。")
    
    # 9. 定义学习率调度器
    if __C.scheduler == 'plateau':
        # 设置min_lr参数避免学习率降为0
        min_lr = getattr(__C, 'min_lr', 1e-6)  # 默认为1e-6
        print(f"[INFO] 使用 ReduceLROnPlateau 调度器 (patience={__C.plateau_patience}, factor={__C.plateau_factor}, min_lr={min_lr}) ")
        train_scheduler = ReduceLROnPlateau(optimizer, mode='max', factor=__C.plateau_factor, patience=__C.plateau_patience, verbose=True, min_lr=min_lr)
    elif __C.scheduler == 'cosine':
        # 余弦退火调度器
        cosine_restart_epochs = getattr(__C, 'cosine_restart_epochs', 50)  # 默认为50
        cosine_min_lr = getattr(__C, 'cosine_min_lr', 0.0)
        
        if cosine_restart_epochs and cosine_restart_epochs > 0:
            # 带重启的余弦退火调度器
            print(f"[INFO] 使用 CosineAnnealingWarmRestarts 调度器 (T_0={cosine_restart_epochs}, eta_min={cosine_min_lr})")
            train_scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=cosine_restart_epochs, eta_min=cosine_min_lr)
        else:
            # 普通余弦退火调度器
            print(f"[INFO] 使用 CosineAnnealingLR 调度器 (T_max={__C.epoch}, eta_min={cosine_min_lr})")
            train_scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=__C.epoch, eta_min=cosine_min_lr)
    else: # 默认使用 'multistep'
        print(f"[INFO] 使用 MultiStepLR 调度器 (milestones={__C.milestones})")
        train_scheduler = optim.lr_scheduler.MultiStepLR(optimizer, milestones=__C.milestones, gamma=__C.lr_decay_rate)
    
    warmup_schedule = None
    if start_epoch <= __C.warmup_epoch:
        print(f"[INFO] 学习率热身已激活，共 {__C.warmup_epoch} 个 epoch。")
        iter_per_epoch = len(train_loader)
        warmup_schedule = WarmUpLR(optimizer, iter_per_epoch * __C.warmup_epoch)
    
    # 初始化可视化工具
    visualizer = TrainingVisualizer(log_dir_path, __C.model, __C.version, __C.dataset)
    
    # 如果使用类别权重，可视化类别权重
    if __C.use_class_weights and class_weights is not None:
        class_names = [idx_to_class.get(i, 'Unknown') for i in range(__C.num_classes)]
        weights_save_path = os.path.join(log_dir_path, 'class_weights.png')
        visualizer.plot_class_weights(class_weights.cpu().numpy(), class_names, weights_save_path)
    
    # 写入初始配置到日志
    with open(log_path, 'w') as logfile:
        logfile.write("="*50 + "\n" + "Training Start Time: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n" + "="*50 + "\n\n")
        logfile.write("Hyper-parameters:\n" + str(__C) + "\n\n")
        logfile.write(f"Loss Function: {loss_function_info}\n\n")
        if __C.use_class_weights and class_weights is not None:
            logfile.write("Calculated Class Weights (before manual overrides):\n")
            for i in range(__C.num_classes): logfile.write(f"  - Class '{idx_to_class.get(i, 'Unknown')}': {class_weights[i]:.4f}\n")
            logfile.write("\n")

            if override_log_messages:
                clean_messages = [msg.replace('[INFO] ', '') for msg in override_log_messages]
                logfile.write("\n".join(clean_messages))
                logfile.write("\n\n")

    # 10. 开始训练循环
    for epoch in range(start_epoch, __C.epoch + 1):
        # 调度器更新（除了plateau策略，其他策略都在epoch开始时更新）
        if __C.scheduler in ['multistep', 'cosine'] and epoch > __C.warmup_epoch:
            if epoch > 1:
                train_scheduler.step()

        start_time = time.time()
        net.train()
        epoch_loss_sum, total_samples = 0, 0
        for step, (images, labels) in enumerate(train_loader):
            if warmup_schedule and epoch <= __C.warmup_epoch:
                warmup_schedule.step()
            
            images, labels = images.cuda(), labels.cuda()
            
            # 梯度清零
            optimizer.zero_grad()
            
            # 前向传播
            if __C.mixed_training:
                with torch.amp.autocast('cuda'):
                    outputs = net(images)
                    loss = loss_function(outputs, labels)
                # 反向传播和参数更新
                scalar.scale(loss).backward()
                scalar.step(optimizer)
                scalar.update()
            else:
                outputs = net(images)
                loss = loss_function(outputs, labels)
                loss.backward()
                optimizer.step()
            
            # 累积损失和样本数
            epoch_loss_sum += loss.item() * images.size(0)
            total_samples += images.size(0)
            print(f'\r[{__C.version}] Training Epoch: {epoch} [{step * __C.batch_size + len(images):>5}/{len(train_loader.dataset):>5}] | Loss: {loss.item():.4f} | LR: {optimizer.param_groups[0]["lr"]:.6f}', end='')
            if __C.fast_dev_run and step >= 5:
                print("\n[INFO] Fast dev run enabled, breaking train loop...")
                break
        print()
        average_train_loss = epoch_loss_sum / total_samples if total_samples > 0 else 0
        
        # 12. 评估模型
        eval_start_time = time.time()
        net.eval()
        test_loss = 0.0
        correct = 0
        total = 0
        all_preds = []
        all_labels = []
        
        with torch.no_grad():
            for images, labels in test_loader:
                images, labels = images.cuda(), labels.cuda()
                outputs = net(images)
                loss = loss_function(outputs, labels)
                
                test_loss += loss.item() * images.size(0)
                _, predicted = outputs.max(1)
                total += labels.size(0)
                correct += predicted.eq(labels).sum().item()
                
                all_preds.extend(predicted.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
                
                if __C.fast_dev_run and len(all_labels) >= 100:
                    break
        
        num_eval_samples = total
        if num_eval_samples == 0:
            print("[WARNING] No samples were evaluated. Skipping metrics calculation.")
            continue

        acc = correct / num_eval_samples
        test_average_loss = test_loss / num_eval_samples
        
        if __C.scheduler == 'plateau' and epoch > __C.warmup_epoch:
            train_scheduler.step(acc)

        print(f'Evaluating Network.....\nTest set: Average loss: {test_average_loss:.4f}, Accuracy: {acc:.4f}, Time consumed:{time.time() - eval_start_time:.2f}s')
        
        # 更新最佳准确率
        is_new_best = acc > best_acc
        if is_new_best:
            best_acc = acc
            best_acc_epoch = epoch
            no_improvement_count = 0  # 重置早停计数器
            # 保存最佳模型
            best_checkpoint = {
                'model': net.state_dict(),
                'optimizer': optimizer.state_dict(),
                'epoch': epoch,
                'best_acc': best_acc
            }
            torch.save(best_checkpoint, best_checkpoint_path)
            print(f"[INFO] 已保存新的最佳模型，准确率: {best_acc:.4f}")
        
        should_log_report = ((__C.log_report_policy == 'always') or (__C.log_report_policy == 'best' and is_new_best) or (__C.log_report_policy == 'final' and epoch == __C.epoch))
        
        # 记录指标到可视化工具
        visualizer.record_metrics(epoch, average_train_loss, test_average_loss, acc, optimizer.param_groups[0]['lr'])
        
        # 写入日志
        with open(log_path, 'a') as logfile:
            logfile.write(f"Epoch {epoch},  Train Average Loss: {average_train_loss:.4f},  Learning Rate: {optimizer.param_groups[0]['lr']:.6f},  Test Average Loss: {test_average_loss:.4f},  Test Accuracy: {acc:.4f}\n")
            
            if should_log_report:
                print("[INFO] Logging detailed classification report...")
                try:
                    test_dataset = test_loader.dataset
                    class_names = test_dataset.dataset.classes if isinstance(test_dataset, Subset) else test_dataset.classes
                    possible_labels = np.arange(__C.num_classes)
                    report = classification_report(all_labels, all_preds, labels=possible_labels, target_names=class_names, digits=4, zero_division=0)
                    logfile.write("Classification Report:\n" + report + "\n\n")
                except Exception as e:
                    print(f"[ERROR] 生成分类报告失败: {e}")
                    logfile.write(f"\n[ERROR] 生成分类报告失败: {e}\n\n")
        
        # 保存当前epoch的regular模型
        regular_checkpoint_path = regular_checkpoint_template.format(epoch=epoch)
        regular_checkpoint = {
            'model': net.state_dict(),
            'optimizer': optimizer.state_dict(),
            'epoch': epoch,
            'accuracy': acc
        }
        torch.save(regular_checkpoint, regular_checkpoint_path)
        print(f"[INFO] 已保存第 {epoch} 个epoch的regular模型")
        
        # 训练可视化
        if epoch % __C.save_epoch == 0:
            visualizer.save_all_plots()        
        
        torch.cuda.empty_cache()

    # 训练结束  
    print(f"--- Training Finished. Best accuracy: {best_acc:.4f} (在epoch {best_acc_epoch}) ---")
    visualizer.save_all_plots()
    with open(log_path, 'a') as logfile:
        logfile.write("="*50 + "\n" + "Training End Time: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
        logfile.write(f"Final Best Accuracy: {best_acc:.4f} (在epoch {best_acc_epoch})\n" + "="*50 + "\n")
