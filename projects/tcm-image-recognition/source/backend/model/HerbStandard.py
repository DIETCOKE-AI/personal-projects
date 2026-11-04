from datetime import datetime
from extensions import db


class HerbStandard(db.Model):
    __tablename__ = 'herb_standard'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    subclass_id = db.Column(db.Integer, db.ForeignKey('herb_subclasses.id'), nullable=False)  # 关联小类ID
    standard_name = db.Column(db.String(100), nullable=False)  # 标准名称
    characteristics = db.Column(db.Text)  # 性状描述
    description = db.Column(db.Text)  # 详细描述
    origin = db.Column(db.String(255))  # 产地信息
    medicinal_parts = db.Column(db.Text) # 药用部位
    plant_name = db.Column(db.String(255)) # 植物中文名
    plant_e_name = db.Column(db.String(255)) # 植物英文名
    latin_name = db.Column(db.String(255)) # 拉丁名
    priority = db.Column(db.Integer) # 展示优先级
    subclass_name = db.Column(db.String(255)) # 药材名称

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 定义关联关系
    subclass = db.relationship('HerbSubClass', backref='standards')

    def __init__(self, subclass_id, standard_name, characteristics=None,
                 description=None, origin=None, medicinal_parts=None, plant_name=None,plant_e_name=None, latin_name=None,priority=None,subclass_name=None):
        self.subclass_id = subclass_id
        self.standard_name = standard_name
        self.characteristics = characteristics
        self.description = description
        self.origin = origin
        self.medicinal_parts = medicinal_parts
        self.plant_name = plant_name
        self.plant_e_name = plant_e_name
        self.priority = priority
        self.latin_name = latin_name
        self.subclass_name = subclass_name

    def to_dict(self):
        return {
            'id': self.id,
            'subclass_id': self.subclass_id,
            # 'subclass_name': self.subclass.subclass_name if self.subclass else None,
            'main_class_id': self.subclass.class_id if self.subclass else None,
            'main_class_name': self.subclass.main_class.class_name if self.subclass and self.subclass.main_class else None,
            'standard_name': self.standard_name,
            'characteristics': self.characteristics,
            'description': self.description,
            'origin': self.origin,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'medicinal_parts': self.medicinal_parts,
            'plant_name': self.plant_name,
            'plant_e_name': self.plant_e_name,
            'priority': self.priority,
            'latin_name': self.latin_name,
            'subclass_name':self.subclass_name
        }

    def __repr__(self):
        return f'<HerbStandard {self.id}: {self.standard_name}>'
