import os
import torch
from tqdm import tqdm
from torch.utils.data import DataLoader, SequentialSampler
from torchvision import datasets, transforms
# from datasets.dataset.medicine import MedicineDataset # Assuming this is correctly defined
from models.get_network import get_network # Assuming this is correctly defined
# from utils.segmentation import CropLargestContourSquare # Assuming this is correctly defined
from PIL import Image, ImageFile
import torch.nn.functional as F

ImageFile.LOAD_TRUNCATED_IMAGES = True  # 允许加载截断的图片

def safe_loader(path):
    try:
        with open(path, 'rb') as f:
            img = Image.open(f)
            return img.convert('RGB')
    except Exception as e:
        print(f"Warning: Failed to load image {path}: {e}")
        return None

def evaluate_generalization_accuracy(__C, data_dir, batch_size=16, num_workers=4, pin_memory=True):
    """
    加载泛化测试集并计算分类准确率，并打印每个样本的分类置信度。
    :param __C: 配置对象，包含模型加载相关参数。
    :param data_dir: 测试数据集的路径（包含类别子文件夹）。
    :param batch_size: 批次大小。
    :param num_workers: 数据加载的进程数。
    :param pin_memory: 是否使用固定内存提高数据加载效率。
    :return: 每个类别的准确率，以及所有分类结果的列表。
    """
    # class_mapping = {
    #     '川麦冬': 0, '浙麦冬': 1
    
    # }
    class_mapping = {
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
    
    # 反向映射 class_mapping: index -> 类别名称
    index_to_class = {v: k for k, v in class_mapping.items()}

    # 定义数据预处理
    transform_test = transforms.Compose([
        #CropLargestContourSquare(debug=False), # 如果不需要，可以注释掉
        transforms.Resize((640,640)),
        transforms.ToTensor(),
        transforms.Normalize(__C.mean, __C.std)
    ])

    # 替换 ImageFolder 的 loader
    test_dataset = datasets.ImageFolder(root=data_dir, transform=transform_test)
    test_dataset.loader = safe_loader
    test_dataset.class_to_idx = class_mapping # 强制使用预定义的映射

    # 关键修正：同步 samples 和 targets
    # 过滤掉不在 class_mapping 中的图片，并根据 class_mapping 更新标签
    filtered_samples = []
    for path, _ in test_dataset.samples:
        class_folder_name = os.path.basename(os.path.dirname(path))
        if class_folder_name in class_mapping:
            filtered_samples.append((path, class_mapping[class_folder_name]))
        else:
            print(f"Warning: Image {path} belongs to class '{class_folder_name}' which is not in class_mapping. Skipping.")
    
    test_dataset.samples = filtered_samples
    test_dataset.targets = [label for _, label in test_dataset.samples]

    # DataLoader 里过滤 None
    def collate_fn(batch):
        # 过滤掉 safe_loader 返回的 None 图像
        batch = list(filter(lambda x: x is not None, batch))
        if len(batch) == 0:
            return None # 如果批次为空，返回 None
        return torch.utils.data.dataloader.default_collate(batch)

    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        sampler=SequentialSampler(test_dataset),
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=False, # 不要丢弃最后一个不完整的批次
        collate_fn=collate_fn
    )

    # 加载模型
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    net = get_network(__C).to(device)
    net.eval() # 设置模型为评估模式

    # 加载模型权重
    weight_path = os.path.join(__C.ckpts_dir, __C.model, __C.ckpt_version,
                               f'{__C.model}-{__C.ckpt_epoch}-{__C.ckpt_type}.pth')
    if not os.path.exists(weight_path):
        print(f"Error: Weight file {weight_path} not found at {weight_path}")
        return None, None # 返回 None 表示失败

    # 加载权重时处理 `module.` 前缀问题
    checkpoint = torch.load(weight_path, map_location=device)
    new_state_dict = {}
    for k, v in checkpoint.items():
        new_key = k.replace("module.", "")  # 去掉 DataParallel 训练时的前缀
        new_state_dict[new_key] = v

    try:
        net.load_state_dict(new_state_dict, strict=True)
    except RuntimeError as e:
        print(f"Error loading state_dict: {e}")
        return None, None # 返回 None 表示失败

    print(f"Successfully loaded weights from {weight_path}")

    # 统计正确数量
    correct_counts = {cls: 0 for cls in class_mapping}
    total_counts = {cls: 0 for cls in class_mapping}
    
    # 存储所有分类结果的详细信息
    all_classification_details = []

    # 计算准确率并收集置信度
    with torch.no_grad(): # 禁用梯度计算，节省内存和计算
        for batch_idx, batch in enumerate(tqdm(test_loader, desc='Generalization Test', total=len(test_loader))):
            if batch is None:
                continue # 跳过空批次
            
            images, labels = batch
            images, labels = images.to(device), labels.to(device)
            outputs = net(images)
            probabilities = F.softmax(outputs, dim=1) # 将 logits 转换为概率
            preds = torch.argmax(probabilities, dim=1)

            # 遍历批次中的每个样本
            for i, (pred, label) in enumerate(zip(preds, labels)):
                # 获取原始图像的路径。由于 DataLoader 可能会打乱或批处理，我们需要精确地索引到原始数据集中的样本
                # 注意：这里假设 test_dataset.samples 的顺序与 DataLoader 遍历的顺序一致，
                # 对于 SequentialSampler 是正确的。
                original_sample_idx = batch_idx * batch_size + i
                if original_sample_idx < len(test_dataset.samples):
                    image_path = test_dataset.samples[original_sample_idx][0]
                else:
                    image_path = "N/A (Path not found)" # 以防万一

                true_class_name = index_to_class[label.item()]
                predicted_class_name = index_to_class[pred.item()]
                
                # 获取预测的置信度
                confidence = probabilities[i, pred.item()].item() 
                
                is_correct = (pred.item() == label.item())

                # 记录所有分类的详细信息
                all_classification_details.append({
                    'image_path': image_path,
                    'true_class': true_class_name,
                    'predicted_class': predicted_class_name,
                    'confidence': confidence,
                    'is_correct': is_correct,
                    'all_probabilities': {index_to_class[k]: v.item() for k, v in enumerate(probabilities[i])}
                })

                # 更新统计计数
                if is_correct:
                    correct_counts[true_class_name] += 1
                total_counts[true_class_name] += 1

    # 计算每个类别的准确率
    accuracy_results = {
        cls: (correct_counts[cls] / total_counts[cls] if total_counts[cls] > 0 else 0)
        for cls in class_mapping
    }

    # 打印分类准确率
    print("\n--- Generalization Accuracy per Class ---")
    for class_name, acc in accuracy_results.items():
        print(f"{class_name}: {acc:.2%}")

    # # 打印所有分类结果，包括置信度
    # print("\n--- Detailed Classification Report (with Confidence) ---")
    # if not all_classification_details:
    #     print("No classification results to display.")
    # else:
    #     for item in all_classification_details:
    #         status = "Correct" if item['is_correct'] else "Misclassified"
    #         print(f"Image: {item['image_path']}")
    #         print(f"  Status: {status}")
    #         print(f"  True Class: {item['true_class']}")
    #         print(f"  Predicted Class: {item['predicted_class']} (Confidence: {item['confidence']:.4f})")
    #         print(f"  All Probabilities: {item['all_probabilities']}")
    #         print("-" * 40) # 分隔线

    return accuracy_results, all_classification_details
