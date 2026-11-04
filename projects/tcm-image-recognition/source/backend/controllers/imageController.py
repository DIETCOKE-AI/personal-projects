import os
from datetime import datetime
from flask import request, jsonify
from werkzeug.utils import secure_filename
from model.Image import Image
from util.file import save_uploaded_file, delete_file
from config.config import Config
from util.database import Database


class ImageController:

    @staticmethod
    def create_image():
        """创建图片记录"""
        data = request.form
        file = request.files.get('file')

        # 验证必填字段
        required_fields = ['chineseName', 'latinName', 'standard', 'confidence', 'uploadedBy']
        if not all(field in data for field in required_fields) or not file:
            return {"code":400,"message": "缺少必要项"}, 400

        try:
            # 保存上传文件
            filename = secure_filename(file.filename)
            filepath = save_uploaded_file(file, Config.UPLOAD_FOLDER)

            # 创建图片记录
            with Database.session_scope() as session:
                new_image = Image(
                    filename=filename,
                    url=f"/uploads/{filename}",
                    chineseName=data['chineseName'],
                    latinName=data['latinName'],
                    standard=data['standard'],
                    confidence=float(data['confidence']),
                    uploadedBy=int(data['uploadedBy'])
                )
                session.add(new_image)
                session.flush()  # 获取生成的ID但不提交事务

                return {
                    "code":0,
                    "data": ImageController._image_to_dict(new_image),
                    "message": "图片创建成功"
                }, 201

        except Exception as e:
            # 如果文件已保存但数据库操作失败，删除文件
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)
            return {"code":500,"message": str(e)}, 500

    @staticmethod
    def get_images():
        """获取所有图片"""
        try:
            with Database.session_scope() as session:
                images = session.query(Image).all()
                return {
                    "code":0,
                    "data": [ImageController._image_to_dict(img) for img in images],
                    "count": len(images)
                }, 200
        except Exception as e:
            return {"code":400,"message": str(e)}, 400

    @staticmethod
    def get_image(image_id):
        """获取单个图片详情"""
        try:
            with Database.session_scope() as session:
                image = session.query(Image).get(image_id)
                if not image:
                    return {"code":404,"message": "未找到该图片"}, 404
                return {"code":0,"data": ImageController._image_to_dict(image)}, 200
        except Exception as e:
            return {"code":400,"message": str(e)}, 400

    @staticmethod
    def update_image(image_id):
        """更新图片信息"""
        data = request.json
        try:
            with Database.session_scope() as session:
                image = session.query(Image).get(image_id)
                if not image:
                    return {"code":404,"message": "未找到该图片"}, 404

                # 更新字段
                updatable_fields = ['chineseName', 'latinName', 'standard', 'confidence', 'uploadedBy']
                for field in updatable_fields:
                    if field in data:
                        setattr(image, field, data[field] if field != 'confidence' else float(data[field]))

                return {
                    "code":0,
                    "data": ImageController._image_to_dict(image),
                    "message": "图片更新成功"
                }, 200

        except Exception as e:
            return {"code":400,"message": str(e)}, 400

    @staticmethod
    def delete_image(image_id):
        """删除图片"""
        try:
            with Database.session_scope() as session:
                image = session.query(Image).get(image_id)
                if not image:
                    return {"code":404,"message": "未找到该图片"}, 404

                # 删除物理文件
                delete_file(Config.UPLOAD_FOLDER, image.filename)

                session.delete(image)
                return {"code":0,"message": "图片删除成功"}, 200

        except Exception as e:
            return {"code":400,"message": str(e)}, 400

    @staticmethod
    def _image_to_dict(image):
        """将Image对象转换为字典"""
        return {
            "id": image.id,
            "filename": image.filename,
            "url": image.url,
            "chineseName": image.chineseName,
            "latinName": image.latinName,
            "standard": image.standard,
            "confidence": image.confidence,
            "uploadedBy": image.uploadedBy,
            "uploadedAt": image.uploadedAt.isoformat() if image.uploadedAt else None
        }
