from datetime import datetime
from extensions import db


class HerbSubClass(db.Model):
    __tablename__ = 'herb_subclasses'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 小类id
    # subclass_name = db.Column(db.String(255))  # 小类名称
    subclass_id = db.Column(db.Integer)  #
    class_id = db.Column(db.Integer, db.ForeignKey('herb_mainclasses.id'))  # 大类id
    # latin_name = db.Column(db.String(255))  # 拉丁名
    # medicinal_parts = db.Column(db.String(255))  # 药用部位
    is_true_herb = db.Column(db.Integer)


    # 时间戳（根据需求可选）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    image_url = db.Column(db.String(255))
    # 关系定义（与主类关联）
    main_class = db.relationship('HerbMainClass', backref='sub_classes')

    # standard = db.relationship('HerbStandard', backref='sub_classes')  # 关联小类

    def __init__(self, subclass_name=None, subclass_id=None, class_id=None, latin_name=None, medicinal_parts=None, image_url=None,is_true_herb=None):
        # self.subclass_name = subclass_name
        self.subclass_id = subclass_id
        self.class_id = class_id
        # self.latin_name = latin_name
        # self.medicinal_parts = medicinal_parts
        self.image_url = image_url
        self.is_true_herb = is_true_herb

    def to_dict(self):
        return {
            'id': self.id,
            # 'subclass_name': self.subclass_name,
            'subclass_id': self.subclass_id,
            'class_id': self.class_id,
            # 'latin_name': self.latin_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'main_class_name': self.main_class.class_name if self.main_class else None,  # 关联字段
            # 'medicinal_parts': self.medicinal_parts if self.medicinal_parts else None,
            'image_url': self.image_url,
            'is_true_herb': self.is_true_herb,
        }

    def __repr__(self):
        return f'<HerbSubClass {self.id}: {self.subclass_name} (Class {self.class_id})>'
