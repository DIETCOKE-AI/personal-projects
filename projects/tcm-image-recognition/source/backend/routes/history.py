from flask import Blueprint, jsonify
from controllers.historyController import HistoryController

history_bp = Blueprint('history', __name__, url_prefix='/history')

@history_bp.route('/add', methods=['POST'])
def create_history():
    result, status_code = HistoryController.create_history()
    return jsonify(result), status_code

@history_bp.route('/batch', methods=['POST'])
def create_batch_history():
    result, status_code = HistoryController.create_batch_history()
    return jsonify(result), status_code

@history_bp.route('/page', methods=['POST'])
def get_histories():
    result, status_code = HistoryController.get_histories()
    return jsonify(result), status_code

@history_bp.route('/<int:history_id>', methods=['POST'])
def get_history(history_id):
    result, status_code = HistoryController.get_history(history_id)
    return jsonify(result), status_code

@history_bp.route('/edit/<int:history_id>', methods=['POST'])
def update_history(history_id):
    result, status_code = HistoryController.update_history(history_id)
    return jsonify(result), status_code

@history_bp.route('/delete/<int:history_id>', methods=['POST'])
def delete_history(history_id):
    result, status_code = HistoryController.delete_history(history_id)
    return jsonify(result), status_code
