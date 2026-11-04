import os
from torchvision import transforms
from torch.utils.data import Dataset
from PIL import Image
from torch.utils.data import DataLoader

class MedicineDataset(Dataset):
    def __init__(self, root_dir, label_type='major', transform=None):
        """
        Args:
            root_dir (string): 数据集的根目录，每个子文件夹代表一个大类。
            label_type (string): 选择'major' 只使用大类标签, 选择'minor' 只使用小类标签。
            transform (callable, optional): 可选的变换操作，应用于样本。
        """
        self.root_dir = root_dir
        self.label_type = label_type
        self.transform = transform
        self.major_classes = [d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))]  # 获取所有大类
        self.class_to_idx = self._create_class_mapping()
        self.samples = self._make_dataset()  # 生成样本列表

    def _create_class_mapping(self):
        """ 创建类别到索引的映射 """
        if self.label_type == 'major':
            return {cls_name: idx for idx, cls_name in enumerate(self.major_classes)}
        elif self.label_type == 'minor':
            minor_classes = set()
            for major_cls in self.major_classes:
                major_cls_dir = os.path.join(self.root_dir, major_cls)
                for sub_cls in os.listdir(major_cls_dir):
                    sub_cls_dir = os.path.join(major_cls_dir, sub_cls)
                    if os.path.isdir(sub_cls_dir):
                        minor_classes.add(sub_cls)
            return {cls_name: idx for idx, cls_name in enumerate(sorted(minor_classes))}
        else:
            raise ValueError("label_type must be 'major' or 'minor'")

    def _make_dataset(self):
        """
        生成样本列表，每个样本是一个元组 (image_path, class_index, class_name)
        """
        samples = []
        for major_cls in self.major_classes:
            major_cls_dir = os.path.join(self.root_dir, major_cls)
            if not os.path.isdir(major_cls_dir):
                continue
            for sub_cls in os.listdir(major_cls_dir):  # 遍历小类文件夹
                sub_cls_dir = os.path.join(major_cls_dir, sub_cls)
                if not os.path.isdir(sub_cls_dir):
                    continue
                for img_name in os.listdir(sub_cls_dir):  # 遍历图片
                    if img_name.endswith('.bmp'):
                        img_path = os.path.join(sub_cls_dir, img_name)
                        if os.path.isfile(img_path):
                            if self.label_type == 'major':
                                label_name = major_cls
                            else:
                                label_name = sub_cls
                            samples.append((img_path, self.class_to_idx[label_name], label_name))
        return samples

    def __len__(self):
        """
        返回数据集的大小
        """
        return len(self.samples)

    def __getitem__(self, idx):
        """
        获取第 idx 个样本
        """
        img_path, label, class_name = self.samples[idx]
        image = Image.open(img_path).convert('RGB')  # 打开图像并转换为RGB格式

        if self.transform:
            image = self.transform(image)

        return image, label

# 示例使用
if __name__ == "__main__":
    # 定义数据变换
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
    ])

    # 选择大类标签数据集
    dataset_major = MedicineDataset(root_dir='./data/medicine', label_type='major', transform=transform)
    dataloader_major = DataLoader(dataset_major, batch_size=16, shuffle=True)

    # 选择小类标签数据集
    dataset_minor = MedicineDataset(root_dir='./data/medicine', label_type='minor', transform=transform)
    dataloader_minor = DataLoader(dataset_minor, batch_size=16, shuffle=True)

    # 遍历所有 batch 并打印形状
    print("=== Major Dataset ===")
    for batch_idx, (images, labels, class_names) in enumerate(dataloader_major):
        print(f"Batch {batch_idx}: Image Shape {images.shape}, Labels Shape {labels.shape}")

    print("\n=== Minor Dataset ===")
    for batch_idx, (images, labels, class_names) in enumerate(dataloader_minor):
        print(f"Batch {batch_idx}: Image Shape {images.shape}, Labels Shape {labels.shape}")
