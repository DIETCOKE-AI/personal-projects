import cv2
import numpy as np
from PIL import Image
import os

class CropLargestContourSquare(object):
    def __init__(self, debug=False, debug_dir='./debug_crop'):
        self.debug = debug
        self.debug_dir = debug_dir
        if self.debug and not os.path.exists(self.debug_dir):
            os.makedirs(self.debug_dir)

    def __call__(self, img):
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
