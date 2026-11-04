from flask import Blueprint
from controllers.predictController import (
    predict_image,
    batch_predict
)

predict_bp = Blueprint('predict', __name__, url_prefix='/predict')

predict_bp.route('/one', methods=['POST'])(predict_image)
predict_bp.route('/batch', methods=['POST'])(batch_predict)
