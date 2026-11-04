from flask import Blueprint, jsonify
from controllers.imageController import ImageController

image_bp = Blueprint('images', __name__, url_prefix='/images')

@image_bp.route('/', methods=['POST'])
def create_image():
    result, status_code = ImageController.create_image()
    return jsonify(result), status_code

@image_bp.route('/', methods=['GET'])
def get_images():
    result, status_code = ImageController.get_images()
    return jsonify(result), status_code

@image_bp.route('/<int:image_id>', methods=['GET'])
def get_image(image_id):
    result, status_code = ImageController.get_image(image_id)
    return jsonify(result), status_code

@image_bp.route('/<int:image_id>', methods=['PUT'])
def update_image(image_id):
    result, status_code = ImageController.update_image(image_id)
    return jsonify(result), status_code

@image_bp.route('/<int:image_id>', methods=['DELETE'])
def delete_image(image_id):
    result, status_code = ImageController.delete_image(image_id)
    return jsonify(result), status_code
