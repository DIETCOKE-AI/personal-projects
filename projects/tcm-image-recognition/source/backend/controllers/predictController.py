# controllers/predictController.py

import os
import time
from datetime import datetime
import logging
from flask import jsonify, request, current_app
from werkzeug.utils import secure_filename
from config.config import Config
from model.History import HistoryData
from model.SimilarRecord import SimilarRecord
from util.database import Database
from PIL import Image
from config.model_config import INFERENCE_BATCH_SIZE

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

def predict_image():
    model_manager = current_app.model_manager
    filepath = None
    try:
        if 'file' not in request.files: return jsonify({"code":400, 'message': '没有上传文件'}), 400
        file = request.files['file']
        if file.filename == '': return jsonify({"code":400, 'message': '没有选择文件'}), 400
        if not allowed_file(file.filename): return jsonify({"code":400, 'message': '不支持的文件类型'}), 400
        timestamp = int(time.time() * 1000)
        _, ext = os.path.splitext(file.filename)
        filename = secure_filename(f"{timestamp}{ext}")
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(filepath)
        result = model_manager.predict(filepath)
        if 'error' in result:
             return jsonify({"code": 400, 'message': result['error']}), 400
        result['imageName'] = filename
        result['imagePath'] = filepath
        with Database.session_scope() as session:
            try:
                # --- 关键改动：从表单中获取用户ID ---
                user_id = request.form.get('userId', 1) # 默认为1，以防前端忘记传递

                subclass_id_to_save = result.get('id') if result.get('is_known') else None
                
                # 1. 创建并添加主历史记录
                new_history = HistoryData(image_name=filename, image_path=filepath, subclass_id=subclass_id_to_save, confidence=float(result['confidence']), created_by=user_id)
                session.add(new_history)
                session.flush() # flush以获取 new_history.id

                # 2. 创建并添加所有相似项记录
                if 'more' in result and isinstance(result['more'], list):
                    for item in result['more']:
                        if 'id' in item and 'confidence' in item:
                            new_record = SimilarRecord(
                                history_id=new_history.id, 
                                subclass_id=item['id'],
                                confidence=float(item['confidence']),
                                created_by=user_id
                            )
                            session.add(new_record)
                
                # 3. 一次性提交所有更改
                session.commit()

            except Exception as e:
                session.rollback()
                result['db_error'] = f'数据存储失败: {str(e)}'
                return jsonify({"code": 207, 'data': result,'message':'预测成功但存储失败'}), 207
        return jsonify({"code": 0, 'data': result,'message':'预测成功'}), 200
    except Exception as e:
        logger.error(f'请求处理或预测过程出错: {str(e)}', exc_info=True)
        return jsonify({"code":500, 'message': f'服务器错误: {str(e)}'}), 500


def batch_predict():
    model_manager = current_app.model_manager
    request_start_time = time.time()
    BATCH_SIZE = INFERENCE_BATCH_SIZE # ❗️现在您可以尝试一个更大的值


    timings = {"file_saving_ms": 0.0, "main_predict_ms": 0.0, "post_process_ms": 0.0}

    try:
        files = request.files.getlist('files')
        if not files or all(file.filename == '' for file in files):
            return jsonify({"code": 400, 'message': '没有选择文件'}), 400

        # --- 步骤 1: 保存所有文件并收集路径和PIL对象 ---
        t_start = time.perf_counter()
        filepaths, original_images, filename_map = [], [], {}
        for file in files:
            if file and allowed_file(file.filename):
                try:
                    img = Image.open(file.stream).convert("RGB")
                    timestamp = int(time.time() * 1000)
                    unique_filename = secure_filename(f"{timestamp}_{file.filename}")
                    # --- 关键修复：从全局配置中，获取在任何环境下都正确的上传目录绝对路径 ---
                    upload_dir = current_app.config['UPLOAD_FOLDER']
                    filepath = os.path.join(upload_dir, unique_filename)
                    print("====="+filepath)
                    img.save(filepath)
                    filepaths.append(filepath)
                    original_images.append(img)
                    filename_map[filepath] = {"original": file.filename, "unique": unique_filename}
                except Exception as e:
                    logger.warning(f"处理文件 {file.filename} 失败: {e}")
        timings["file_saving_ms"] = (time.perf_counter() - t_start) * 1000

        if not filepaths:
            return jsonify({"code": 400, 'message': '没有有效的文件被处理'}), 400

        # --- 步骤 2: 对主模型进行分块批量预测 ---
        all_main_results = []
        t_start = time.perf_counter()
        for i in range(0, len(filepaths), BATCH_SIZE):
            filepath_chunk = filepaths[i:i + BATCH_SIZE]
            chunk_results = model_manager.predict_batch_main_ensemble(filepath_chunk)
            all_main_results.extend(chunk_results)
        timings["main_predict_ms"] = (time.perf_counter() - t_start) * 1000

        # --- 步骤 3: 串行处理后续逻辑 ---
        final_response = []
        success_count = 0
        t_start = time.perf_counter()
        with Database.session_scope() as session:
            # ✅【核心改动】删除了创建 cursor 的错误代码
            for i, main_res in enumerate(all_main_results):
                filepath = filepaths[i]
                original_filename = filename_map[filepath]["original"]
                unique_filename = filename_map[filepath]["unique"]
                file_response = {"filename": original_filename}

                if "error" in main_res:
                    file_response.update({"code": 400, "message": main_res["error"]})
                else:
                    # ✅【核心改动】调用新的自包含函数，不再传递 cursor
                    result = model_manager._get_final_result_after_main(main_res, original_images[i])

                    if "error" in result:
                        file_response.update({"code": 400, "message": result["error"]})
                    else:
                        success_count += 1
                        # --- 关键修复：构建正确的Web路径 ---
                        web_image_path = f"/uploads/{unique_filename}"
                        result.update({'imageName': unique_filename, 'imagePath': web_image_path})
                        file_response.update({"code": 0, "message": "Processing successful", "data": result})
                        subclass_id = result.get('id') if result.get('is_known') else None
                        
                        # --- 关键修复：向数据库存储正确的Web路径和用户ID ---
                        user_id = request.form.get('userId', 1) # 从表单获取userId
                        history = HistoryData(image_name=unique_filename, image_path=web_image_path, subclass_id=subclass_id, confidence=float(result.get('confidence', 0.0)), created_by=user_id)
                        session.add(history)
                        session.flush() # 关键：立即执行，以获取 history.id
                        # --- 关键补充：保存相似项记录 ---
                        if 'more' in result and isinstance(result['more'], list):
                            for item in result['more']:
                                if 'id' in item and 'confidence' in item and item['id'] != -1:  # 只插入有效的subclass_id
                                    new_record = SimilarRecord(
                                        history_id=history.id,
                                        subclass_id=item['id'],
                                        confidence=float(item['confidence']),
                                        created_by=user_id
                                    )
                                    session.add(new_record)
                final_response.append(file_response)
            session.commit()
        timings["post_process_ms"] = (time.perf_counter() - t_start) * 1000

        total_time = round(time.time() - request_start_time, 2)
        logger.info(f"批量处理完成: {len(files)}个, 成功{success_count}个, 总耗时{total_time}秒, BATCH_SIZE={BATCH_SIZE}")
        logger.info(f"性能剖析(ms): 文件保存:{timings['file_saving_ms']:.2f} | 主模型批量预测:{timings['main_predict_ms']:.2f} | 后处理+DB:{timings['post_process_ms']:.2f}")
        return jsonify({"code": 0, "message": "识别成功", "data": final_response, "performance": timings}), 200

    except Exception as e:
        logger.error(f'批量请求处理出错: {str(e)}', exc_info=True)
        return jsonify({"code": 500, "message": f'服务器错误: {str(e)}'}), 500
