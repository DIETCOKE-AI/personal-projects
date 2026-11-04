import jwt
from flask import jsonify, request
from flask_jwt_extended import create_access_token
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash
from model.UserContact import UserContact
from util.database import Database
from typing import Tuple, Dict, Any
class UserContactController:

    ##定义用户联系方式更新方法
    @staticmethod
    def updateContactInfo(user_id, data):
        print(data)
        if not data:
            return {"code": 1, "message": "请求数据不能为空"}, 400
        required_fields = ['address', 'city', 'country', 'postalCode']
        if not all(field in data for field in required_fields):
            return {"code": 1, "message": "缺少必填字段"}, 400
    
        try:
            with Database.session_scope() as session:
                userContact = session.query(UserContact).filter(UserContact.user_id == user_id).first()
                if not userContact:
                    userContact = UserContact(
                        user_id = user_id,
                        address = data.get('address'),
                        city = data.get('city'),
                        country = data.get('country'),
                        postal_code = data.get('postalCode')
                    )
                    session.add(userContact)
                else:
                    userContact.address = data.get('address')
                    userContact.city = data.get('city')
                    userContact.country = data.get('country')
                    userContact.postal_code = data.get('postalCode')
                return {"code": 0, "message": "更新成功"}, 200
        except Exception as e:
            return {"code": 1, "message": "数据库操作失败"}, 500
    
    @staticmethod
    def getContactInfo(user_id):
        #由于没有uid的用户无法进入联系方式修改界面，所以不需要进行判断
        #根据id查询数据库
        with Database.session_scope() as session:
            userContact = session.query(UserContact).filter(UserContact.user_id == user_id).first()
            if not userContact:
                return {"code": 1, "message": "未找到联系方式"}, 404
            return {"code": 0, "message": "查询成功", "data": userContact.to_dict()}, 200
        return {"code": 0, "message": "更新成功"}, 200
    
