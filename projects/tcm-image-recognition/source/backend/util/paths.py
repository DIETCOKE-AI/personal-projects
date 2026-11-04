# tcm/util/paths.py
import os
import sys

def resource_path(relative_path):
    """
    获取资源的绝对路径，兼容开发环境和PyInstaller打包环境。
    """
    try:
        # PyInstaller 会创建一个名为 _MEIPASS 的临时文件夹，并将所有资源放在那里
        base_path = sys._MEIPASS
    except Exception:
        # 在开发环境中，sys._MEIPASS 不存在，此时我们使用当前脚本所在的目录
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)
