from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """根路由，返回上传页面"""
    return render_template('index.html')
