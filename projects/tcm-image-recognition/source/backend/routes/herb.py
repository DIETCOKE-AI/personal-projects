from flask import Blueprint, jsonify

from controllers.herbController import HerbController

herb_bp = Blueprint('herb', __name__, url_prefix='/herb')

@herb_bp.route('/page', methods=['POST'])
def get_herbs():
    result, status_code = HerbController.get_herb_all()
    return jsonify(result), status_code

@herb_bp.route('/getOne', methods=['POST'])
def get_herb_one():
    result, status_code = HerbController.get_herb_one()
    return jsonify(result), status_code
@herb_bp.route('/queryAllClasses', methods=['GET'])
def get_herb_Classes():
    result, status_code = HerbController.get_herb_classes()
    return jsonify(result), status_code
