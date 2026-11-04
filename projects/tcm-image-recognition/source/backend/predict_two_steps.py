# tcm/predict_two_steps.py

from torchvision import transforms
from PIL import Image
from collections import OrderedDict, defaultdict
import json
import cv2
import os
import mysql.connector
import mysql.connector.pooling
import time
import traceback
import datetime

import torch
import torch.nn.functional as F

# 从更新后的配置文件导入所有需要的变量
from config.model_config import (
    NORMALIZATION_MEAN, NORMALIZATION_STD,
    SEGMENTATION_CLASSES, HIGH_RESOLUTION_CLASSES, PAFPN_CLASSES,RESIZE_CROP_CLASSES,
    MODEL_TYPE_CONFIG, IMAGE_SIZE_CONFIG, MODEL_PATH_CONFIG, DB_CONFIG,
    MODEL_REGISTRY,
    MAIN_ENSEMBLE_CONFIG, OPEN_SET_CONFIDENCE_THRESHOLD, # VOTE_THRESHOLD 已移除
    NUM_KNOWN_CLASSES
)


class ModelManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            # ✅ 版本号更新，明确这是基于加权策略的版本
            print("正在初始化模型管理器 (V9.0 - 加权集成策略版)...")
            cls._instance = super(ModelManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"模型将运行在: {self.device}")
        self.use_autocast = 'cuda' in str(self.device)
        print(f"将使用半精度(FP16)推理: {'是' if self.use_autocast else '否'}")
        self.mean, self.std = NORMALIZATION_MEAN, NORMALIZATION_STD
        self.open_set_threshold = OPEN_SET_CONFIDENCE_THRESHOLD
        img_size = IMAGE_SIZE_CONFIG["default"][0]
        self.transforms_dict = {
            'force_resize': transforms.Compose([transforms.Resize((img_size, img_size)), transforms.ToTensor(), transforms.Normalize(self.mean, self.std)]),
            'center_crop': transforms.Compose([transforms.Resize(img_size), transforms.CenterCrop(img_size), transforms.ToTensor(), transforms.Normalize(self.mean, self.std)])
        }
        self.subclass_transforms = {
            'default': self.transforms_dict['force_resize'],
            'high_resolution': transforms.Compose([transforms.Resize(IMAGE_SIZE_CONFIG["high_resolution"]), transforms.ToTensor(), transforms.Normalize(mean=self.mean, std=self.std)]),
            #'shayuanzi': transforms.Compose([transforms.Resize(IMAGE_SIZE_CONFIG["shayuanzi"]), transforms.ToTensor(), transforms.Normalize(mean=self.mean, std=self.std)]),
            'pafpn': transforms.Compose([transforms.Resize(IMAGE_SIZE_CONFIG["pafpn"]), transforms.ToTensor(), transforms.Normalize(mean=self.mean, std=self.std)]),
            # --- 新增的数据处理方式 ---
            'resize_center_crop': transforms.Compose([
                transforms.Resize(img_size), # 将短边缩放到 img_size (640)
                transforms.CenterCrop(img_size), # 从中心裁剪出 img_size (640x640)
                transforms.ToTensor(),
                transforms.Normalize(self.mean, self.std)
            ])
        }
        self.db_config = DB_CONFIG
        print(f"数据库配置: {self.db_config['host']}:{self.db_config.get('port', 3306)}/{self.db_config['database']}")
        try:
            print("正在创建数据库连接池...")
            self.connection_pool = mysql.connector.pooling.MySQLConnectionPool(**self.db_config)
            print("✅ 数据库连接池创建成功")
        except Exception as e:
            print(f"❌ 创建数据库连接池失败: {str(e)}")
            import traceback
            traceback.print_exc()
            self.connection_pool = None
        print("正在加载主集成模型...")
        self.main_ensemble_models = self._load_main_ensemble_models()
        print("正在加载子模型...")
        self.subclass_models = self._preload_subclass_models()
        print("所有模型加载完成！")
        if self.main_ensemble_models:
            print(f"主集成模型数量: {len(self.main_ensemble_models)}")
            print(f"开集策略: {len(self.main_ensemble_models)}模型置信度加权, 最终置信度 > {self.open_set_threshold} 通过")
            self._warmup_models()
        self._initialized = True

    def _warmup_models(self):
        print("🚀 正在进行模型预热...")
        img_size = IMAGE_SIZE_CONFIG["default"][0]
        dummy_inputs = {'force_resize': torch.randn(2, 3, img_size, img_size, device=self.device), 'center_crop': torch.randn(2, 3, img_size, img_size, device=self.device)}
        with torch.no_grad(), torch.amp.autocast(self.device.type, enabled=self.use_autocast):
            for model, config in zip(self.main_ensemble_models, MAIN_ENSEMBLE_CONFIG):
                _ = model(dummy_inputs[config['transform_type']])
        if self.device.type == 'cuda': torch.cuda.synchronize()
        print("✅ 模型预热完成!")

    def _load_main_ensemble_models(self):
        models = []
        for i, config in enumerate(MAIN_ENSEMBLE_CONFIG, 1):
            model_name, ckpt_path = config['model_name'], config['ckpt_path']
            print(f"[{i}/{len(MAIN_ENSEMBLE_CONFIG)}] 检查模型: {model_name}")
            print(f"    路径: {ckpt_path}")
            
            if not os.path.exists(ckpt_path):
                print(f"    ⚠️  模型文件不存在，跳过")
                continue
            
            ModelClass = MODEL_REGISTRY.get(model_name)
            if not ModelClass:
                print(f"    ⚠️  未找到模型类 {model_name}，跳过")
                continue
            
            try:
                print(f"    ✓ 正在实例化模型...")
                net = ModelClass(num_classes=NUM_KNOWN_CLASSES).to(self.device)
                
                print(f"    ✓ 正在加载权重...")
                checkpoint = torch.load(ckpt_path, map_location=self.device, weights_only=True)
                
                print(f"    ✓ 正在应用权重...")
                net.load_state_dict({k.replace("module.", ""): v for k, v in checkpoint.items()}, strict=True)
                
                net.eval()
                models.append(net)
                print(f"    ✅ 模型加载成功!")
            except Exception as e:
                print(f"    ❌ 加载失败: {e}")
                import traceback
                traceback.print_exc()
                
        print(f"\n成功加载 {len(models)}/{len(MAIN_ENSEMBLE_CONFIG)} 个主集成模型")
        return models

    def _preload_subclass_models(self):
        subclass_models = {}
        conn = self._get_db_connection()
        if not conn: return subclass_models
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT m.class_name, m.model_path, COUNT(s.subclass_id) as subclass_count FROM herb_mainclasses m JOIN herb_subclasses s ON m.id = s.class_id GROUP BY m.id, m.class_name, m.model_path HAVING COUNT(s.subclass_id) > 1")
            for row in cursor:
                class_name = row['class_name'].strip()
                model_path = MODEL_PATH_CONFIG.get(class_name) or (os.path.normpath(row['model_path']) if row['model_path'] else None)
                if not model_path: continue
                model = self._load_single_subclass_model(class_name, model_path, row['subclass_count'])
                if model: subclass_models[class_name] = model
        finally:
            if conn and conn.is_connected(): conn.close()
        return subclass_models

    def _load_single_subclass_model(self, class_name, model_path, subclass_count):
        try:
            model_type_str = MODEL_TYPE_CONFIG.get(class_name, MODEL_TYPE_CONFIG["default"])
            ModelClass = MODEL_REGISTRY[model_type_str]
            model = ModelClass(num_classes=subclass_count).to(self.device)
            # 修改：加载完整检查点，而不仅限于权重
            checkpoint = torch.load(model_path, map_location=self.device, weights_only=False)
            # 检查是否是包含完整训练状态的检查点
            if 'model' in checkpoint:
                state_dict = checkpoint['model']
            else:
                state_dict = checkpoint
            model.load_state_dict(OrderedDict((k.replace("module.", ""), v) for k, v in state_dict.items()), strict=True)
            model.eval()
            return model
        except Exception as e:
            print(f"加载子模型 '{class_name}' 权重失败: {e}，将尝试使用strict=False模式加载")
            try:
                # 第二次尝试：使用strict=False，忽略不匹配的键
                checkpoint = torch.load(model_path, map_location=self.device, weights_only=False)
                if 'model' in checkpoint:
                    state_dict = checkpoint['model']
                else:
                    state_dict = checkpoint
                model.load_state_dict(OrderedDict((k.replace("module.", ""), v) for k, v in state_dict.items()), strict=False)
                model.eval()
                return model
            except Exception as e2:
                print(f"第二次尝试也失败: {e2}"); return None

    def _get_db_connection(self):
        try:
            return self.connection_pool.get_connection() if self.connection_pool else mysql.connector.connect(**self.db_config)
        except Exception as e:
            print(f"获取数据库连接失败: {str(e)}"); return None

    def clean_for_json(self, data):
        if isinstance(data, dict): return {k: self.clean_for_json(v) for k, v in data.items()}
        if isinstance(data, list): return [self.clean_for_json(elem) for elem in data]
        if isinstance(data, (datetime.datetime, datetime.date)): return data.isoformat()
        return data
        
    def _get_final_result_after_main(self, main_result, original_img):
        # 此函数的主体逻辑保持不变，它依赖于 `main_result` 中的 `averaged_probs`
        # 我们的修改已经提升了 `averaged_probs` 的质量，所以此处的逻辑将自动受益

        # REJECT 情况处理
        if main_result['decision'] == 'REJECT':
            k = min(5, NUM_KNOWN_CLASSES)
            # 使用更可靠的加权平均概率来决定"更多可能"
            topk_confidences, topk_indices = torch.topk(main_result['averaged_probs'], k)
            details = []
            conn = self._get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor(dictionary=True)
                    for idx, confidence in zip(topk_indices.tolist(), topk_confidences.tolist()):
                        cursor.execute("SELECT class_name, id FROM herb_mainclasses WHERE id = %s", (idx + 1,))
                        res = cursor.fetchone()
                        if res:
                            cursor.execute("SELECT * FROM herb_standard WHERE subclass_id IN (SELECT id FROM herb_subclasses WHERE class_id = %s) LIMIT 1", (res['id'],))
                            standard_result = cursor.fetchone()
                            standard_info = {k: v for k, v in standard_result.items() if k not in ['id', 'class_id', 'subclass_id', 'created_at', 'updated_at']} if standard_result else {}
                            details.append({
                                "id": standard_result.get('subclass_id', -1) if standard_result else -1,
                                "chineseName": standard_result.get('subclass_name', res['class_name']) if standard_result else res['class_name'],
                                "latinName": standard_info.get('latin_name', ''),
                                "confidence": round(float(confidence), 4),
                                "source": standard_info
                            })
                finally:
                    if conn.is_connected(): conn.close()
            
            return self.clean_for_json({
                "id": -1, "chineseName": "未知类别", "latinName": "Unknown",
                "source": {"description": "该图像可能不属于系统定义的已知类别，或图像质量较低，模型无法给出高置信度判断。"},
                "confidence": main_result['confidence'], "is_known": False,
                "more": details
            })
        
        # ACCEPT 情况处理
        averaged_probs = main_result['averaged_probs']
        k = min(5, NUM_KNOWN_CLASSES)
        topk_confidences, topk_indices = torch.topk(averaged_probs, k)

        main_predicted_indices = topk_indices.tolist()
        main_confidences = topk_confidences.tolist()

        conn = self._get_db_connection()
        if not conn: return {"error": "无法连接数据库"}

        try:
            cursor = conn.cursor(dictionary=True)
            results = []
            
            for predicted_index, main_confidence in zip(main_predicted_indices, main_confidences):
                predicted_index_db = predicted_index + 1 # 数据库ID从1开始
                main_confidence = round(float(main_confidence), 4)
                if main_confidence == 0: continue

                cursor.execute("SELECT class_name, id FROM herb_mainclasses WHERE id = %s", (predicted_index_db,))
                result = cursor.fetchone()
                if not result: continue

                class_name = result['class_name'].strip()
                class_id = result['id']

                cursor.execute("SELECT COUNT(*) as subclass_count FROM herb_subclasses WHERE class_id = %s", (class_id,))
                subclass_count = cursor.fetchone()['subclass_count']

                if subclass_count <= 1:
                    sql = "SELECT hst.*, hs.id FROM herb_subclasses hs LEFT JOIN herb_standard hst ON hs.id = hst.subclass_id WHERE hs.class_id = %s ORDER BY hst.priority DESC LIMIT 1"
                    cursor.execute(sql, (class_id,))
                    subclass_result = cursor.fetchone()
                    if subclass_result:
                        standard_info = {k: v for k, v in subclass_result.items() if k not in ['id', 'subclass_id', 'subclass_name', 'latin_name', 'created_at', 'updated_at']}
                        results.append({"id": subclass_result['id'], "chineseName": subclass_result['subclass_name'], "latinName": subclass_result['latin_name'], "source": standard_info, 'confidence': main_confidence})
                else:
                    subclass_model = self.subclass_models.get(class_name)
                    if not subclass_model: continue
                    
                    if class_name in RESIZE_CROP_CLASSES:
                        transform_subclass = self.subclass_transforms['resize_center_crop']
                    elif class_name in HIGH_RESOLUTION_CLASSES: 
                        transform_subclass = self.subclass_transforms['high_resolution']
                    elif class_name == '沙苑子类': 
                        transform_subclass = self.subclass_transforms['shayuanzi']
                    elif class_name in PAFPN_CLASSES: 
                        transform_subclass = self.subclass_transforms['pafpn']
                    else: 
                        transform_subclass = self.subclass_transforms['default']

                    if class_name in SEGMENTATION_CLASSES:
                        from segmentation import segment_single_image
                        try:
                            segmented_img = segment_single_image(original_img)
                            img_sub = transform_subclass(Image.fromarray(cv2.cvtColor(segmented_img, cv2.COLOR_BGR2RGB)))
                        except Exception as e:
                            print(f"分割处理出错: {e}, 使用原始图像"); img_sub = transform_subclass(original_img)
                    else:
                        img_sub = transform_subclass(original_img)
                    
                    img_sub = img_sub.unsqueeze(0).to(self.device, non_blocking=True)
                    with torch.no_grad(), torch.amp.autocast(self.device.type, enabled=self.use_autocast):
                        subclass_output = subclass_model(img_sub)
                        subclass_probabilities = F.softmax(subclass_output.float(), dim=1)
                        k_sub = min(5, subclass_probabilities.shape[1])
                        subclass_confidences, subclass_predicted = torch.topk(subclass_probabilities, k_sub, dim=1)

                    for sub_idx, sub_conf in zip(subclass_predicted[0].tolist(), subclass_confidences[0].tolist()):
                        sub_conf = round(float(sub_conf), 4)
                        if sub_conf == 0: continue
                        final_confidence = round(main_confidence * sub_conf, 4)
                        if final_confidence > 0:
                            sql = "SELECT hst.*, hs.id FROM herb_subclasses hs LEFT JOIN herb_standard hst ON hs.id = hst.subclass_id WHERE hs.class_id = %s AND hs.subclass_id = %s ORDER BY hst.priority DESC LIMIT 1"
                            cursor.execute(sql, (class_id, sub_idx))
                            subclass_result = cursor.fetchone()
                            if subclass_result:
                                standard_info = {k: v for k, v in subclass_result.items() if k not in ['id', 'subclass_id', 'subclass_name', 'latin_name', 'created_at', 'updated_at']}
                                results.append({"id": subclass_result['id'], "chineseName": subclass_result['subclass_name'], "latinName": subclass_result['latin_name'], "source": standard_info, 'confidence': final_confidence})
            
            if not results: return {"error": "没有找到匹配的结果"}
            results.sort(key=lambda x: x['confidence'], reverse=True)
            
            final_result = results[0]
            if len(results) > 1:
                final_result["more"] = results[1:5]
            
            final_result["is_known"] = True
            return self.clean_for_json(final_result)
        except Exception as e:
            print(f"预测过程出错: {e}"); traceback.print_exc()
            return {"error": "预测过程中发生数据库查询或处理错误"}
        finally:
            if conn and conn.is_connected(): conn.close()

    def predict(self, image_path):
        try:
            original_img = Image.open(image_path).convert("RGB")
        except Exception as e:
            return {"error": f"图片加载失败: {e}"}

        main_result = self.predict_batch_main_ensemble([image_path])[0]
        if "error" in main_result:
            return main_result

        return self._get_final_result_after_main(main_result, original_img)

    def predict_batch_main_ensemble(self, image_paths: list):
        if not image_paths: return []
        batch_images_dict = defaultdict(list)
        try:
            for path in image_paths:
                img = Image.open(path).convert("RGB")
                for t_type, transform_func in self.transforms_dict.items():
                    batch_images_dict[t_type].append(transform_func(img))
            for t_type, tensor_list in batch_images_dict.items():
                batch_images_dict[t_type] = torch.stack(tensor_list, 0).to(self.device, non_blocking=True)
        except Exception as e:
            return [{"error": f"批量预处理失败: {e}"} for _ in image_paths]

        return self._predict_main_class_ensemble_batch(batch_images_dict)

    # ✅✅✅【核心修改】✅✅✅
    # 此函数已从“投票制”修改为“加权制”，与测试脚本中的 'weighting' 策略保持一致。
    def _predict_main_class_ensemble_batch(self, images_dict_batch: dict):
        batch_size = next(iter(images_dict_batch.values())).size(0)
        batch_all_probs = []
        with torch.no_grad(), torch.amp.autocast(self.device.type, enabled=self.use_autocast):
            for model, config in zip(self.main_ensemble_models, MAIN_ENSEMBLE_CONFIG):
                tensor_for_model = images_dict_batch[config['transform_type']]
                outputs = model(tensor_for_model)
                probs = F.softmax(outputs.float(), dim=1)
                batch_all_probs.append(probs)

        results = []
        # 对批次中的每一张图片进行处理
        for i in range(batch_size):
            # 1. 提取当前图片在所有模型下的完整概率向量和置信度
            #    - full_probs_i: [[prob_cls1, prob_cls2,...], [...], ...] (N_models x N_classes)
            #    - confs_i: [max_prob_model1, max_prob_model2, ...] (N_models)
            full_probs_i = [p[i] for p in batch_all_probs]
            confs_i = [torch.max(p, dim=0)[0].item() for p in full_probs_i]
            
            # 2. 计算加权平均概率向量
            sum_weights = sum(confs_i)
            # 使用每个模型的置信度作为权重，对概率向量进行加权求和
            # 如果所有模型置信度都接近于0，则退化为简单平均，以避免除以零
            if sum_weights > 1e-9:
                weighted_avg_probs_i = sum(prob * w for prob, w in zip(full_probs_i, confs_i)) / sum_weights
            else:
                weighted_avg_probs_i = torch.mean(torch.stack(full_probs_i), dim=0)

            # 3. 从加权平均概率中得出最终结论
            #    - final_confidence: 加权后概率向量中的最大值
            #    - final_pred_idx_tensor: 对应的类别索引
            final_confidence_tensor, final_pred_idx_tensor = torch.max(weighted_avg_probs_i, dim=0)
            final_confidence = final_confidence_tensor.item()
            
            # 4. 根据阈值判断是接受还是拒绝
            if final_confidence >= self.open_set_threshold:
                final_decision = "ACCEPT"
                final_pred_idx = final_pred_idx_tensor.item()
            else:
                final_decision = "REJECT"
                final_pred_idx = -1 # 拒绝时，类别索引无意义

            results.append({
                "decision": final_decision,
                "pred_idx": final_pred_idx,
                "confidence": round(final_confidence, 4),
                "averaged_probs": weighted_avg_probs_i # 这个字段对后续处理(包括'more'功能)很重要
            })
            
        return results
