from flask import Blueprint, request, jsonify
# 确保导入路径正确，注意大小写
from controllers.userContactController import UserContactController  # 修改类名首字母小写

userContact_bp = Blueprint('userContact', __name__, url_prefix='/userContact')

@userContact_bp.route('/updateContactInfo/<int:user_id>', methods=['POST'])
def update_contact_info(user_id):
    """更新用户联系信息路由"""
    data = request.get_json()
    result, status_code = UserContactController.updateContactInfo(user_id, data)
    return jsonify(result), status_code
@userContact_bp.route('/getUserContactInfo/<int:user_id>', methods=['GET'])
def getUserContactInfo(user_id):
    """获取用户联系信息路由"""
    result, status_code = UserContactController.getContactInfo(user_id)  # 使用修改后的类名
    return jsonify(result), status_code
