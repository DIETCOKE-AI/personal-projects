from collections import defaultdict

from flask import request
from sqlalchemy.sql.operators import or_

from model.HerbMainClass import HerbMainClass
from model.HerbStandard import HerbStandard
from model.HerbSubClass import HerbSubClass
from util.database import Database


class HerbController:
    @staticmethod
    def get_herb_all():
        try:
            data = request.get_json(silent=True) or {}
            #print(data)
            page_num = max(1, int(data.get('pageNum', 1)))  # 至少为1
            page_size = min(max(1, int(data.get('pageSize', 8))), 100)  # 限制1~100
            search_name = data.get('searchName', '').strip()

            with Database.session_scope() as session:
                query = session.query(
                    HerbSubClass,
                    HerbMainClass
                ).join(
                    HerbMainClass, HerbSubClass.class_id == HerbMainClass.id
                )

                if search_name:
                    # 应该先建立与HerbStandard的关联
                    query = query.join(HerbStandard, HerbSubClass.id == HerbStandard.subclass_id)
                    #设置标准表和子类表的连接，因为需要将子类当中所有编号相同的都呈现出来
                    query = query.filter(
                        or_(
                            HerbStandard.subclass_name.ilike(f"%{search_name}%"),
                            HerbStandard.plant_name.ilike(f"%{search_name}%")
                        )
                    )
                total = query.count()
                records = query.order_by(HerbSubClass.created_at.desc()).paginate(page=page_num,per_page=page_size)
                # .paginate(page=page_num,per_page=page_size)
                # 关联标准数据
                subclass_ids = [r.HerbSubClass.id for r in records]#生成所有的药材小类列表
                standards_map = defaultdict(list)
                if subclass_ids:
                    standards = session.query(
                        HerbStandard
                    ).filter(HerbStandard.subclass_id.in_(subclass_ids)).all()

                    for std in standards:
                        standards_map[std.subclass_id].append({
                            'standardName': std.standard_name,
                            'standardId': std.subclass_id,
                            'characteristics':std.characteristics,
                            'description': std.description,
                            'origin': std.origin,
                            'created_at': std.created_at,
                            'updated_at': std.updated_at,
                            'id':std.id,
                            'medicinalParts': std.medicinal_parts,
                            'plantName': std.plant_name,
                            'plantEName': std.plant_e_name,
                            'priority': std.priority,
                            'latinName': std.latin_name,
                            'subclassName': std.subclass_name
                        })

                result = [{
                    'id': record.HerbSubClass.id,
                    # 'subclassName':record.HerbSubClass.subclass_name,
                    'classId': record.HerbSubClass.class_id,
                    # 'latinName': record.HerbSubClass.latin_name,
                    # 'medicinalParts': record.HerbSubClass.medicinal_parts,
                    'className': record.HerbMainClass.class_name,
                    'createdAt': record.HerbSubClass.created_at,
                    'source': standards_map.get(record.HerbSubClass.id, []),
                    'imageUrl':record.HerbSubClass.image_url,
                    'isTrueHerb': record.HerbSubClass.is_true_herb,
                } for record in records]

                return {
                    "code": 0,
                    "data": {
                        "pageNum": page_num,
                        "pageSize": page_size,
                        "total": total,
                        "isLastPage": (page_num * page_size) >= total,
                        "list": result
                    },
                    "message": "查询成功"
                }, 200


        except ValueError as e:
            return {"code": 400, "message": f"参数错误: {str(e)}"}, 400

    @staticmethod
    def get_herb_one():
        """根据ID获取单个药材的详细信息（包含关联标准数据）"""
        try:
            # 获取参数
            data = request.get_json(silent=True) or {}
            subclass_id = data.get('id')
            if subclass_id is None:
                return {"code": 400, "message": "参数错误：必须传入id参数"}, 400
            subclass_id = int(subclass_id)

            with Database.session_scope() as session:
                # 查询主数据（药材小类+大类信息）
                record = session.query(
                    HerbSubClass,
                    HerbMainClass
                ).join(
                    HerbMainClass, HerbSubClass.class_id == HerbMainClass.id
                ).filter(
                    HerbSubClass.id == subclass_id
                ).first()

                if not record:
                    return {"code": 404, "message": "未找到该药材"}, 404

                # 查询关联的标准数据
                standards = session.query(
                    HerbStandard
                ).filter(
                    HerbStandard.subclass_id == subclass_id
                ).all()

                # 构造标准数据列表
                standards_list = [{
                    'standardName': std.standard_name,
                    'standardId': std.id,
                    'characteristics': std.characteristics,
                    'description': std.description,
                    'origin': std.origin,
                    'createdAt': std.created_at.isoformat() if std.created_at else None,
                    'updatedAt': std.updated_at.isoformat() if std.updated_at else None,
                    'medicinalParts': std.medicinal_parts,
                    'plantName': std.plant_name,
                    'plantEName': std.plant_e_name,
                    'priority': std.priority,
                    'latinName': std.latin_name,
                    'subclassName':std.subclass_name
                } for std in standards]

                # 构造响应数据
                result = {
                    'id': record.HerbSubClass.id,
                    # 'subclassName': record.HerbSubClass.subclass_name,
                    'classId': record.HerbSubClass.class_id,
                    # 'latinName': record.HerbSubClass.latin_name,
                    # 'medicinalParts': record.HerbSubClass.medicinal_parts,
                    'className': record.HerbMainClass.class_name,
                    'createdAt': record.HerbSubClass.created_at.isoformat() if record.HerbSubClass.created_at else None,
                    'source': standards_list,  # 所有关联标准数据
                    'imageUrl': record.HerbSubClass.image_url,
                    'isTrueHerb': record.HerbSubClass.is_true_herb,
                    # 可以继续添加其他需要的字段
                }

                return {
                    "code": 0,
                    "data": result,
                    "message": "查询成功"
                }, 200

        except ValueError:
            return {"code": 400, "message": "参数错误：id必须为整数"}, 400
        except Exception as e:
            print(f"查询药材详情失败: {str(e)}")
            return {"code": 500, "message": "服务器内部错误"}, 500
###实现查询所有的大类
    @staticmethod
    def get_herb_classes():
        """获取所有药材大类"""
        try:
            with Database.session_scope() as session:
                # 查询所有大类
                classes = session.query(
                    HerbMainClass
                ).all()
                # 构造响应数据
                result = [{
                    ##'id': cls.id,
                    'className': cls.class_name##目前只需要返回药材的类别即可
                    # 可以继续添加其他需要的字段
                } for cls in classes]
                print(result)
                return {
                    "code": 0,
                    "data": result,
                    "message": "查询成功"
                },200
                ##查找失败
        except Exception as e:
            print(f"查询药材大类失败: {str(e)}")
            return {"code": 500, "message": "服务器内部错误"}, 500
