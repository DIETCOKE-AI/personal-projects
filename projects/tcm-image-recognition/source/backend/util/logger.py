import logging
from logging.handlers import RotatingFileHandler
import os


def setup_logging(app):
    """配置应用日志"""
    if not os.path.exists('logs'):
        os.mkdir('logs')

    # 文件日志处理器
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10240,
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)

    # 控制台日志
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # 应用日志配置
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)

    # 禁用默认的日志处理器
    app.logger.propagate = False
