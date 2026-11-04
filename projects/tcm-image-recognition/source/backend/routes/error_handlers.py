from flask import Blueprint, jsonify

error_bp = Blueprint('errors', __name__)

@error_bp.app_errorhandler(404)
def not_found(e):
    """处理404错误"""
    return jsonify({'error': '未找到请求的页面'}), 404

@error_bp.app_errorhandler(500)
def server_error(e):
    """处理500错误"""
    return jsonify({'error': '服务器内部错误'}), 500
