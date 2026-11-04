import cv2
import numpy as np
import os
from PIL import Image
import torch

def extract_patch(image, center, patch_size=(640, 640)):
    """
    根据物体的中心提取640x640大小的patch
    :param image: 原图像
    :param center: 物体中心坐标 (cx, cy)
    :param patch_size: patch大小 (默认640x640)
    :return: 提取出的patch
    """
    patch_h, patch_w = patch_size
    cx, cy = center

    # 计算左上角坐标，确保patch不会超出图像边界
    x1 = max(cx - patch_w // 2, 0)
    y1 = max(cy - patch_h // 2, 0)

    # 确保patch右下角不超出图像边界
    x2 = min(cx + patch_w // 2, image.shape[1])
    y2 = min(cy + patch_h // 2, image.shape[0])

    # 重新计算patch大小，防止超出边界
    patch = image[y1:y2, x1:x2]

    # 如果patch小于640x640，填充空白背景（白色）
    if patch.shape[0] < patch_h or patch.shape[1] < patch_w:
        patch_resized = np.ones((patch_h, patch_w, 3), dtype=np.uint8) * 255  # 使用白色背景
        patch_resized[:patch.shape[0], :patch.shape[1]] = patch
        patch = patch_resized

    return patch


def find_largest_contour_center(image):
    """
    使用传统方法通过轮廓检测找到面积最大的物体的中心
    :param image: 输入图像
    :return: 面积最大物体的中心坐标 (cx, cy)
    """
    # 转换为灰度图像
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 使用Otsu的自适应阈值进行分割
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # 找到轮廓
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None  # 没有找到轮廓，返回None

    # 找到面积最大的轮廓
    largest_contour = max(contours, key=cv2.contourArea)

    # 计算轮廓的质心
    M = cv2.moments(largest_contour)
    if M["m00"] != 0:
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        return (cx, cy)
    else:
        return None


def process_images_in_folder(input_folder, output_folder, patch_size=(640, 640)):
    """
    对文件夹中的每张图片执行提取patch操作，并保存结果（每张图只保存一个patch）
    :param input_folder: 输入文件夹路径
    :param output_folder: 输出文件夹路径
    :param patch_size: 提取的patch大小 (默认640x640)
    """
    # 获取文件夹中的所有图片文件，支持 .bmp 格式
    image_files = [f for f in os.listdir(input_folder) if f.endswith(('.jpg', '.png', '.tiff', '.jpeg', '.bmp'))]

    if len(image_files) == 0:
        print("没有找到符合条件的图像文件！")
        return

    for image_file in image_files:
        print(f"正在处理图像: {image_file}")

        # 读取图像
        image_path = os.path.join(input_folder, image_file)
        image = cv2.imread(image_path)

        if image is None:
            print(f"无法加载图像: {image_path}")
            continue

        # 找到面积最大的物体的中心
        center = find_largest_contour_center(image)

        if center is None:
            print(f"在图像 {image_file} 中未找到任何物体！")
            continue

        # 提取patch
        patch = extract_patch(image, center,patch_size)

        # 保存提取的patch
        output_path = os.path.join(output_folder, f"{os.path.splitext(image_file)[0]}_patch.bmp")
        try:
            success = cv2.imwrite(output_path, patch)
            if not success:
                print(f"无法保存patch到 {output_path}")
            else:
                print(f"保存patch到 {output_path}")
        except Exception as e:
            print(f"保存图像时发生错误: {e}")


def segment_single_image(image):
    """对单张图像进行分割处理
    Args:
        image: PIL Image或numpy array格式的图像
    Returns:
        处理后的图像(numpy array格式)
    """
    # 如果输入是PIL Image,转换为numpy array
    if isinstance(image, Image.Image):
        image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    # 找到最大轮廓的中心
    center = find_largest_contour_center(image)
    if center is None:
        return image  # 如果没找到物体,返回原图
        
    # 提取patch
    patch = extract_patch(image, center, patch_size=(640, 640))
    return patch


if __name__ == "__main__":
    # 输入大类文件夹路径
    input_folder = 'danzhuye'  # 大类文件夹路径

    # 输出大类文件夹路径
    output_folder = 'danzhuye_seg'  # 输出大类文件夹路径

    # 确保输出大类文件夹存在
    os.makedirs(output_folder, exist_ok=True)

    # 遍历大类文件夹中的每个小类子文件夹
    for root, dirs, files in os.walk(input_folder):
        for dir_name in dirs:
            subfolder_path = os.path.join(root, dir_name)  # 小类子文件夹路径
            output_subfolder = os.path.join(output_folder, dir_name)  # 输出对应的小类子文件夹路径

            # 确保每个小类子文件夹的输出目录存在
            os.makedirs(output_subfolder, exist_ok=True)

            # 对每个小类子文件夹中的图片进行处理
            process_images_in_folder(subfolder_path, output_subfolder)


