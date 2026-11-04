from config.config import Config
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager

from extensions import db


class Database:
    @staticmethod
    def init_app(app):
        """初始化数据库配置"""
        app.config.setdefault('SQLALCHEMY_DATABASE_URI', Config.SQLALCHEMY_DATABASE_URI)
        app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
        app.config.setdefault('SQLALCHEMY_ENGINE_OPTIONS', {
            'pool_size': 10,
            'pool_recycle': 3600,
            'pool_pre_ping': True
        })
        db.init_app(app)

    @staticmethod
    @contextmanager
    def session_scope():
        """提供数据库会话上下文"""
        session = db.session
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @staticmethod
    def create_all(app):
        """创建所有表"""
        with app.app_context():
            db.create_all()

    @staticmethod
    def drop_all(app):
        """删除所有表"""
        with app.app_context():
            db.drop_all()

    # 封装常用CRUD操作
    @staticmethod
    def add(instance):
        """添加记录"""
        try:
            db.session.add(instance)
            db.session.commit()
            return instance
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e

    @staticmethod
    def update():
        """更新记录（直接操作session）"""
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e

    @staticmethod
    def delete(instance):
        """删除记录"""
        try:
            db.session.delete(instance)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e

    @staticmethod
    def query_all(model):
        """查询所有记录"""
        return model.query.all()

    @staticmethod
    def query_by_id(model, id):
        """通过ID查询"""
        return model.query.get(id)

    @staticmethod
    def query_filter(model, **kwargs):
        """条件查询"""
        return model.query.filter_by(**kwargs).all()
