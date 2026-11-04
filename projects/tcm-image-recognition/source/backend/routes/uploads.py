from flask import send_from_directory, abort, Blueprint, current_app
import os
from werkzeug.utils import secure_filename
from config.config import Config

uploads_bp = Blueprint('uploads', __name__, url_prefix='/uploads')

@uploads_bp.route('/<string:filename>', methods=['GET'])
def uploaded_file(filename):
    # 安全处理文件名
    safe_filename = secure_filename(filename)

    # 检查文件扩展名是否合法
    if '.' not in safe_filename or safe_filename.rsplit('.', 1)[1].lower() not in Config.ALLOWED_EXTENSIONS:
        abort(400, description="不支持的文件类型")

    # 使用 Config.UPLOAD_FOLDER 作为唯一查找路径
    file_path = os.path.join(Config.UPLOAD_FOLDER, safe_filename)
    
    # 调试信息
    print("UPLOAD_FOLDER:", Config.UPLOAD_FOLDER)
    print("file_path:", file_path)
    print("文件是否存在:", os.path.exists(file_path))

    # 检查文件是否存在
    if os.path.exists(file_path):
        return send_from_directory(Config.UPLOAD_FOLDER, safe_filename)
    else:
        abort(404, description="文件不存在")
