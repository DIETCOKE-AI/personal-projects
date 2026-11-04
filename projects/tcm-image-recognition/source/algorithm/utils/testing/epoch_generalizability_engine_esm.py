import os
import torch
from torch.utils.data import DataLoader, SequentialSampler
from torchvision import datasets, transforms
from datasets.dataset.medicine import MedicineDataset
from models.get_network import get_network
from utils.segmentation import CropLargestContourSquare
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True  # 允许加载截断的图片
def evaluate_generalization_accuracy(__C, data_dir, batch_size=16, num_workers=4, pin_memory=True):
    """
    串联主模型和易混淆类别子模型，统计整体、主模型、子模型准确率。
    :param __C: 配置对象，包含主模型加载相关参数。
    :param data_dir: 测试数据集的路径（包含类别子文件夹）。
    :param batch_size: 批次大小。
    :param num_workers: 数据加载的进程数。
    :param pin_memory: 是否使用固定内存提高数据加载效率。
    :return: 各类准确率。
    """
    # 主模型类别映射
    class_mapping = {
        '亚麻籽类': 0, '使君子类': 1, '决明子类': 2, '白芍类': 3, '土茯苓类': 4, '月季类': 5, '望江南类': 6, '枸杞类': 7, '栀子类': 8,
        '淡竹叶类': 9, '炒稻芽类': 10, '白扁豆类': 11, '板蓝根类': 12, '莪术类': 13, '蔓荆子类': 14, '麦冬类': 15,
        '黄荆子类': 16, '补骨脂类': 17, '苍术类': 18, '草豆蔻类': 19, '草果类': 20, '赤小豆类': 21, '川芎类': 22, '大枣类': 23, '茯神类': 24, '鼓槌石斛类': 25, '黑豆类': 26, '红参类': 27, '红花类': 28, '槐花类': 29, '黄连类': 30, '鸡血藤类': 31, '韭菜子类': 32, '莲须类': 33, '麦芽类': 34, '芡实类': 35, '人参类': 36, '三叶青类': 37, '山楂类': 38, '蛇床子类': 39, '锁阳类': 40, '通草类': 41, '夏枯草类': 42, '薏苡仁类': 43, '余甘子类': 44, '郁李仁类': 45, '沙苑子类': 46,
        '姜黄类': 47, '半夏类': 48, '枣仁类': 49, '菊花类': 50, '肉豆蔻类': 51, '三七类': 52, '仙茅类': 53, '浙石斛类': 54, '枳实类': 55, '白鲜皮类': 56, '楮实子类': 57, '川牛膝类': 58, '罗汉果类': 59, '山麦冬类': 60, '牛膝类': 61, '广藿香类': 62, '延胡索类': 63, '代代花类': 64, '千金子类': 65, '玫瑰类': 66, '苍耳子类': 67, '黑顺片类': 68, '火麻仁类': 69, '苦杏仁类': 70, '款冬花类': 71, '五味子类': 72, '玉米须类': 73, '枳壳类': 74, '拳参类': 75,
        '黑芝麻类': 76, '肺形草类': 77, '水半夏类': 78, '淮小麦类': 79, '菝葜类': 80, '防己类': 81, '梅花类': 82, '片姜黄类': 83, '桑葚类': 84, '天麻类': 85, '透骨草类': 86, '石菖蒲类': 87, '地黄类': 88, '瓜蒌子类': 89, '山茱萸类': 90, '天花粉类': 91, '小茴香类': 92, '土贝母类': 93, '白术类': 94, '山慈菇类': 95, '芦根类': 96, '陈皮类': 97, '干姜类': 98
    }
    # 易混淆类别映射
    class_mapping2 = {
        '人参类': 0, '代代花类': 1, '使君子类': 2, '千金子类': 3, '半夏类': 4,
        '天花粉类': 5, '天麻类': 6, '小茴香类': 7, '山慈菇类': 8, '干姜类': 9,
        '广藿香类': 10, '延胡索类': 11, '拳参类': 12, '款冬花类': 13, '水半夏类': 14,
        '片姜黄类': 15, '瓜蒌子类': 16, '石菖蒲类': 17, '蔓荆子类': 18, '陈皮类': 19,
        '黑芝麻类': 20, '黑顺片类': 21
    }
    index_to_class = {v: k for k, v in class_mapping.items()}
    index_to_class2 = {v: k for k, v in class_mapping2.items()}
    
    # 创建子模型类别到主模型类别的映射
    sub_to_main_mapping = {k: class_mapping[k] for k in class_mapping2.keys()}

    # 数据预处理
    transform_test = transforms.Compose([
        transforms.Resize((640,640)),
        transforms.ToTensor(),
        transforms.Normalize(__C.mean, __C.std)
    ])

    # 替换 ImageFolder 的 loader
    test_dataset = datasets.ImageFolder(root=data_dir, transform=transform_test)
    test_dataset.class_to_idx = class_mapping
    test_dataset.samples = [
        (path, class_mapping[os.path.basename(os.path.dirname(path))])
        for path, _ in test_dataset.samples
        if os.path.basename(os.path.dirname(path)) in class_mapping
    ]
    test_dataset.targets = [label for _, label in test_dataset.samples]

    def collate_fn(batch):
        batch = list(filter(lambda x: x is not None, batch))
        if len(batch) == 0:
            return None
        return torch.utils.data.dataloader.default_collate(batch)

    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        sampler=SequentialSampler(test_dataset),
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=False,
        collate_fn=collate_fn
    )

    # 加载主模型
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    main_model = get_network(__C).to(device)
    main_model.eval()
    weight_path = os.path.join(__C.ckpts_dir, __C.model, __C.ckpt_version,
                               f'{__C.model}-{__C.ckpt_epoch}-{__C.ckpt_type}.pth')
    if not os.path.exists(weight_path):
        print(f"Error: Weight file {weight_path} not found!")
        return
    checkpoint = torch.load(weight_path, map_location=device)
    new_state_dict = {k.replace("module.", ""): v for k, v in checkpoint.items()}
    main_model.load_state_dict(new_state_dict, strict=True)
    print(f"Successfully loaded main model weights from {weight_path}")

    # 加载子模型
    from models.net.mobilevit_large import MobileViT_large
    sub_model = MobileViT_large(num_classes=22, pretrained=False).to(device)  # 直接使用EfficientNetB7,写死类别数
    sub_model.eval()
    sub_model_path = './ckpts/example-submodel.pth'  # 直接写死路径
    if not os.path.exists(sub_model_path):
        print(f"Error: Sub model weight file {sub_model_path} not found!")
        return
    sub_checkpoint = torch.load(sub_model_path, map_location=device)
    sub_new_state_dict = {k.replace("module.", ""): v for k, v in sub_checkpoint.items()}
    sub_model.load_state_dict(sub_new_state_dict, strict=True)
    print(f"Successfully loaded sub model weights from {sub_model_path}")

    # 统计
    total, correct = 0, 0
    misclassified_counts = {i: {j: 0 for j in range(len(class_mapping))} for i in range(len(class_mapping))}
    
    # 添加每个类别的统计
    class_correct = {cls: 0 for cls in class_mapping}
    class_total = {cls: 0 for cls in class_mapping}

    with torch.no_grad():
        for batch in test_loader:
            if batch is None:
                continue
            images, labels = batch
            images, labels = images.to(device), labels.to(device)
            main_outputs = main_model(images)
            main_preds = torch.argmax(main_outputs, dim=1)

            for i, (main_pred, label) in enumerate(zip(main_preds, labels)):
                true_class = index_to_class[label.item()]
                pred_class = index_to_class[main_pred.item()]
                total += 1
                class_total[true_class] += 1  # 统计每个类别的总数

                # 判断是否属于易混淆类别
                if pred_class in class_mapping2:
                    # 用子模型再细分
                    sub_input = images[i].unsqueeze(0)
                    sub_output = sub_model(sub_input)
                    sub_pred = torch.argmax(sub_output, dim=1).item()
                    sub_pred_class = index_to_class2[sub_pred]
                    # 将子模型的预测结果映射回主模型的类别索引
                    final_pred = class_mapping[sub_pred_class]
                else:
                    final_pred = main_pred.item()

                # 统计准确率
                if final_pred == label.item():
                    correct += 1
                    class_correct[true_class] += 1  # 统计每个类别的正确数
                else:
                    # 确保使用索引进行统计
                    true_idx = label.item()
                    pred_idx = final_pred
                    misclassified_counts[true_idx][pred_idx] += 1

    print(f"\n总样本数: {total}")
    print(f"整体准确率: {correct/total:.2%}")

    # 打印每个类别的准确率
    print("\n每个类别的准确率:")
    for cls in class_mapping:
        if class_total[cls] > 0:
            acc = class_correct[cls] / class_total[cls]
            print(f"{cls}: {class_correct[cls]}/{class_total[cls]} = {acc:.2%}")

    # 打印详细误分类
    print("\n误分类情况:")
    for true_idx, misclassified in misclassified_counts.items():
        true_class = index_to_class[true_idx]
        misclassified_info = {index_to_class[pred_idx]: count for pred_idx, count in misclassified.items() if count > 0}
        if misclassified_info:
            print(f"{true_class} was misclassified as: {misclassified_info}")

    return {
        "overall_acc": correct/total,
        "class_acc": {cls: class_correct[cls]/class_total[cls] for cls in class_mapping if class_total[cls] > 0}
    }
