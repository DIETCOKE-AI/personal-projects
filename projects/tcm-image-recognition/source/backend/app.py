import logging
import os
import sys
import time
from datetime import timedelta
from flask import Flask
from flask_jwt_extended import JWTManager

# --- 关键修复：在此处直接定义 resource_path 函数 ---
def resource_path(relative_path):
    """
    获取资源的绝对路径，兼容开发环境和PyInstaller打包环境。
    """
    try:
        # PyInstaller会创建一个名为_MEIPASS的临时文件夹，并将所有资源放在那里
        base_path = sys._MEIPASS
    except Exception:
        # 在开发环境中，sys._MEIPASS不存在，此时我们使用当前脚本所在的目录
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

from config.config import Config
from extensions import cors
from predict_two_steps import ModelManager
from util.database import Database

# 全局模型管理器
model_manager = None

def init_model():
    """初始化模型管理器（单例模式）"""
    global model_manager
    if model_manager is None:
        model_manager = ModelManager()
        logger.info("模型管理器初始化完成")

def create_app(config_class=Config):
    """应用工厂函数"""
    
    # 关键修改：使用 resource_path 来正确配置 Flask 应用的模板路径
    template_folder = resource_path('templates')
    app = Flask(__name__, template_folder=template_folder)
    
    # 加载配置
    app.config.from_object(config_class)

    # JWT 配置
    app.config['JWT_SECRET_KEY'] = Config.JWT_SECRET_KEY
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=10)
    app.config['JWT_TOKEN_LOCATION'] = ['headers', 'cookies']
    jwt = JWTManager(app)

    # 初始化扩展
    initialize_extensions(app)

    # 数据库初始化
    Database.init_app(app)
    with app.app_context():
        from model.SysUser import SysUser
        from model.Image import Image
        from model.HerbMainClass import HerbMainClass
        from model.HerbSubClass import HerbSubClass
        from model.HerbStandard import HerbStandard
        from model.History import HistoryData
        from model.SimilarRecord import SimilarRecord
        Database.create_all(app)

    # 初始化并附加模型管理器
    init_model()
    app.model_manager = model_manager

    # 注册蓝图
    register_blueprints(app)

    # 确保上传目录存在
    ensure_directories(app)
    
    return app

def initialize_extensions(app):
    """初始化所有Flask扩展"""
    cors.init_app(app)


def register_blueprints(app):
    """注册所有蓝图"""
    from routes.main_routes import main_bp
    from routes.predict import predict_bp
    from routes.image import image_bp
    from routes.history import history_bp
    from routes.uploads import uploads_bp
    from routes.herb import herb_bp
    from routes.contact import userContact_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(predict_bp)
    app.register_blueprint(image_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(uploads_bp)
    app.register_blueprint(herb_bp)
    app.register_blueprint(userContact_bp)

def ensure_directories(app):
    """确保必要的目录存在，并设置正确的上传路径到全局配置中"""
    # 使用 resource_path 来获取在任何环境下都正确的 uploads 文件夹的绝对路径
    upload_folder_path = resource_path('uploads')
    
    # 确保这个文件夹真实存在，如果不存在，就创建它
    os.makedirs(upload_folder_path, exist_ok=True)
    
    # 将这个绝对正确的路径，设置到Flask的全局配置中，供其他模块使用
    app.config['UPLOAD_FOLDER'] = upload_folder_path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


if __name__ == '__main__':
    app = create_app()
    logger.info("Starting Flask server...")
    
    # --- READY SIGNAL FOR ELECTRON ---
    # This specific print statement is used by the Electron host to detect when the server is ready.
    print("BACKEND_READY_FOR_ELECTRON")
    # Ensure the signal is sent immediately by flushing the stdout buffer.
    sys.stdout.flush()
    
    # 在生产环境中，debug应为False
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
