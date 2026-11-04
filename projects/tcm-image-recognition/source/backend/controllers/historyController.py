import os
import time
from collections import defaultdict
from datetime import datetime
from flask import request, jsonify
from sqlalchemy import or_, func

from model.HerbStandard import HerbStandard
from model.HerbSubClass import HerbSubClass
from model.History import HistoryData
from model.SysUser import SysUser
from util.file import save_uploaded_file, delete_file
from config.config import Config
from util.database import Database


class HistoryController:
    @staticmethod
    def create_history():
        """创建历史记录"""
        data = request.form

        try:
            # 保存上传文件
            image_name = data['image_name']
            image_url = f"/uploads/{image_name}"
            print(image_url)
            # 创建历史记录
            with Database.session_scope() as session:
                new_history = HistoryData(
                    image_name=image_name,
                    image_path=image_url,
                    confidence=float(data['confidence']),
                    created_by=int(data['createdBy']),
                    subclass_id=data.get('subclassId'),
                )
                session.add(new_history)
                session.flush()  # 获取生成的ID但不提交事务

                return {
                    "code":0,
                    "data": HistoryController._history_to_dict(new_history),
                    "message": "历史记录创建成功"
                }, 200

        except Exception as e:
            return {"code":1,"message": str(e)}, 500

    @staticmethod
    def create_batch_history():
        """批量创建历史记录"""
        data = request.get_json()  # 获取JSON格式的请求数据

        if not data or not isinstance(data, list):
            return {"code": 1, "message": "请求数据必须是JSON数组格式"}, 400

        try:
            results = []
            with Database.session_scope() as session:
                for item in data:
                    # 验证必要字段
                    required_fields = ['image_name', 'filepath',
                                       'subclass_id', 'confidence']
                    if not all(field in item for field in required_fields):
                        results.append({
                            "success": False,
                            "message": f"缺少必要字段，记录: {item.get('image_name', '未知')}",
                            "data": item
                        })
                        continue
                    image_name1 = os.path.basename(item['image_name'])
                    image_url = f"/uploads/{item[image_name1]}"
                    print(image_url)
                    try:
                        # 创建历史记录
                        new_history = HistoryData(
                            image_name=item['image_name'],
                            image_path=image_url,
                            subclass_id=item['subclass_id'],
                            confidence=float(item['confidence']),
                            created_by=int(item['created_by']),
                        )
                        session.add(new_history)
                        session.flush()  # 生成ID但不提交

                        results.append({
                            "success": True,
                            "message": "创建成功",
                            "data": HistoryController._history_to_dict(new_history)
                        })

                    except Exception as e:
                        results.append({
                            "success": False,
                            "message": str(e),
                            "data": item
                        })

                # 只有所有操作都尝试后才会提交事务
                if len([r for r in results if not r['success']])==0:
                    return {
                        "code": 0,
                        "data": results,
                        "message": f"批量操作完成，成功{len([r for r in results if r['success']])}条，失败{len([r for r in results if not r['success']])}条"
                    }, 200
                else:
                    return {
                        "code": 1,
                        "data": results,
                        "message": f"历史记录存储失败，成功{len([r for r in results if r['success']])}条，失败{len([r for r in results if not r['success']])}条"
                    }, 200

        except Exception as e:
            return {"code": 1, "message": f"批量操作发生错误: {str(e)}"}, 500

    @staticmethod
    def get_histories():
        try:
            data = request.get_json(silent=True) or {}
            page_num = max(1, int(data.get('pageNum', 1)))
            page_size = min(max(1, int(data.get('pageSize', 8))), 100)
            search_name = data.get('searchName', '').strip()
            search_time = data.get('searchTime', [])
            
            # 关键新增：获取前端传递的用户身份信息
            user_id = data.get('userId')
            is_admin = data.get('isAdmin', False)

            with Database.session_scope() as session:
                subclass_ids_to_search = []
                if search_name:
                    if search_name == '未知类别':
                        query = session.query(HistoryData).filter(HistoryData.subclass_id.is_(None))
                    else:
                        subquery = session.query(
                            HerbStandard.subclass_id,
                            func.row_number().over(
                                partition_by=HerbStandard.subclass_id,
                                order_by=HerbStandard.priority
                            ).label('row_num')
                        ).filter(HerbStandard.subclass_name.ilike(f'%{search_name}%')).subquery()

                        matching_standards = session.query(subquery.c.subclass_id).filter(subquery.c.row_num == 1).all()
                        subclass_ids_to_search = [std.subclass_id for std in matching_standards]
                        if not subclass_ids_to_search:
                            return {"code": 0, "data": {"pageNum": page_num, "pageSize": page_size, "total": 0, "isLastPage": True, "list": []}, "message": "无匹配数据"}, 200

                base_query = session.query(
                    HistoryData,
                    HerbSubClass.subclass_id,
                    SysUser.nick_name.label('creator_name')
                ).distinct(HistoryData.id).outerjoin(
                    HerbSubClass, HistoryData.subclass_id == HerbSubClass.id
                ).join(
                    SysUser, HistoryData.created_by == SysUser.user_id
                )

                # 关键修复：权限过滤逻辑
                if not is_admin:
                    if not user_id:
                        return {"code": 403, "message": "非管理员用户必须提供用户ID"}, 403
                    base_query = base_query.filter(HistoryData.created_by == user_id)

                if search_name and search_name != '未知类别':
                    base_query = base_query.filter(HistoryData.subclass_id.in_(subclass_ids_to_search))
                elif search_name == '未知类别':
                    base_query = base_query.filter(HistoryData.subclass_id.is_(None))

                if len(search_time) == 2:
                    try:
                        start = datetime.fromisoformat(search_time[0].replace('Z', '+00:00'))
                        end = datetime.fromisoformat(search_time[1].replace('Z', '+00:00'))
                        base_query = base_query.filter(HistoryData.created_at.between(start, end))
                    except (ValueError, AttributeError):
                        return {"code": 400, "message": "时间格式错误"}, 400

                total = base_query.count()

                if (page_num - 1) * page_size >= total:
                    return {"code": 0, "data": {"pageNum": page_num, "pageSize": page_size, "total": total, "isLastPage": True, "list": []}, "message": "无更多数据"}, 200

                records_with_user = base_query.order_by(HistoryData.created_at.desc()) \
                    .offset((page_num - 1) * page_size) \
                    .limit(page_size) \
                    .all()

                subclass_ids = [r.HistoryData.subclass_id for r in records_with_user if r.HistoryData.subclass_id is not None]
                standards_map = {}
                if subclass_ids:
                    subquery = session.query(
                        HerbStandard.subclass_id,
                        func.row_number().over(partition_by=HerbStandard.subclass_id, order_by=HerbStandard.priority).label('row_num'),
                        HerbStandard.subclass_name,
                        HerbStandard.latin_name,
                        HerbStandard.standard_name
                    ).filter(HerbStandard.subclass_id.in_(subclass_ids)).subquery()

                    standards = session.query(subquery).filter(subquery.c.row_num == 1).all()
                    for std in standards:
                        standards_map[std.subclass_id] = {'subclassChineseName': std.subclass_name, 'latinName': std.latin_name, 'standardName': std.standard_name}

                result_list = []
                for record in records_with_user:
                    history_item = record.HistoryData
                    subclass_id = history_item.subclass_id
                    standard_data = standards_map.get(subclass_id, {})
                    
                    is_unknown = subclass_id is None
                    
                    result_list.append({
                        'id': history_item.id,
                        'imageName': history_item.image_name,
                        'imagePath': history_item.image_path,
                        'subclassId': subclass_id,
                        'subclassChineseName': '未知类别' if is_unknown else standard_data.get('subclassChineseName', ''),
                        'latinName': '' if is_unknown else standard_data.get('latinName', ''),
                        'creatorName': record.creator_name,
                        'createdAt': history_item.created_at.isoformat(),
                        'source': [] if is_unknown else [{'standardName': standard_data.get('standardName', '')}],
                        'confidence': history_item.confidence
                    })

                return {
                    "code": 0,
                    "data": {
                        "pageNum": page_num,
                        "pageSize": page_size,
                        "total": total,
                        "isLastPage": (page_num * page_size) >= total,
                        "list": result_list
                    },
                    "message": "查询成功"
                }, 200

        except ValueError as e:
            return {"code": 400, "message": f"参数错误: {str(e)}"}, 400
        except Exception as e:
            logger.error(f"查询历史记录时发生错误: {str(e)}", exc_info=True)
            return {"code": 500, "message": f"服务器错误: {str(e)}"}, 500

    @staticmethod
    def get_history(history_id):
        """获取单个历史记录详情"""
        try:
            with Database.session_scope() as session:
                history = session.query(HistoryData).get(history_id)
                if not history:
                    return {"code":1,"message": "未找到该历史记录"}, 404
                return {"code":0,"data": HistoryController._history_to_dict(history)}, 200
        except Exception as e:
            return {"code":1,"message": str(e)}, 400

    @staticmethod
    def update_history(history_id):
        """更新历史记录信息"""
        data = request.json
        try:
            with Database.session_scope() as session:
                history = session.query(HistoryData).get(history_id)
                if not history:
                    return {"code":404,"message": "未找到该历史记录"}, 404

                # 更新字段
                updatable_fields = [
                    'chineseName', 'latinName', 'standard', 'confidence',
                    'uploadedBy', 'categoryName', 'categoryId', 'subcategoryName'
                ]
                for field in updatable_fields:
                    if field in data:
                        if field in ['confidence', 'categoryId']:
                            setattr(history, field.lower(), float(data[field]) if field == 'confidence' else int(data[field]))
                        else:
                            # 转换字段名到模型属性名 (camelCase to snake_case)
                            model_field = {
                                'chineseName': 'chinese_name',
                                'latinName': 'latin_name',
                                'categoryName': 'category_name',
                                'subcategoryName': 'subcategory_name',
                                'uploadedBy': 'uploaded_by'
                            }.get(field, field.lower())
                            setattr(history, model_field, data[field])

                return {
                    "code":0,
                    "data": HistoryController._history_to_dict(history),
                    "message": "历史记录更新成功"
                }, 200

        except Exception as e:
            return {"code":400,"message": str(e)}, 400

    @staticmethod
    def delete_history(history_id):
        """删除历史记录"""
        try:
            with Database.session_scope() as session:
                history = session.query(HistoryData).get(history_id)
                if not history:
                    return {"code":404,"message": "未找到该历史记录"}, 404

                # 删除物理文件
                delete_file(Config.UPLOAD_FOLDER, history.image_name)

                session.delete(history)
                return {"code":0,"message": "历史记录删除成功"}, 200

        except Exception as e:
            return {"code":400,"message": str(e)}, 400

    @staticmethod
    def _history_to_dict(history):
        """将HistoryData对象转换为字典"""
        return {
            "id": history.id,
            "image_name": history.image_name,
            "image_path": history.image_path,
            "subclassId": history.subclass_id,
            "confidence": history.confidence,
            "createdBy": history.created_by,
            "createdAt": history.created_at.isoformat() if history.created_at else None,
        }
