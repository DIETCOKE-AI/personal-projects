import os
import sys
from dotenv import load_dotenv

load_dotenv()

if getattr(sys, 'frozen', False):
    # 如果是打包后的exe，BASE_DIR指向PyInstaller创建的临时目录
    BASE_DIR = sys._MEIPASS
else:
    # 如果是作为普通脚本运行
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Config:
    # config.py
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'tiff', 'bmp'}

    SECRET_KEY = os.environ["TCM_SECRET_KEY"]
    JWT_SECRET_KEY = os.environ["TCM_JWT_SECRET_KEY"]
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

    SQLALCHEMY_DATABASE_URI = os.environ["TCM_DATABASE_URL"]
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'pool_size': 10,
        'max_overflow': 20,
        'echo': False
    }

    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200MB

    REQUEST_TIMEOUT = 30
