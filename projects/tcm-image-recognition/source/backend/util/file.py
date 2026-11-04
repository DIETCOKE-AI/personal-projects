import os
from werkzeug.utils import secure_filename


def save_uploaded_file(file, upload_folder):
    """安全保存上传文件"""
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    filename = secure_filename(file.filename)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)
    return filepath


def delete_file(upload_folder, filename):
    """删除文件"""
    filepath = os.path.join(upload_folder, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
